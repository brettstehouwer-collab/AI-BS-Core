"""Exercise actual declared middleware policy and owned capture, with temp data."""
import ast
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
import fe_express_owned_records as records


def production_policy():
    source = Path(__file__).resolve().parents[1] / 'AI_BS_Backend.py'
    calls = [node for node in ast.walk(ast.parse(source.read_text(encoding='utf-8-sig')))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
             and node.func.attr == 'add_middleware' and node.args
             and isinstance(node.args[0], ast.Name) and node.args[0].id == 'CORSMiddleware']
    if len(calls) != 1:
        raise AssertionError('Unambiguous current production CORS declaration required')
    return {item.arg: ast.literal_eval(item.value) for item in calls[0].keywords}


class FECaptureCorsTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'AI_BS_ADMIN_KEY': 'fixture-cors-admin-key'})
        self.environment.start()
        self.temp = tempfile.TemporaryDirectory(prefix='aibs-fe-cors-')
        self.database = Path(self.temp.name) / 'work.sqlite3'
        app = FastAPI()
        app.add_middleware(CORSMiddleware, **production_policy())
        app.include_router(records.router)
        app.dependency_overrides[records.database_path] = lambda: self.database
        self.client = TestClient(app)
        self.path = '/api/v1/fe-express/driver-records'

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()
        self.environment.stop()

    def preflight(self, origin, headers='authorization,content-type,x-operation-id'):
        return self.client.options(self.path + '/loads/fixture/attachments', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': headers})

    def test_hosted_capture_header(self):
        origin = 'https://ai-bs-dashboard.web.app'
        response = self.preflight(origin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-origin'], origin)
        self.assertIn('x-operation-id', response.headers['access-control-allow-headers'].lower())
        self.assertFalse(self.database.exists())

    def test_desktop_capture_header(self):
        origin = 'http://localhost:5173'
        response = self.preflight(origin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['access-control-allow-origin'], origin)

    def test_foreign_origin_denied(self):
        response = self.preflight('https://untrusted.invalid')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('access-control-allow-origin', response.headers)

    def test_unlisted_header_remains_denied(self):
        response = self.preflight('https://ai-bs-dashboard.web.app', 'authorization,x-force-owner')
        self.assertEqual(response.status_code, 400)

    def test_anonymous_capture_remains_denied(self):
        response = self.client.post(self.path + '/sync', json={},
                                    headers={'Origin': 'https://ai-bs-dashboard.web.app'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.database.exists())

    def test_admitted_operation_preserves_identity_and_bytes(self):
        headers = {'X-Admin-Key': 'fixture-cors-admin-key', 'Origin': 'https://ai-bs-dashboard.web.app'}
        response = self.client.post(self.path + '/sync', headers=headers, json={
            'op_id': 'fixture-save', 'load_id': 'fixture-load', 'base_revision': 0,
            'payload': {'load_ref': 'synthetic-capture'}})
        self.assertEqual(response.status_code, 200)
        content = b'synthetic-evidence-original'
        response = self.client.post(self.path + '/loads/fixture-load/attachments', content=content,
            headers={**headers, 'X-Operation-Id': 'fixture-evidence', 'Content-Type': 'application/pdf'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attachment_id'], 'fixture-evidence')
        self.assertEqual(response.json()['sha256'], hashlib.sha256(content).hexdigest())
        self.assertEqual(response.headers['access-control-allow-origin'], headers['Origin'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
