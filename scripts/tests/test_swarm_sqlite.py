"""Only temporary, synthetic databases are opened by this qualification."""
from concurrent.futures import ThreadPoolExecutor, CancelledError
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from backend.db.swarm_sqlite import SQLiteStore, SQLitePolicy, WriteCancelled


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aibs-wal-')
        self.root = Path(self.temp.name)
        self.stores = []
        for name in ['backend', 'database']:
            (self.root / name).mkdir()
            with closing(sqlite3.connect(self.root / name / 'aibs_master.db')) as db:
                db.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, value TEXT)')
                db.commit()

    def tearDown(self):
        for store in self.stores:
            self.assertTrue(store.close(timeout=3, cancel_pending=True))
        self.temp.cleanup()

    def store(self, name='master', policy=None):
        store = SQLiteStore(self.root, name, policy)
        self.stores.append(store)
        store.activate(self.root / (name + '-before.sqlite'), allow_activation=True)
        return store

    def test_inert_and_explicit_activation(self):
        store = SQLiteStore(self.root, 'master')
        self.assertFalse(Path(str(store.path) + '-wal').exists())
        with self.assertRaises(PermissionError):
            store.activate(self.root / 'refused.sqlite')
        self.assertFalse((self.root / 'refused.sqlite').exists())
        with self.assertRaises(RuntimeError):
            store.submit(lambda c, e: None)

    def test_settings_backup_and_distinct_stores(self):
        master, audit = self.store(), self.store('cdz_audit')
        for store in (master, audit):
            with store.reader() as db:
                for pragma, expected in [('journal_mode', 'wal'), ('synchronous', 2),
                                         ('busy_timeout', 10000), ('cache_size', -8192),
                                         ('mmap_size', 0), ('wal_autocheckpoint', 1000)]:
                    self.assertEqual(db.execute('PRAGMA ' + pragma).fetchone()[0], expected)
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute("INSERT INTO records VALUES(1,'no')")
        committed = master.submit(lambda c, e: c.execute("INSERT INTO records VALUES(1,'master')").rowcount)
        committed.future.result(3)
        self.assertFalse(committed.cancel())
        self.assertFalse(committed.cancel_event.is_set())
        with audit.reader() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
        for name in ['master', 'cdz_audit']:
            with closing(sqlite3.connect(self.root / (name + '-before.sqlite'))) as backup:
                self.assertEqual(backup.execute('PRAGMA quick_check').fetchone()[0], 'ok')
                self.assertEqual(backup.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)

    def test_concurrent_writes_with_snapshot_reader(self):
        store = self.store()
        with store.reader() as reader:
            self.assertEqual(reader.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
            def write(i):
                return store.submit(lambda db, e: db.execute('INSERT INTO records VALUES(?,?)', (i, str(i))).rowcount).future.result(5)
            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(sum(pool.map(write, range(60))), 60)
            self.assertEqual(reader.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
        with store.reader() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 60)
        self.assertEqual(len(store.checkpoint().future.result(3)), 3)
        self.assertEqual(store.metrics()['journal_mode'], 'wal')

    def test_same_database_adapter_rejected(self):
        self.store()
        other = SQLiteStore(self.root, 'master')
        with self.assertRaises(RuntimeError):
            other.activate(self.root / 'other.sqlite', allow_activation=True)
        self.assertFalse((self.root / 'other.sqlite').exists())

    def test_existing_backup_never_overwritten(self):
        path = self.root / 'keep.sqlite'
        path.write_bytes(b'preserved evidence')
        store = SQLiteStore(self.root, 'master')
        with self.assertRaises(FileExistsError):
            store.activate(path, allow_activation=True)
        self.assertEqual(path.read_bytes(), b'preserved evidence')
        self.assertTrue(store.close())
        # The refused activation releases its reservation for a valid adapter.
        self.store()

    def test_hardlink_source_refused_before_backup(self):
        import os
        os.link(self.root / 'backend/aibs_master.db', self.root / 'alias.db')
        store = SQLiteStore(self.root, 'master')
        with self.assertRaises(ValueError):
            store.activate(self.root / 'refused.sqlite', allow_activation=True)
        self.assertFalse((self.root / 'refused.sqlite').exists())

    def test_closed_adapter_does_not_admit_new_work(self):
        store = self.store()
        self.assertTrue(store.close())
        with self.assertRaises(RuntimeError):
            store.submit(lambda c, e: None)
        with self.assertRaises(RuntimeError):
            with store.reader():
                pass

    def test_lock_timeout_reported_no_retry(self):
        store = self.store(policy=SQLitePolicy(busy_timeout_ms=50))
        with closing(sqlite3.connect(store.path, isolation_level=None)) as blocker:
            blocker.execute('BEGIN IMMEDIATE')
            handle = store.submit(lambda c, e: c.execute("INSERT INTO records VALUES(1,'blocked')").rowcount)
            with self.assertRaises(sqlite3.OperationalError):
                handle.future.result(3)
            blocker.rollback()
        with store.reader() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)

    def test_locked_backup_has_deadline_and_does_not_activate(self):
        store = SQLiteStore(self.root, 'master', SQLitePolicy(busy_timeout_ms=50))
        with closing(sqlite3.connect(store.path, isolation_level=None)) as blocker:
            blocker.execute('BEGIN EXCLUSIVE')
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                store.activate(self.root / 'timed-out.sqlite', allow_activation=True)
            self.assertLess(time.monotonic() - started, 2)
            blocker.rollback()
        with self.assertRaises(RuntimeError):
            store.submit(lambda c, e: None)
        self.assertTrue(store.close())

    def test_closed_callback_connection_future_settles_and_writer_stops(self):
        store = self.store()
        def closes_connection(c, cancel):
            c.close()
            raise ValueError('callback violated connection lifetime')
        handle = store.submit(closes_connection)
        with self.assertRaises(sqlite3.ProgrammingError):
            handle.future.result(3)
        self.assertTrue(store.close(timeout=3))
        with self.assertRaises(RuntimeError):
            store.submit(lambda c, e: None)

    def test_cancellation_queue_bounds_and_close(self):
        store = self.store(policy=SQLitePolicy(max_pending_writes=1))
        entered, release = threading.Event(), threading.Event()
        def running(c, cancel):
            c.execute("INSERT INTO records VALUES(1,'cancel')")
            entered.set()
            release.wait(3)
        first = store.submit(running)
        self.assertTrue(entered.wait(2))
        second = store.submit(lambda c, e: c.execute("INSERT INTO records VALUES(2,'queued')").rowcount)
        with self.assertRaises(RuntimeError):
            store.submit(lambda c, e: None)
        first.cancel()
        second.future.add_done_callback(lambda _: second.cancel())
        self.assertTrue(second.cancel())
        self.assertFalse(store.close(timeout=.01))
        release.set()
        with self.assertRaises(WriteCancelled):
            first.future.result(3)
        with self.assertRaises(CancelledError):
            second.future.result(3)
        self.assertTrue(store.close(timeout=3))
        with closing(sqlite3.connect(store.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)

    def test_reader_limit_and_close_wait(self):
        store = self.store(policy=SQLitePolicy(max_readers=1))
        with store.reader():
            with self.assertRaises(TimeoutError):
                with store.reader(timeout=.01):
                    pass
            self.assertFalse(store.close(timeout=.01))
        self.assertTrue(store.close(timeout=2))

    def test_callback_cannot_commit_early_and_error_rolls_back(self):
        store = self.store()
        def bad(c, e):
            c.execute("INSERT INTO records VALUES(1,'must roll back')")
            c.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            store.submit(bad).future.result(3)
        with store.reader() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)

    def test_disk_full_visible_and_queue_survives(self):
        store = self.store()
        def fill(c, e):
            pages = c.execute('PRAGMA page_count').fetchone()[0]
            c.execute('PRAGMA max_page_count=' + str(pages))
            c.execute('INSERT INTO records VALUES(1,?)', ('x' * 100000,))
        with self.assertRaises(sqlite3.OperationalError) as caught:
            store.submit(fill).future.result(3)
        self.assertIn('full', str(caught.exception).lower())
        self.assertEqual(store.submit(lambda c, e: c.execute('SELECT COUNT(*) FROM records').fetchone()[0]).future.result(3), 0)

    def test_interrupted_process_recovery_and_restore(self):
        store = self.store()
        store.submit(lambda c, e: c.execute("INSERT INTO records VALUES(1,'committed')").rowcount).future.result(3)
        self.assertTrue(store.close())
        program = "import sqlite3,sys,os; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); c.execute(\"INSERT INTO records VALUES(2,'uncommitted')\"); os._exit(23)"
        child = subprocess.run([sys.executable, '-I', '-c', program, str(store.path)], capture_output=True, timeout=5)
        self.assertEqual(child.returncode, 23)
        with closing(sqlite3.connect(store.path)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('SELECT id FROM records').fetchall(), [(1,)])
            with closing(sqlite3.connect(self.root / 'restored.sqlite')) as restored:
                db.backup(restored)
                self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(restored.execute('SELECT id FROM records').fetchall(), [(1,)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
