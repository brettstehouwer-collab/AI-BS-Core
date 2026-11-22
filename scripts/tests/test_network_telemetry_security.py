"""Offline telemetry security tests: AST definitions, synthetic headers and memory only.

Never import the application, Scapy, sensor modules, provider clients or live stores.
"""
import ast
import asyncio
import inspect
import json
from pathlib import Path
import types
import unittest

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def engine_definitions():
    path = ROOT / 'backend/modules/network_telemetry.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = []
    for node in tree.body:
        # Scapy's top-level import is an optional Try block; never execute it.
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef,
                             ast.AnnAssign)):
            nodes.append(node)
        elif isinstance(node, ast.Assign):
            targets = [n.id for n in node.targets if isinstance(n, ast.Name)]
            if not {'network_telemetry_engine', 'telemetry_manager'} & set(targets):
                nodes.append(node)
    namespace = {'__name__': 'isolated_network_telemetry', 'NPCAP_AVAILABLE': False}
    exec(compile(ast.fix_missing_locations(ast.Module(nodes, [])), str(path), 'exec'), namespace)
    namespace['is_npcap_available'] = lambda: False
    return namespace


def router_definitions(engine, air, principal):
    path = ROOT / 'backend/routers/network_telemetry_router.py'
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or '').startswith(('modules.', 'security.')):
            continue
        nodes.append(node)
    namespace = dict(__name__='isolated_telemetry_router',
                     network_telemetry_engine=engine, telemetry_manager=engine,
                     air_sensor_engine=air, get_admin_principal=principal)
    namespace.update({name: value for name, value in engine_definitions().items()
                      if name.startswith('sanitize_')})
    exec(compile(ast.fix_missing_locations(ast.Module(nodes, [])), str(path), 'exec'), namespace)
    if 'get_air_sensor_engine' in namespace:
        namespace['get_air_sensor_engine'] = lambda: air
    return namespace


def fixture_record(**overrides):
    record = dict(id='offline-tx', type='TRANSACTION', engine='ASGI', protocol='http',
                  timestamp='2026-10-30T22:08:25Z', method='GET', path='/offline-fixture',
                  status_code=200, flow_id='offline-flow', body_bytes_in=0,
                  body_bytes_out=0, headers={'X-Admin-Key': 'synthetic-admin-sentinel',
                                            'X_Local_Token': 'synthetic-local-sentinel',
                                            'Content-Type': 'application/json'})
    record.update(overrides)
    return record


class FixtureEngine:
    def __init__(self):
        import threading
        self.calls = []
        self.lock = threading.Lock()
        self.subscribers = []
        self.capture_mode = 'ASGI'
        self.record = fixture_record()

    def get_summary(self):
        self.calls.append('summary')
        return {'transactions': {}, 'capture_engine': {'mode': 'ASGI'}, 'flows': {}}

    def get_traffic(self, **kwargs):
        self.calls.append('traffic')
        return [self.record]

    def get_flow_correlation(self, **kwargs):
        self.calls.append('correlation')
        return {'target_transaction': self.record, 'correlated_transactions': [self.record]}

    def get_interfaces(self):
        self.calls.append('interfaces')
        return []

    def set_mode(self, **kwargs):
        self.calls.append('capture')
        return {'status': 'success'}

    def clear(self):
        self.calls.append('clear')


class FixtureAir:
    def __init__(self): self.calls = []
    def scan_air(self): self.calls.append('scan'); return {'status': 'success'}
    def get_records(self, **kwargs): self.calls.append('records'); return []
    def get_summary(self): self.calls.append('summary'); return {}


async def response_start(app, path, method='GET', headers=None):
    """Read only ASGI response-start, then cancel streams before an infinite wait."""
    started = asyncio.Event()
    result = {}
    scope = {'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.3'},
             'http_version': '1.1', 'method': method, 'scheme': 'http', 'root_path': '',
             'path': path, 'raw_path': path.encode(), 'query_string': b'',
             'headers': [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
             'client': ('127.0.0.1', 12345), 'server': ('offline.invalid', 80)}
    received = False
    async def receive():
        nonlocal received
        if not received:
            received = True
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        await asyncio.Future()
    async def send(message):
        if message['type'] == 'http.response.start':
            result.update(status=message['status'], headers=dict(message['headers']))
            started.set()
    task = asyncio.create_task(app(scope, receive, send))
    try:
        await asyncio.wait_for(started.wait(), 2)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    return result


class RouteSecurityTests(unittest.TestCase):
    def setUp(self):
        self.engine = FixtureEngine(); self.air = FixtureAir()
        def principal(key='', authorization=''):
            return {'Bearer offline-admin-a': 'verified-admin-a',
                    'Bearer offline-admin-b': 'verified-admin-b'}.get(authorization)
        self.namespace = router_definitions(self.engine, self.air, principal)
        self.app = FastAPI(); self.app.include_router(self.namespace['router'])
        self.client = TestClient(self.app); self.addCleanup(self.client.close)
        self.admin = {'Authorization': 'Bearer offline-admin-a', 'X-Client-ID': 'spoofed-owner'}

    def test_every_route_denies_anonymous_and_spoofed_identity_before_engine_access(self):
        for route in self.namespace['router'].routes:
            for method in route.methods - {'HEAD', 'OPTIONS'}:
                for headers in ({}, {'X-Client-ID': 'verified-admin-a'}, {'Authorization': 'Bearer member'}):
                    with self.subTest(path=route.path, method=method, headers=headers):
                        self.engine.calls.clear(); self.air.calls.clear()
                        response = asyncio.run(response_start(self.app, route.path, method, headers))
                        self.assertEqual(response['status'], 403)
                        self.assertIn(b'no-store', response['headers'].get(b'cache-control', b''))
                        self.assertEqual(self.engine.calls + self.air.calls, [])
        self.assertEqual(self.engine.subscribers, [])

    def test_router_does_not_initialize_sensor_database_at_import(self):
        tree = ast.parse((ROOT / 'backend/routers/network_telemetry_router.py').read_text(encoding='utf-8-sig'))
        eager = [n for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                 for n in ast.walk(node) if isinstance(n, ast.ImportFrom)
                 and (n.module or '').startswith('modules.ambient_sensor_telemetry')]
        self.assertEqual(eager, [])

    def test_authenticated_global_host_scope_uses_verified_principal_and_no_store(self):
        for path in ('summary', 'capture-mode', 'interfaces', 'traffic', 'flows', 'routes',
                     'correlation', 'air/records', 'air/summary'):
            with self.subTest(path=path):
                result = self.client.get('/api/network-telemetry/' + path, headers=self.admin)
                self.assertEqual(result.status_code, 200)
                body = result.json()
                self.assertEqual(body['tenant'], 'verified-admin-a')
                self.assertEqual(body['scope'], 'global_host_admin_only')
                self.assertIn('no-store', result.headers.get('cache-control', ''))

    def test_capture_and_active_air_scan_are_held_even_for_verified_admin(self):
        for mode in ('ASGI', 'NPCAP', 'HYBRID'):
            result = self.client.post('/api/network-telemetry/capture-mode?mode=' + mode, headers=self.admin)
            self.assertIn(result.status_code, (409, 503))
            self.assertIn('no-store', result.headers.get('cache-control', ''))
        result = self.client.get('/api/network-telemetry/air/scan', headers=self.admin)
        self.assertIn(result.status_code, (409, 503))
        self.assertNotIn('capture', self.engine.calls)
        self.assertEqual(self.air.calls, [])

    def test_legacy_traffic_and_nested_correlation_redact_before_readback(self):
        for path in ('traffic', 'correlation'):
            result = self.client.get('/api/network-telemetry/' + path, headers=self.admin)
            self.assertEqual(result.status_code, 200)
            self.assertNotIn('synthetic-admin-sentinel', result.text)
            self.assertNotIn('synthetic-local-sentinel', result.text)
            self.assertIn('application/json', result.text)

    def test_verified_admin_clear_is_explicit_global_control(self):
        result = self.client.post('/api/network-telemetry/clear', headers=self.admin)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['scope'], 'global_host_admin_only')
        self.assertEqual(self.engine.calls, ['clear'])
        self.assertIn('no-store', result.headers.get('cache-control', ''))

    def test_stream_redacts_legacy_queue_records_and_cleans_up_subscription(self):
        async def scenario():
            endpoint = self.namespace['stream_live_telemetry']
            kwargs = {'tenant': 'verified-admin-a'}
            if 'request' in inspect.signature(endpoint).parameters:
                kwargs['request'] = Request({'type': 'http', 'headers': [(b'authorization', b'Bearer offline-admin-a')]})
            response = await endpoint(**kwargs)
            self.assertIn('no-store', response.headers.get('cache-control', ''))
            iterator = response.body_iterator
            try:
                initial = await asyncio.wait_for(anext(iterator), 1)
                self.assertIn('global_host_admin_only', initial)
                self.assertEqual(len(self.engine.subscribers), 1)
                self.engine.subscribers[0].put_nowait(fixture_record())
                packet = await asyncio.wait_for(anext(iterator), 1)
                self.assertNotIn('synthetic-admin-sentinel', packet)
                self.assertNotIn('synthetic-local-sentinel', packet)
            finally:
                await iterator.aclose()
            self.assertEqual(self.engine.subscribers, [])
        asyncio.run(scenario())

    def test_stream_stops_before_new_data_when_administrator_access_is_revoked(self):
        async def scenario():
            endpoint = self.namespace['stream_live_telemetry']
            kwargs = {'tenant': 'verified-admin-a'}
            if 'request' in inspect.signature(endpoint).parameters:
                kwargs['request'] = Request({'type': 'http', 'headers': [(b'authorization', b'Bearer offline-admin-a')]})
            response = await endpoint(**kwargs)
            iterator = response.body_iterator
            try:
                await asyncio.wait_for(anext(iterator), 1)
                self.namespace['get_admin_principal'] = lambda *args: None
                self.engine.subscribers[0].put_nowait({'id': 'must-not-publish-after-revocation'})
                try:
                    data = await asyncio.wait_for(anext(iterator), 1)
                except StopAsyncIteration:
                    data = ''
                self.assertNotIn('must-not-publish-after-revocation', data)
            finally:
                await iterator.aclose()
            self.assertEqual(self.engine.subscribers, [])
        asyncio.run(scenario())


class EngineSecurityTests(unittest.TestCase):
    def setUp(self):
        self.namespace = engine_definitions()
        self.engine = self.namespace['NetworkTelemetryEngine']()

    def test_record_ingest_redacts_variants_and_unknown_headers_without_aliasing(self):
        variants = ['X-Admin-Key', 'x_admin_key', 'X.Admin.Key', 'X-Local-Token',
                    'x_local_token', 'Authorization', 'Cookie', 'X-API-Key',
                    'X-New-Service-Secret']
        headers = {name: 'synthetic-credential-sentinel' for name in variants}
        headers['Content-Type'] = 'application/json'
        record = fixture_record(headers=headers)
        self.engine.record_transaction(record)
        stored = self.engine.transaction_buffer[0]
        self.assertNotIn('synthetic-credential-sentinel', json.dumps(stored))
        self.assertEqual(stored['headers'].get('Content-Type'), 'application/json')
        headers['Content-Type'] = 'mutated-after-ingest'
        self.assertEqual(stored['headers'].get('Content-Type'), 'application/json')

    def test_engine_does_not_import_hardware_capture_bindings_at_startup(self):
        tree = ast.parse((ROOT / 'backend/modules/network_telemetry.py').read_text(encoding='utf-8-sig'))
        eager = [n for node in tree.body if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                 for n in ast.walk(node) if isinstance(n, ast.ImportFrom)
                 and (n.module or '').startswith('scapy')]
        self.assertEqual(eager, [])

    def test_legacy_buffer_traffic_and_flow_correlation_cannot_return_secrets(self):
        record = fixture_record()
        self.engine.transaction_buffer.append(record)
        self.engine.flows['offline-flow'] = {'transaction_ids': ['offline-tx'], 'frame_ids': []}
        for response in (list(self.engine.buffer), self.engine.get_traffic(),
                         self.engine.get_flow_correlation(transaction_id='offline-tx')):
            self.assertNotIn('synthetic-admin-sentinel', json.dumps(response))
            self.assertNotIn('synthetic-local-sentinel', json.dumps(response))

    def test_subscriber_dispatch_also_sanitizes_and_snapshots_legacy_records(self):
        queue = asyncio.Queue()
        self.engine.subscribers.append(queue)
        record = fixture_record()
        self.engine._dispatch_to_subscribers(record)
        published = queue.get_nowait()
        self.assertNotIn('synthetic-admin-sentinel', json.dumps(published))
        record['headers']['Content-Type'] = 'mutated-after-dispatch'
        self.assertEqual(published['headers']['Content-Type'], 'application/json')

    def test_middleware_never_stores_admin_headers_or_asserts_client_owner(self):
        async def scenario():
            async def app(scope, receive, send):
                await send({'type': 'http.response.start', 'status': 204, 'headers': []})
                await send({'type': 'http.response.body', 'body': b''})
            middleware = self.namespace['NetworkTelemetryMiddleware'](app, self.engine)
            async def receive(): return {'type': 'http.request', 'body': b''}
            async def send(message): pass
            scope = {'type': 'http', 'path': '/offline-fixture', 'method': 'GET',
                     'server': ('offline.invalid', 80), 'client': ('127.0.0.1', 1),
                     'headers': [(b'x-admin-key', b'synthetic-admin-sentinel'),
                                 (b'x-local-token', b'synthetic-local-sentinel'),
                                 (b'x-client-id', b'spoofed-owner')]}
            await middleware(scope, receive, send)
            record = self.engine.transaction_buffer[0]
            self.assertNotIn('synthetic-admin-sentinel', json.dumps(record))
            self.assertNotIn('synthetic-local-sentinel', json.dumps(record))
            self.assertNotEqual(record.get('client_id'), 'spoofed-owner')
            self.assertEqual(record.get('client_label'), 'spoofed-owner')
        asyncio.run(scenario())


if __name__ == '__main__': unittest.main()
