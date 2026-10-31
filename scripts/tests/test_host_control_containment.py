"""Offline host-control regression tests using selected source definitions.

Only selected source definitions execute. No application/engine/provider imports,
real process/device calls or live databases are permitted. Writes use temporary
fixtures only; production files are read as source and never imported.
"""
import ast
import asyncio
import builtins
import inspect
import json
import logging
import ntpath
import os
import re
from pathlib import Path
import subprocess
import time
import tempfile
import threading
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Body, Depends, FastAPI, File, Header, HTTPException, Path as FPath, Query, Request, Response, UploadFile
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError, field_validator

ROOT = Path(os.environ.get('AIBS_AUDIT_SOURCE_ROOT', 'C:/AI-BS'))
PRIVATE_HEADERS = {'Cache-Control': 'private, no-store', 'Vary': 'Authorization, X-Admin-Key, X-Api-Key'}


class ForbiddenEffect(AssertionError):
    pass


class FixtureDispatcher:
    def __init__(self): self.calls = []
    def get_autonomy_mode(self): self.calls.append('mode'); return 'SAFE'
    def get_pending_actions(self): self.calls.append('pending'); return []
    def get_action_history(self, **kwargs): self.calls.append('history'); return []
    def set_autonomy_mode(self, value): self.calls.append('set_mode'); return value
    def dispatch(self, **kwargs): self.calls.append('dispatch'); raise ForbiddenEffect('offline dispatcher denied')
    def resolve_action(self, **kwargs): self.calls.append('resolve'); raise ForbiddenEffect('offline action denied')
    def emergency_halt(self): self.calls.append('halt'); return {'status': 'fixture'}
    def _exec_crypto_order(self, *args): self.calls.append('crypto'); raise ForbiddenEffect('offline exchange denied')
    def _exec_vault_query(self, *args): self.calls.append('vault'); raise ForbiddenEffect('offline store denied')


def fixture_principal(key='', authorization=''):
    return 'offline-verified-admin' if key == 'offline-admin-key' or authorization == 'Bearer offline-admin' else None


def basic_namespace():
    return dict(__name__='offline_host_control_fixture', Any=Any, Dict=Dict, List=List, Optional=Optional,
                Literal=Literal, APIRouter=APIRouter, APIRoute=APIRoute, Body=Body, Depends=Depends,
                FastAPI=FastAPI, Header=Header, HTTPException=HTTPException, FPath=FPath, Path=Path, Query=Query,
                Request=Request, Response=Response, RequestValidationError=RequestValidationError,
                StarletteHTTPException=StarletteHTTPException,
                BaseModel=BaseModel, Field=Field, ConfigDict=ConfigDict, StrictBool=StrictBool,
                StrictInt=StrictInt, StrictStr=StrictStr, field_validator=field_validator,
                asyncio=asyncio, json=json, re=re, time=time, logging=logging, logger=logging.getLogger('offline-host-control'),
                get_admin_principal=fixture_principal, HOST_CONTROL_PRIVATE_HEADERS=PRIVATE_HEADERS)


def load_helper():
    path = ROOT/'backend/security/host_control_access.py'
    namespace = basic_namespace()
    if not path.is_file():
        namespace['AdminHostControlRoute'] = APIRoute
        async def absent_helper(request):
            raise HTTPException(403, 'Host control helper absent', headers=PRIVATE_HEADERS)
        namespace['require_host_admin'] = absent_helper
        return namespace
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or '').startswith(('security.', 'core.', 'backend.')):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Assign, ast.AnnAssign)):
            nodes.append(node)
    exec(compile(ast.fix_missing_locations(ast.Module(nodes, [])), str(path), 'exec'), namespace)
    namespace['get_admin_principal'] = fixture_principal
    return namespace


def extract_router(relative, helper):
    path = ROOT/relative
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'router' for t in node.targets):
            nodes.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            # Only literal constants may initialize this fixture. Constructors,
            # path mutations, SDK clients and arbitrary module code are omitted.
            try:
                ast.literal_eval(node.value)
                nodes.append(node)
            except (ValueError, TypeError):
                pass
    namespace = basic_namespace()
    namespace.update({k: v for k, v in helper.items() if k in
        ('AdminHostControlRoute', 'require_host_admin', 'HOST_CONTROL_PRIVATE_HEADERS')})
    namespace.update(os=types.SimpleNamespace(path=ntpath, environ={'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS': 'true'},
        getenv=lambda key, default='': 'true' if key == 'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS' else default),
        sys=types.SimpleNamespace(path=[]), WORKSPACE_ROOT=Path('E:/offline-never-materialized'),
        BOOTROM_SIGNATURES={}, TOOL_MANIFEST={},
        psutil=Mock(side_effect=ForbiddenEffect('offline host inspection denied')),
        httpx=types.SimpleNamespace(AsyncClient=Mock(side_effect=ForbiddenEffect('offline transport denied'))),
        subprocess=types.SimpleNamespace(run=Mock(side_effect=ForbiddenEffect('offline process denied'))),
        ctypes=Mock(), wintypes=Mock(), sentinel_engine=Mock(), cloud_burst_engine=Mock(),
        EcosystemTelemetryEngine=Mock(side_effect=ForbiddenEffect('offline host inspection denied')),
        ObsBroadcastController=Mock(side_effect=ForbiddenEffect('offline OBS denied')))
    namespace['ctypes'].windll.kernel32.CreateFileW.side_effect = ForbiddenEffect('offline device access denied')
    namespace['executive_dispatcher'] = FixtureDispatcher()
    exec(compile(ast.fix_missing_locations(ast.Module(nodes, [])), str(path), 'exec'), namespace)
    return namespace


class HostControlTests(unittest.TestCase):
    def setUp(self):
        self.helper = load_helper()
        self.routers = [extract_router('backend/routers/executive_cockpit_router.py', self.helper),
                        extract_router('backend/routers/usb_recovery_router.py', self.helper)]
        self.process = Mock(side_effect=ForbiddenEffect('offline subprocess access denied'))
        guard = patch.object(subprocess, 'run', self.process)
        guard.start(); self.addCleanup(guard.stop)
        self.clients = []
        for namespace in self.routers:
            app = FastAPI(); app.include_router(namespace['router'])
            client = TestClient(app, raise_server_exceptions=False)
            self.clients.append(client); self.addCleanup(client.close)
        self.admin = {'Authorization': 'Bearer offline-admin'}
        original_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name.split('.')[0] in {'core', 'modules', 'backend', 'routers', 'clients',
                                     'commercial_gateway', 'requests', 'psutil'}:
                raise ForbiddenEffect('offline application/provider import denied')
            return original_import(name, *args, **kwargs)
        guard = patch.object(builtins, '__import__', side_effect=guarded_import)
        guard.start(); self.addCleanup(guard.stop)

    def test_shared_helper_exists_and_returns_verified_principal_asynchronously(self):
        self.assertTrue((ROOT/'backend/security/host_control_access.py').is_file())
        self.assertTrue(inspect.iscoroutinefunction(self.helper['require_host_admin']))
        scope = {'type': 'http', 'headers': [(b'authorization', b'Bearer offline-admin')]}
        result = asyncio.run(self.helper['require_host_admin'](Request(scope)))
        self.assertEqual(result, 'offline-verified-admin')

    def effect_counts(self, namespace):
        return (len(namespace['executive_dispatcher'].calls),
                len(namespace['subprocess'].run.mock_calls),
                len(namespace['httpx'].AsyncClient.mock_calls),
                len(namespace['psutil'].mock_calls),
                len(namespace['ctypes'].mock_calls),
                len(namespace['sentinel_engine'].mock_calls),
                len(namespace['cloud_burst_engine'].mock_calls),
                len(namespace['EcosystemTelemetryEngine'].mock_calls),
                len(namespace['ObsBroadcastController'].mock_calls))

    def test_all_routes_deny_unverified_callers_before_body_validation_or_effects(self):
        headers_cases = [{}, {'X-Client-ID': 'offline-verified-admin'},
                         {'X-User-Role': 'admin', 'X-User-Email': 'operator@example.invalid'},
                         {'Authorization': 'Bearer unverified'}]
        for namespace, client in zip(self.routers, self.clients):
            for route in namespace['router'].routes:
                path = route.path.replace('{action_id}', 'offline-action')
                for method in route.methods - {'HEAD', 'OPTIONS'}:
                    for headers in headers_cases:
                        with self.subTest(path=path, method=method, headers=headers):
                            before = self.process.call_count
                            effects = self.effect_counts(namespace)
                            response = client.request(method, path, headers=headers, json={})
                            self.assertEqual(response.status_code, 403)
                            self.assertIn('no-store', response.headers.get('cache-control', ''))
                            self.assertEqual(self.process.call_count, before)
                            self.assertEqual(self.effect_counts(namespace), effects)

    def test_verified_admin_read_stays_available_and_private(self):
        result = self.clients[0].get('/api/v1/executive/settings/autonomy', headers=self.admin)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['autonomy_mode'], 'SAFE')
        self.assertIn('no-store', result.headers.get('cache-control', ''))
        self.process.assert_not_called()

    def test_authenticated_git_operations_remain_held_even_with_destructive_flag(self):
        for path in ('vibe-checkpoint', 'vibe-rollback'):
            with self.subTest(path=path):
                self.process.reset_mock()
                response = self.clients[0].post('/api/v1/executive/' + path,
                    headers=self.admin, json={'label': 'offline fixture'})
                self.assertEqual(response.status_code, 503)
                self.assertIn('no-store', response.headers.get('cache-control', ''))
                self.process.assert_not_called()

    def test_authenticated_usb_rebuild_is_held_before_preflight_or_format(self):
        for confirm in (False, True):
            with self.subTest(confirm=confirm):
                result = self.clients[1].post('/api/usb-recovery/rebuild-partition', headers=self.admin,
                    json={'disk_number': 4, 'file_system': 'FAT32', 'volume_label': 'OFFLINE_FIXTURE',
                          'confirm_destructive': confirm})
                self.assertEqual(result.status_code, 503)
                self.assertIn('no-store', result.headers.get('cache-control', ''))
        self.process.assert_not_called()
        self.routers[1]['subprocess'].run.assert_not_called()

    def test_usb_schema_rejects_coercion_and_command_text(self):
        model = self.routers[1]['PartitionRebuildRequest']
        base = {'disk_number': 4, 'file_system': 'FAT32', 'volume_label': 'OFFLINE_FIXTURE',
                'confirm_destructive': True}
        for edits in ({'disk_number': True}, {'disk_number': '4'}, {'disk_number': -1},
                      {'file_system': 'FAT32; offline-command'}, {'volume_label': "fixture'; offline-command"},
                      {'volume_label': 'fixture\ncommand'}, {'volume_label': None}, {'volume_label': ''},
                      {'volume_label': 'A' * 33}, {'confirm_destructive': 'true'},
                      {'file_system': 'EXT4'}, {'unexpected': 'property'}):
            with self.subTest(edits=edits):
                with self.assertRaises(ValidationError): model(**dict(base, **edits))

    def test_direct_destructive_compatibility_handlers_cannot_bypass_hold(self):
        executive, usb = self.routers
        operations = [lambda: executive['rollback_vibe_checkpoint'](),
                      lambda: executive['create_vibe_checkpoint'](executive['VibeCheckpointRequest']()),
                      lambda: usb['rebuild_partition'](usb['PartitionRebuildRequest'](
                          disk_number=4, confirm_destructive=True), tenant='offline-verified-admin')]
        for operation in operations:
            with self.subTest(operation=operations.index(operation)):
                observed = None
                try:
                    asyncio.run(operation())
                except HTTPException as exc:
                    observed = exc.status_code
                except ForbiddenEffect:
                    observed = 'forbidden_effect_attempted'
                self.assertEqual(observed, 503)


    def test_verified_principal_is_resolved_off_the_event_loop_for_supported_headers(self):
        main_thread = threading.get_ident()
        for headers, expected_key, expected_authorization in (
                ([(b'authorization', b'Bearer offline-admin')], '', 'Bearer offline-admin'),
                ([(b'x-admin-key', b'offline-admin-key')], 'offline-admin-key', ''),
                ([(b'x-api-key', b'offline-admin-key')], 'offline-admin-key', '')):
            with self.subTest(headers=headers):
                calls = []
                def resolver(key='', authorization=''):
                    calls.append((key, authorization, threading.get_ident()))
                    return fixture_principal(key, authorization)
                with patch.dict(self.helper, {'get_admin_principal': resolver}):
                    try:
                        result = asyncio.run(self.helper['require_host_admin'](Request(
                            {'type': 'http', 'headers': headers})))
                    except HTTPException as exc:
                        self.fail(f'Verified fixture administrator was denied: {exc.status_code}')
                self.assertEqual(result, 'offline-verified-admin')
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][:2], (expected_key, expected_authorization))
                self.assertNotEqual(calls[0][2], main_thread)

    def test_verification_failure_returns_private_denial_without_exception_details(self):
        def verifier_failure(*args, **kwargs):
            raise RuntimeError('OFFLINE_PRIVATE_VERIFIER_ERROR')
        with patch.dict(self.helper, {'get_admin_principal': verifier_failure}):
            response = self.clients[0].get('/api/v1/executive/settings/autonomy', headers=self.admin)
        self.assertEqual(response.status_code, 403)
        self.assertIn('no-store', response.headers.get('cache-control', ''))
        self.assertNotIn('OFFLINE_PRIVATE', response.text)

    def test_unauthenticated_malformed_body_is_denied_before_decoding(self):
        for client, path in ((self.clients[0], '/api/v1/executive/chat'),
                             (self.clients[1], '/api/usb-recovery/rebuild-partition')):
            with self.subTest(path=path):
                response = client.post(path, content=b'{"OFFLINE_PRIVATE_INVALID_BODY":',
                                       headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 403)
                self.assertIn('no-store', response.headers.get('cache-control', ''))
                self.assertNotIn('OFFLINE_PRIVATE_INVALID_BODY', response.text)

    def test_usb_probe_schema_rejects_non_integer_negative_and_unknown_fields(self):
        model = self.routers[1]['ProbeRequest']
        for values in ({'disk_number': True}, {'disk_number': '4'}, {'disk_number': -1},
                       {'disk_number': 4.0}, {'disk_number': 4, 'unexpected': True}):
            with self.subTest(values=values):
                with self.assertRaises(ValidationError): model(**values)
        self.assertEqual(model(disk_number=4).disk_number, 4)

    def test_each_route_declares_the_shared_administrator_boundary(self):
        expected = self.helper['AdminHostControlRoute']
        self.assertIsNot(expected, APIRoute)
        for namespace in self.routers:
            for route in namespace['router'].routes:
                with self.subTest(path=route.path): self.assertIsInstance(route, expected)

    def privacy_client(self):
        temporary = tempfile.TemporaryDirectory(prefix='aibs-host-control-',
            dir=os.environ.get('AIBS_AUDIT_TEMP_ROOT'))
        self.addCleanup(temporary.cleanup)
        fixture = Path(temporary.name)/'fixture.txt'
        fixture.write_text('offline fixture bytes', encoding='utf-8')
        router = APIRouter(route_class=self.helper['AdminHostControlRoute'])
        class PrivateInput(BaseModel):
            count: StrictInt
        @router.get('/plain')
        async def plain():
            response = PlainTextResponse('offline fixture',
                headers={'Vary': 'Accept-Language', 'Cache-Control': 'public, max-age=3600'})
            response.set_cookie('offline_first', 'one')
            response.set_cookie('offline_second', 'two')
            response.headers.append('Vary', 'Accept-Encoding')
            return response
        @router.get('/stream')
        async def stream():
            return StreamingResponse(iter([b'offline fixture']), media_type='text/plain')
        @router.get('/file')
        async def file_response():
            return FileResponse(fixture)
        @router.get('/denial')
        async def denial():
            raise StarletteHTTPException(409, 'Reviewed request conflict.',
                headers={'Retry-After': '2', 'Vary': 'Accept-Encoding', 'Cache-Control': 'public'})
        @router.get('/failure')
        async def failure():
            raise RuntimeError('OFFLINE_PRIVATE_RUNTIME_ERROR')
        @router.post('/validation')
        async def validate(req: PrivateInput):
            return {'count': req.count}
        app = FastAPI(); app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(client.close)
        return client

    def test_response_variants_are_private_and_preserve_existing_vary(self):
        client = self.privacy_client()
        for path in ('/plain', '/stream', '/file'):
            with self.subTest(path=path):
                response = client.get(path, headers=self.admin)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers.get('cache-control'), 'private, no-store')
                self.assertIn('Authorization', response.headers.get('vary', ''))
        self.assertIn('Accept-Language', client.get('/plain', headers=self.admin).headers.get('vary', ''))
        self.assertIn('Accept-Encoding', client.get('/plain', headers=self.admin).headers.get('vary', ''))
        self.assertEqual(len(client.get('/plain', headers=self.admin).headers.get_list('set-cookie')), 2)

    def test_reviewed_http_denial_keeps_status_and_auxiliary_headers_private(self):
        response = self.privacy_client().get('/denial', headers=self.admin)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['detail'], 'Reviewed request conflict.')
        self.assertEqual(response.headers.get('retry-after'), '2')
        self.assertEqual(response.headers.get('cache-control'), 'private, no-store')
        self.assertIn('Accept-Encoding', response.headers.get('vary', ''))
        self.assertIn('Authorization', response.headers.get('vary', ''))

    def test_validation_error_is_private_and_does_not_reflect_sensitive_input(self):
        response = self.privacy_client().post('/validation', headers=self.admin,
            json={'count': 'OFFLINE_PRIVATE_VALIDATION_INPUT'})
        self.assertEqual(response.status_code, 422)
        self.assertIn('no-store', response.headers.get('cache-control', ''))
        self.assertNotIn('OFFLINE_PRIVATE_VALIDATION_INPUT', response.text)

    def test_unexpected_error_is_sanitized_and_private(self):
        response = self.privacy_client().get('/failure', headers=self.admin)
        self.assertEqual(response.status_code, 500)
        self.assertIn('no-store', response.headers.get('cache-control', ''))
        self.assertNotIn('OFFLINE_PRIVATE_RUNTIME_ERROR', response.text)


class HostUploadBudgetTests(unittest.TestCase):
    def setUp(self):
        self.helper = load_helper()
        limiter = self.helper.get('limit_host_upload')
        async def absent_limit(request):
            return None
        self.limit = limiter or absent_limit
        guard = patch.dict(self.helper, {'HOST_UPLOAD_REQUEST_MAX_BYTES': 512})
        guard.start(); self.addCleanup(guard.stop)
        self.admin = {'Authorization': 'Bearer offline-admin'}

    def request(self, chunks, headers=(), path='/api/v1/media/upload', method='POST'):
        received = []
        pending = list(chunks)
        async def receive():
            if not pending:
                return {'type': 'http.disconnect'}
            block = pending.pop(0)
            received.append(len(block))
            return {'type': 'http.request', 'body': block, 'more_body': bool(pending)}
        request = Request({'type': 'http', 'method': method, 'path': path,
            'query_string': b'', 'headers': list(headers), 'scheme': 'http'}, receive)
        return request, received

    def upload_client(self, central=False):
        router = APIRouter(route_class=self.helper['AdminHostControlRoute'])
        self.stored = []
        @router.post('/api/v1/media/upload')
        async def uploaded(file: UploadFile = File(...)):
            self.stored.append(file)
            return {'data': (await file.read()).decode('ascii')}
        app = FastAPI(); app.include_router(router)
        if central:
            helper = self.helper
            class CentralBudget(BaseHTTPMiddleware):
                async def dispatch(self, request, call_next):
                    try:
                        await helper['require_host_admin'](request)
                        await helper['limit_host_upload'](request)
                    except HTTPException as exc:
                        return JSONResponse({'detail': exc.detail}, status_code=exc.status_code,
                                            headers=exc.headers)
                    return await call_next(request)
            app.add_middleware(CentralBudget)
        client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(client.close)
        return client

    def test_upload_limiter_is_an_async_shared_api(self):
        self.assertTrue('limit_host_upload' in self.helper, 'Shared upload limiter is absent')
        self.assertTrue(inspect.iscoroutinefunction(self.helper.get('limit_host_upload')))

    def test_declared_oversized_upload_is_denied_before_reading_on_every_alias(self):
        for path in ('/documents/upload', '/api/v1/media/upload',
                     '/api/v1/audio/demucs/upload_and_separate'):
            with self.subTest(path=path):
                request, received = self.request([b'never consumed'], [(b'content-length', b'513')], path)
                with self.assertRaises(HTTPException) as failure:
                    asyncio.run(self.limit(request))
                self.assertEqual(failure.exception.status_code, 413)
                self.assertIn('no-store', failure.exception.headers.get('Cache-Control', ''))
                self.assertEqual(received, [])

    def test_actual_chunked_bytes_stop_at_budget_before_retaining_the_excess(self):
        request, received = self.request([b'a'*300, b'b'*300, b'never consumed'])
        original_receive = request._receive
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(self.limit(request))
        self.assertEqual(failure.exception.status_code, 413)
        self.assertEqual(received, [300, 300])
        self.assertFalse(hasattr(request, '_body'))
        self.assertIs(request._receive, original_receive)

    def test_small_declared_length_cannot_hide_actual_oversized_body(self):
        request, received = self.request([b'a'*300, b'b'*300], [(b'content-length', b'1')])
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(self.limit(request))
        self.assertEqual(failure.exception.status_code, 413)
        self.assertEqual(received, [300, 300])

    def test_exact_budget_is_cached_for_replay_without_changing_receive(self):
        request, received = self.request([b'a'*256, b'b'*256], [(b'content-length', b'512')])
        original_receive = request._receive
        async def exercise():
            await self.limit(request)
            first = await request.body()
            second = await request.body()
            await request.close()
            return first, second
        first, second = asyncio.run(exercise())
        self.assertEqual(first, b'a'*256+b'b'*256)
        self.assertEqual(first, second)
        self.assertEqual(received, [256, 256])
        self.assertIs(request._receive, original_receive)

    def test_already_cached_oversized_body_is_denied_without_receiving(self):
        request, received = self.request([b'never consumed'])
        request._body = b'x'*513
        with self.assertRaises(HTTPException) as failure:
            asyncio.run(self.limit(request))
        self.assertEqual(failure.exception.status_code, 413)
        self.assertEqual(received, [])

    def test_non_upload_paths_and_read_methods_do_not_consume_body(self):
        for path, method in (('/api/v1/executive/chat', 'POST'),
                             ('/api/v1/media/upload', 'GET')):
            with self.subTest(path=path, method=method):
                request, received = self.request([b'never consumed'], path=path, method=method)
                asyncio.run(self.limit(request))
                self.assertEqual(received, [])
                self.assertFalse(hasattr(request, '_body'))

    def test_invalid_and_conflicting_lengths_are_private_bad_requests(self):
        for values in ((b'-1',), (b'invalid',), (b'1', b'2'), (b'1, 2',)):
            with self.subTest(values=values):
                request, received = self.request([b'never consumed'],
                    [(b'content-length', value) for value in values])
                with self.assertRaises(HTTPException) as failure:
                    asyncio.run(self.limit(request))
                self.assertEqual(failure.exception.status_code, 400)
                self.assertIn('no-store', failure.exception.headers.get('Cache-Control', ''))
                self.assertEqual(received, [])

    def test_oversized_admin_stream_never_reaches_multipart_parser_or_handler(self):
        for central in (False, True):
            with self.subTest(central=central):
                client = self.upload_client(central=central)
                parser = AsyncMock(side_effect=ForbiddenEffect('multipart parser reached before upload admission'))
                headers = dict(self.admin, **{'Content-Type': 'multipart/form-data; boundary=fixture'})
                with patch('starlette.formparsers.MultiPartParser.parse', parser):
                    response = client.post('/api/v1/media/upload', headers=headers,
                                           content=iter([b'a'*300, b'b'*300]))
                self.assertEqual(response.status_code, 413)
                self.assertEqual(response.headers.get('cache-control'), 'private, no-store')
                parser.assert_not_called()
                self.assertEqual(self.stored, [])

    def test_unverified_oversized_upload_is_denied_before_body_budget_and_parser(self):
        client = self.upload_client()
        produced = []
        def chunks():
            produced.append('body read')
            yield b'x'*600
        parser = AsyncMock(side_effect=ForbiddenEffect('unverified multipart parser attempted'))
        with patch('starlette.formparsers.MultiPartParser.parse', parser):
            response = client.post('/api/v1/media/upload', content=chunks(),
                headers={'Content-Type': 'multipart/form-data; boundary=fixture', 'Content-Length': '600'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.get('cache-control'), 'private, no-store')
        self.assertEqual(produced, [])
        parser.assert_not_called()
        self.assertEqual(self.stored, [])

    def test_valid_multipart_is_replayed_and_upload_file_is_closed(self):
        for central in (False, True):
            with self.subTest(central=central):
                response = self.upload_client(central=central).post('/api/v1/media/upload', headers=self.admin,
                    files={'file': ('fixture.txt', b'offline fixture', 'text/plain')})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'data': 'offline fixture'})
                self.assertEqual(len(self.stored), 1)
                self.assertTrue(self.stored[0].file.closed)


class LegacyTelemetryPrivacyTests(unittest.TestCase):
    def fixture(self,authorization=''):
        path=ROOT/'backend/routers/telemetry_websocket.py'
        async def verifier(websocket):
            if websocket.headers.get('authorization')!='Bearer fixture-admin':raise HTTPException(403,'fixture denied')
            return 'fixture-owner'
        database=Mock()
        database.Row=object
        database.connect.return_value.cursor.return_value.fetchall.return_value=[{'fixture_private':'not-live'}]
        socket=types.SimpleNamespace(headers={'authorization':authorization},accept=AsyncMock(),close=AsyncMock(),send_json=AsyncMock())
        namespace=dict(APIRouter=APIRouter,WebSocket=WebSocket,WebSocketDisconnect=WebSocketDisconnect,
            HTTPException=HTTPException,List=List,Dict=Dict,re=re,require_host_admin=verifier,
            sqlite3=database,os=types.SimpleNamespace(path=types.SimpleNamespace(join=lambda *a:'fixture-path',exists=lambda p:True)),
            asyncio=types.SimpleNamespace(sleep=AsyncMock(side_effect=WebSocketDisconnect(1000))))
        nodes=[n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
        namespace['router']=APIRouter()
        exec(compile(ast.Module(nodes,[]),str(path),'exec'),namespace)
        namespace['manager']=namespace['ConnectionManager']()
        namespace['RESOURCE_DIR']='fixture-only'
        return namespace,socket,database

    def test_anonymous_socket_is_denied_before_accept_or_database(self):
        ns,socket,database=self.fixture()
        asyncio.run(ns['websocket_telemetry_endpoint'](socket,'finance'))
        socket.accept.assert_not_called();database.connect.assert_not_called()
        socket.close.assert_awaited_once_with(code=1008,reason='Verified administrator authorization is required.')

    def test_authenticated_legacy_stream_is_unavailable_without_fake_rows_or_sqlite_writes(self):
        ns,socket,database=self.fixture('Bearer fixture-admin')
        asyncio.run(ns['websocket_telemetry_endpoint'](socket,'finance'))
        socket.accept.assert_awaited_once();database.connect.assert_not_called()
        payload=socket.send_json.call_args.args[0]
        self.assertEqual(payload['status'],'unavailable');self.assertIsNone(payload['data'])
        socket.close.assert_awaited_once_with(code=1013,reason='Verified telemetry producer unavailable.')
        self.assertEqual(ns['manager'].active_connections,[])

    def test_industry_paths_are_rejected_before_any_store_access(self):
        for industry in ('..\\private','C:\\private','../private','file:stream','a'*65):
            with self.subTest(industry=industry):
                ns,socket,database=self.fixture('Bearer fixture-admin')
                asyncio.run(ns['websocket_telemetry_endpoint'](socket,industry))
                socket.close.assert_awaited_once_with(code=1008,reason='Invalid industry identifier.')
                database.connect.assert_not_called();socket.send_json.assert_not_called()

    def test_audit_chain_router_has_admin_boundary_and_ignores_caller_tenant(self):
        path=ROOT/'backend/routers/audit_ledger_router.py';tree=ast.parse(path.read_text(encoding='utf-8-sig'))
        router=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='router' for t in n.targets))
        self.assertTrue(any(k.arg=='route_class' and isinstance(k.value,ast.Name) and k.value.id=='AdminHostControlRoute' for k in router.value.keywords))
        tenant=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_tenant')
        namespace=dict(Optional=Optional,Header=Header)
        exec(compile(ast.Module([tenant],[]),str(path),'exec'),namespace)
        self.assertEqual(namespace['get_tenant']('forged-owner'),'stehouwer_publishing')


class WebSocketAdmissionTests(unittest.TestCase):
    def fixture(self, headers=(), scope_type='websocket', verifier=None):
        helper=load_helper()
        if verifier is not None:helper['get_admin_principal']=verifier
        calls=[];sent=[];reads=[]
        async def downstream(scope,receive,send):calls.append(scope)
        async def receive():
            reads.append(True)
            raise ForbiddenEffect('Socket body read before admission')
        async def send(message):sent.append(message)
        middleware=helper.get('AdminWebSocketBoundaryMiddleware',lambda app:app)(downstream)
        scope={'type':scope_type,'path':'/ws/telemetry','headers':list(headers),
               'query_string':b'authorization=Bearer%20offline-admin','scheme':'ws'}
        asyncio.run(middleware(scope,receive,send))
        return calls,sent,reads

    def test_anonymous_socket_never_reaches_handler_or_reads_frames(self):
        calls,sent,reads=self.fixture()
        self.assertEqual(calls,[]);self.assertEqual(reads,[])
        self.assertEqual(sent,[{'type':'websocket.close','code':1008,
                               'reason':'Verified administrator authorization is required.'}])

    def test_only_verified_header_credentials_admit_socket(self):
        calls,sent,reads=self.fixture([(b'authorization',b'Bearer offline-admin')])
        self.assertEqual(len(calls),1);self.assertEqual(sent,[]);self.assertEqual(reads,[])

    def test_verifier_failure_denies_without_detail_leak(self):
        def failure(*args):raise ValueError('PRIVATE_FIXTURE_PROVIDER_ERROR')
        calls,sent,reads=self.fixture([(b'x-admin-key',b'offline-admin-key')],verifier=failure)
        self.assertEqual(calls,[]);self.assertEqual(reads,[])
        self.assertEqual(sent[0]['code'],1008)
        self.assertNotIn('PRIVATE_FIXTURE',str(sent))

    def test_http_and_lifespan_passthrough_without_verifier(self):
        for kind in ('http','lifespan'):
            with self.subTest(kind=kind):
                verifier=Mock(side_effect=ForbiddenEffect('Non-socket authentication attempted'))
                calls,sent,reads=self.fixture(scope_type=kind,verifier=verifier)
                self.assertEqual(len(calls),1);verifier.assert_not_called()

    def test_global_socket_boundary_is_registered_in_main(self):
        tree=ast.parse((ROOT/'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
        registrations=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
            and isinstance(n.func.value,ast.Name) and n.func.value.id=='app'
            and n.func.attr=='add_middleware']
        boundary=[n for n in registrations if any(isinstance(a,ast.Name)
            and a.id=='AdminWebSocketBoundaryMiddleware' for a in n.args)]
        self.assertEqual(len(boundary),1)
        self.assertEqual(boundary[0].lineno,max(n.lineno for n in registrations),
                         'Socket admission must precede telemetry middleware acceptance observations.')


class EmailDispatchContainmentTests(unittest.TestCase):
    def test_email_router_requires_verified_admin_before_parsing(self):
        tree=ast.parse((ROOT/'backend/routers/email_client_router.py').read_text(encoding='utf-8-sig'))
        node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='router' for t in n.targets))
        self.assertTrue(any(k.arg=='route_class' and isinstance(k.value,ast.Name)
                            and k.value.id=='AdminHostControlRoute' for k in node.value.keywords))

    def test_smtp_is_held_before_credentials_or_network_even_if_flag_true(self):
        path=ROOT/'backend/routers/email_client_router.py'
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='send_email')
        node.decorator_list=[]
        creds=Mock(side_effect=ForbiddenEffect('SMTP credentials read before dispatch hold'))
        ns={'SendEmailPayload':Any,'HTTPException':HTTPException,'JSONResponse':JSONResponse,
            '_load_env_credentials':creds,'os':types.SimpleNamespace(getenv=lambda *args:'true')}
        exec(compile(ast.Module([node],[]),str(path),'exec'),ns)
        with self.assertRaises(HTTPException) as denial:
            asyncio.run(ns['send_email'](types.SimpleNamespace(to='fixture@example.invalid')))
        self.assertEqual(denial.exception.status_code,503);creds.assert_not_called()

    def test_duplicate_relay_never_reports_unperformed_delivery(self):
        path=ROOT/'backend/AI_BS_Backend.py'
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='send_email_relay')
        node.decorator_list=[]
        ns={'EmailSendPayload':Any,'HTTPException':HTTPException,'time':types.SimpleNamespace(time=lambda:123)}
        exec(compile(ast.Module([node],[]),str(path),'exec'),ns)
        with self.assertRaises(HTTPException) as denial:
            asyncio.run(ns['send_email_relay'](types.SimpleNamespace(to='fixture@example.invalid')))
        self.assertEqual(denial.exception.status_code,503)

    def test_central_boundary_also_covers_email_aliases(self):
        tree=ast.parse((ROOT/'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
        node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AdminExecutionBoundaryMiddleware')
        prefixes=next(ast.literal_eval(n.value) for n in node.body if isinstance(n,ast.Assign)
                      and any(isinstance(t,ast.Name) and t.id=='SENSITIVE_PREFIXES' for t in n.targets))
        self.assertTrue(any('/api/v1/emails/send'.startswith(p) for p in prefixes))

    def test_gmail_outbox_approval_is_held_before_draft_read_or_provider_import(self):
        path=ROOT/'backend/AI_BS_Backend.py'
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.AsyncFunctionDef) and n.name=='approve_and_send_email')
        node.decorator_list=[]
        opener=Mock(side_effect=ForbiddenEffect('Outbox accessed before dispatch hold'))
        ns={'ApproveSendRequest':Any,'HTTPException':HTTPException,'JSONResponse':JSONResponse,
            '_backend_dir':'fixture-only','os':types.SimpleNamespace(path=types.SimpleNamespace(join=lambda *a:'fixture-outbox',exists=lambda p:True)),
            'open':opener}
        exec(compile(ast.Module([node],[]),str(path),'exec'),ns)
        with self.assertRaises(HTTPException) as denial:
            asyncio.run(ns['approve_and_send_email'](types.SimpleNamespace(draft_id='fixture-draft')))
        self.assertEqual(denial.exception.status_code,503);opener.assert_not_called()


class BackgroundStartupPolicyTests(unittest.TestCase):
    def test_audit_watcher_obeys_background_policy_before_import_or_start(self):
        source=ROOT/'backend/AI_BS_Backend.py'
        tree=ast.parse(source.read_text(encoding='utf-8-sig'))
        node=next(n for n in tree.body if any(isinstance(child,ast.ImportFrom) and child.module=='modules.audit_ledger_watcher' for child in ast.walk(n)))
        for flag in (None,'false','true'):
            with self.subTest(flag=flag):
                watcher=types.SimpleNamespace(start=Mock())
                router=APIRouter()
                def import_fixture(name,globals=None,locals=None,fromlist=(),level=0):
                    if name=='modules.audit_ledger_watcher':return types.SimpleNamespace(cdz_watcher=watcher)
                    if name=='routers.audit_ledger_router':return types.SimpleNamespace(router=router)
                    raise ForbiddenEffect('Unexpected startup import')
                imports=dict(vars(builtins));imports['__import__']=import_fixture
                ns={'__builtins__':imports,'app':FastAPI(),'os':types.SimpleNamespace(getenv=lambda key,default=None:default if flag is None else flag),'print':Mock()}
                exec(compile(ast.Module([node],[]),str(source),'exec'),ns)
                if flag=='true':watcher.start.assert_called_once()
                else:watcher.start.assert_not_called()


if __name__ == '__main__': unittest.main()
