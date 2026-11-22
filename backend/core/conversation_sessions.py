"""Owner-scoped immutable conversation revisions in the existing SQLite vault.

No initialization on import, deletions, global search insertion, embeddings or
model training. Callers supply an authenticated server-derived owner.
"""
import hashlib
import json
from pathlib import Path
import re
import sqlite3

MAX_BYTES = 16 * 1024 * 1024
MAX_REVISION = 2**53 - 1


class ConversationConflict(ValueError):
    pass


class ConversationNotFound(LookupError):
    pass


class ConversationEvidenceError(RuntimeError):
    pass


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{32}', value):
        raise ValueError('Identifiers must contain 32 lowercase hexadecimal characters')
    return value


def _owner(value):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError('Verified conversation owner is required')


def _revision(value, *, minimum=0):
    if type(value) is not int or not minimum <= value <= MAX_REVISION:
        raise ValueError('Revision must be a bounded nonnegative integer')


def _payload(messages, title):
    if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
        raise ValueError('A nonempty list of message objects is required')
    identifiers = [_identifier(m.get('id')) for m in messages]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('Message identifiers must be unique in a revision')
    if not isinstance(title, str) or len(title) > 2000:
        raise ValueError('Conversation title is invalid')
    try:
        raw = json.dumps({'messages': messages, 'title': title}, sort_keys=True,
                         separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        encoded = raw.encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        raise ValueError('Conversation must contain valid finite UTF-8 JSON') from None
    if len(encoded) > MAX_BYTES:
        raise ValueError('Conversation exceeds 16 MiB; nothing was truncated')
    return raw, hashlib.sha256(encoded).hexdigest()


def _open(db_path, *, write=False):
    connection = sqlite3.connect(Path(db_path).resolve().as_uri() + ('?mode=rw' if write else '?mode=ro'),
                                 uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA synchronous=FULL' if write else 'PRAGMA query_only=ON')
        columns = {r[1] for r in connection.execute('PRAGMA table_info(vault_items)')}
        if not {'id', 'title', 'content', 'collection', 'tags'}.issubset(columns):
            raise ConversationEvidenceError('Existing vault schema is unavailable')
    except BaseException:
        connection.close()
        raise
    return connection


def _schema(connection, *, create=False):
    names = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('conversation_heads','conversation_revisions')")}
    if names and len(names) != 2:
        raise ConversationEvidenceError('Conversation schema is incomplete')
    if not names and not create:
        return False
    if not names:
        connection.execute('''CREATE TABLE conversation_heads (
            owner TEXT NOT NULL, conversation_id TEXT NOT NULL, revision INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(owner,conversation_id))''')
        connection.execute('''CREATE TABLE conversation_revisions (
            owner TEXT NOT NULL, conversation_id TEXT NOT NULL, revision INTEGER NOT NULL,
            request_id TEXT NOT NULL, expected_revision INTEGER NOT NULL,
            payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL, message_count INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(owner,conversation_id,revision), UNIQUE(owner,conversation_id,request_id),
            FOREIGN KEY(owner,conversation_id) REFERENCES conversation_heads(owner,conversation_id))''')
    return True


def _load(connection, owner, conversation_id, revision=None):
    head = connection.execute('SELECT revision FROM conversation_heads WHERE owner=? AND conversation_id=?',
                              (owner, conversation_id)).fetchone()
    if head is None:
        raise ConversationNotFound('Conversation not found')
    if type(head['revision']) is not int or not 1 <= head['revision'] <= MAX_REVISION:
        raise ConversationEvidenceError('Conversation head is invalid')
    target = head['revision'] if revision is None else revision
    if target > head['revision']:
        raise ConversationNotFound('Conversation revision not found')
    row = connection.execute('SELECT * FROM conversation_revisions WHERE owner=? AND conversation_id=? AND revision=?',
                             (owner, conversation_id, target)).fetchone()
    if row is None:
        raise ConversationEvidenceError('Recorded conversation revision is missing')
    try:
        payload = json.loads(row['payload_json'])
        raw, digest = _payload(payload['messages'], payload['title'])
        _identifier(row['request_id'])
        if (raw != row['payload_json'] or digest != row['payload_sha256']
                or row['message_count'] != len(payload['messages']) or row['expected_revision'] != target-1):
            raise ValueError('Revision evidence mismatch')
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ConversationEvidenceError('Recorded conversation evidence is inconsistent') from None
    receipt = {'conversation_id': conversation_id, 'request_id': row['request_id'],
               'revision': target, 'expected_revision': row['expected_revision'],
               'payload_sha256': digest, 'message_count': row['message_count'],
               'storage': 'sqlite_vault', 'durable': True}
    return {'conversation_id': conversation_id, 'revision': target,
            'messages': payload['messages'], 'title': payload['title'],
            'updated_at': row['created_at'], 'receipt': receipt}


def read_conversation(db_path, owner, conversation_id, *, revision=None):
    _owner(owner)
    _identifier(conversation_id)
    if revision is not None:
        _revision(revision, minimum=1)
    connection = _open(db_path)
    try:
        connection.execute('BEGIN')
        if not _schema(connection):
            raise ConversationNotFound('Conversation not found')
        return _load(connection, owner, conversation_id, revision)
    finally:
        connection.close()


def _confirm_revision(db_path, owner, conversation_id, revision, request_id, digest):
    result = read_conversation(db_path, owner, conversation_id, revision=revision)
    receipt = result['receipt']
    if receipt['request_id'] != request_id or receipt['payload_sha256'] != digest:
        raise ConversationEvidenceError('Committed conversation receipt does not match')
    return receipt


def save_conversation(db_path, owner, conversation_id, *, request_id, expected_revision, messages, title='Chat'):
    _owner(owner)
    _identifier(conversation_id)
    _identifier(request_id)
    _revision(expected_revision)
    if expected_revision == MAX_REVISION:
        raise ValueError('Conversation revision limit reached')
    raw, digest = _payload(messages, title)
    connection = _open(db_path, write=True)
    try:
        connection.execute('BEGIN IMMEDIATE')
        _schema(connection, create=True)
        previous = connection.execute('''SELECT revision,expected_revision,payload_json,payload_sha256
            FROM conversation_revisions WHERE owner=? AND conversation_id=? AND request_id=?''',
                                      (owner, conversation_id, request_id)).fetchone()
        if previous:
            if (previous['expected_revision'] != expected_revision or previous['payload_json'] != raw
                    or previous['payload_sha256'] != digest):
                raise ConversationConflict('Request ID already belongs to different revision inputs')
            revision = previous['revision']
        else:
            head = connection.execute('SELECT revision FROM conversation_heads WHERE owner=? AND conversation_id=?',
                                      (owner, conversation_id)).fetchone()
            current = head['revision'] if head else 0
            if head is not None:
                _load(connection, owner, conversation_id)
            if current != expected_revision:
                raise ConversationConflict('Conversation changed; load the current revision before saving')
            revision = current + 1
            if head:
                connection.execute('''UPDATE conversation_heads SET revision=?,updated_at=CURRENT_TIMESTAMP
                    WHERE owner=? AND conversation_id=?''', (revision, owner, conversation_id))
            else:
                connection.execute('INSERT INTO conversation_heads(owner,conversation_id,revision) VALUES(?,?,?)',
                                   (owner, conversation_id, revision))
            connection.execute('''INSERT INTO conversation_revisions
                (owner,conversation_id,revision,request_id,expected_revision,payload_json,payload_sha256,message_count)
                VALUES(?,?,?,?,?,?,?,?)''',
                               (owner, conversation_id, revision, request_id, expected_revision, raw, digest, len(messages)))
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
    return _confirm_revision(db_path, owner, conversation_id, revision, request_id, digest)


def list_conversations(db_path, owner, *, limit=20, before=None):
    _owner(owner)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError('Conversation page size must be 1 through 50')
    if before is not None:
        _identifier(before)
    connection = _open(db_path)
    try:
        connection.execute('BEGIN')
        if not _schema(connection):
            return {'items': [], 'next_cursor': None}
        rows = connection.execute('''SELECT conversation_id FROM conversation_heads WHERE owner=?
            AND conversation_id < ? ORDER BY conversation_id DESC LIMIT ?''',
                                  (owner, before if before is not None else 'g', limit+1)).fetchall()
        items = []
        for row in rows[:limit]:
            result = _load(connection, owner, row['conversation_id'])
            items.append({key: result[key] for key in ('conversation_id', 'revision', 'title', 'updated_at')}
                         | {'message_count': result['receipt']['message_count']})
        return {'items': items, 'next_cursor': items[-1]['conversation_id'] if len(rows)>limit else None}
    finally:
        connection.close()
