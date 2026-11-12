"""Offline AST fixtures only: no application, NVML, provider or live credential imports."""
import ast
import asyncio
import __future__
import json
import logging
from pathlib import Path
import types
import unittest
from unittest.mock import Mock
import urllib.request
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
FAN = ROOT / 'backend/routers/gpu_telemetry_router.py'
VAST = ROOT / 'backend/core/cluster/vast_federation_daemon.py'


def execute(nodes, namespace, filename):
    exec(compile(ast.fix_missing_locations(ast.Module(nodes, [])), str(filename), 'exec',
                 flags=__future__.annotations.compiler_flag), namespace)


def fan_fixture(engine):
    namespace = dict(__name__='offline_fan_fixture', APIRouter=APIRouter, Depends=Depends,
                     HTTPException=HTTPException, Request=Request, Response=Response,
                     BaseModel=BaseModel, Field=Field, model_validator=model_validator,
                     gpu_telemetry_engine=engine, logger=Mock(), asyncio=asyncio,
                     get_admin_principal=lambda key, token: 'fixture-owner' if token == 'Bearer offline-admin' else None)
    auth_path = ROOT / 'backend/security/financial_auth.py'
    execute([node for node in ast.parse(auth_path.read_text(encoding='utf-8-sig')).body
             if isinstance(node, ast.AsyncFunctionDef) and node.name == 'require_financial_owner'], namespace, auth_path)
    selected = []
    for node in ast.parse(FAN.read_text(encoding='utf-8-sig')).body:
        if isinstance(node, ast.ClassDef) and node.name == 'FanControlPayload':
            selected.append(node)
        elif isinstance(node, ast.AsyncFunctionDef) and node.name == 'control_gpu_fan':
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'router' for target in node.targets):
            selected.append(node)
    execute(selected, namespace, FAN)
    app = FastAPI(); app.include_router(namespace['router'])
    return TestClient(app, raise_server_exceptions=False)


class FanSecurityTests(unittest.TestCase):
    def setUp(self):
        self.engine = types.SimpleNamespace(set_fan_speed=Mock(return_value={'success': True, 'message': 'Offline acknowledgement'}))
        self.client = fan_fixture(self.engine)
        self.addCleanup(self.client.close)
        self.url = '/api/v1/hardware/gpu/fan-control'
        self.auth = {'Authorization': 'Bearer offline-admin'}

    def test_anonymous_and_spoofed_callers_never_reach_hardware(self):
        for headers in ({}, {'X-Client-ID': 'fixture-owner'}, {'Authorization': 'Bearer unverified'}):
            result = self.client.post(self.url, headers=headers, json={'speed': 100, 'auto': False})
            self.assertEqual(result.status_code, 403)
            self.assertIn('no-store', result.headers.get('cache-control', ''))
        self.engine.set_fan_speed.assert_not_called()

    def test_verified_manual_and_automatic_controls_preserve_valid_payloads(self):
        for speed, auto in ((30, False), (100, False), (0, True)):
            with self.subTest(speed=speed, auto=auto):
                result = self.client.post(self.url, headers=self.auth, json={'speed': speed, 'auto': auto})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['status'], 'success')
                self.assertIn('no-store', result.headers.get('cache-control', ''))
                self.engine.set_fan_speed.assert_called_with(speed=speed, auto=auto)

    def test_unsafe_or_coerced_values_do_not_reach_hardware(self):
        for payload in ({'speed': 29}, {'speed': 101}, {'speed': -1}, {'speed': True},
                        {'speed': '100'}, {'speed': 100.5}, {'speed': 100, 'auto': 'false'},
                        {'speed': 100, 'extra_control': True}):
            with self.subTest(payload=payload):
                result = self.client.post(self.url, headers=self.auth, json=payload)
                self.assertEqual(result.status_code, 422)
        self.engine.set_fan_speed.assert_not_called()

    def test_driver_failure_does_not_expose_internal_exception_details(self):
        self.engine.set_fan_speed.side_effect = RuntimeError('offline-private-driver-detail')
        result = self.client.post(self.url, headers=self.auth, json={'speed': 100})
        self.assertEqual(result.status_code, 500)
        self.assertNotIn('offline-private-driver-detail', result.text)
        self.assertIn('no-store', result.headers.get('cache-control', ''))


def vast_fixture(key='offline-vast-token', result=None):
    response = types.SimpleNamespace()
    response.__enter__ = lambda self: self
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return json.dumps(result or {'offers': []}).encode()
    transport = Mock(return_value=Reply())
    logger = Mock()
    namespace = dict(__name__='offline_vast_fixture', Any=Any, Dict=Dict, List=List, Optional=Optional,
        json=json, logger=logger, sys=types.SimpleNamespace(executable='offline-python'),
        os=types.SimpleNamespace(name='offline', getenv=lambda name, default='': default),
        _VAST_CLI_PATH=types.SimpleNamespace(exists=lambda: False),
        subprocess=types.SimpleNamespace(run=Mock(side_effect=AssertionError('No processes in fixture'))),
        urllib=types.SimpleNamespace(request=types.SimpleNamespace(Request=urllib.request.Request,
            HTTPRedirectHandler=urllib.request.HTTPRedirectHandler, urlopen=transport,
            build_opener=lambda *handlers: types.SimpleNamespace(open=transport))))
    execute([node for node in ast.parse(VAST.read_text(encoding='utf-8-sig')).body
             if isinstance(node, ast.ClassDef) and node.name != 'FederatedNode'], namespace, VAST)
    daemon = object.__new__(namespace['VastFederationDaemon'])
    daemon.api_key = key; daemon.max_hourly_rate_usd = 0.35
    return daemon, transport, logger, namespace


class VastCredentialTests(unittest.TestCase):
    def test_no_nonempty_provider_key_fallback_exists(self):
        tree = ast.parse(VAST.read_text(encoding='utf-8-sig'))
        unsafe = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == 'getenv'
                  and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'VAST_API_KEY'
                  and len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and bool(node.args[1].value)]
        self.assertTrue(not unsafe, 'Provider credentials must never have a nonempty source fallback')

    def test_missing_key_never_attempts_provider_or_cli(self):
        daemon, transport, _, ns = vast_fixture(key='')
        self.assertEqual(daemon.search_spot_offers(), [])
        transport.assert_not_called(); ns['subprocess'].run.assert_not_called()

    def test_official_bearer_transport_has_no_key_in_url_or_body_and_sends_filters(self):
        daemon, transport, _, _ = vast_fixture(result={'offers': [
            {'id': 7, 'gpu_name': 'Offline GPU', 'gpu_ram': 24576, 'dph_total': 0.2}]})
        offers = daemon.search_spot_offers(min_vram_gb=16, max_price_usd=0.25, limit=3)
        self.assertEqual(len(offers), 1)
        request = transport.call_args.args[0]
        self.assertEqual(request.full_url, 'https://console.vast.ai/api/v0/bundles')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(request.get_header('Authorization'), 'Bearer offline-vast-token')
        self.assertEqual(transport.call_args.kwargs['timeout'], 10)
        body = json.loads(request.data)
        self.assertEqual(body['gpu_ram'], {'gte': 16384})
        self.assertEqual(body['dph_total'], {'lte': 0.25})
        self.assertEqual(body['limit'], 3)
        self.assertNotIn('offline-vast-token', request.full_url + request.data.decode())

    def test_transport_errors_do_not_echo_credentials(self):
        daemon, transport, logger, _ = vast_fixture()
        transport.side_effect = RuntimeError('offline-vast-token')
        self.assertEqual(daemon.search_spot_offers(), [])
        self.assertNotIn('offline-vast-token', str(logger.mock_calls))

    def test_authenticated_search_does_not_forward_credentials_through_redirects(self):
        _, _, _, ns = vast_fixture()
        handler = ns.get('_VastSearchNoRedirect')
        self.assertIsNotNone(handler, 'Authenticated search must refuse automatic redirects')
        result = handler().redirect_request(None, None, 302, 'offline redirect', {}, 'https://offline.invalid')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
