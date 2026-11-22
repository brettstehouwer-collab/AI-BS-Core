"""Confirmed, idempotent conversation archives in the existing SQLite vault.

No storage/client initialization on import. Raw archives are not automatically
exported, embedded, promoted to preferences or used for model-weight training.
"""
import hashlib
import json
import re
import uuid
from core.owned_vault import _owner, _connection, _ownership, _ensure_ownership

MAX_ARCHIVE_BYTES = 16 * 1024 * 1024


class ArchiveConflict(ValueError):
    pass


def _transcript(payload):
    lines = ['# ' + payload['session_title'], 'Source: ' + payload['source'], '']
    for message in payload['messages']:
        content = message.get('content', '')
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False)
        lines.extend(['### ' + str(message.get('role', 'user')), content, ''])
    return '\n'.join(lines)


def _storage_id(owner, archive_id):
    return 'owned_v1:' + hashlib.sha256(owner.encode('utf-8')).hexdigest() + ':' + archive_id


def _lookup(connection, owner, archive_id):
    owned = _ownership(connection)
    keys = [_storage_id(owner, archive_id)] + ([archive_id] if owner == 'local_admin' else [])
    for key in keys:
        owner_column = 'v.owner' if owned else 'NULL'
        row = connection.execute('''SELECT r.payload_json,r.payload_sha256,r.message_count,
            r.vault_item_id,v.content,v.title,v.collection,''' + owner_column + ''' AS stored_owner
            FROM chat_archive_receipts r JOIN vault_items v ON v.id=r.vault_item_id
            WHERE r.archive_id=?''', (key,)).fetchone()
        if row is not None and (row['stored_owner'] or 'local_admin') == owner:
            return row
    return None


def _confirm_archive(db_path, archive_id, expected_sha, *, owner=None):
    owner = _owner(owner)
    with _connection(db_path) as connection:
        row = _lookup(connection, owner, archive_id)
        _check_evidence(row, expected_sha)
        return {'archive_id':archive_id, 'payload_sha256':expected_sha, 'owner':owner,
                'message_count':row[2], 'vault_item_id':row[3],
                'storage':'sqlite_vault', 'durable':True}


def _check_evidence(row, expected_sha):
    if not row or row[1] != expected_sha or hashlib.sha256(row[0].encode('utf-8')).hexdigest() != expected_sha:
        raise ValueError('Archive receipt is missing or inconsistent')
    payload = json.loads(row[0])
    if (json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False) != row[0]
            or row[2] != len(payload['messages']) or row[4] != _transcript(payload)
            or row[5] != payload['session_title'] or row[6] != 'stehouwer_conversations'):
        raise ValueError('Archived conversation evidence has changed')


def archive_chat(db_path, messages, *, owner=None, archive_id=None, session_title='Chat Session Archive', source='chat_ui'):
    owner = _owner(owner)
    archive_id = archive_id if archive_id is not None else uuid.uuid4().hex
    if not isinstance(archive_id, str) or not re.fullmatch(r'[a-f0-9]{32}', archive_id):
        raise ValueError('Archive ID must contain 32 lowercase hexadecimal characters')
    if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
        raise ValueError('A nonempty list of message objects is required')
    if not isinstance(session_title, str) or len(session_title) > 2000 or not isinstance(source, str) or len(source) > 256:
        raise ValueError('Archive title or source is invalid')
    payload = {'messages':messages, 'session_title':session_title, 'source':source}
    try:
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError('Archive messages must contain finite JSON values') from None
    encoded = raw.encode('utf-8')
    if len(encoded) > MAX_ARCHIVE_BYTES:
        raise ValueError('Archive exceeds the 16 MiB limit; no messages were truncated or saved')
    digest = hashlib.sha256(encoded).hexdigest()
    transcript = _transcript(payload)
    transcript.encode('utf-8')  # Reject invalid Unicode before any mutation.
    with _connection(db_path, write=True) as connection:
        _ensure_ownership(connection)
        connection.execute('''CREATE TABLE IF NOT EXISTS chat_archive_receipts (
            archive_id TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL,
            message_count INTEGER NOT NULL, vault_item_id INTEGER NOT NULL REFERENCES vault_items(id),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        previous = _lookup(connection, owner, archive_id)
        if previous:
            if (previous['payload_sha256'], previous['payload_json']) != (digest, raw):
                raise ArchiveConflict('Archive ID already belongs to different conversation bytes')
            _check_evidence(previous, digest)
            if previous['stored_owner'] is None:
                connection.execute('UPDATE vault_items SET owner=? WHERE id=? AND owner IS NULL', (owner, previous['vault_item_id']))
        else:
            row = connection.execute('INSERT INTO vault_items(title,content,collection,tags,owner,is_hidden) VALUES(?,?,?,?,?,0)',
                (session_title, transcript, 'stehouwer_conversations', 'chat_archive:' + archive_id, owner))
            connection.execute('''INSERT INTO chat_archive_receipts
                (archive_id,payload_sha256,payload_json,message_count,vault_item_id) VALUES(?,?,?,?,?)''',
                (_storage_id(owner, archive_id),digest,raw,len(messages),row.lastrowid))
        connection.commit()
    return _confirm_archive(db_path, archive_id, digest, owner=owner)
