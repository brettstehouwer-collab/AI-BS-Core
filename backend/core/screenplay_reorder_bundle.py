"""Dormant, recoverable three-file reorder writer; no route or Git activation.

The owning project service must supply an admitted directory and its exclusive
project lock, perform manuscript/workflow CAS, and block ALL other mutations
while this journal is pending. Compose this writer with WorkflowStore.write;
recover this bundle explicitly BEFORE recovering that workflow operation.
Neither SQLite transaction spans the other database or filesystem promotions.
This is local recovery infrastructure, not a cross-process ownership boundary.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

APP_ID = 0x41494252
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_RETAINED_BYTES = 128 * 1024 * 1024
MAX_OPERATIONS = 256


class BundleError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


def _reject(message, status=409):
    raise BundleError(message, status)


def _hash(raw):
    return None if raw is None else hashlib.sha256(raw).hexdigest()


class ReorderBundle:
    def __init__(self, directory, lock):
        self.directory = Path(directory)
        self.lock = lock
        self.path = self.directory / '.writing-reorder.sqlite3'
        self.names = (f'{self.directory.name}.fdx', 'project.json', 'screenplay.fountain')

    def _safe(self, path):
        if self.directory.is_symlink() or (hasattr(self.directory, 'is_junction') and self.directory.is_junction()):
            _reject('Reorder projects cannot be links or junctions.', 400)
        try:
            parts = path.relative_to(self.directory).parts
        except ValueError:
            _reject('Reorder files must stay inside the admitted project.', 400)
        current = self.directory
        for part in parts:
            current = current / part
            if (current.is_symlink() or (hasattr(current, 'is_junction') and current.is_junction())
                    or not current.resolve().is_relative_to(self.directory.resolve())):
                _reject('Reorder files cannot traverse links or leave the project.', 400)
        return path

    def _read(self, name):
        path = self._safe(self.directory / name)
        if not path.exists():
            return None
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            _reject('A reorder member is not a bounded regular file.')
        raw = path.read_bytes()
        self._bytes(raw)
        return raw

    def _bytes(self, raw, missing=False):
        if raw is None and missing:
            return
        if not isinstance(raw, bytes) or len(raw) > MAX_FILE_BYTES:
            _reject('Reorder members require UTF-8 bytes within the 16 MiB file limit.', 400)
        try:
            raw.decode('utf-8')
        except UnicodeError:
            _reject('Reorder cannot normalize or replace invalid UTF-8 originals.', 400)

    def _payloads(self, outputs, expected):
        if (not isinstance(outputs, dict) or not isinstance(expected, dict)
                or set(outputs) != set(self.names) or set(expected) != set(self.names)):
            _reject('Reorder requires exactly the screenplay, project metadata and named FDX.', 400)
        for name in self.names:
            self._bytes(outputs[name])
            self._bytes(expected[name], missing=True)

    @contextmanager
    def _connection(self, create=False):
        for suffix in ('', '-journal', '-wal', '-shm'):
            self._safe(Path(str(self.path) + suffix))
        exists = self.path.exists()
        if not exists and not create:
            yield None
            return
        connection = None
        try:
            connection = (sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, timeout=5)
                          if exists else sqlite3.connect(self.path, timeout=5))
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA synchronous=FULL')
            if not exists:
                connection.executescript('''
                    BEGIN IMMEDIATE;
                    CREATE TABLE operations(id TEXT PRIMARY KEY, status TEXT NOT NULL,
                        digest TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE UNIQUE INDEX one_pending ON operations(status) WHERE status='PREPARED';
                    CREATE TABLE files(operation_id TEXT NOT NULL, name TEXT NOT NULL,
                        position INTEGER NOT NULL, before_content BLOB, after_content BLOB NOT NULL,
                        before_sha TEXT, after_sha TEXT NOT NULL, PRIMARY KEY(operation_id,name));
                ''')
                connection.execute(f'PRAGMA application_id={APP_ID}')
                connection.execute('PRAGMA user_version=1')
                connection.commit()
            if (connection.execute('PRAGMA application_id').fetchone()[0] != APP_ID
                    or connection.execute('PRAGMA user_version').fetchone()[0] != 1
                    or connection.execute('PRAGMA journal_mode').fetchone()[0] != 'delete'
                    or {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} != {'operations', 'files'}):
                _reject('Unrecognized reorder journal; preserve its existing bytes.')
            connection.execute('BEGIN IMMEDIATE')
            yield connection
            connection.commit()
        except sqlite3.Error as error:
            raise BundleError('Reorder journal could not be verified or committed; preserve it for explicit recovery.') from error
        finally:
            if connection is not None:
                connection.close()

    def _digest(self, identity, records):
        entries = [dict(name=row['name'], position=row['position'], before_sha=row['before_sha'],
                        after_sha=row['after_sha'], before_length=None if row['before_content'] is None else len(row['before_content']),
                        after_length=len(row['after_content'])) for row in records]
        return hashlib.sha256(json.dumps(dict(id=identity, files=entries), sort_keys=True,
                                         separators=(',', ':')).encode()).hexdigest()

    def _pending(self, connection):
        if connection is None:
            return None
        rows = connection.execute("SELECT * FROM operations WHERE status='PREPARED'").fetchall()
        if len(rows) > 1:
            _reject('Multiple pending reorder operations require review.')
        return rows[0] if rows else None

    def _record(self, connection, operation):
        identity = operation['id']
        if not isinstance(identity, str) or len(identity) != 32 or any(c not in '0123456789abcdef' for c in identity):
            _reject('Retained reorder identity is invalid.')
        rows = connection.execute('SELECT * FROM files WHERE operation_id=? ORDER BY position', (identity,)).fetchall()
        if len(rows) != len(self.names):
            _reject('Retained reorder file set is incomplete.')
        for index, row in enumerate(rows):
            if row['name'] != self.names[index] or type(row['position']) is not int or row['position'] != index:
                _reject('Retained reorder member identity/order is invalid.')
            self._bytes(row['before_content'], missing=True)
            self._bytes(row['after_content'])
            if row['before_sha'] != _hash(row['before_content']) or row['after_sha'] != _hash(row['after_content']):
                _reject('Retained reorder content failed its hash check.')
        if self._digest(identity, rows) != operation['digest']:
            _reject('Retained reorder manifest failed its integrity check.')
        return rows

    def status(self):
        with self.lock, self._connection() as connection:
            pending = self._pending(connection)
            if pending is None:
                return dict(pending_operation=None)
            rows = self._record(connection, pending)
            return dict(pending_operation=dict(id=pending['id'], status='PREPARED',
                files=[dict(name=row['name'], before_sha=row['before_sha'], after_sha=row['after_sha']) for row in rows]))

    def assert_ready(self):
        if self.status()['pending_operation']:
            _reject('Explicit reorder recovery is required before any project mutation.')

    def _promote(self, name, expected, target, operation):
        path = self._safe(self.directory / name)
        if self._read(name) != expected:
            _reject('A reorder member changed before promotion; preserve the pending journal.')
        if expected == target:
            return
        if target is None:
            # Preserve newly created outputs on explicit abort; never discard them.
            retained = self._safe(self.directory / '.writing-reorder-retained' / operation / name)
            if retained.exists():
                _reject('Retained rollback output already exists; preserve both versions.')
            retained.parent.mkdir(parents=True, exist_ok=True)
            self._safe(retained)
            os.replace(path, retained)
        else:
            # Failed promotion buffers are intentionally retained as evidence.
            with tempfile.NamedTemporaryFile(dir=self.directory, prefix='.reorder-', suffix='.tmp', delete=False) as stream:
                stream.write(target)
                stream.flush()
                os.fsync(stream.fileno())
                temporary = stream.name
            if self._read(name) != expected:
                _reject('A reorder member changed during staging; preserve the staged buffer.')
            os.replace(temporary, path)

    def _complete(self, connection, operation, action):
        rows = self._record(connection, operation)
        # Preflight the entire bundle before touching ANY file, including on restart.
        for row in rows:
            if self._read(row['name']) not in (row['before_content'], row['after_content']):
                _reject('Unrelated edits prevent reorder recovery; preserve every version.')
        sequence = rows if action == 'complete' else list(reversed(rows))
        for row in sequence:
            target = row['after_content'] if action == 'complete' else row['before_content']
            current = self._read(row['name'])
            if current not in (row['before_content'], row['after_content']):
                _reject('A reorder member changed after preflight; retain the pending intent.')
            if current != target:
                self._promote(row['name'], current, target, operation['id'])
        for row in rows:
            target = row['after_content'] if action == 'complete' else row['before_content']
            if self._read(row['name']) != target:
                _reject('Reorder final bytes differ from the retained intent.')
        connection.execute('UPDATE operations SET status=? WHERE id=? AND status=\'PREPARED\'',
                           ('COMPLETED' if action == 'complete' else 'ABORTED', operation['id']))
        return dict(id=operation['id'], status='COMPLETED' if action == 'complete' else 'ABORTED', unchanged=False)

    def apply(self, outputs, expected):
        self._payloads(outputs, expected)
        with self.lock:
            self.assert_ready()
            if any(self._read(name) != expected[name] for name in self.names):
                _reject('Reorder originals changed. Keep the draft and reconcile current files.')
            if outputs == expected:
                return dict(id=None, status='UNCHANGED', unchanged=True)
            with self._connection(create=True) as connection:
                if self._pending(connection):
                    _reject('A reorder operation is already pending.')
                if any(self._read(name) != expected[name] for name in self.names):
                    _reject('Reorder originals changed before journal admission.')
                size = connection.execute('SELECT coalesce(sum(coalesce(length(before_content),0)+length(after_content)),0) FROM files').fetchone()[0]
                additional = sum(len(outputs[name]) + len(expected[name] or b'') for name in self.names)
                if size + additional > MAX_RETAINED_BYTES or connection.execute('SELECT count(*) FROM operations').fetchone()[0] >= MAX_OPERATIONS:
                    _reject('Retained reorder history reached its logical budget; preserve/export it first.')
                identity = uuid.uuid4().hex
                rows = [dict(name=name, position=index, before_content=expected[name], after_content=outputs[name],
                             before_sha=_hash(expected[name]), after_sha=_hash(outputs[name])) for index, name in enumerate(self.names)]
                connection.execute('INSERT INTO operations VALUES(?,?,?,?)',
                    (identity, 'PREPARED', self._digest(identity, rows), datetime.now(timezone.utc).isoformat()))
                for row in rows:
                    connection.execute('INSERT INTO files VALUES(?,?,?,?,?,?,?)',
                        (identity, row['name'], row['position'], row['before_content'], row['after_content'], row['before_sha'], row['after_sha']))
                connection.commit()  # Intent must survive BEFORE the first filesystem replacement.
                connection.execute('BEGIN IMMEDIATE')
                return self._complete(connection, self._pending(connection), 'complete')

    def recover(self, operation_id, action):
        if action not in {'complete', 'abort'}:
            _reject('Reorder recovery requires an explicit complete or abort action.', 400)
        with self.lock, self._connection() as connection:
            pending = self._pending(connection)
            if pending is None or pending['id'] != operation_id:
                _reject('The specified reorder operation is not pending. Reload current status.')
            return self._complete(connection, pending, action)
