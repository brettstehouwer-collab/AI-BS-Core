"""Inert, owner-scoped FE capture foundation; importing does not open storage."""
import asyncio
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from security.firebase_auth import get_admin_principal

router = APIRouter(prefix='/api/v1/fe-express/driver-records', tags=['Owned FE records'])
MAX_REQUEST = 128 * 1024
MAX_ATTACHMENT = 10 * 1024 * 1024
TIME_FIELDS = set('pickup_appointment delivery_appointment pickup_arrival pickup_departure delivery_arrival delivery_departure'.split())
FIELDS = TIME_FIELDS | set('load_ref pickup_address delivery_address notes delays pay_issues expenses dispatch_text'.split())


def database_path():
    return Path(__file__).resolve().parents[1] / 'saved_data' / 'fe_express_driver_records.sqlite3'


async def require_owner(request: Request, response: Response):
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Vary'] = 'Authorization, X-Admin-Key, X-Api-Key'
    owner = await asyncio.to_thread(get_admin_principal,
        request.headers.get('x-admin-key') or request.headers.get('x-api-key', ''),
        request.headers.get('authorization', ''))
    if not owner:
        raise HTTPException(403, 'Verified administrator ownership required', headers={'Cache-Control': 'private, no-store'})
    return owner


@contextmanager
def connection(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS loads(owner TEXT, load_id TEXT, revision INTEGER NOT NULL,
                payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(owner,load_id));
            CREATE TABLE IF NOT EXISTS operations(owner TEXT, op_id TEXT, fingerprint TEXT NOT NULL,
                result TEXT NOT NULL, PRIMARY KEY(owner,op_id));
            CREATE TABLE IF NOT EXISTS attachments(owner TEXT, load_id TEXT, attachment_id TEXT,
                sha256 TEXT NOT NULL, size INTEGER NOT NULL, media_type TEXT NOT NULL,
                content BLOB NOT NULL, PRIMARY KEY(owner,load_id,attachment_id));
        ''')
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
        raise HTTPException(422, 'Invalid identifier')
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) - FIELDS:
        raise HTTPException(422, 'Unknown load fields')
    for key, value in payload.items():
        if not isinstance(value, str) or len(value) > 16000:
            raise HTTPException(422, 'Load fields must be bounded original strings')
        if key in TIME_FIELDS and value:
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value):
                    raise ValueError()
                stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if stamp.utcoffset() is None:
                    raise ValueError()
            except ValueError:
                raise HTTPException(422, 'Event times require a valid ISO timestamp with offset')


def retry(db, owner, op_id, fingerprint):
    row = db.execute('SELECT fingerprint,result FROM operations WHERE owner=? AND op_id=?', (owner, op_id)).fetchone()
    if row:
        if row['fingerprint'] != fingerprint:
            raise HTTPException(409, 'Operation ID already used with different content')
        return json.loads(row['result'])


def remember(db, owner, op_id, fingerprint, result):
    db.execute('INSERT INTO operations VALUES(?,?,?,?)', (owner, op_id, fingerprint, canonical(result)))
    return result


async def bounded_body(request, limit):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > limit:
            raise HTTPException(413, 'Capture exceeds size limit')
        raw.extend(chunk)
    return bytes(raw)


@router.get('/identity')
def identity(owner=Depends(require_owner)):
    return {'owner': owner, 'scope': 'driver_work'}


@router.get('/loads')
def list_loads(owner=Depends(require_owner), path=Depends(database_path)):
    with connection(path) as db:
        loads = []
        for row in db.execute('SELECT * FROM loads WHERE owner=? ORDER BY load_id', (owner,)):
            record = {key: row[key] for key in ('load_id', 'revision', 'updated_at')}
            record['payload'] = json.loads(row['payload'])
            record['attachments'] = [dict(item) for item in db.execute('SELECT attachment_id,sha256,size,media_type FROM attachments WHERE owner=? AND load_id=? ORDER BY attachment_id', (owner, row['load_id']))]
            loads.append(record)
        return {'loads': loads}


@router.post('/sync')
async def sync(request: Request, owner=Depends(require_owner), path=Depends(database_path)):
    try:
        operation = json.loads(await bounded_body(request, MAX_REQUEST))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, 'Invalid JSON')
    if not isinstance(operation, dict) or set(operation) - {'action', 'op_id', 'load_id', 'base_revision', 'payload'} or operation.get('action', 'upsert') != 'upsert':
        raise HTTPException(422, 'Invalid load operation')
    op_id, load_id = identifier(operation.get('op_id')), identifier(operation.get('load_id'))
    revision, payload = operation.get('base_revision'), operation.get('payload')
    if type(revision) is not int or revision < 0:
        raise HTTPException(422, 'Invalid base revision')
    validate_payload(payload)
    return await asyncio.to_thread(store_load, path, owner, op_id, load_id, revision, payload, operation)


def store_load(path, owner, op_id, load_id, revision, payload, operation):
    """Run hashing and the complete disk transaction outside the ASGI loop."""
    fingerprint = hashlib.sha256(canonical(operation).encode()).hexdigest()
    with connection(path) as db:
        previous = retry(db, owner, op_id, fingerprint)
        if previous is not None:
            return previous
        row = db.execute('SELECT revision FROM loads WHERE owner=? AND load_id=?', (owner, load_id)).fetchone()
        current = row['revision'] if row else 0
        if revision != current:
            raise HTTPException(409, {'message': 'Revision conflict', 'current_revision': current})
        result = dict(load_id=load_id, revision=current + 1, payload=payload, updated_at=datetime.now(timezone.utc).isoformat())
        db.execute('INSERT INTO loads VALUES(?,?,?,?,?) ON CONFLICT(owner,load_id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at', (owner, load_id, result['revision'], canonical(payload), result['updated_at']))
        return remember(db, owner, op_id, fingerprint, result)


@router.post('/loads/{load_id}/attachments')
async def upload(load_id: str, request: Request, owner=Depends(require_owner), path=Depends(database_path)):
    identifier(load_id)
    op_id = identifier(request.headers.get('x-operation-id'))
    media_type = request.headers.get('content-type', '').lower()
    if media_type not in {'application/pdf', 'image/jpeg', 'image/png', 'application/octet-stream',
                          'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav',
                          'audio/webm;codecs=opus', 'audio/ogg;codecs=opus'}:
        raise HTTPException(422, 'Unsupported evidence media type')
    content = await bounded_body(request, MAX_ATTACHMENT)
    if not content:
        raise HTTPException(422, 'Evidence is empty')
    return await asyncio.to_thread(store_attachment, path, owner, op_id, load_id, media_type, content)


def store_attachment(path, owner, op_id, load_id, media_type, content):
    """Preserve evidence in one worker-owned transaction."""
    digest = hashlib.sha256(content).hexdigest()
    fingerprint = hashlib.sha256(canonical(['attachment', load_id, media_type, digest]).encode()).hexdigest()
    with connection(path) as db:
        previous = retry(db, owner, op_id, fingerprint)
        if previous is not None:
            return previous
        if not db.execute('SELECT 1 FROM loads WHERE owner=? AND load_id=?', (owner, load_id)).fetchone():
            raise HTTPException(404, 'Load not found')
        count, size = db.execute('SELECT COUNT(*),COALESCE(SUM(size),0) FROM attachments WHERE owner=? AND load_id=?', (owner, load_id)).fetchone()
        if count >= 20 or size + len(content) > 50 * 1024 * 1024:
            raise HTTPException(413, 'Load evidence limit reached')
        result = dict(attachment_id=op_id, sha256=digest, size=len(content), media_type=media_type)
        db.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?,?)', (owner, load_id, op_id, digest, len(content), media_type, content))
        return remember(db, owner, op_id, fingerprint, result)


@router.get('/loads/{load_id}/attachments/{attachment_id}')
def download(load_id: str, attachment_id: str, owner=Depends(require_owner), path=Depends(database_path)):
    identifier(load_id)
    identifier(attachment_id)
    with connection(path) as db:
        row = db.execute('SELECT * FROM attachments WHERE owner=? AND load_id=? AND attachment_id=?', (owner, load_id, attachment_id)).fetchone()
        if not row:
            raise HTTPException(404, 'Evidence not found')
        return Response(row['content'], media_type=row['media_type'], headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Content-Disposition': 'attachment', 'ETag': '"' + row['sha256'] + '"'})
