"""Mounted scan acceptance with host-owned watchers and disposable stores only."""
from contextlib import closing, contextmanager
from copy import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.swarm_runtime import SwarmRuntime
from db.swarm_sqlite import SQLiteStore
from database import cdz_audit_db as cdz
from modules.audit_ledger_watcher import CDZAuditLedgerWatcher
from routers import audit_ledger_router as api


@contextmanager
def temporary_watcher():
    with tempfile.TemporaryDirectory(prefix='aibs-cdz-scan-regression-') as temp:
        root = Path(temp)
        source = root / 'source'
        source.mkdir()
        database = root / 'database/aibs_master.db'
        database.parent.mkdir()
        with closing(sqlite3.connect(database)) as db:
            db.execute('CREATE TABLE sentinel(value TEXT)')
            db.commit()
        store = SQLiteStore(root, 'cdz_audit')
        store.activate(root / 'before.sqlite', allow_activation=True)
        try:
            with patch.object(cdz, 'get_db_connection', side_effect=AssertionError('Legacy DB forbidden')):
                yield root, source, store, CDZAuditLedgerWatcher(store=store, watch_dirs=[str(source)])
        finally:
            store.close(timeout=5)


def synthetic_ledger(valid=True):
    return {'records': [{'index': 1, 'timestamp': 1700000001,
                        'domain': 'synthetic', 'event': 'regression',
                        'detail': 'temporary fixture', 'hash': 'hash-1',
                        'prev_hash': 'previous', 'full_hash': 'full-1'}],
            'integrity': {'valid': valid}}


class CDZScanCompositionTests(unittest.TestCase):
    def test_readable_invalid_integrity_ingests_once_without_unchanged_retry(self):
        with temporary_watcher() as (_, source, store, watcher):
            ledger = source / 'synthetic_audit_ledger.json'
            ledger.write_text(json.dumps(synthetic_ledger(valid=False)), encoding='utf-8')
            result = watcher.scan_now()
            self.assertEqual(result['new_blocks_ingested'], 1)
            self.assertEqual(len(result['files_evaluated']), 1)
            self.assertIs(result['files_evaluated'][0]['valid'], False)
            self.assertEqual(result['files_evaluated'][0]['total_blocks'], 1)
            self.assertEqual(watcher.new_blocks_ingested, 1)
            self.assertEqual(watcher.files_tracked, 1)
            # An unchanged readable file is remembered even if integrity is false.
            with patch('modules.audit_ledger_watcher.ingest_ledger_file',
                       side_effect=AssertionError('Unchanged file retried')) as ingest:
                repeated = watcher.scan_now()
                ingest.assert_not_called()
            self.assertEqual(repeated['new_blocks_ingested'], 0)
            self.assertEqual(repeated['files_evaluated'], [])
            self.assertEqual(watcher.new_blocks_ingested, 1)
            self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 1)

    def test_malformed_json_fails_generically_and_retries_corrected_input(self):
        with temporary_watcher() as (root, source, store, watcher):
            ledger = source / 'synthetic_audit_ledger.json'
            ledger.write_text('{ malformed fixture', encoding='utf-8')
            with self.assertRaises(RuntimeError) as failure:
                watcher.scan_now()
            self.assertEqual(str(failure.exception), 'Shared-store source scan failed')
            self.assertNotIn(str(root), str(failure.exception))
            self.assertEqual(watcher.files_tracked, 0)
            self.assertEqual(watcher.new_blocks_ingested, 0)
            ledger.write_text(json.dumps(synthetic_ledger()), encoding='utf-8')
            corrected = watcher.scan_now()
            self.assertEqual(corrected['new_blocks_ingested'], 1)
            self.assertIs(corrected['files_evaluated'][0]['valid'], True)
            self.assertEqual(watcher.files_tracked, 1)
            self.assertEqual(watcher.new_blocks_ingested, 1)
            self.assertEqual(cdz.get_cdz_summary(store=store)['total_blocks'], 1)

    def test_host_bound_scan_auth_idempotency_binding_and_closed_store(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-scan-http-') as temp:
            root = Path(temp)
            workspace = root / 'tasks'
            workspace.mkdir()
            source = root / 'synthetic-source'
            source.mkdir()
            project = root / 'project'
            for directory in ('backend', 'database'):
                path = project / directory / 'aibs_master.db'
                path.parent.mkdir(parents=True)
                with closing(sqlite3.connect(path)) as db:
                    db.execute('CREATE TABLE sentinel(value TEXT)')
                    db.execute("INSERT INTO sentinel VALUES('preserved')")
                    db.commit()
            runtime = SwarmRuntime(workspace, project_root=project,
                                   config_path=ROOT / 'config/swarm_orchestration.json')
            store = runtime.stores['cdz_audit']
            store.activate(root / 'before.sqlite', allow_activation=True)
            app = FastAPI()
            app.state.swarm_runtime = runtime
            app.include_router(api.router)
            headers = {'x-admin-key': 'synthetic-admin'}

            def ledger(index):
                path = source / ('synthetic_audit_ledger_' + str(index) + '.json')
                path.write_text(json.dumps({'records': [{
                    'index': index, 'timestamp': 1700000000 + index,
                    'domain': 'synthetic', 'event': 'mounted_scan',
                    'detail': 'temporary fixture', 'hash': 'hash-' + str(index),
                    'prev_hash': 'previous', 'full_hash': 'full-' + str(index)
                }]}), encoding='utf-8')
                return path

            try:
                watcher = CDZAuditLedgerWatcher(store=store, watch_dirs=[str(source)])
                app.state.cdz_watcher = watcher
                first = ledger(1)
                with patch('security.host_control_access.get_admin_principal',
                           side_effect=lambda key, auth: 'admin' if key == 'synthetic-admin' else None), \
                     patch.object(cdz, 'get_db_connection', side_effect=AssertionError('Legacy DB forbidden')), \
                     patch.object(api.cdz_watcher, 'scan_now', side_effect=AssertionError('Legacy scan forbidden')) as legacy_scan, \
                     TestClient(app) as client:
                    for refused_headers in ({}, {'x-admin-key': 'invalid'}):
                        denied = client.post('/api/audit-ledger/scan', headers=refused_headers)
                        self.assertEqual(denied.status_code, 403)
                        self.assertEqual(denied.headers['cache-control'], 'private, no-store')
                    self.assertEqual(watcher.total_scans, 0)
                    result = client.post('/api/audit-ledger/scan', headers=headers)
                    self.assertEqual(result.status_code, 200)
                    self.assertEqual(result.json()['scan_result']['new_blocks_ingested'], 1)
                    self.assertEqual(result.json()['summary']['total_blocks'], 1)
                    self.assertEqual(result.headers['cache-control'], 'private, no-store')
                    # The response and direct query refer to the same activated store.
                    self.assertEqual(cdz.get_cdz_blocks(store=store)['blocks'][0]['hash'], 'hash-1')
                    repeated = client.post('/api/audit-ledger/scan', headers=headers)
                    self.assertEqual(repeated.status_code, 200)
                    self.assertEqual(repeated.json()['scan_result']['new_blocks_ingested'], 0)
                    self.assertEqual(repeated.json()['summary']['total_blocks'], 1)
                    for label, candidate in (
                        ('absent', None),
                        ('unbound', CDZAuditLedgerWatcher(watch_dirs=[str(source)])),
                        ('mismatched', CDZAuditLedgerWatcher(store=copy(store), watch_dirs=[str(source)])),
                    ):
                        with self.subTest(watcher=label):
                            app.state.cdz_watcher = candidate
                            refused = client.post('/api/audit-ledger/scan', headers=headers)
                            self.assertEqual(refused.status_code, 409)
                            self.assertEqual(refused.headers['cache-control'], 'private, no-store')
                    app.state.cdz_watcher = watcher
                    self.assertTrue(runtime.close(timeout=5))
                    second = ledger(2)
                    failed = client.post('/api/audit-ledger/scan', headers=headers)
                    self.assertEqual(failed.status_code, 500)
                    self.assertEqual(failed.json(), {'detail': 'Host-control request failed.'})
                    self.assertEqual(failed.headers['cache-control'], 'private, no-store')
                    for private_value in (str(root), str(first), str(second), 'Legacy'):
                        self.assertNotIn(private_value, failed.text)
                    legacy_scan.assert_not_called()
                with closing(sqlite3.connect(store.path)) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM cdz_audit_ledger').fetchone()[0], 1)
                    self.assertEqual(db.execute('SELECT value FROM sentinel').fetchall(), [('preserved',)])
                with closing(sqlite3.connect(runtime.stores['master'].path)) as db:
                    self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='cdz_audit_ledger'").fetchone())
            finally:
                self.assertTrue(runtime.close(timeout=5))


if __name__ == '__main__':
    unittest.main(verbosity=2)
