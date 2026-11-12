"""Actual launch route/dependencies with synthetic verification/controller only.

AST mounting avoids the router module's unrelated import-time store/service setup.
No dependency overrides, real Firebase tokens, providers, processes or originals.
This is not qualification of the full HostControlMiddleware or live backend.
"""
import ast
import asyncio
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from security.firebase_auth import VerifiedFirebaseContext
from security.screenwriting_access import require_screenwriting_access

URL = '/api/screenwriting/native/launch'
BODY = dict(project_name='Synthetic Project', expected_revision='synthetic-revision',
    expected_source_sha256='a'*64)


def actual_namespace(*, mounted=False):
    tree = ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
    ns = dict(asyncio=asyncio, json=json, Request=Request, HTTPException=HTTPException,
        JSONResponse=JSONResponse, APIRouter=APIRouter, Depends=Depends,
        require_screenwriting_access=require_screenwriting_access,
        _NATIVE_CREATIVE_CONTROLLER=None, _NATIVE_CREATIVE_ADAPTER=None)
    endpoint = next(node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'launch_native_creative')
    if mounted:
        helpers = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
            and node.name in {'_native_creative_owner', '_screenwriting_owner_scope'}]
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'router' for target in node.targets))
        # Execute the actual APIRouter dependency declaration, not a rewritten
        # dependency_override or a hand-selected allow-all replacement.
        nodes = [*helpers, assignment, endpoint]
    else:
        endpoint.decorator_list = []
        nodes = [endpoint]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-native-launch-route>', 'exec'), ns)
    return ns


class LaunchBody(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ns = actual_namespace()
        self.calls = []; self.tokens = []
        self.context = VerifiedFirebaseContext('firebase:fixture:synthetic-owner', time.monotonic()+60)
        self.adapter = object()
        def launch(context, **scope):
            self.calls.append((context, scope))
            return SimpleNamespace(pid=12345, grant='must-not-return', stdout='must-not-return')
        self.controller = SimpleNamespace(adapter=self.adapter, launch=launch)
        self.ns.update(_NATIVE_CREATIVE_CONTROLLER=self.controller, _NATIVE_CREATIVE_ADAPTER=self.adapter)
        def verify(token):
            self.tokens.append(token); return self.context
        self.verify = patch('security.firebase_auth.verified_firebase_context', side_effect=verify)
        self.verifier = self.verify.start(); self.addCleanup(self.verify.stop)

    def request(self, body=None, *, headers=None):
        if body is None: body = json.dumps(BODY).encode()
        async def receive(): return dict(type='http.request', body=body, more_body=False)
        return Request(dict(type='http', method='POST', path=URL, query_string=b'',
            headers=headers if headers is not None else [(b'authorization', b'Bearer synthetic-firebase')]), receive)

    async def test_exact_input_calls_only_fixed_controller_and_returns_starting_without_secrets(self):
        response = await self.ns['launch_native_creative'](self.request())
        self.assertEqual(response.status_code, 202)
        self.assertEqual(json.loads(response.body), dict(status='starting', project=BODY['project_name']))
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['pragma'], 'no-cache')
        self.assertEqual(self.tokens, ['synthetic-firebase'])
        self.assertEqual(self.calls, [(self.context, dict(project=BODY['project_name'],
            revision=BODY['expected_revision'], source_sha256=BODY['expected_source_sha256']))])
        self.assertNotIn(b'must-not-return', response.body)
        self.assertNotIn(b'pid', response.body)

    async def test_disabled_and_adapter_mismatch_refuse_without_controller_call(self):
        for controller, adapter in ((None, self.adapter), (self.controller, None),
                                    (self.controller, object())):
            self.ns.update(_NATIVE_CREATIVE_CONTROLLER=controller, _NATIVE_CREATIVE_ADAPTER=adapter)
            with self.assertRaises(HTTPException) as error:
                await self.ns['launch_native_creative'](self.request())
            self.assertEqual(error.exception.status_code, 503)
        self.assertEqual(self.calls, [])

    async def test_missing_duplicate_wrong_scheme_or_whitespace_bearer_is_refused_before_sdk(self):
        for headers in ([], [(b'authorization', b'Basic synthetic')],
            [(b'authorization', b'Bearer ')], [(b'authorization', b'Bearer synthetic ' )],
            [(b'authorization', b'Bearer two tokens')],
            [(b'authorization', b'Bearer one'), (b'authorization', b'Bearer two')]):
            with self.assertRaises(HTTPException) as error:
                await self.ns['launch_native_creative'](self.request(headers=headers))
            self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.tokens, []); self.assertEqual(self.calls, [])

    async def test_unverified_expired_or_local_admin_context_is_never_launch_authority(self):
        for context in (None, object(),
            VerifiedFirebaseContext('local_admin', time.monotonic()+60),
            VerifiedFirebaseContext('firebase:fixture:owner', time.monotonic()-1),
            VerifiedFirebaseContext('firebase:fixture:owner', float('inf')),
            VerifiedFirebaseContext('firebase:fixture:owner', True)):
            self.context = context
            with self.assertRaises(HTTPException) as error:
                await self.ns['launch_native_creative'](self.request())
            self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.calls, [])

    async def test_duplicate_extra_nested_or_nonfinite_json_is_refused(self):
        valid = json.dumps(BODY).encode()
        bodies = [b'not-json', b'[]', b'{}', b'\xff', b'['*1500+b'0'+b']'*1500,
            b'{"project_name":"a","project_name":"b"}',
            valid[:-1]+b',"owner":"forged"}',
            json.dumps({**BODY, 'expected_revision': True}).encode(),
            json.dumps({**BODY, 'expected_source_sha256': 'A'*64}).encode(),
            valid.replace(b'"synthetic-revision"', b'NaN')]
        for body in bodies:
            with self.subTest(body_length=len(body)):
                with self.assertRaises(HTTPException) as error:
                    await self.ns['launch_native_creative'](self.request(body))
                self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(self.calls, [])

    async def test_path_argv_pid_environment_and_grant_fields_never_reach_controller(self):
        for key in ('path', 'executable', 'argv', 'pid', 'environment', 'owner', 'grant', 'candidate_sha256'):
            body = json.dumps({**BODY, key:'caller-controlled'}).encode()
            with self.assertRaises(HTTPException) as error:
                await self.ns['launch_native_creative'](self.request(body))
            self.assertEqual(error.exception.status_code, 422)
        for name in ('../escape', 'a/b', 'a\\b', 'C:\\escape', 'NUL.txt', ' trailing', 'trailing.', '.', ''):
            with self.assertRaises(HTTPException) as error:
                await self.ns['launch_native_creative'](self.request(json.dumps({**BODY, 'project_name':name}).encode()))
            self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(self.calls, [])

    async def test_oversize_stream_stops_without_consuming_later_input(self):
        consumed = []
        class Streaming:
            headers = Headers({'authorization':'Bearer synthetic-firebase'})
            async def stream(self):
                yield b'x'*2000
                yield b'x'*2097
                consumed.append('beyond-limit')
                yield b'x'
        with self.assertRaises(HTTPException) as error:
            await self.ns['launch_native_creative'](Streaming())
        self.assertEqual(error.exception.status_code, 413)
        self.assertEqual(consumed, []); self.assertEqual(self.calls, [])

    async def test_authentication_precedes_request_body_consumption(self):
        self.context = None
        consumed = []
        class Streaming:
            headers = Headers({'authorization':'Bearer synthetic-invalid'})
            async def stream(self):
                consumed.append(True); yield b'{}'
        with self.assertRaises(HTTPException) as error:
            await self.ns['launch_native_creative'](Streaming())
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(consumed, [])

    async def test_verifier_and_controller_errors_are_sanitized_including_wrapped_conflicts(self):
        with patch('security.firebase_auth.verified_firebase_context',
                   side_effect=RuntimeError('synthetic-private-verifier-marker')):
            with self.assertRaises(HTTPException) as error:
                await self.ns['launch_native_creative'](self.request())
            self.assertEqual(error.exception.status_code, 403)
            self.assertNotIn('private-verifier', str(error.exception.detail))
        def failed(*args, **kwargs): raise HTTPException(409, 'synthetic-private-project-marker')
        self.controller.launch = failed
        with self.assertRaises(HTTPException) as error:
            await self.ns['launch_native_creative'](self.request())
        self.assertEqual(error.exception.status_code, 503)
        self.assertNotIn('private-project', str(error.exception.detail))

    def test_source_default_is_disabled_without_candidate_activation(self):
        tree = ast.parse((ROOT/'backend/routers/screenwriting_router.py').read_text(encoding='utf-8'))
        for name in ('_NATIVE_CREATIVE_CONTROLLER', '_NATIVE_CREATIVE_ADAPTER'):
            assignments = [node for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
            self.assertEqual(len(assignments), 1)
            self.assertIsInstance(assignments[0].value, ast.Constant)
            self.assertIsNone(assignments[0].value.value)


class MountedLaunchAccess(unittest.TestCase):
    def setUp(self):
        self.ns = actual_namespace(mounted=True)
        self.calls = []; self.tokens = []
        self.context = VerifiedFirebaseContext('firebase:fixture:fresh-owner', time.monotonic()+60)
        adapter = object()
        def launch(context, **scope): self.calls.append((context, scope))
        self.ns.update(_NATIVE_CREATIVE_ADAPTER=adapter,
            _NATIVE_CREATIVE_CONTROLLER=SimpleNamespace(adapter=adapter, launch=launch))
        def allowed(key, authorization):
            return key in {'synthetic-local-key', 'synthetic.jwt.token'} or authorization in {
                'Bearer synthetic-firebase', 'Bearer synthetic-local-key'}
        def principal(key, authorization):
            return 'local_admin' if key or authorization == 'Bearer synthetic-local-key' else self.context.principal
        def fresh(token):
            self.tokens.append(token)
            return self.context if token == 'synthetic-firebase' else None
        for guard in (
            patch('security.screenwriting_access.verify_admin_credentials', side_effect=allowed),
            patch('security.firebase_auth.get_admin_principal', side_effect=principal),
            patch('security.firebase_auth.verified_firebase_context', side_effect=fresh)):
            guard.start(); self.addCleanup(guard.stop)
        app = FastAPI(); app.include_router(self.ns['router'])
        self.client = TestClient(app); self.addCleanup(self.client.close)

    def test_anonymous_and_local_key_only_never_reach_fresh_verifier_or_controller(self):
        for headers in ({}, {'X-API-Key':'synthetic-local-key'}, {'X-API-Key':'synthetic.jwt.token'}):
            response = self.client.post(URL, json=BODY, headers=headers)
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tokens, []); self.assertEqual(self.calls, [])

    def test_local_key_bearer_or_local_key_plus_invalid_bearer_cannot_launch(self):
        for headers in ({'Authorization':'Bearer synthetic-local-key'},
            {'X-API-Key':'synthetic-local-key', 'Authorization':'Bearer synthetic-invalid'}):
            response = self.client.post(URL, json=BODY, headers=headers)
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tokens, ['synthetic-local-key', 'synthetic-invalid'])
        self.assertEqual(self.calls, [])

    def test_actual_bearer_context_is_used_even_when_local_key_binds_local_admin(self):
        response = self.client.post(URL, json=BODY, headers={'X-API-Key':'synthetic-local-key',
            'Authorization':'Bearer synthetic-firebase'})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.tokens, ['synthetic-firebase'])
        self.assertIs(self.calls[0][0], self.context)
        self.assertEqual(response.json(), dict(status='starting', project=BODY['project_name']))

    def test_fresh_bearer_without_local_key_is_admitted_by_both_boundaries(self):
        response = self.client.post(URL, json=BODY, headers={'Authorization':'Bearer synthetic-firebase'})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.tokens, ['synthetic-firebase'])
        self.assertIs(self.calls[0][0], self.context)

    def test_openapi_declares_starting_status_instead_of_success_ready(self):
        response_codes = self.client.app.openapi()['paths'][URL]['post']['responses']
        self.assertIn('202', response_codes)
        self.assertNotIn('200', response_codes)

    def test_router_access_policy_is_retained_before_fresh_admission(self):
        with patch('security.screenwriting_access.verify_admin_credentials', return_value=False):
            response = self.client.post(URL, json=BODY, headers={'Authorization':'Bearer synthetic-firebase'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tokens, []); self.assertEqual(self.calls, [])

    def test_lease_header_cannot_bypass_or_trigger_launch(self):
        response = self.client.post(URL, json=BODY, headers={'X-API-Key':'synthetic-local-key',
            'Authorization':'Bearer synthetic-firebase', 'X-AI-BS-Creative-Lease':'forged'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.tokens, []); self.assertEqual(self.calls, [])

    def test_duplicate_authorization_and_extra_fields_fail_before_controller(self):
        response = self.client.post(URL, json=BODY, headers=[('X-API-Key','synthetic-local-key'),
            ('Authorization','Bearer synthetic-firebase'), ('Authorization','Bearer synthetic-firebase')])
        self.assertEqual(response.status_code, 403)
        response = self.client.post(URL, json={**BODY,'argv':['forged']},
            headers={'Authorization':'Bearer synthetic-firebase'})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
