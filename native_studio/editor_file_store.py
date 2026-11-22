"""Checkpoint exact editor bytes before an explicit filesystem save.

The existing master database must be available in checked WAL/FULL mode. Every
save first commits original/draft bytes, then checks the current file again and
atomically promotes an owned same-directory temporary file. SQLite serializes
cooperating saves; this is not an OS-global compare-and-swap against arbitrary
external writers and does not promise immunity to storage/power failure.
"""
from __future__ import annotations

from datetime import datetime, timezone
from contextlib import closing
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import uuid

MASTER_DATABASE = Path(r'C:\AI-BS\backend\aibs_master.db')
MAX_SOURCE_BYTES = 16 * 1024 * 1024
_UNSPECIFIED = object()
_COLUMNS = (
    ('operation_id', 'TEXT'), ('target_path', 'TEXT'), ('expected_kind', 'TEXT'),
    ('expected_sha256', 'TEXT'), ('original_bytes', 'BLOB'), ('original_sha256', 'TEXT'),
    ('draft_bytes', 'BLOB'), ('draft_sha256', 'TEXT'), ('staged_path', 'TEXT'),
    ('original_backup_path', 'TEXT'),
    ('phase', 'TEXT'), ('file_written', 'INTEGER'), ('error_code', 'TEXT'),
    ('checkpointed_utc', 'TEXT'), ('finished_utc', 'TEXT'),
)
_SCHEMA = '''CREATE TABLE native_editor_writes (
    operation_id TEXT PRIMARY KEY,
    target_path TEXT NOT NULL,
    expected_kind TEXT NOT NULL CHECK(expected_kind IN ('unconstrained','missing','sha256')),
    expected_sha256 TEXT,
    original_bytes BLOB,
    original_sha256 TEXT,
    draft_bytes BLOB NOT NULL,
    draft_sha256 TEXT NOT NULL,
    staged_path TEXT NOT NULL,
    original_backup_path TEXT,
    phase TEXT NOT NULL CHECK(phase IN ('CHECKPOINTED','WRITTEN','CONFLICT','FAILED')),
    file_written INTEGER NOT NULL DEFAULT 0 CHECK(file_written IN (0,1)),
    error_code TEXT,
    checkpointed_utc TEXT NOT NULL,
    finished_utc TEXT
)'''


class EditorFileStoreError(RuntimeError):
    def __init__(self, code, *, operation_id=None, written=False):
        self.code, self.operation_id, self.written = code, operation_id, written
        super().__init__('Editor save needs attention: ' + code)


class EditorWriteConflict(EditorFileStoreError):
    pass


def _sha(value):
    return None if value is None else hashlib.sha256(value).hexdigest()


def _utc():
    return datetime.now(timezone.utc).isoformat()


def _plain(path, *, missing=False):
    for part in (path, *path.parents):
        try:
            value = part.lstat()
        except FileNotFoundError:
            if missing:
                continue
            raise EditorFileStoreError('path_unavailable') from None
        except OSError:
            raise EditorFileStoreError('path_unavailable') from None
        if stat.S_ISLNK(value.st_mode) or getattr(value, 'st_file_attributes', 0) & 0x400:
            raise EditorFileStoreError('redirected_path')


def _path(value, *, missing):
    path = Path(value)
    if not path.is_absolute():
        raise EditorFileStoreError('absolute_path_required')
    path = Path(os.path.abspath(path))
    _plain(path, missing=missing)
    return path.resolve(strict=not missing)


def _snapshot(target):
    _plain(target, missing=True)
    try:
        stream = target.open('rb')
    except FileNotFoundError:
        return None, None, None
    except OSError:
        raise EditorFileStoreError('source_unreadable') from None
    try:
        with stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise EditorFileStoreError('regular_single_link_file_required')
            if before.st_size > MAX_SOURCE_BYTES:
                raise EditorFileStoreError('existing_source_too_large')
            data = stream.read(MAX_SOURCE_BYTES + 1)
            after = os.fstat(stream.fileno())
            _plain(target)
            current = target.stat()
            identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            if (len(data) > MAX_SOURCE_BYTES
                    or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != identity
                    or (current.st_dev, current.st_ino) != identity[:2]):
                raise EditorWriteConflict('source_changed_during_read')
            return data, identity, stat.S_IMODE(before.st_mode)
    except EditorFileStoreError:
        raise
    except OSError:
        raise EditorFileStoreError('source_unreadable') from None


def _schema(connection, *, create):
    row = connection.execute(
        "SELECT type FROM sqlite_master WHERE name='native_editor_writes'").fetchone()
    if row is None:
        if not create:
            raise EditorFileStoreError('checkpoint_table_missing')
        connection.execute(_SCHEMA)
    elif row[0] != 'table':
        raise EditorFileStoreError('checkpoint_schema_mismatch')
    actual = connection.execute('PRAGMA table_info(native_editor_writes)').fetchall()
    if tuple((r[1], r[2].upper()) for r in actual) != _COLUMNS or actual[0][5] != 1:
        raise EditorFileStoreError('checkpoint_schema_mismatch')


def _open(database):
    database = _path(database, missing=False)
    if not database.is_file() or database.stat().st_nlink != 1:
        raise EditorFileStoreError('existing_database_required')
    connection = sqlite3.connect(database.as_uri() + '?mode=rw', uri=True,
                                 timeout=5, isolation_level=None)
    try:
        connection.execute('PRAGMA busy_timeout=5000')
        connection.execute('PRAGMA trusted_schema=OFF')
        mode = connection.execute('PRAGMA journal_mode=WAL').fetchone()
        if not mode or str(mode[0]).lower() != 'wal':
            raise EditorFileStoreError('wal_not_confirmed')
        connection.execute('PRAGMA synchronous=FULL')
        if connection.execute('PRAGMA synchronous').fetchone()[0] != 2:
            raise EditorFileStoreError('full_sync_not_confirmed')
        return connection
    except BaseException:
        connection.close()
        raise


def _phase(connection, operation_id, phase, *, written=False, error=None):
    connection.execute('''UPDATE native_editor_writes
        SET phase=?,file_written=?,error_code=?,finished_utc=? WHERE operation_id=?''',
        (phase, int(written), error, _utc(), operation_id))


def _stage(path, data, mode):
    # Exclusive staging never adopts or truncates an existing neighboring file.
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if mode is not None:
        os.chmod(path, mode)


def _windows_path(path):
    value = str(path)
    if value.startswith('\\\\?\\'):
        return value
    if value.startswith('\\\\'):
        return '\\\\?\\UNC\\' + value[2:]
    return '\\\\?\\' + value


def _promote_existing(staged, target, backup):
    """Keep the original metadata backup; never relax failed ACL/stream merges.

    Windows ReplaceFileW flags0 preserves the documented original DACL,
    creation time, compression/encryption and named streams absent from the
    staged file. Its partial failures can move the original to ``backup``;
    this function never deletes that backup or retries another promotion.
    https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew

    The non-Windows fallback retains an original hard link but provides only
    the previous basic-mode replacement contract for the resulting target.
    """
    _plain(backup, missing=True)
    if backup.exists():
        raise EditorFileStoreError('original_backup_already_exists')
    if os.name != 'nt':
        os.link(target, backup)
        os.replace(staged, target)
        return
    kernel = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=0x00000800)
    replace = kernel.ReplaceFileW
    replace.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                        wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID]
    replace.restype = wintypes.BOOL
    if not replace(_windows_path(target), _windows_path(staged), _windows_path(backup),
                   0, None, None):
        raise ctypes.WinError(ctypes.get_last_error())


def durable_write_source(target, code_bytes, *, database=MASTER_DATABASE,
                         expected_sha256=_UNSPECIFIED):
    """Save operator-selected bytes after a durable original/draft checkpoint.

    Omitted expected_sha256 accepts the current snapshot. None means the target
    must be absent; a SHA256 means the loaded file must still match. Conflicts
    retain the current original and proposed edit in the checkpoint, not Git.
    Errors carry operation_id when preservation was committed and ``written``
    when the new target was promoted but later bookkeeping/readback failed.
    """
    if type(code_bytes) is not bytes or len(code_bytes) > MAX_SOURCE_BYTES:
        raise EditorFileStoreError('invalid_or_oversized_draft')
    if (expected_sha256 is not _UNSPECIFIED and expected_sha256 is not None
            and (not isinstance(expected_sha256, str)
                 or re.fullmatch('[0-9a-f]{64}', expected_sha256) is None)):
        raise EditorFileStoreError('invalid_expected_hash')
    target = _path(target, missing=True)
    original, identity, mode = _snapshot(target)
    original_hash, draft_hash = _sha(original), _sha(code_bytes)
    expected_kind = ('unconstrained' if expected_sha256 is _UNSPECIFIED
                     else 'missing' if expected_sha256 is None else 'sha256')
    initial_conflict = expected_kind != 'unconstrained' and expected_sha256 != original_hash
    operation_id = uuid.uuid4().hex
    staged = target.with_name('.aibs-editor-' + operation_id + '.tmp')
    backup = (target.with_name('.aibs-editor-original-' + operation_id + '.bak')
              if original is not None else None)
    connection = None
    checkpointed, promoted = False, False
    try:
        connection = _open(database)
        connection.execute('BEGIN IMMEDIATE')
        _schema(connection, create=True)
        connection.execute('''INSERT INTO native_editor_writes
            (operation_id,target_path,expected_kind,expected_sha256,original_bytes,original_sha256,
             draft_bytes,draft_sha256,staged_path,original_backup_path,phase,checkpointed_utc)
            VALUES(?,?,?,?,?,?,?,?,?,?,'CHECKPOINTED',?)''',
            (operation_id, str(target), expected_kind,
             expected_sha256 if expected_kind == 'sha256' else None,
             original, original_hash, code_bytes, draft_hash, str(staged),
             str(backup) if backup is not None else None, _utc()))
        connection.commit()
        checkpointed = True
        # The first committed WAL record is the pre-write durability boundary.
        # Holding SQLite's writer lock now serializes other saves using this DB.
        connection.execute('BEGIN IMMEDIATE')
        if initial_conflict:
            raise EditorWriteConflict('loaded_source_changed')
        current, current_identity, _ = _snapshot(target)
        if current != original or current_identity != identity:
            raise EditorWriteConflict('source_changed_after_checkpoint')
        target.parent.mkdir(parents=True, exist_ok=True)
        _plain(target.parent)
        _stage(staged, code_bytes, mode)
        current, current_identity, _ = _snapshot(target)
        if current != original or current_identity != identity:
            raise EditorWriteConflict('source_changed_before_promotion')
        if original is None:
            # Same-filesystem hard-link creation is atomic and refuses to
            # overwrite any intervening file. No nonatomic 'xb' fallback.
            os.link(staged, target)
            promoted = True
            staged.unlink()
        else:
            _promote_existing(staged, target, backup)
            promoted = True
            retained_original, _, _ = _snapshot(backup)
            if retained_original != original:
                raise EditorFileStoreError('original_backup_not_confirmed')
        written, _, _ = _snapshot(target)
        if written != code_bytes:
            raise EditorWriteConflict('source_changed_after_promotion')
        _phase(connection, operation_id, 'WRITTEN', written=True)
        connection.commit()
        return {'operation_id': operation_id, 'target_path': str(target),
                'original_sha256': original_hash, 'source_sha256': draft_hash,
                'original_backup_path': str(backup) if backup is not None else None,
                'draft_sha256': draft_hash, 'checkpointed': True, 'written': True}
    except Exception as error:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        conflict = isinstance(error, EditorWriteConflict) or (original is None and isinstance(error, FileExistsError))
        windows_error = getattr(error, 'winerror', None)
        code = error.code if isinstance(error, EditorFileStoreError) else (
            'new_target_appeared' if conflict else
            'windows_replace_' + str(windows_error) if windows_error in {1175, 1176, 1177} else
            'file_write_failed' if checkpointed else 'checkpoint_failed')
        if connection is not None and checkpointed:
            try:
                connection.execute('BEGIN IMMEDIATE')
                _phase(connection, operation_id, 'CONFLICT' if conflict else 'FAILED',
                       written=promoted, error=code)
                connection.commit()
            except Exception:
                if connection.in_transaction:
                    connection.rollback()
                # The first CHECKPOINTED record remains the recovery authority.
        cls = EditorWriteConflict if conflict else EditorFileStoreError
        raise cls(code, operation_id=operation_id if checkpointed else None, written=promoted) from None
    finally:
        if connection is not None:
            connection.close()
        # Failed owned staging files remain inspectable. Never remove originals
        # or another writer's file in an error/rollback handler.


def read_source_checkpoint(operation_id, *, database=MASTER_DATABASE):
    """Read retained bytes only; never replay a file save or alter its state."""
    if not isinstance(operation_id, str) or re.fullmatch('[a-f0-9]{32}', operation_id) is None:
        raise EditorFileStoreError('invalid_operation_id')
    path = _path(database, missing=False)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)) as connection:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('PRAGMA trusted_schema=OFF')
        _schema(connection, create=False)
        connection.row_factory = sqlite3.Row
        row = connection.execute('SELECT * FROM native_editor_writes WHERE operation_id=?',
                                 (operation_id,)).fetchone()
        if row is None:
            raise EditorFileStoreError('checkpoint_missing')
        value = dict(row)
        if (_sha(value['original_bytes']) != value['original_sha256']
                or _sha(value['draft_bytes']) != value['draft_sha256']):
            raise EditorFileStoreError('checkpoint_hash_mismatch')
        return value
