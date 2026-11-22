"""Immutable original bytes linked to an existing, verified-owner payment.

No filesystem names are used as storage paths and no document is executed,
parsed, rendered or uploaded to a provider. Reads never initialize storage.
"""
import asyncio
from contextlib import closing
import hashlib
import json
import re
import sqlite3
import time
from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response
from security.document_retention import safe_drive_leaf
from security.financial_auth import require_financial_owner

router = APIRouter(prefix='/api/personal-finance/payments', tags=['Personal originals'])
MAX_DOCUMENT = 10 * 1024 * 1024
MAX_PAYMENT_BYTES = 50 * 1024 * 1024
MAX_DOCUMENTS = 20
TABLE = 'personal_payment_originals_v1'
PRIVATE = {'Cache-Control': 'private, no-store', 'Vary': 'Authorization, X-Admin-Key, X-Api-Key'}


def failure(code, detail):
    return HTTPException(code, detail, headers=PRIVATE)


def payment_exists(db, owner, payment_id, kind='personal_payment'):
    if db is None or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounting_owned_records_v1'").fetchone():
        raise failure(404, 'Payment not found')
    if kind not in ('personal_payment', 'personal_filing'):
        raise failure(404, 'Personal record not found')
    if not db.execute('SELECT 1 FROM accounting_owned_records_v1 WHERE owner=? AND id=? AND kind=?',
                      (owner, payment_id, kind)).fetchone():
        raise failure(404, 'Payment not found')


def metadata(row):
    return {key: row[key] for key in ('document_id', 'payment_id', 'filename', 'declared_media_type',
                                     'size', 'sha256', 'created_at')}


def read_documents(owner, payment_id, document_id=None, *, kind='personal_payment'):
    from modules.accounting_router import get_db, has_table
    connection = get_db()
    if connection is None:
        raise failure(404, 'Payment not found')
    with closing(connection) as db:
        payment_exists(db, owner, payment_id, kind)
        if not has_table(db, TABLE):
            if document_id is not None:
                raise failure(404, 'Document not found')
            return []
        if document_id is None:
            return [metadata(row) for row in db.execute(
                f'SELECT document_id,payment_id,filename,declared_media_type,size,sha256,created_at FROM {TABLE} '
                'WHERE owner=? AND payment_id=? ORDER BY created_at,document_id', (owner, payment_id))]
        row = db.execute(f'SELECT * FROM {TABLE} WHERE owner=? AND payment_id=? AND document_id=?',
                         (owner, payment_id, document_id)).fetchone()
        if row is None:
            raise failure(404, 'Document not found')
        raw = row['content']
        if len(raw) != row['size'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise failure(409, 'Original-document integrity requires review')
        return metadata(row), raw


def store_document(owner, payment_id, operation, filename, declared_type, raw, *, kind='personal_payment'):
    from modules.accounting_router import get_db
    # Owner existence is checked read-only before additive schema initialization.
    connection = get_db()
    if connection is None:
        raise failure(404, 'Payment not found')
    with closing(connection) as db:
        payment_exists(db, owner, payment_id, kind)
    digest = hashlib.sha256(raw).hexdigest()
    fingerprint = hashlib.sha256(json.dumps([filename, declared_type, digest],
                                           ensure_ascii=False).encode('utf-8')).hexdigest()
    with closing(get_db(write=True)) as db:
        db.execute('BEGIN IMMEDIATE')
        payment_exists(db, owner, payment_id, kind)
        db.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE}(
            owner TEXT NOT NULL,payment_id INTEGER NOT NULL,document_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,filename TEXT NOT NULL,declared_media_type TEXT NOT NULL,
            size INTEGER NOT NULL,sha256 TEXT NOT NULL,created_at INTEGER NOT NULL,content BLOB NOT NULL,
            PRIMARY KEY(owner,payment_id,document_id))''')
        for action in ('UPDATE', 'DELETE'):
            db.execute(f'''CREATE TRIGGER IF NOT EXISTS personal_original_no_{action.lower()}_v1
                BEFORE {action} ON {TABLE} BEGIN SELECT RAISE(ABORT,'immutable personal original'); END''')
        prior = db.execute(f'SELECT * FROM {TABLE} WHERE owner=? AND payment_id=? AND document_id=?',
                           (owner, payment_id, operation)).fetchone()
        if prior:
            if prior['fingerprint'] != fingerprint:
                raise failure(409, 'Idempotency-Key reused for different original evidence')
            if prior['content'] != raw:
                raise failure(409, 'Original-document integrity requires review')
            db.rollback()
            return metadata(prior)
        count, size = db.execute(f'SELECT COUNT(*),COALESCE(SUM(size),0) FROM {TABLE} WHERE owner=? AND payment_id=?',
                                 (owner, payment_id)).fetchone()
        if count >= MAX_DOCUMENTS or size + len(raw) > MAX_PAYMENT_BYTES:
            raise failure(413, 'Payment evidence limit reached')
        db.execute(f'INSERT INTO {TABLE} VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (owner, payment_id, operation, fingerprint, filename, declared_type, len(raw), digest, int(time.time()), raw))
        row = db.execute(f'SELECT * FROM {TABLE} WHERE owner=? AND payment_id=? AND document_id=?',
                         (owner, payment_id, operation)).fetchone()
        db.commit()
        return metadata(row)


@router.post('/{payment_id}/documents', status_code=201)
async def upload_document(request: Request, payment_id: int = Path(gt=0),
                          owner=Depends(require_financial_owner),
                          operation: str = Header(alias='Idempotency-Key', min_length=1, max_length=128),
                          filename: str = Header(alias='X-Document-Name', min_length=1, max_length=1800),
                          filename_encoding: str | None = Header(default=None, alias='X-Document-Name-Encoding')):
    return await receive_document(request, payment_id, owner, operation, filename, filename_encoding)


async def receive_document(request, payment_id, owner, operation, filename, filename_encoding=None, *, kind='personal_payment'):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', operation):
        raise failure(422, 'Invalid Idempotency-Key')
    if filename_encoding is not None:
        if filename_encoding != 'uri' or re.search(r'%(?![0-9A-Fa-f]{2})', filename):
            raise failure(422, 'Invalid document filename encoding')
        try:
            filename = unquote(filename, encoding='utf-8', errors='strict')
        except UnicodeError:
            raise failure(422, 'Invalid UTF-8 document filename') from None
    if len(filename) > 200:
        raise failure(422, 'Document filename exceeds 200 characters')
    # Validate the exact supplied leaf; never silently rename original evidence.
    if safe_drive_leaf(filename) != filename:
        raise failure(422, 'Supply an exact filename without surrounding whitespace')
    declared = request.headers.get('content-type', 'application/octet-stream')
    if len(declared) > 160 or any(ord(ch) < 32 for ch in declared):
        raise failure(422, 'Invalid declared content type')
    length = request.headers.get('content-length')
    if length is not None:
        if not re.fullmatch(r'[0-9]{1,12}', length):
            raise failure(422, 'Invalid Content-Length')
        if int(length) > MAX_DOCUMENT:
            raise failure(413, 'Original exceeds 10 MiB')
    # Reject unknown/cross-owner payment before reading any document body.
    await asyncio.to_thread(read_documents, owner, payment_id, kind=kind)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_DOCUMENT:
            raise failure(413, 'Original exceeds 10 MiB')
        data.extend(chunk)
    if not data:
        raise failure(422, 'An original document must contain bytes')
    if length is not None and len(data) != int(length):
        raise failure(422, 'Content-Length does not match original bytes')
    value = await asyncio.to_thread(store_document, owner, payment_id, operation, filename, declared, bytes(data), kind=kind)
    return {'status': 'success', 'document': value, 'preservation': 'stored_original_bytes',
            'verification': 'manual_unreconciled', 'content_parsed': False}


@router.get('/{payment_id}/documents')
def list_documents(payment_id: int = Path(gt=0), owner=Depends(require_financial_owner)):
    rows = read_documents(owner, payment_id)
    return {'status': 'success', 'documents': rows, 'count': len(rows), 'verification': 'manual_unreconciled'}


@router.get('/{payment_id}/documents/{document_id}')
def download_document(document_id: str, payment_id: int = Path(gt=0), owner=Depends(require_financial_owner)):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', document_id):
        raise failure(404, 'Document not found')
    info, raw = read_documents(owner, payment_id, document_id)
    return Response(raw, media_type='application/octet-stream', headers={**PRIVATE,
                    'X-Content-Type-Options': 'nosniff', 'X-Content-SHA256': info['sha256'],
                    'Content-Disposition': "attachment; filename*=UTF-8''" + quote(info['filename'], safe='')})
