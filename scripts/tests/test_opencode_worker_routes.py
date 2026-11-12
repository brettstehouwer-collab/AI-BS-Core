"""Exercise admission, schema, owner binding, failures and disconnect cleanup offline."""
import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
gateway = importlib.import_module('routers.ai_providers_router')


class WorkerError(Exception):
    def __init__(self, code='capacity', status=429):
        self.code = code
        self.status_code = status
        self.public_message = 'Worker capacity is unavailable.'


class WorkerRoutes(unittest.TestCase):
    def setUp(self):
        self.calls = []

        async def run_worker(**kwargs):
            self.calls.append(kwargs)
            return dict(status='completed', content='Synthetic proposal', model=kwargs['model'], receipt={})

        self.worker = types.ModuleType('core.opencode_worker')
        self.worker.run_worker = run_worker
        self.worker.WorkerError = WorkerError
        self.worker.list_worker_models = lambda: [dict(id='beam-free', label='Beam Free')]
        self.modules = patch.dict(sys.modules, {'core.opencode_worker': self.worker})
        self.modules.start()
        self.auth = patch('security.host_control_access.get_admin_principal',
                          side_effect=lambda key, authorization: 'firebase:test-project:owner-a' if key == 'test-only-admin' else None)
        self.auth.start()
        app = FastAPI()
        app.include_router(gateway.router)
        self.client = TestClient(app)
        self.headers = {'X-Admin-Key': 'test-only-admin'}

    def tearDown(self):
        self.client.close()
        self.auth.stop()
        self.modules.stop()

    def test_anonymous_is_rejected_before_body_validation_or_worker(self):
        response = self.client.post('/api/ai/opencode/work', content='not json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('no-store', response.headers['cache-control'])
        self.assertEqual(self.client.get('/api/ai/opencode/models').status_code, 403)
        self.assertEqual(self.calls, [])

    def test_extra_owner_history_and_invalid_types_do_not_reach_worker(self):
        for body in [dict(model='beam-free', prompt='Review', owner='owner-b'),
                     dict(model='beam-free', prompt='Review', messages=['private']),
                     dict(model=123, prompt='Review'), dict(model='beam-free', prompt='')]:
            response = self.client.post('/api/ai/opencode/work', headers=self.headers, json=body)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.calls, [])

    def test_verified_owner_and_only_explicit_task_are_delegated(self):
        response = self.client.post('/api/ai/opencode/work', headers=self.headers,
                                    json=dict(model='beam-free', prompt='Review this loop'))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.calls, [dict(owner='firebase:test-project:owner-a', model='beam-free', prompt='Review this loop', public_input_only=False)])
        self.assertEqual(response.json()['status'], 'completed')
        self.assertIn('no-store', response.headers['cache-control'])

    def test_catalogue_does_not_touch_provider_config(self):
        with patch.object(gateway, 'load_config', side_effect=AssertionError('Provider config must stay untouched')):
            response = self.client.get('/api/ai/opencode/models', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['primary_unchanged'])
        self.assertEqual(len(response.json()['models']), 1)
        self.assertEqual(self.calls, [])

    def test_quota_error_is_preserved_without_fallback_or_replay(self):
        async def fail(**kwargs):
            self.calls.append(kwargs)
            raise WorkerError()
        self.worker.run_worker = fail
        response = self.client.post('/api/ai/opencode/work', headers=self.headers,
                                    json=dict(model='beam-free', prompt='Review'))
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()['detail']['code'], 'capacity')
        self.assertEqual(len(self.calls), 1)

    def test_public_input_declaration_is_strict_and_explicit(self):
        for value in ('true', 1, None):
            response = self.client.post('/api/ai/opencode/work', headers=self.headers,
                json=dict(model='nemotron-3.5-lightning-free', prompt='Review public code', public_input_only=value))
            self.assertEqual(response.status_code, 422)
        response = self.client.post('/api/ai/opencode/work', headers=self.headers,
            json=dict(model='nemotron-3.5-lightning-free', prompt='Review public code', public_input_only=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.calls[0]['public_input_only'], True)


class DisconnectCleanup(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_cancels_and_awaits_worker_cleanup(self):
        started, cleaned = asyncio.Event(), asyncio.Event()
        async def worker(**kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()
        class Request:
            async def is_disconnected(self):
                await started.wait()
                return True
        module = types.ModuleType('core.opencode_worker')
        module.run_worker, module.WorkerError = worker, WorkerError
        with patch.dict(sys.modules, {'core.opencode_worker': module}):
            with self.assertRaises(HTTPException) as failure:
                await gateway.delegate_opencode_work(gateway.OpenCodeWorkerRequest(model='beam-free', prompt='Review'), Request(), owner='local_admin')
        self.assertEqual(failure.exception.status_code, 499)
        self.assertTrue(cleaned.is_set())


if __name__ == '__main__':
    unittest.main()
