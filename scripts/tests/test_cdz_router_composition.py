"""Mounted real CDZ router and shared runtime; disposable DBs, no live app/network."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.swarm_runtime import SwarmRuntime
from database import cdz_audit_db as cdz
from routers import audit_ledger_router as api


class CDZRouterCompositionTests(unittest.TestCase):
    def test_mounted_shared_runtime_auth_queries_and_failure_boundaries(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-http-') as temp:
            root = Path(temp)
            workspace = root / 'tasks'
            workspace.mkdir()
            project = root / 'project'
            for directory in ('backend', 'database'):
                path = project / directory / 'aibs_master.db'
                path.parent.mkdir(parents=True)
                self.assertTrue(path.resolve().is_relative_to(root.resolve()))
                with closing(sqlite3.connect(path)) as db:
                    db.execute('CREATE TABLE sentinel(value TEXT)')
                    db.commit()
            runtime = SwarmRuntime(workspace, project_root=project,
                                   config_path=ROOT / 'config/swarm_orchestration.json')
            store = runtime.stores['cdz_audit']
            store.activate(root / 'before.sqlite', allow_activation=True)
            ledger = root / 'fixture.json'
            ledger.write_text(json.dumps({'records': [{'index': 1, 'timestamp': 1700000000,
                'domain': 'synthetic', 'event': 'fixture', 'detail': 'temporary only',
                'hash': 'h1', 'prev_hash': 'h0', 'full_hash': 'full1'}]}))
            app = FastAPI()
            app.state.swarm_runtime = runtime
            app.include_router(api.router)
            headers = {'x-admin-key': 'synthetic-admin', 'x-client-id': 'caller-cannot-select-owner'}
            try:
                with patch('security.host_control_access.get_admin_principal', side_effect=lambda key, auth: 'admin' if key == 'synthetic-admin' else None), patch.object(cdz, 'get_db_connection', side_effect=AssertionError('No legacy fallback')), patch.object(api.cdz_watcher, 'get_status', return_value={'running': False}), patch.object(api.cdz_watcher, 'scan_now', side_effect=AssertionError('No real source scan')) as scan, TestClient(app) as client:
                    cdz.ingest_ledger_file(str(ledger), store=store)
                    for route in ('summary', 'blocks'):
                        denied = client.get('/api/audit-ledger/' + route)
                        self.assertEqual(denied.status_code, 403)
                        self.assertEqual(denied.headers['cache-control'], 'private, no-store')
                    summary = client.get('/api/audit-ledger/summary', headers=headers)
                    self.assertEqual(summary.status_code, 200)
                    self.assertEqual(summary.json()['total_blocks'], 1)
                    self.assertEqual(summary.json()['tenant'], 'stehouwer_publishing')
                    self.assertEqual(summary.json()['verification_scope'], 'stored_audit_records_only')
                    blocks = client.get('/api/audit-ledger/blocks?domain=synthetic&event=fixture&search=temporary&limit=1', headers=headers)
                    self.assertEqual(blocks.status_code, 200)
                    self.assertEqual(blocks.json()['blocks'][0]['hash'], 'h1')
                    self.assertEqual(blocks.headers['cache-control'], 'private, no-store')
                    invalid = client.get('/api/audit-ledger/blocks?limit=0', headers=headers)
                    self.assertEqual(invalid.status_code, 422)
                    refused = client.post('/api/audit-ledger/scan', headers=headers)
                    self.assertEqual(refused.status_code, 409)
                    self.assertEqual(refused.headers['cache-control'], 'private, no-store')
                    scan.assert_not_called()
                    self.assertTrue(runtime.close(timeout=5))
                    for route in ('summary', 'blocks'):
                        failed = client.get('/api/audit-ledger/' + route, headers=headers)
                        self.assertEqual(failed.status_code, 500)
                        self.assertEqual(failed.json(), {'detail': 'Host-control request failed.'})
                        self.assertNotIn(str(root), failed.text)
                        self.assertEqual(failed.headers['cache-control'], 'private, no-store')
                    app.state.swarm_runtime = object()
                    malformed = client.get('/api/audit-ledger/summary', headers=headers)
                    self.assertEqual(malformed.status_code, 500)
                    app.state.swarm_runtime = SimpleNamespace(stores={'cdz_audit': None})
                    missing = client.get('/api/audit-ledger/summary', headers=headers)
                    self.assertEqual(missing.status_code, 500)
                    app.state.swarm_runtime = SimpleNamespace(stores={'cdz_audit': runtime.stores['master']})
                    wrong = client.get('/api/audit-ledger/summary', headers=headers)
                    self.assertEqual(wrong.status_code, 500)
                with closing(sqlite3.connect(runtime.stores['master'].path)) as db:
                    self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='cdz_audit_ledger'").fetchone())
                with closing(sqlite3.connect(store.path)) as db:
                    self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            finally:
                self.assertTrue(runtime.close(timeout=5))

    def test_unbound_default_router_uses_synthetic_legacy_database(self):
        with tempfile.TemporaryDirectory(prefix='aibs-cdz-http-legacy-') as temp:
            app = FastAPI()
            app.include_router(api.router)
            with patch.object(cdz, 'DB_PATH', str(Path(temp) / 'legacy.db')), patch('security.host_control_access.get_admin_principal', return_value='admin'), patch.object(api.cdz_watcher, 'get_status', return_value={'running': False}), patch.object(api.cdz_watcher, 'scan_now', return_value={'synthetic': True}) as scan, TestClient(app) as client:
                self.assertEqual(client.get('/api/audit-ledger/summary').status_code, 200)
                self.assertEqual(client.get('/api/audit-ledger/blocks').json()['total'], 0)
                result = client.post('/api/audit-ledger/scan')
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['scan_result'], {'synthetic': True})
                scan.assert_called_once_with()


if __name__ == '__main__':
    unittest.main(verbosity=2)
