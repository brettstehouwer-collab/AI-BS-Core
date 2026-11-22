"""Owner-filtered access to the existing vault, without import-time initialization."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

MAX_BYTES = 16 * 1024 * 1024
QUERY_SECONDS = 0.5
PREVIEW_CHARS = 16000
RESPONSE_CHARS = 256000


class VaultEvidenceError(RuntimeError):
    pass


class VaultRecordNotFound(LookupError):
    pass


def _owner(owner):
    valid = owner == 'local_admin'
    if isinstance(owner, str) and owner.startswith('firebase:'):
        parts = owner.split(':', 2)
        valid = len(parts) == 3 and bool(parts[1]) and bool(parts[2])
    if not valid or not isinstance(owner, str) or len(owner) > 512 or any(ord(c) < 32 or ord(c) == 127 for c in owner):
        raise PermissionError('Verified vault ownership is required.')
    return owner


def _ownership(conn):
    columns = {row[1]: row[2].upper() for row in conn.execute('PRAGMA table_info(vault_items)')}
    if not {'id', 'title', 'content', 'collection', 'tags'}.issubset(columns):
        raise VaultEvidenceError('Existing vault schema is unavailable.')
    present = {'owner', 'is_hidden'} & columns.keys()
    if present and (len(present) != 2 or columns['owner'] != 'TEXT' or columns['is_hidden'] != 'INTEGER'):
        raise VaultEvidenceError('Vault ownership schema is incomplete.')
    return bool(present)


def _ensure_ownership(conn):
    if not _ownership(conn):
        conn.execute('ALTER TABLE vault_items ADD COLUMN owner TEXT')
        conn.execute('ALTER TABLE vault_items ADD COLUMN is_hidden INTEGER NOT NULL DEFAULT 0')
    conn.execute('CREATE INDEX IF NOT EXISTS aibs_vault_owner_v1 ON vault_items(owner,id) WHERE owner IS NOT NULL')


@contextmanager
def _connection(db_path, write=False):
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=FULL' if write else 'PRAGMA query_only=ON')
        _ownership(conn)
        if write:
            conn.execute('BEGIN IMMEDIATE')
        yield conn
    except BaseException:
        if write:
            conn.rollback()
        raise
    finally:
        conn.close()


def _visible(conn, owner, include_legacy=True, include_hidden=False):
    if not _ownership(conn):
        return ('1' if owner == 'local_admin' and include_legacy else '0'), []
    clause = '(owner=? OR owner IS NULL)' if owner == 'local_admin' and include_legacy else 'owner=?'
    args = [owner]
    if not include_hidden:
        clause += ' AND is_hidden=0'
    return clause, args


def _record(row):
    result = dict(row)
    result['ownership_legacy'] = result.get('owner') is None
    result['owner'] = result.get('owner') or 'local_admin'
    result['is_hidden'] = bool(result.get('is_hidden', 0))
    text = result.get('content')
    result['content_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest() if isinstance(text, str) else None
    return result


def _preview(row, start=0, budget=PREVIEW_CHARS):
    result = _record(row)
    text = result.get('content')
    if isinstance(text, str):
        end = min(len(text), start + budget)
        result.update(content=text[start:end], char_start=start, char_end=end,
                      content_characters=len(text), content_truncated=start > 0 or end < len(text))
    tags = result.get('tags')
    if isinstance(tags, str):
        result.update(tags=tags[:1024], tags_truncated=len(tags) > 1024,
                      tags_sha256=hashlib.sha256(tags.encode('utf-8')).hexdigest())
    title = result.get('title')
    if isinstance(title, str) and len(title) > 2000:
        result.update(title=title[:2000], title_truncated=True)
    return result


def _limit(value):
    if type(value) is not int or not 1 <= value <= 50:
        raise ValueError('Vault result limit must be between1 and50.')
    return value


def read_record(db_path, owner, record_id, *, include_hidden=False, include_legacy=True):
    owner = _owner(owner)
    if type(record_id) is not int or record_id < 1:
        raise ValueError('A positive vault record ID is required.')
    with _connection(db_path) as conn:
        clause, args = _visible(conn, owner, include_legacy, include_hidden)
        row = conn.execute('SELECT * FROM vault_items WHERE id=? AND ' + clause, [record_id, *args]).fetchone()
        if row is None:
            raise VaultRecordNotFound('Vault record not found.')
        return _record(row)


def list_records(db_path, owner, *, limit=50, include_legacy=True):
    owner, limit = _owner(owner), _limit(limit)
    with _connection(db_path) as conn:
        clause, args = _visible(conn, owner, include_legacy)
        result, budget = [], RESPONSE_CHARS
        for row in conn.execute('SELECT * FROM vault_items WHERE ' + clause + ' ORDER BY id DESC LIMIT ?', [*args, limit]):
            item = _preview(row, budget=min(PREVIEW_CHARS, budget))
            result.append(item)
            budget -= len(item.get('content') or '')
            if budget <= 0:
                break
        return result


def store_record(db_path, owner, title, content, *, collection='stehouwer_heuristics', tags=None):
    owner = _owner(owner)
    if not isinstance(title, str) or len(title) > 2000 or not isinstance(content, str) or not isinstance(collection, str) or len(collection) > 256:
        raise ValueError('Vault record text metadata is invalid.')
    if tags is None:
        tags = []
    try:
        canonical = json.dumps([owner, title, content, collection, tags], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        tags_text = json.dumps(tags, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, UnicodeError):
        raise ValueError('Vault records require finite UTF-8 JSON.') from None
    if len(canonical) > MAX_BYTES:
        raise ValueError('Vault record exceeds16MiB; nothing was truncated.')
    fingerprint = 'owned_v1:' + hashlib.sha256(canonical).hexdigest()
    with _connection(db_path, write=True) as conn:
        _ensure_ownership(conn)
        columns = {r[1] for r in conn.execute('PRAGMA table_info(vault_items)')}
        if 'item_hash' not in columns:
            raise VaultEvidenceError('Existing vault fingerprint column is unavailable.')
        old = conn.execute('SELECT * FROM vault_items WHERE owner=? AND item_hash=?', (owner, fingerprint)).fetchone()
        if old:
            if any(old[k] != v for k, v in {'title': title, 'content': content, 'collection': collection, 'tags': tags_text}.items()):
                raise VaultEvidenceError('Existing record fingerprint evidence changed.')
            record_id = old['id']
            conn.execute('UPDATE vault_items SET is_hidden=0 WHERE id=? AND owner=?', (record_id, owner))
        else:
            record_id = conn.execute('INSERT INTO vault_items(title,content,collection,tags,item_hash,owner,is_hidden) VALUES(?,?,?,?,?,?,0)',
                                     (title, content, collection, tags_text, fingerprint, owner)).lastrowid
        conn.commit()
    confirmed = read_record(db_path, owner, record_id)
    if any(confirmed.get(k) != v for k, v in {'title': title, 'content': content, 'collection': collection, 'tags': tags_text, 'item_hash': fingerprint}.items()):
        raise VaultEvidenceError('Vault record readback did not match.')
    return confirmed


def hide_record(db_path, owner, record_id):
    owner = _owner(owner)
    original = read_record(db_path, owner, record_id, include_hidden=True)
    with _connection(db_path, write=True) as conn:
        _ensure_ownership(conn)
        clause, args = _visible(conn, owner, include_hidden=True)
        updated = conn.execute('UPDATE vault_items SET owner=COALESCE(owner,?),is_hidden=1 WHERE id=? AND ' + clause,
                               [owner, record_id, *args]).rowcount
        if updated != 1:
            raise VaultRecordNotFound('Vault record not found.')
        conn.commit()
    actual = read_record(db_path, owner, record_id, include_hidden=True)
    if not actual['is_hidden'] or actual.get('content') != original.get('content'):
        raise VaultEvidenceError('Hidden record preservation was not confirmed.')
    return {'id': record_id, 'action': 'hidden_from_active_view', 'preserved': True}


def search_records(db_path, owner, query, *, collection=None, limit=5, include_legacy=True):
    owner, limit = _owner(owner), _limit(limit)
    if not isinstance(query, str) or len(query) > 2000:
        raise ValueError('Vault queries require at most2000characters.')
    tokens = list(dict.fromkeys(w.casefold() for w in re.findall(r'\w+', query, re.UNICODE) if len(w) >= 3))[:8]
    if not tokens:
        return []
    if collection is not None and (not isinstance(collection, str) or len(collection) > 256):
        raise ValueError('Vault collection is invalid.')
    started = time.monotonic()
    with _connection(db_path) as conn:
        conn.set_progress_handler(lambda: int(time.monotonic() - started > QUERY_SECONDS), 10000)
        clause, args = _visible(conn, owner, include_legacy)
        if collection is not None:
            clause += ' AND collection=?'
            args.append(collection)
        matches = []
        for token in tokens:
            escaped = token.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            matches.append("(title LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\')")
            args.extend(['%' + escaped + '%'] * 2)
        clause += ' AND (' + ' OR '.join(matches) + ')'
        result, budget = [], RESPONSE_CHARS
        for row in conn.execute('SELECT * FROM vault_items WHERE ' + clause + ' ORDER BY id DESC LIMIT ?', [*args, limit]):
            if time.monotonic() - started > QUERY_SECONDS:
                raise VaultEvidenceError('Vault query time budget exceeded.')
            text = row['content'] if isinstance(row['content'], str) else ''
            title = row['title'] if isinstance(row['title'], str) else ''
            locations = [match.start() for token in tokens if (match := re.search(re.escape(token), text, re.IGNORECASE))]
            start = max(0, min(locations) - 150) if locations else 0
            item = _preview(row, start=start, budget=min(PREVIEW_CHARS, budget))
            from core.personal_memory_scope import is_sensitive_memory_text
            item.update(score=sum(t in (title + '\n' + text).casefold() for t in tokens) / len(tokens),
                        score_kind='lexical_token_coverage', source='sqlite_vault',
                        sensitive_content=is_sensitive_memory_text(title + '\n' + text + '\n' + str(row['tags'] or '')))
            if time.monotonic() - started > QUERY_SECONDS:
                raise VaultEvidenceError('Vault query time budget exceeded.')
            result.append(item)
            budget -= len(item.get('content') or '')
            if budget <= 0:
                break
        return result


def list_collections(db_path, owner):
    owner = _owner(owner)
    started = time.monotonic()
    with _connection(db_path) as conn:
        conn.set_progress_handler(lambda: int(time.monotonic() - started > QUERY_SECONDS), 10000)
        clause, args = _visible(conn, owner)
        return [r[0] for r in conn.execute('SELECT DISTINCT collection FROM vault_items WHERE ' + clause + ' AND collection IS NOT NULL ORDER BY collection LIMIT 50', args)]
