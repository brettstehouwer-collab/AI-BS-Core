"""Network dispatch containment; AST fixtures only, no app/provider/store imports."""
import ast
import asyncio
import copy
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from security import financial_auth


def definitions(path, initial=None):
    """Execute selected definitions; discard imports and application initializers."""
    source = ast.parse(path.read_text(encoding='utf-8-sig'))
    namespace = dict(APIRouter=APIRouter, Depends=Depends, HTTPException=HTTPException,
                     Request=Request, Response=Response, JSONResponse=JSONResponse,
                     BaseModel=BaseModel, Any=Any, Dict=Dict, List=List, Optional=Optional,
                     require_financial_owner=financial_auth.require_financial_owner,
                     __name__='isolated_network_fixture', __file__=str(path))
    namespace.update(initial or {})
    body = []
    for node in source.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'gpu_network_router' for t in node.targets):
                body.append(node)
            else:
                try:
                    ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    continue
                body.append(node)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


class NetworkDispatchTests(unittest.TestCase):
    def setUp(self):
        self.ns = definitions(ROOT / 'backend/commercial_gateway/gpu_network_router.py')
        self.effects = Mock(side_effect=AssertionError('Provider/store/process effect attempted'))
        for name in ('load_real_compute_ledger', 'save_real_compute_ledger'):
            if name in self.ns:
                self.ns['original_' + name] = self.ns[name]
            self.ns[name] = self.effects
        app = FastAPI()
        app.include_router(self.ns['gpu_network_router'])
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        owner = patch.object(financial_auth, 'get_admin_principal',
                             side_effect=lambda key='', auth='': 'owner-a' if auth == 'Bearer offline-a' else None)
        owner.start()
        self.addCleanup(owner.stop)
        self.auth = {'Authorization': 'Bearer offline-a'}

    def test_anonymous_and_spoofed_owners_cannot_reach_any_handler(self):
        routes = [('GET', '/nodes'), ('GET', '/earnings/unknown-fixture'), ('GET', '/treasury-status'),
                  ('POST', '/register-node'), ('POST', '/heartbeat'), ('POST', '/submit-job'), ('POST', '/redeem-payout')]
        for method, route in routes:
            for headers in ({}, {'x-client-id': 'owner-a'}):
                with self.subTest(method=method, route=route, headers=headers):
                    result = self.client.request(method, '/v1/network' + route, headers=headers, json={})
                    self.assertEqual(result.status_code, 403)
                    self.assertIn('no-store', result.headers.get('cache-control', ''))
        self.effects.assert_not_called()

    def test_authorized_mutations_held_before_body_validation_or_side_effect(self):
        before = {key: copy.deepcopy(self.ns[key]) for key in ('JOB_QUEUE', 'EARNINGS_LEDGER', 'NODES_REGISTRY')}
        for route in ('register-node', 'heartbeat', 'submit-job', 'redeem-payout'):
            for body in (b'not-json', b'{"amount_usd":-999,"payout_method":"unknown","prompt_or_code":"fixture"}'):
                with self.subTest(route=route, body=body):
                    result = self.client.post('/v1/network/' + route, headers=dict(self.auth, **{'Content-Type': 'application/json'}), content=body)
                    self.assertEqual(result.status_code, 503)
                    self.assertIn('no-store', result.headers.get('cache-control', ''))
        for key, value in before.items():
            self.assertEqual(self.ns[key], value)
        self.effects.assert_not_called()

    def test_owned_reads_never_admit_legacy_data_or_create_a_ledger(self):
        self.ns['NODES_REGISTRY']['foreign'] = {'private': 'unowned fixture'}
        self.ns['EARNINGS_LEDGER']['foreign'] = {'pending_usd': 999}
        before = copy.deepcopy(self.ns['EARNINGS_LEDGER'])
        for route in ('nodes', 'earnings/unknown-fixture', 'earnings/foreign', 'treasury-status'):
            with self.subTest(route=route):
                response = self.client.get('/v1/network/' + route, headers=self.auth)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data['status'], 'unavailable')
                self.assertEqual(data['schema_version'], 1)
                self.assertFalse(data['payouts_enabled'])
                self.assertFalse(data['job_dispatch_enabled'])
                self.assertFalse(data['registration_enabled'])
                self.assertIsNone(data['hardware'])
                self.assertIsNone(data['treasury'])
                self.assertTrue(all(value is None for value in data['ledger'].values()))
                self.assertFalse(data['idle_policy']['enforced'])
                self.assertNotIn('foreign', response.text)
                self.assertNotIn('999', response.text)
                self.assertIn('no-store', response.headers['cache-control'])
        self.assertEqual(self.ns['EARNINGS_LEDGER'], before)
        self.effects.assert_not_called()

    def test_direct_legacy_ledger_helpers_are_closed(self):
        for name, args in [('load_real_compute_ledger', ()), ('save_real_compute_ledger', ({'pending_usd': 100},))]:
            with self.subTest(name=name), patch('builtins.open', self.effects):
                with self.assertRaises(RuntimeError):
                    self.ns['original_' + name](*args)
        self.effects.assert_not_called()

    def test_no_provider_or_environment_import_initializers(self):
        source = ast.parse((ROOT / 'backend/commercial_gateway/gpu_network_router.py').read_text(encoding='utf-8-sig'))
        imports = [n.module or '' for n in source.body if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(name.startswith(('web3', 'eth_account', 'dotenv', 'aiohttp')) for name in imports))
        for node in source.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                self.assertNotEqual(getattr(node.value.func, 'id', ''), 'load_dotenv')


class ComputeConsumerTests(unittest.TestCase):
    def setUp(self):
        self.effects = Mock(side_effect=AssertionError('Legacy dispatch effect attempted'))
        logger = types.SimpleNamespace(info=lambda *a, **kw: None, warning=lambda *a, **kw: None, error=lambda *a, **kw: None)
        self.ns = definitions(ROOT / 'backend/compute_orchestrator_agent.py',
                              {'JOB_QUEUE': [{'job_id': 'offline-poisoned-queue', 'max_budget_usd': 999, 'prompt_or_code': 'fixture'}],
                               'logger': logger, 'load_real_compute_ledger': self.effects, 'save_real_compute_ledger': self.effects,
                               'os': types.SimpleNamespace(path=types.SimpleNamespace(exists=lambda p: False), makedirs=self.effects),
                               'subprocess': types.SimpleNamespace(run=self.effects), 'time': types.SimpleNamespace(sleep=self.effects)})
        self.agent = self.ns['ComputeOrchestratorAgent']()

    def test_existing_poisoned_queue_cannot_be_consumed_or_credited(self):
        before = copy.deepcopy(self.ns['JOB_QUEUE'])
        result = asyncio.run(self.agent.process_task('offline fixture'))
        self.assertEqual(result['status'], 'held')
        self.assertFalse(result['execution_enabled'])
        self.assertEqual(self.ns['JOB_QUEUE'], before)
        self.effects.assert_not_called()

    def test_direct_dispatch_credit_and_schedule_helpers_are_closed(self):
        for method, args in [('_execute_wsl2_docker_job', ({'job_id': 'fixture'},)), ('_credit_earnings', (999,)), ('_set_swarm_override', (True,))]:
            with self.subTest(method=method), patch('builtins.open', self.effects):
                with self.assertRaises(RuntimeError):
                    getattr(self.agent, method)(*args)
        self.effects.assert_not_called()


if __name__ == '__main__':
    unittest.main()
