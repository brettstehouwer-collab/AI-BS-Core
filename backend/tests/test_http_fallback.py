"""Exercise the actual main fallback without importing its startup side effects."""
import ast
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch
import uuid
from urllib.parse import quote

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))


class HttpFallbackTests(unittest.TestCase):
    def setUp(self):
        checkpoint = os.environ.get('AIBS_FALLBACK_TEST_OUTPUT')
        if not checkpoint:
            raise RuntimeError('Supply an explicit retained synthetic fixture directory')
        self.root = Path(checkpoint) / 'fixtures' / uuid.uuid4().hex
        self.dist = self.root / 'frontend/dist'
        self.public = self.root / 'frontend/public'
        self.dist.mkdir(parents=True)
        self.public.mkdir(parents=True)
        (self.dist / 'index.html').write_text('<html>synthetic SPA</html>', encoding='utf-8')
        self.canary = self.root / 'frontend/private.txt'
        self.canary.write_text('SYNTHETIC_PRIVATE_CANARY', encoding='utf-8')
        self.calls = {'known': 0, 'network': 0}
        outer = self

        class NeverNetwork:
            def __init__(self, *args, **kwargs):
                outer.calls['network'] += 1
                raise AssertionError('Unknown fallback attempted network access')

        self.app = FastAPI()

        @self.app.post('/api/fixture-known')
        async def known():
            self.calls['known'] += 1
            return {'actual_handler': True}

        @self.app.post('/v1/chat/completions')
        async def canonical_chat():
            self.calls['known'] += 1
            return {'canonical_fixture': True}

        @self.app.get('/api/multi-method')
        async def multi_get():
            return {'read': True}

        @self.app.delete('/api/multi-method')
        async def multi_delete():
            return {'delete': True}

        included = APIRouter(prefix='/api/included')

        @included.post('/run')
        async def included_post():
            self.calls['known'] += 1
            return {'included': True}

        nested = APIRouter(prefix='/inner')

        @nested.post('/run')
        @nested.delete('/run')
        async def nested_run():
            self.calls['known'] += 1
            return {'nested': True}

        included.include_router(nested, prefix='/v2')
        self.app.include_router(included, prefix='/gateway')

        tree = ast.parse((ROOT / 'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
        node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'catch_all')
        scope = {'app': self.app, 'Request': Request, '_root_dir': str(self.root), 'os': os,
                 'FileResponse': FileResponse, 'JSONResponse': JSONResponse, 'json': json,
                 'httpx': types.SimpleNamespace(AsyncClient=NeverNetwork)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<actual-main-catch-all>', 'exec'), scope)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()

    def request(self, method, path, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.client.request(method, path, **kwargs)

    def test_unknown_api_get_has_404_not_success(self):
        response = self.request('GET', '/api/no-such-operation')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'detail': 'Not Found'})

    def test_unknown_methods_are_404_without_work(self):
        for method in ['POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']:
            with self.subTest(method=method):
                response = self.request(method, '/v1/no-such-operation', content=b'not-json')
                self.assertEqual(response.status_code, 404)
        self.assertEqual(self.calls, {'known': 0, 'network': 0})

    def test_wrong_method_returns_actual_allow(self):
        response = self.request('GET', '/api/fixture-known')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {'detail': 'Method Not Allowed'})
        self.assertEqual(response.headers['allow'], 'POST')
        self.assertEqual(self.calls['known'], 0)

    def test_method_allow_unions_prior_real_routes(self):
        response = self.request('PUT', '/api/multi-method')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(set(response.headers['allow'].split(', ')), {'GET', 'DELETE'})

    def test_included_router_method_uses_effective_prefix(self):
        response = self.request('GET', '/gateway/api/included/run')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers['allow'], 'POST')
        self.assertEqual(self.calls['known'], 0)

    def test_nested_included_router_unions_effective_methods(self):
        response = self.request('GET', '/gateway/api/included/v2/inner/run')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(set(response.headers['allow'].split(', ')), {'POST', 'DELETE'})
        self.assertEqual(self.calls['known'], 0)

    def test_known_post_still_reaches_original_route(self):
        response = self.request('POST', '/api/fixture-known')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'actual_handler': True})
        self.assertEqual(self.calls['known'], 1)

    def test_canonical_chat_is_not_replaced(self):
        response = self.request('POST', '/v1/chat/completions', json={'messages': []})
        self.assertEqual(response.json(), {'canonical_fixture': True})
        self.assertEqual(self.calls, {'known': 1, 'network': 0})

    def test_wrong_chat_method_cannot_generate(self):
        response = self.request('GET', '/v1/chat/completions')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.headers['allow'], 'POST')
        self.assertEqual(self.calls, {'known': 0, 'network': 0})

    def test_substring_chat_aliases_never_dispatch(self):
        for path in ['/api/no-such/chat/completions', '/untrusted/chat/completions',
                     '/v1/chat/completions-extra', '/api/v1/chat/completions']:
            with self.subTest(path=path):
                response = self.request('POST', path, content=b'not-json')
                self.assertEqual(response.status_code, 404)
        self.assertEqual(self.calls, {'known': 0, 'network': 0})

    def test_substring_model_aliases_do_not_contact_ollama(self):
        for method in ['GET', 'POST']:
            with self.subTest(method=method):
                response = self.request(method, '/api/no-such-models')
                self.assertEqual(response.status_code, 404)
        self.assertEqual(self.calls['network'], 0)

    def test_static_index_and_spa_preserved(self):
        for path in ['/', '/index.html', '/workspace/screenwriting']:
            with self.subTest(path=path):
                response = self.request('GET', path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, '<html>synthetic SPA</html>')

    def test_asset_and_public_fallback_preserved(self):
        (self.dist / 'assets').mkdir()
        (self.dist / 'assets/main.js').write_text('window.fixture = true;', encoding='utf-8')
        (self.public / 'download.txt').write_text('synthetic public download', encoding='utf-8')
        self.assertEqual(self.request('GET', '/assets/main.js').text, 'window.fixture = true;')
        self.assertEqual(self.request('GET', '/download.txt').text, 'synthetic public download')

    def test_apk_content_type_preserved(self):
        (self.public / 'AI-BS-Mobile.apk').write_bytes(b'synthetic-apk-not-an-executable')
        response = self.request('GET', '/AI-BS-Mobile.apk')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/vnd.android.package-archive')

    def test_head_has_headers_without_file_body(self):
        response = self.request('HEAD', '/index.html')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertEqual(int(response.headers['content-length']), len(b'<html>synthetic SPA</html>'))

    def test_api_namespace_cannot_be_static_or_spa(self):
        for prefix in ['api', 'v1', 'API']:
            folder = self.public / prefix
            folder.mkdir(exist_ok=True)
            (folder / 'shadow.json').write_text('{"false_success":true}', encoding='utf-8')
            with self.subTest(prefix=prefix):
                response = self.request('GET', '/' + prefix + '/shadow.json')
                self.assertEqual(response.status_code, 404)

    def test_encoded_windows_traversal_and_absolute_file_denied(self):
        paths = ['/%2e%2e%5cprivate.txt', '/%2e%2e/private.txt',
                 '/' + quote(str(self.canary), safe='')]
        for path in paths:
            with self.subTest(path=path):
                response = self.request('GET', path)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn('SYNTHETIC_PRIVATE_CANARY', response.text)

    def test_hidden_ads_device_and_alias_paths_denied(self):
        (self.public / '.env').write_text('synthetic-private-setting', encoding='utf-8')
        (self.public / '.well-known').mkdir()
        (self.public / '.well-known/proof.txt').write_text('public-proof', encoding='utf-8')
        for path in ['/.env', '/.git/config', '/file.txt%3Ahidden', '/CON.txt', '/dir/NUL',
                     '/file.txt.', '/space%20', '/%00', '/a%5cb']:
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path).status_code, 404)
        self.assertEqual(self.request('GET', '/.well-known/proof.txt').text, 'public-proof')

    @unittest.skipUnless(os.name == 'nt', 'Real Windows junction fixture')
    def test_junction_cannot_escape_public_directory(self):
        private = self.root / 'private'; private.mkdir()
        (private / 'document.txt').write_text('SYNTHETIC_PRIVATE_CANARY', encoding='utf-8')
        linked = self.dist / 'escape'
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(linked), str(private)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, 'Synthetic junction fixture creation failed')
        self.assertTrue(linked.is_junction())
        response = self.request('GET', '/escape/document.txt')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('SYNTHETIC_PRIVATE_CANARY', response.text)

    def test_compatibility_selection_is_exact_and_method_bound(self):
        helper = importlib.import_module('core.http_fallback')
        self.assertEqual(helper.compatibility_target('v1/chat/completions', 'POST'), 'chat')
        self.assertEqual(helper.compatibility_target('v1/models', 'GET'), 'models')
        for path, method in [('v1/chat/completions', 'GET'), ('v1/models', 'POST'),
                             ('untrusted/chat/completions', 'POST'), ('api/v1/chat/completions', 'POST'),
                             ('api/unknown-models', 'GET'), ('v1\\chat/completions', 'POST')]:
            with self.subTest(path=path, method=method):
                self.assertIsNone(helper.compatibility_target(path, method))

    def test_invalid_windows_paths_rejected_before_file_lookup(self):
        helper = importlib.import_module('core.http_fallback')
        with patch.object(helper, '_public_file', side_effect=AssertionError('Unexpected file lookup')) as lookup:
            for path in ['//untrusted/share/file', '\\\\untrusted\\share\\file', 'C:/private.txt',
                         '../private.txt', 'a/../private.txt', 'a//file', 'LPT1.txt', 'COM\u00b9.txt',
                         '.env', 'nested/.secret', 'file:stream', 'a\x00b']:
                with self.subTest(path=path):
                    self.assertEqual(helper.static_fallback_response(self.root, path, 'GET').status_code, 404)
            self.assertEqual(lookup.call_count, 0)

    @unittest.skipUnless(os.name == 'nt', 'Real Windows public-root junction fixture')
    def test_public_root_junction_cannot_serve_external_index(self):
        workspace = self.root / 'other-workspace'
        (workspace / 'frontend').mkdir(parents=True)
        outside = self.root / 'outside-public'
        outside.mkdir()
        (outside / 'index.html').write_text('SYNTHETIC_PRIVATE_CANARY', encoding='utf-8')
        linked = workspace / 'frontend/dist'
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(linked), str(outside)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, 'Synthetic root junction fixture creation failed')
        helper = importlib.import_module('core.http_fallback')
        self.assertEqual(helper.static_fallback_response(workspace, '', 'GET').status_code, 404)


if __name__ == '__main__':
    unittest.main()
