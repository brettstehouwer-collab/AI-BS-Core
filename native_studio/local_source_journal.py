"""Durable private proposal records; never writes an original source file.

WAL and FULL synchronous commits are checked for this connection. They improve
recovery but cannot guarantee zero loss under every storage/hardware failure.
No connection or schema migration occurs at import or construction time.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

_COLUMNS = ('operation_id', 'source_path', 'source_sha256', 'source_bytes',
            'candidate_sha256', 'candidate_bytes', 'status', 'receipt_json',
            'failure_code', 'created_utc')


class LocalSourceJournal:
    def __init__(self, database=Path('C:/AI-BS/backend/aibs_master.db'), *, create=False):
        self.database = Path(database)
        self.create = create

    @contextmanager
    def _connect(self):
        mode = 'rwc' if self.create else 'rw'
        connection = sqlite3.connect(self.database.absolute().as_uri() + '?mode=' + mode,
                                     uri=True, timeout=2)
        try:
            connection.execute('PRAGMA trusted_schema=OFF')
            if connection.execute('PRAGMA journal_mode=WAL').fetchone()[0].lower() != 'wal':
                raise RuntimeError('SQLite WAL mode is unavailable; no source write is authorized')
            connection.execute('PRAGMA synchronous=FULL')
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('''CREATE TABLE IF NOT EXISTS native_refactor_runs (
                operation_id TEXT PRIMARY KEY, source_path TEXT NOT NULL,
                source_sha256 TEXT NOT NULL, source_bytes BLOB NOT NULL,
                candidate_sha256 TEXT, candidate_bytes BLOB, status TEXT NOT NULL,
                receipt_json TEXT, failure_code TEXT, created_utc TEXT NOT NULL)''')
            columns = tuple(row[1] for row in connection.execute('PRAGMA table_info(native_refactor_runs)'))
            if columns != _COLUMNS:
                raise RuntimeError('Existing native proposal journal schema does not match')
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def begin(self, source_path, original_bytes):
        if type(original_bytes) is not bytes or not 0 < len(original_bytes) <= 32768:
            raise ValueError('A bounded exact source snapshot is required')
        operation = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute('INSERT INTO native_refactor_runs '
                '(operation_id,source_path,source_sha256,source_bytes,status,created_utc) '
                'VALUES (?,?,?,?,?,?)', (operation, str(source_path),
                hashlib.sha256(original_bytes).hexdigest(), original_bytes,
                'STARTED', datetime.now(timezone.utc).isoformat()))
        return operation

    def record_candidate(self, operation, proposal):
        original, candidate = proposal['original_bytes'], proposal['candidate_bytes']
        if type(original) is not bytes or type(candidate) is not bytes or len(candidate) > 1024 * 1024:
            raise ValueError('Invalid proposal byte records')
        receipt = proposal['receipt']
        if not receipt.get('completion_verified') or not receipt.get('generation_verified'):
            raise ValueError('Unverified generation cannot become a ready proposal')
        safe_receipt = {key: receipt.get(key) for key in ('provider', 'model', 'actual_model',
            'endpoint', 'status', 'completion_reason', 'completion_verified', 'generation_verified')}
        with self._connect() as connection:
            row = connection.execute('SELECT source_path,source_sha256,source_bytes,status '
                'FROM native_refactor_runs WHERE operation_id=?', (operation,)).fetchone()
            if (row is None or row[3] != 'STARTED' or row[0] != str(proposal['source_path'])
                    or row[1] != hashlib.sha256(original).hexdigest() or row[2] != original):
                raise ValueError('Source snapshot changed or operation is not writable')
            connection.execute('UPDATE native_refactor_runs SET candidate_sha256=?, '
                'candidate_bytes=?,status=?,receipt_json=? WHERE operation_id=?',
                (hashlib.sha256(candidate).hexdigest(), candidate, 'PROPOSAL_READY',
                 json.dumps(safe_receipt, sort_keys=True), operation))

    def fail(self, operation, code):
        if not isinstance(code, str) or not code.isidentifier() or len(code) > 80:
            raise ValueError('Use a fixed diagnostic error class, not source text')
        with self._connect() as connection:
            connection.execute('UPDATE native_refactor_runs SET status=?,failure_code=? '
                'WHERE operation_id=? AND status=?', ('FAILED', code, operation, 'STARTED'))

    def read(self, operation):
        with self._connect() as connection:
            row = connection.execute('SELECT * FROM native_refactor_runs WHERE operation_id=?',
                                     (operation,)).fetchone()
            return dict(zip(_COLUMNS, row)) if row else None
