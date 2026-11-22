"""Synthetic host composition only: all SQLite files live in TemporaryDirectory."""
from concurrent.futures import ThreadPoolExecutor, CancelledError
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core.swarm_runtime import SwarmRuntime
from core.swarm_orchestration import AdmissionError
from db.swarm_sqlite import WriteCancelled


class RuntimeCompositionTests(unittest.TestCase):
    def make_runtime(self, root):
        workspace = root / 'tasks'
        workspace.mkdir()
        project = root / 'synthetic-project'
        for directory in ('backend', 'database'):
            path = project / directory / 'aibs_master.db'
            path.parent.mkdir(parents=True)
            self.assertTrue(path.resolve().is_relative_to(root.resolve()))
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, value TEXT)')
                db.commit()
        runtime = SwarmRuntime(workspace, project_root=project,
                               config_path=ROOT / 'config/swarm_orchestration.json')
        self.addCleanup(lambda: self.assertTrue(runtime.close(timeout=5)))
        for name, store in runtime.stores.items():
            self.assertTrue(store.path.resolve().is_relative_to(root.resolve()))
            store.activate(root / (name + '-before.sqlite'), allow_activation=True)
        return runtime

    def test_shared_two_database_writers_snapshot_admission_and_drain(self):
        with tempfile.TemporaryDirectory(prefix='aibs-runtime-composition-') as temp:
            root = Path(temp)
            runtime = self.make_runtime(root)
            try:
                leases = [runtime.registry.acquire('lead', 'lead_orchestrator', [])]
                for index, role in enumerate(('test_runner', 'frontend_ui_worker', 'database_state_worker')):
                    leases.append(runtime.registry.acquire('worker-' + str(index), role, []))
                with self.assertRaises(AdmissionError):
                    runtime.registry.acquire('overflow', 'native_ui_worker', [])
                with runtime.stores['master'].reader() as master_reader, runtime.stores['cdz_audit'].reader() as audit_reader:
                    for reader in (master_reader, audit_reader):
                        self.assertEqual(reader.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
                    def task(index):
                        for name, store in runtime.stores.items():
                            for sequence in range(12):
                                key = index * 100 + sequence
                                value = name + ':' + str(key)
                                store.submit(lambda db, event, k=key, v=value: db.execute(
                                    'INSERT INTO records VALUES(?,?)', (k, v)).rowcount).future.result(5)
                    with ThreadPoolExecutor(max_workers=3) as pool:
                        list(pool.map(task, range(3)))
                    for reader in (master_reader, audit_reader):
                        self.assertEqual(reader.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
                for name, store in runtime.stores.items():
                    with store.reader() as db:
                        rows = db.execute('SELECT id,value FROM records ORDER BY id').fetchall()
                        self.assertEqual(len(rows), 36)
                        self.assertTrue(all(value == name + ':' + str(key) for key, value in rows))
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                    self.assertEqual(store.metrics()['journal_mode'], 'wal')
                    self.assertEqual(len(store.checkpoint().future.result(5)), 3)
                    with closing(sqlite3.connect(root / (name + '-before.sqlite'))) as backup:
                        self.assertEqual(backup.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
                runtime.request_shutdown()
                with self.assertRaises(AdmissionError):
                    runtime.registry.acquire('late', 'native_ui_worker', [])
                self.assertTrue(all(lease.cancel_event.is_set() for lease in leases))
                self.assertFalse(runtime.close(timeout=0))
                for lease in reversed(leases):
                    runtime.registry.finish(lease)
                self.assertTrue(runtime.close(timeout=5))
                self.assertTrue(runtime.registry.is_drained())
                for store in runtime.stores.values():
                    with self.assertRaises(RuntimeError):
                        store.submit(lambda db, event: None)
                    with self.assertRaises(RuntimeError):
                        with store.reader():
                            pass
            finally:
                self.assertTrue(runtime.close(timeout=5))

    def test_host_close_waits_for_running_write_and_cancels_queued_write(self):
        with tempfile.TemporaryDirectory(prefix='aibs-runtime-drain-') as temp:
            root = Path(temp)
            runtime = self.make_runtime(root)
            entered, release = threading.Event(), threading.Event()
            store = runtime.stores['master']
            def running(db, event):
                db.execute("INSERT INTO records VALUES(1,'running')")
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('Synthetic callback release missing')
            first = store.submit(running)
            try:
                self.assertTrue(entered.wait(3))
                second = store.submit(lambda db, event: db.execute("INSERT INTO records VALUES(2,'queued')").rowcount)
                self.assertFalse(runtime.close(timeout=0))
                self.assertTrue(first.cancel() is False)  # Running Future cannot be cancelled directly.
                release.set()
                with self.assertRaises(WriteCancelled):
                    first.future.result(5)
                with self.assertRaises(CancelledError):
                    second.future.result(5)
                self.assertTrue(runtime.close(timeout=5))
                for candidate in runtime.stores.values():
                    with closing(sqlite3.connect(candidate.path)) as db:
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                release.set()
                self.assertTrue(runtime.close(timeout=5))


if __name__ == '__main__':
    unittest.main(verbosity=2)
