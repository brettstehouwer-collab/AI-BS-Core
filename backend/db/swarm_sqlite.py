"""Opt-in SQLite ownership adapter. Importing this module opens no database.

Legacy callers retain their existing connection policies. One adapter per database
may be active in this process; other processes/legacy connections still rely on
SQLite's writer locking. Callbacks are trusted application code, not a sandbox.
"""
from __future__ import annotations

from concurrent.futures import Future
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
from queue import Queue, Empty, Full
import sqlite3
import threading
import time
from typing import Callable

DATABASES = {'master': 'backend/aibs_master.db', 'cdz_audit': 'database/aibs_master.db'}


@dataclass(frozen=True)
class SQLitePolicy:
    busy_timeout_ms: int = 10000
    cache_size_kib: int = 8192
    max_readers: int = 8
    max_pending_writes: int = 128

    def __post_init__(self):
        for name, low, high in [('busy_timeout_ms', 1, 60000), ('cache_size_kib', 1, 8192),
                                ('max_readers', 1, 8), ('max_pending_writes', 1, 4096)]:
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(name + ' outside bounded policy')


class WriteCancelled(RuntimeError):
    pass


class WriteHandle:
    def __init__(self):
        self.future = Future()
        self.cancel_event = threading.Event()
        self._commit_lock = threading.RLock()
        self._committed = False

    def cancel(self):
        with self._commit_lock:
            if self._committed or self.future.done():
                return False
            self.cancel_event.set()
            return self.future.cancel()


def _checked_path(path: Path) -> Path:
    path = path.absolute()
    for part in (path, *path.parents):
        redirected = part.is_symlink() or getattr(part, 'is_junction', lambda: False)()
        if part.exists() and os.name == 'nt':
            redirected = redirected or bool(part.stat(follow_symlinks=False).st_file_attributes & 0x400)
        if redirected:
            raise ValueError('Redirected database/backup path refused')
    if path.is_file() and path.stat().st_nlink != 1:
        raise ValueError('Hard-linked database/backup path refused')
    return path.resolve(strict=True)


class SQLiteStore:
    """Explicitly activated named store with bounded, owned connections.

    Write callbacks receive (connection, cancellation_event), must return
    materialized values and must not retain the connection. Transaction control
    is adapter-owned. Cancellation is cooperative and checked before commit.
    """
    _registry_lock = threading.Lock()
    _registry: set[str] = set()

    def __init__(self, root: Path, name: str, policy: SQLitePolicy | None = None):
        if name not in DATABASES:
            raise ValueError('Unknown named database')
        self.path = Path(root).absolute() / DATABASES[name]
        self.name, self.policy = name, policy or SQLitePolicy()
        self._queue = Queue(self.policy.max_pending_writes)
        self._read_slots = threading.BoundedSemaphore(self.policy.max_readers)
        self._lock = threading.Condition(threading.RLock())
        self._closing = threading.Event()
        self._thread = None
        self._key = None
        self._active_readers = 0
        self._error = None
        self._ready = threading.Event()
        self._checkpoint_task = lambda conn, event: conn.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()

    def _connect(self, readonly=False):
        path = _checked_path(self.path)
        conn = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'),
                               uri=True, timeout=self.policy.busy_timeout_ms / 1000,
                               isolation_level=None)
        try:
            conn.execute(f'PRAGMA busy_timeout={self.policy.busy_timeout_ms}')
            conn.execute('PRAGMA synchronous=FULL')
            conn.execute(f'PRAGMA cache_size={-self.policy.cache_size_kib}')
            conn.execute('PRAGMA mmap_size=0')
            conn.execute('PRAGMA wal_autocheckpoint=1000')
            if readonly:
                conn.execute('PRAGMA query_only=ON')
            return conn
        except BaseException:
            conn.close()
            raise

    def activate(self, backup_path: Path, *, allow_activation=False):
        if allow_activation is not True:
            raise PermissionError('Explicit activation is required')
        with self._lock:
            if self._thread is not None or self._closing.is_set():
                raise RuntimeError('Store activation is single-use')
            path = _checked_path(self.path)
            self.path = path
            key = os.path.normcase(str(path))
            with self._registry_lock:
                if key in self._registry:
                    raise RuntimeError('Database already has an active adapter')
                self._registry.add(key)
            self._key = key
            try:
                backup_path = Path(backup_path).absolute()
                _checked_path(backup_path.parent)
                if backup_path.exists() or backup_path == path:
                    raise FileExistsError('Backup must be a new distinct file')
                # Reserve the destination, never overwrite another backup.
                with backup_path.open('xb'):
                    pass
                source = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True,
                                         timeout=min(.1, self.policy.busy_timeout_ms / 1000))
                target = sqlite3.connect(backup_path)
                try:
                    deadline = time.monotonic() + self.policy.busy_timeout_ms / 1000
                    def backup_progress(status, remaining, total):
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Pre-activation backup deadline exceeded')
                    source.backup(target, pages=128, progress=backup_progress, sleep=.01)
                    if target.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                        raise RuntimeError('Pre-activation backup integrity failure')
                finally:
                    source.close()
                    target.close()
                self._thread = threading.Thread(target=self._run, name='aibs-sqlite-' + self.name,
                                                daemon=False)
                self._thread.start()
            except BaseException:
                with self._registry_lock:
                    self._registry.discard(key)
                self._key = None
                raise
        if not self._ready.wait(self.policy.busy_timeout_ms / 1000 + 5):
            self._closing.set()
            raise TimeoutError('Writer startup has not drained; retain store and call close')
        if self._error:
            self.close()
            raise self._error
        return backup_path

    def _run(self):
        conn = None
        current_handle = None
        try:
            conn = self._connect()
            if conn.execute('PRAGMA journal_mode=WAL').fetchone()[0].lower() != 'wal':
                raise RuntimeError('WAL activation refused')
            self._ready.set()
            while not self._closing.is_set() or not self._queue.empty():
                try:
                    handle, callback = self._queue.get(timeout=.05)
                    current_handle = handle
                except Empty:
                    continue
                try:
                    if not handle.future.set_running_or_notify_cancel():
                        continue
                    if handle.cancel_event.is_set():
                        raise WriteCancelled('Write cancelled before transaction')
                    if callback is self._checkpoint_task:
                        handle.future.set_result(callback(conn, handle.cancel_event))
                        continue
                    conn.execute('BEGIN IMMEDIATE')
                    # Reject accidental callback commit/rollback; not hostile-code isolation.
                    conn.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY
                                        if action == sqlite3.SQLITE_TRANSACTION else sqlite3.SQLITE_OK)
                    conn.set_progress_handler(lambda: int(handle.cancel_event.is_set()), 1000)
                    result = callback(conn, handle.cancel_event)
                    conn.set_progress_handler(None, 0)
                    conn.set_authorizer(None)
                    with handle._commit_lock:
                        if handle.cancel_event.is_set():
                            raise WriteCancelled('Write cancelled before commit')
                        conn.commit()
                        handle._committed = True
                    handle.future.set_result(result)
                except BaseException as error:
                    try:
                        conn.set_progress_handler(None, 0)
                        conn.set_authorizer(None)
                        if conn.in_transaction:
                            conn.rollback()
                    except BaseException as rollback_error:
                        if not handle.future.done():
                            handle.future.set_exception(rollback_error)
                        raise
                    if not handle.future.done():
                        handle.future.set_exception(error)
                finally:
                    self._queue.task_done()
        except BaseException as error:
            self._error = error
            self._ready.set()
        finally:
            if current_handle is not None and not current_handle.future.done():
                current_handle.future.set_exception(self._error or RuntimeError('Writer stopped'))
            try:
                if conn is not None:
                    conn.close()
            except BaseException as error:
                self._error = self._error or error
            while True:
                try:
                    handle, _ = self._queue.get_nowait()
                except Empty:
                    break
                if not handle.future.done():
                    handle.future.set_exception(self._error or RuntimeError('Writer stopped'))
                self._queue.task_done()

    def submit(self, callback: Callable) -> WriteHandle:
        with self._lock:
            if self._closing.is_set() or self._thread is None or not self._ready.is_set() or self._error:
                raise RuntimeError('Store is not accepting writes')
            handle = WriteHandle()
            try:
                self._queue.put_nowait((handle, callback))
            except Full:
                raise RuntimeError('Writer queue is full') from None
            return handle

    @contextmanager
    def reader(self, timeout=10):
        if not self._read_slots.acquire(timeout=timeout):
            raise TimeoutError('Reader capacity exhausted')
        conn = None
        try:
            with self._lock:
                if self._closing.is_set() or self._thread is None or not self._ready.is_set() or self._error:
                    raise RuntimeError('Store is not accepting readers')
                self._active_readers += 1
            try:
                conn = self._connect(readonly=True)
                conn.execute('BEGIN')
                yield conn
            finally:
                if conn is not None:
                    conn.close()
                with self._lock:
                    self._active_readers -= 1
                    self._lock.notify_all()
        finally:
            self._read_slots.release()

    def metrics(self):
        with self.reader() as conn:
            mode = conn.execute('PRAGMA journal_mode').fetchone()[0]
        wal = Path(str(self.path) + '-wal')
        try:
            wal_bytes = wal.stat().st_size
        except FileNotFoundError:
            wal_bytes = 0
        return {'journal_mode': mode, 'wal_bytes': wal_bytes,
                'queued_writes': self._queue.qsize(), 'active_readers': self._active_readers}

    def checkpoint(self):
        """Queue a PASSIVE checkpoint; return its busy/log/checkpointed-page tuple."""
        return self.submit(self._checkpoint_task)

    def close(self, timeout=10, *, cancel_pending=False):
        deadline = time.monotonic() + timeout
        with self._lock:
            self._closing.set()
            if cancel_pending:
                with self._queue.mutex:
                    pending = [handle for handle, _ in self._queue.queue]
                for handle in pending:
                    handle.cancel()
        if self._thread is not None:
            if self._thread is threading.current_thread():
                raise RuntimeError('Writer cannot join itself')
            self._thread.join(max(0, deadline - time.monotonic()))
        with self._lock:
            while self._active_readers and time.monotonic() < deadline:
                self._lock.wait(max(0, deadline - time.monotonic()))
            drained = (self._thread is None or not self._thread.is_alive()) and not self._active_readers
            if drained and self._key is not None:
                with self._registry_lock:
                    self._registry.discard(self._key)
                self._key = None
            return drained
