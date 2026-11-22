"""Real CDZ caller against disposable databases; never imports the app/watcher."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core.swarm_runtime import SwarmRuntime
from database import cdz_audit_db as cdz


class CDZHostCompositionTests(unittest.TestCase):
    def ledger(self, root, index, records=None):
        path = root / ('ledger-' + str(index) + '.json')
        if records is None:
            records = [{'index': index, 'timestamp': 1700000000 + index,
                        'domain': 'synthetic', 'event': 'test', 'detail': 'fixture',
                        'hash': 'hash-' + str(index), 'prev_hash': 'previous',
                        'full_hash': 'full-' + str(index)}]
        path.write_text(json.dumps({'records': records, 'integrity': {'valid': True}}), encoding='utf-8')
        return str(path)

    def runtime(self, root):
        workspace = root / 'tasks'
        workspace.mkdir()
        project = root / 'project'
        for directory in ('backend', 'database'):
            path = project / directory / 'aibs_master.db'
            path.parent.mkdir(parents=True)
            self.assertTrue(path.resolve().is_relative_to(root.resolve()))
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE sentinel(value TEXT)')
                db.execute("INSERT INTO sentinel VALUES('unchanged')")
                db.commit()
        runtime = SwarmRuntime(workspace, project_root=project,
                               config_path=ROOT / 'config/swarm_orchestration.json')
        store = runtime.stores['cdz_audit']
        store.activate(root / 'audit-before.sqlite', allow_activation=True)
        return runtime

    def test_real_caller_shared_runtime_concurrent_ingest_query_and_close(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-host-') as temp:
            root = Path(temp)
            runtime = self.runtime(root)
            store = runtime.stores['cdz_audit']
            try:
                files = [self.ledger(root, i) for i in range(12)]
                # Any legacy fallback would fail before it could open a database.
                with patch.object(cdz, 'get_db_connection', side_effect=AssertionError('Legacy connection forbidden')):
                    cdz.init_cdz_schema(store=store)
                    with store.reader() as snapshot:
                        self.assertEqual(snapshot.execute('SELECT COUNT(*) FROM cdz_audit_ledger').fetchone()[0], 0)
                        with ThreadPoolExecutor(max_workers=3) as pool:
                            results = list(pool.map(lambda f: cdz.ingest_ledger_file(f, store=store), files))
                        self.assertEqual(sum(r[0] for r in results), 12)
                        self.assertTrue(all(r[2] for r in results))
                        self.assertEqual(snapshot.execute('SELECT COUNT(*) FROM cdz_audit_ledger').fetchone()[0], 0)
                    with ThreadPoolExecutor(max_workers=3) as pool:
                        repeated = list(pool.map(lambda f: cdz.ingest_ledger_file(f, store=store), files))
                    self.assertEqual(sum(r[0] for r in repeated), 0)
                    self.assertTrue(all(r[1] == 12 for r in repeated))
                    summary = cdz.get_cdz_summary(store=store)
                    self.assertEqual(summary['total_blocks'], 12)
                    self.assertEqual(summary['domain_breakdown'], {'SYNTHETIC': 12})
                    self.assertEqual(summary['head_hash'], 'hash-11')
                    blocks = cdz.get_cdz_blocks(domain='synthetic', event='test', search='fixture', limit=3, offset=2, store=store)
                    self.assertEqual(blocks['total'], 12)
                    self.assertEqual([b['block_index'] for b in blocks['blocks']], [9, 8, 7])
                    self.assertTrue(runtime.close(timeout=5))
                    with self.assertRaises(RuntimeError):
                        cdz.get_cdz_summary(store=store)
                    with self.assertRaises(RuntimeError):
                        cdz.ingest_ledger_file(files[0], store=store)
                for path in (store.path, runtime.stores['master'].path, root / 'audit-before.sqlite'):
                    with closing(sqlite3.connect(path)) as db:
                        self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                        self.assertEqual(db.execute('SELECT value FROM sentinel').fetchall(), [('unchanged',)])
                with closing(sqlite3.connect(runtime.stores['master'].path)) as db:
                    self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='cdz_audit_ledger'").fetchone())
                with closing(sqlite3.connect(root / 'audit-before.sqlite')) as db:
                    self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='cdz_audit_ledger'").fetchone())
            finally:
                self.assertTrue(runtime.close(timeout=5))

    def test_shared_transaction_rollback_and_wrong_store_refusal(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-rollback-') as temp:
            root = Path(temp)
            runtime = self.runtime(root)
            store = runtime.stores['cdz_audit']
            try:
                with patch.object(cdz, 'get_db_connection', side_effect=AssertionError('Legacy connection forbidden')):
                    with self.assertRaises(ValueError):
                        cdz.init_cdz_schema(store=runtime.stores['master'])
                    good = json.loads(Path(self.ledger(root, 1)).read_text())['records'][0]
                    bad = dict(good, index=None, full_hash='invalid-distinct')
                    # INSERT OR IGNORE intentionally skips SQL constraints, so use a binding error
                    # after a valid first record to verify atomic rollback of the whole batch.
                    bad['detail'] = {'unsupported': 'binding'}
                    path = self.ledger(root, 'bad', [good, bad])
                    with self.assertRaises(sqlite3.ProgrammingError):
                        cdz.ingest_ledger_file(path, store=store)
                    self.assertEqual(cdz.get_cdz_blocks(store=store)['total'], 0)
                    self.assertEqual(cdz.ingest_ledger_file(self.ledger(root, 2), store=store), (1, 1, True))
            finally:
                self.assertTrue(runtime.close(timeout=5))

    def test_default_legacy_signatures_still_work_on_synthetic_path(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-legacy-') as temp:
            root = Path(temp)
            with patch.object(cdz, 'DB_PATH', str(root / 'legacy.db')):
                path = self.ledger(root, 4)
                self.assertEqual(cdz.ingest_ledger_file(path), (1, 1, True))
                self.assertEqual(cdz.ingest_ledger_file(path), (0, 1, True))
                self.assertEqual(cdz.get_cdz_summary()['total_blocks'], 1)
                self.assertEqual(cdz.get_cdz_blocks()['total'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
