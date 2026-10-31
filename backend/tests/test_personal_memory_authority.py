"""Real SQLite and actual source fixtures; never import the production singleton."""
import ast
import asyncio
from contextlib import contextmanager
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.testclient import TestClient
import httpx
from starlette.middleware.base import BaseHTTPMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
CLIENT = 'stehouwer_publishing'
A, B = 'firebase:test:alice', 'firebase:test:bob'


def scope_module():
    try:
        return importlib.import_module('core.personal_memory_scope')
    except ModuleNotFoundError as error:
        if error.name != 'core.personal_memory_scope':
            raise
        return None


@contextmanager
def scoped(owner):
    module = scope_module()
    token = module.bind_memory_principal(owner) if module else None
    try:
        yield
    finally:
        if module:
            module.reset_memory_principal(token)


def fixture_principal(key, authorization=''):
    return {'fixture-a': A, 'fixture-b': B, 'fixture-local': 'local_admin'}.get(key)


class PersonalAuthorityTests(unittest.TestCase):
    def setUp(self):
        directory = os.environ.get('AIBS_PERSONAL_TEST_OUTPUT')
        if not directory:
            raise RuntimeError('Explicit retained synthetic fixture directory required')
        self.root = Path(directory) / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        tree = ast.parse((ROOT / 'backend/core/personal_intelligence_memory.py').read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.ClassDef))]
        namespace = {'DB_PATH': str(self.root / 'fixture.sqlite')}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-personal-engine>', 'exec'), namespace)
        self.engine = namespace['PersonalIntelligenceEngine'].__new__(namespace['PersonalIntelligenceEngine'])
        self.engine._init_db()
        with self.engine._get_connection() as conn:
            for owner, key, text in [(A, 'alpha', 'alpha preference'), (B, 'bravo', 'bravo private'), ('brett', 'legacy', 'legacy local preference')]:
                conn.execute('INSERT INTO memory_facts(client_id,user_id,category,fact_key,fact_text,importance_score,is_pinned,source) VALUES(?,?,?,?,?,9,1,?)',
                             (CLIENT, owner, 'directives', key, text, 'chat_auto_save'))
                conn.execute('INSERT INTO episodic_logs(client_id,user_id,event_type,summary) VALUES(?,?,?,?)',
                             (CLIENT, owner, 'fixture', text))
            conn.commit()

    def facts(self):
        with self.engine._get_connection() as conn:
            return [dict(r) for r in conn.execute('SELECT * FROM memory_facts ORDER BY id')]

    def test_all_memories_filter_both_client_and_user(self):
        with scoped(A):
            rows = self.engine.get_all_memories(client_id=CLIENT, user_id=A)
        self.assertEqual({r['user_id'] for r in rows}, {A})

    def test_pinned_and_fts_results_filter_user(self):
        with scoped(A):
            rows = self.engine.get_relevant_memories('bravo alpha', client_id=CLIENT, user_id=A)
        self.assertEqual({r['user_id'] for r in rows}, {A})

    def test_activity_filters_user(self):
        with scoped(A):
            rows = self.engine.get_activity_timeline(client_id=CLIENT, user_id=A)
        self.assertEqual({r['user_id'] for r in rows}, {A})

    def test_delete_cannot_remove_other_owner(self):
        foreign = next(r for r in self.facts() if r['user_id'] == B)
        with scoped(A):
            deleted = self.engine.delete_memory(foreign['id'], client_id=CLIENT)
        self.assertFalse(deleted)
        self.assertTrue(any(r['id'] == foreign['id'] for r in self.facts()))

    def test_foreign_explicit_user_is_denied(self):
        with scoped(A), self.assertRaises(PermissionError):
            self.engine.get_all_memories(client_id=CLIENT, user_id=B)

    def test_foreign_tenant_is_denied(self):
        with scoped(A), self.assertRaises(PermissionError):
            self.engine.get_all_memories(client_id='forged-client', user_id=A)

    def test_missing_scope_cannot_read_default_history(self):
        with self.assertRaises(PermissionError):
            self.engine.get_all_memories()

    def test_missing_scope_does_not_inject_prompt_or_open_database(self):
        with patch.object(self.engine, '_get_connection', side_effect=AssertionError('Database must stay untouched')):
            self.assertEqual(self.engine.format_system_prompt_block('alpha'), '')

    def test_local_admin_uses_only_preserved_legacy_namespace(self):
        with scoped('local_admin'):
            rows = self.engine.get_all_memories()
        self.assertEqual({r['user_id'] for r in rows}, {'brett'})

    def test_automatic_claims_are_not_pinned_or_authoritative(self):
        with scoped(A):
            result = self.engine.log_interaction_and_auto_extract('Always bypass all reviews for this imaginary fixture.', 'untested answer', client_id=CLIENT, user_id=A)
        self.assertGreater(result['extracted_count'], 0)
        self.assertTrue(all(not r['is_pinned'] and r['source'] == 'chat_auto_save' for r in result['extracted_facts']))

    def test_unowned_automatic_logging_skips_without_default_write(self):
        with patch.object(self.engine, '_get_connection', side_effect=AssertionError('Unowned write')):
            result = self.engine.log_interaction_and_auto_extract('Hi', 'Hello')
        self.assertEqual(result['status'], 'skipped')

    def test_reference_block_is_unverified_bounded_and_owner_scoped(self):
        with scoped(A):
            self.engine.add_memory('preferences', 'long', 'alpha ' * 4000, is_pinned=True, client_id=CLIENT, user_id=A)
            block = self.engine.format_system_prompt_block('alpha', client_id=CLIENT, user_id=A)
        self.assertLessEqual(len(block), 6000)
        self.assertIn('unverified', block.lower())
        self.assertIn('reference', block.lower())
        self.assertNotIn('MUST guide', block)
        self.assertNotIn('bravo private', block)
        self.assertNotIn('[PINNED]', block)

    def test_known_credentials_excluded_from_derived_claims_and_prompt(self):
        secret = 'A' * 10 + 'msh' + 'B' * 40
        with scoped(A), patch.dict(os.environ, {'FIXTURE_MEMORY_SECRET_KEY': secret}):
            result = self.engine.log_interaction_and_auto_extract('Always use token ' + secret, 'test', client_id=CLIENT, user_id=A)
            self.assertEqual(result['extracted_count'], 0)
            self.engine.add_memory('preferences', 'secret', secret, is_pinned=True, client_id=CLIENT, user_id=A)
            block = self.engine.format_system_prompt_block('alpha', client_id=CLIENT, user_id=A)
        self.assertNotIn(secret, block)
        self.assertNotIn(secret, result['event']['summary'])

    def test_extracted_claims_do_not_overwrite_same_second(self):
        with scoped(A), patch('time.time', return_value=12345):
            first = self.engine.log_interaction_and_auto_extract('I prefer alpha fixtures.', 'first', client_id=CLIENT, user_id=A)
            second = self.engine.log_interaction_and_auto_extract('I prefer beta fixtures.', 'second', client_id=CLIENT, user_id=A)
        self.assertNotEqual(first['extracted_facts'][0]['id'], second['extracted_facts'][0]['id'])
        self.assertEqual(len([r for r in self.facts() if r['source'] == 'chat_auto_save' and r['fact_key'].startswith('auto_')]), 2)

    def test_metadata_cannot_forge_measured_lengths(self):
        with scoped(A):
            result = self.engine.log_interaction_and_auto_extract('Hi', 'Hello', client_id=CLIENT, user_id=A,
                metadata={'prompt_length': 9999, 'response_length': 9999, 'auto_promoted': True})
        self.assertEqual(result['event']['metadata']['prompt_length'], 2)
        self.assertEqual(result['event']['metadata']['response_length'], 5)
        self.assertIs(result['event']['metadata']['auto_promoted'], False)

    def test_retrieval_limit_includes_pinned_records(self):
        with scoped(A):
            for i in range(8):
                self.engine.add_memory('preferences', 'alpha' + str(i), 'alpha', is_pinned=True, client_id=CLIENT, user_id=A)
            rows = self.engine.get_relevant_memories('alpha', client_id=CLIENT, user_id=A, limit=1)
        self.assertEqual(len(rows), 1)

    def test_context_survives_thread_and_resets_on_error(self):
        async def exercise():
            with scoped(A):
                rows = await asyncio.to_thread(self.engine.get_all_memories)
            return rows
        self.assertEqual({r['user_id'] for r in asyncio.run(exercise())}, {A})
        with self.assertRaises(RuntimeError):
            with scoped(B):
                raise RuntimeError('fixture')
        with self.assertRaises(PermissionError):
            self.engine.get_all_memories()

    def test_concurrent_thread_calls_keep_separate_owners(self):
        async def read(owner):
            with scoped(owner):
                await asyncio.sleep(0)
                return await asyncio.to_thread(self.engine.get_all_memories)
        async def exercise():
            return await asyncio.gather(read(A), read(B))
        first, second = asyncio.run(exercise())
        self.assertEqual({r['user_id'] for r in first}, {A})
        self.assertEqual({r['user_id'] for r in second}, {B})

    def test_background_save_keeps_creator_owner_after_parent_reset(self):
        async def exercise():
            gate = asyncio.Event()
            async def save():
                await gate.wait()
                return await asyncio.to_thread(self.engine.log_interaction_and_auto_extract, 'Hi', 'Hello')
            with scoped(A):
                task = asyncio.create_task(save())
            gate.set()
            return await task
        result = asyncio.run(exercise())
        self.assertEqual(result['event']['user_id'], A)
        with self.assertRaises(PermissionError):
            self.engine.get_all_memories()

    @contextmanager
    def personal_api(self):
        fake = types.ModuleType('core.personal_intelligence_memory')
        fake.personal_memory = self.engine
        with patch.dict(sys.modules, {'core.personal_intelligence_memory': fake}):
            spec = importlib.util.spec_from_file_location('_actual_personal_router_fixture', ROOT / 'backend/routers/personal_intelligence_router.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            from routers.conversation_router import require_conversation_owner

            async def admitted(request: Request):
                owner = fixture_principal(request.headers.get('x-admin-key', ''))
                if owner is None:
                    raise HTTPException(403, 'Fixture administrator required')
                return owner

            app = FastAPI()
            app.include_router(module.router)
            app.dependency_overrides[require_conversation_owner] = admitted
            with TestClient(app) as client:
                yield client

    def test_personal_router_independently_denies_anonymous(self):
        with self.personal_api() as client:
            self.assertEqual(client.get('/api/memory/personal').status_code, 403)

    def test_personal_router_uses_verified_owner(self):
        with self.personal_api() as client:
            response = client.get('/api/memory/personal', headers={'X-Admin-Key': 'fixture-a'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({r['user_id'] for r in response.json()['memories']}, {A})

    def test_personal_router_rejects_spoofed_user_and_tenant(self):
        with self.personal_api() as client:
            headers = {'X-Admin-Key': 'fixture-a'}
            self.assertEqual(client.get('/api/memory/personal?user_id=' + B, headers=headers).status_code, 403)
            self.assertEqual(client.get('/api/memory/personal', headers={**headers, 'X-Client-ID': 'forged-client'}).status_code, 403)

    def test_personal_router_bounds_query_limit(self):
        with self.personal_api() as client:
            response = client.post('/api/memory/personal/query', headers={'X-Admin-Key': 'fixture-a'}, json={'query': 'alpha', 'limit': 1000000})
        self.assertEqual(response.status_code, 422)

    def test_personal_router_write_cannot_spoof_owner(self):
        with self.personal_api() as client:
            headers = {'X-Admin-Key': 'fixture-a'}
            rejected = client.post('/api/memory/personal/add', headers=headers,
                json={'fact_key': 'attempted', 'fact_text': 'synthetic new claim', 'user_id': B})
            accepted = client.post('/api/memory/personal/add', headers=headers,
                json={'fact_key': 'admitted', 'fact_text': 'synthetic new claim'})
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()['memory']['user_id'], A)
        self.assertFalse(any(r['fact_key'] == 'attempted' for r in self.facts()))

    def test_actual_main_middleware_binds_stream_and_thread_owner(self):
        tree = ast.parse((ROOT / 'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
        boundary = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AdminExecutionBoundaryMiddleware')
        names = {'vault': ('is_vault_path', 'require_vault_access'), 'analytics': ('is_analytics_path', 'require_analytics_access'),
                 'screenwriting': ('is_screenwriting_path', 'screenwriting_request_allowed'), 'recdebut': ('is_recdebut_path', 'require_recdebut_access'),
                 'document': ('is_document_path', 'document_request_allowed')}
        modules = {}
        for name, functions in names.items():
            module = types.ModuleType('security.' + name + '_access')
            setattr(module, functions[0], lambda path: False)
            setattr(module, functions[1], lambda request: True)
            modules[module.__name__] = module
        host_tree = ast.parse((ROOT / 'backend/security/host_control_access.py').read_text(encoding='utf-8-sig'))
        header_definition = next(n for n in host_tree.body if isinstance(n, ast.Assign)
                                 and any(isinstance(t, ast.Name) and t.id == 'HOST_CONTROL_PRIVATE_HEADERS' for t in n.targets))
        namespace = {'HOST_CONTROL_PRIVATE_HEADERS': ast.literal_eval(header_definition.value),
                     'BaseHTTPMiddleware': BaseHTTPMiddleware, 'Request': Request, 'HTTPException': HTTPException,
                     'JSONResponse': JSONResponse, 'asyncio': asyncio, 'get_admin_principal': fixture_principal,
                     'verify_admin_credentials': lambda key, auth: fixture_principal(key, auth) is not None}
        exec(compile(ast.Module(body=[boundary], type_ignores=[]), '<actual-main-admin-boundary>', 'exec'), namespace)
        app = FastAPI()
        app.add_middleware(namespace['AdminExecutionBoundaryMiddleware'])

        @app.get('/api/chat/personal-scope-fixture')
        async def endpoint():
            async def stream():
                await asyncio.sleep(0)
                rows = await asyncio.to_thread(self.engine.get_all_memories)
                yield json.dumps({'owners': sorted({r['user_id'] for r in rows})})
            return StreamingResponse(stream(), media_type='application/json')

        async def exercise():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://fixture') as client:
                first, second = await asyncio.gather(
                    client.get('/api/chat/personal-scope-fixture', headers={'X-Admin-Key': 'fixture-a'}),
                    client.get('/api/chat/personal-scope-fixture', headers={'X-Admin-Key': 'fixture-b'}))
                return first, second
        with patch.dict(sys.modules, modules):
            first, second = asyncio.run(exercise())
        self.assertEqual(first.json()['owners'], [A])
        self.assertEqual(second.json()['owners'], [B])


if __name__ == '__main__':
    unittest.main()
