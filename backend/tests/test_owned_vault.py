"""Actual SQLite/source/router fixtures for owned archives; no production import."""
import ast
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import types
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core import chat_archive
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
A, B = 'firebase:fixture:alice', 'firebase:fixture:bob'


@contextmanager
def admitted(owner):
    token = bind_memory_principal(owner)
    try:
        yield
    finally:
        reset_memory_principal(token)


class OwnedVaultTests(unittest.TestCase):
    def setUp(self):
        directory = os.environ.get('AIBS_OWNED_TEST_OUTPUT')
        if not directory:
            raise RuntimeError('Explicit retained synthetic fixture directory required')
        self.root = Path(directory) / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.db = self.root / 'vault.sqlite'
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT,content TEXT,collection TEXT,tags TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,item_hash TEXT)')
            conn.execute("INSERT INTO vault_items(title,content,collection,tags) VALUES('Legacy','UNREVIEWED_LEGACY_SOURCE alpha','legacy','original')")
        try:
            self.helper = importlib.import_module('core.owned_vault')
        except ModuleNotFoundError as error:
            if error.name != 'core.owned_vault':
                raise
            self.helper = None
        self.messages = [{'role': 'user', 'content': 'alpha unfinished question', 'id': 7, 'attachment': {'name': 'source.md', 'text': 'full metadata'}},
                         {'role': 'assistant', 'content': 'untested beta idea', 'outcome': 'failed'}]

    def owned(self):
        self.assertIsNotNone(self.helper, 'Owned vault helper is missing')
        return self.helper

    def save(self, owner=A, archive_id='a' * 32, messages=None):
        return chat_archive.archive_chat(self.db, self.messages if messages is None else messages,
            owner=owner, archive_id=archive_id, session_title='Partial fixture', source='fixture')

    def test_archive_requires_explicit_verified_owner(self):
        with self.assertRaises(PermissionError):
            chat_archive.archive_chat(self.db, self.messages, archive_id='a' * 32)

    def test_archive_owner_and_raw_metadata_confirmed(self):
        receipt = self.save()
        self.assertEqual(receipt['owner'], A)
        self.assertEqual(receipt['storage'], 'sqlite_vault')
        self.assertTrue(receipt['durable'])
        with sqlite3.connect(self.db) as conn:
            raw = conn.execute('SELECT payload_json FROM chat_archive_receipts').fetchone()[0]
            owner = conn.execute('SELECT owner FROM vault_items WHERE id=?', (receipt['vault_item_id'],)).fetchone()[0]
        self.assertEqual(json.loads(raw)['messages'], self.messages)
        self.assertEqual(owner, A)

    def test_same_external_id_is_independent_across_owners(self):
        first, second = self.save(A), self.save(B)
        self.assertNotEqual(first['vault_item_id'], second['vault_item_id'])
        self.assertEqual(first['archive_id'], second['archive_id'])
        self.assertEqual({r['owner'] for r in self.owned().list_records(self.db, B)}, {B})

    def test_same_owner_retry_deduplicates(self):
        first, second = self.save(), self.save()
        self.assertEqual(first, second)
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM chat_archive_receipts').fetchone()[0], 1)

    def test_changed_retry_preserves_original(self):
        first = self.save()
        with self.assertRaises(ValueError):
            self.save(messages=[{'role': 'user', 'content': 'changed'}])
        actual = chat_archive._confirm_archive(self.db, 'a' * 32, first['payload_sha256'], owner=A)
        self.assertEqual(actual, first)

    def test_foreign_owner_cannot_confirm_receipt(self):
        first = self.save()
        with self.assertRaises((ValueError, LookupError)):
            chat_archive._confirm_archive(self.db, 'a' * 32, first['payload_sha256'], owner=B)

    def test_legacy_receipt_only_local_operator_and_preserved(self):
        payload = {'messages': self.messages, 'session_title': 'Old fixture', 'source': 'old'}
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
        digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        with sqlite3.connect(self.db) as conn:
            transcript = chat_archive._transcript(payload)
            row = conn.execute('INSERT INTO vault_items(title,content,collection,tags) VALUES(?,?,?,?)', ('Old fixture', transcript, 'stehouwer_conversations', 'old'))
            conn.execute('CREATE TABLE chat_archive_receipts(archive_id TEXT PRIMARY KEY,payload_sha256 TEXT NOT NULL,payload_json TEXT NOT NULL,message_count INTEGER NOT NULL,vault_item_id INTEGER NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
            conn.execute('INSERT INTO chat_archive_receipts(archive_id,payload_sha256,payload_json,message_count,vault_item_id) VALUES(?,?,?,?,?)', ('b' * 32, digest, raw, 2, row.lastrowid))
        before = self.db.read_bytes()
        receipt = chat_archive._confirm_archive(self.db, 'b' * 32, digest, owner='local_admin')
        self.assertEqual(receipt['owner'], 'local_admin')
        with self.assertRaises((ValueError, LookupError)):
            chat_archive._confirm_archive(self.db, 'b' * 32, digest, owner=A)
        self.assertEqual(self.db.read_bytes(), before)

    def test_invalid_payload_does_not_migrate_or_create_file(self):
        before = self.db.read_bytes()
        with self.assertRaises(ValueError):
            self.save(messages=[])
        self.assertEqual(before, self.db.read_bytes())
        missing = self.root / 'missing.sqlite'
        with self.assertRaises((OSError, sqlite3.Error)):
            chat_archive.archive_chat(missing, self.messages, owner=A, archive_id='a' * 32)
        self.assertFalse(missing.exists())

    def test_owner_reads_and_legacy_display_are_separate(self):
        helper = self.owned()
        helper.store_record(self.db, A, 'A', 'alpha owned A', collection='notes')
        helper.store_record(self.db, B, 'B', 'beta owned B', collection='notes')
        self.assertEqual({r['owner'] for r in helper.list_records(self.db, A)}, {A})
        self.assertEqual(len(helper.list_records(self.db, 'local_admin')), 1)
        self.assertEqual(helper.list_records(self.db, 'local_admin', include_legacy=False), [])

    def test_remove_hides_and_keeps_archive_and_receipt(self):
        receipt = self.save()
        helper = self.owned()
        helper.hide_record(self.db, A, receipt['vault_item_id'])
        self.assertEqual(helper.list_records(self.db, A), [])
        second = helper.hide_record(self.db, A, receipt['vault_item_id'])
        self.assertTrue(second['preserved'])
        self.assertTrue(chat_archive._confirm_archive(self.db, 'a' * 32, receipt['payload_sha256'], owner=A)['durable'])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM vault_items WHERE id=?', (receipt['vault_item_id'],)).fetchone()[0], 1)

    def test_foreign_record_cannot_be_hidden(self):
        receipt = self.save()
        with self.assertRaises(LookupError):
            self.owned().hide_record(self.db, B, receipt['vault_item_id'])
        self.assertEqual(len(self.owned().list_records(self.db, A)), 1)

    def test_legacy_reads_never_initialize_schema(self):
        before = self.db.read_bytes()
        self.assertEqual(self.owned().list_records(self.db, A), [])
        self.assertEqual(len(self.owned().list_records(self.db, 'local_admin')), 1)
        self.assertEqual(before, self.db.read_bytes())

    def test_partial_ownership_schema_fails_without_repairing_it(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute('ALTER TABLE vault_items ADD COLUMN owner TEXT')
        before = self.db.read_bytes()
        with self.assertRaises(RuntimeError):
            self.owned().list_records(self.db, A)
        self.assertEqual(before, self.db.read_bytes())

    def test_search_respects_owner_collection_and_reports_real_coverage(self):
        helper = self.owned()
        helper.store_record(self.db, A, 'One', 'alpha beta', collection='notes')
        helper.store_record(self.db, A, 'Two', 'alpha', collection='notes')
        helper.store_record(self.db, B, 'Foreign', 'alpha beta', collection='notes')
        helper.store_record(self.db, A, 'Other collection', 'alpha beta', collection='other')
        rows = helper.search_records(self.db, A, 'alpha beta', collection='notes', limit=5)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['score'] for r in rows}, {0.5, 1.0})
        self.assertTrue(all(r['score_kind'] == 'lexical_token_coverage' and r['owner'] == A for r in rows))

    @contextmanager
    def api(self):
        memory = types.ModuleType('core.memory_bank')
        for name in ['store_heuristic', 'add_memory', 'get_memory_bank_status']:
            setattr(memory, name, lambda *a, **k: {})
        memory.get_master_memory_path = lambda: str(self.root / 'unused-global.json')
        memory.VAULT_DB_PATH = str(self.db)
        loop = types.ModuleType('core.infinite_learning_loop')
        loop.learning_loop_instance = types.SimpleNamespace()
        with patch.dict(sys.modules, {'core.memory_bank': memory, 'core.infinite_learning_loop': loop}):
            spec = importlib.util.spec_from_file_location('_actual_owned_memory_router', ROOT / 'backend/routers/memory_router.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            from routers.conversation_router import require_conversation_owner
            async def owner(request: Request):
                principal = {'fixture-a': A, 'fixture-b': B, 'fixture-local': 'local_admin'}.get(request.headers.get('x-admin-key'))
                if principal is None:
                    raise HTTPException(403, 'Fixture administrator required')
                return principal
            app = FastAPI()
            app.include_router(module.router)
            app.dependency_overrides[require_conversation_owner] = owner
            with TestClient(app) as client:
                yield client

    def test_parent_router_denies_anonymous_without_main_middleware(self):
        with self.api() as client:
            self.assertEqual(client.get('/api/memory').status_code, 403)
            self.assertEqual(client.post('/api/memory/ingest-chat', json={'messages': self.messages}).status_code, 403)

    def test_api_archive_binds_owner_and_rejects_forged_body(self):
        with self.api() as client:
            headers = {'X-Admin-Key': 'fixture-a'}
            rejected = client.post('/api/memory/ingest-chat', headers=headers, json={'messages': self.messages, 'owner': B})
            self.assertEqual(rejected.status_code, 422)
            accepted = client.post('/api/memory/ingest-chat', headers=headers, json={'messages': self.messages, 'archive_id': 'a' * 32})
            self.assertEqual(accepted.status_code, 200)
            self.assertEqual(accepted.json()['archive_receipt']['owner'], A)
            foreign = client.get('/api/memory', headers={'X-Admin-Key': 'fixture-b'})
            self.assertEqual(foreign.json()['count'], 0)

    def test_explicit_main_recall_route_enforces_owner_without_global_fallback(self):
        helper = self.owned()
        helper.store_record(self.db, A, 'Own', 'alpha OWN_RECALL_REFERENCE', collection='notes')
        helper.store_record(self.db, B, 'Foreign', 'alpha FOREIGN_RECALL_CANARY', collection='notes')
        tree = ast.parse((ROOT / 'backend/AI_BS_Backend.py').read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in {'MemoryRecallPayload', 'memory_recall'}]
        from routers.conversation_router import require_conversation_owner
        app = FastAPI()
        namespace = {'app': app, 'BaseModel': BaseModel, 'Field': Field, 'Optional': Optional,
                     'Depends': Depends, 'HTTPException': HTTPException, 'require_conversation_owner': require_conversation_owner}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-main-recall>', 'exec'), namespace)
        ingestor = types.ModuleType('sovereign_memory_ingestor')
        ingestor.search_memory = lambda *a, **k: [{'document': 'FOREIGN_GLOBAL_RECALL_CANARY'}]
        router_module = types.ModuleType('routers.memory_router')
        router_module.VAULT_DB_PATH = str(self.db)
        async def owner(request: Request):
            if request.headers.get('x-admin-key') != 'fixture-a':
                raise HTTPException(403, 'Fixture administrator required')
            return A
        app.dependency_overrides[require_conversation_owner] = owner
        with patch.dict(sys.modules, {ingestor.__name__: ingestor, router_module.__name__: router_module}), TestClient(app) as client:
            self.assertEqual(client.get('/api/memory/recall?query=alpha').status_code, 403)
            response = client.get('/api/memory/recall?query=alpha', headers={'X-Admin-Key': 'fixture-a'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('OWN_RECALL_REFERENCE', response.text)
        self.assertNotIn('FOREIGN', response.text)

    def vault_class(self):
        path = ROOT / 'backend/core/sovereign_reasoning/memory_vault.py'
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        nodes = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.ClassDef))]
        namespace = {'__file__': str(path)}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<actual-unified-vault>', 'exec'), namespace)
        cls = namespace['SovereignMemoryVault']
        cls.VAULT_DB_PATH = self.db
        cls.MASTER_DB = str(self.root / 'old_raw_telemetry.sqlite')
        return cls

    @contextmanager
    def foreign_providers(self):
        calls = []
        history = types.ModuleType('core.stehouwer_history_retriever')
        def forbidden(*args, **kwargs):
            calls.append(True)
            return 'FOREIGN_GLOBAL_CANARY'
        history.get_stehouwer_historical_context = forbidden
        lexicon = types.ModuleType('core.lexicon_service')
        lexicon.LexiconService = types.SimpleNamespace(bulk_expand=lambda p: (forbidden(p), {})[1])
        omni = types.ModuleType('core.omni_space_manager')
        omni.omni_space_manager = types.SimpleNamespace(search_all_spaces=lambda *a, **k: (forbidden(), {})[1])
        with patch.dict(sys.modules, {m.__name__: m for m in [history, lexicon, omni]}):
            yield calls

    def test_unowned_unified_context_never_calls_global_providers(self):
        cls = self.vault_class()
        with self.foreign_providers() as calls:
            self.assertEqual(cls.get_unified_context('alpha'), '')
        self.assertEqual(calls, [])

    def test_unified_context_only_own_bounded_cited_unverified_records(self):
        helper = self.owned()
        helper.store_record(self.db, A, 'Own', 'prefix ' + 'alpha evidence ' * 900, collection='notes')
        helper.store_record(self.db, B, 'Foreign', 'alpha FOREIGN_OWNER_CANARY', collection='notes')
        cls = self.vault_class()
        with admitted(A), self.foreign_providers() as calls:
            context = cls.get_unified_context('alpha')
        self.assertLessEqual(len(context), 6000)
        self.assertIn('unverified', context.lower())
        self.assertIn('sha256', context)
        self.assertIn('char_start', context)
        self.assertNotIn('FOREIGN_OWNER_CANARY', context)
        self.assertNotIn('UNREVIEWED_LEGACY_SOURCE', context)
        self.assertEqual(calls, [])

    def test_swarm_telemetry_is_owned_metadata_without_raw_prompts_or_grade(self):
        cls = self.vault_class()
        calls = []
        personal = types.ModuleType('core.personal_intelligence_memory')
        personal.personal_memory = types.SimpleNamespace(record_ecosystem_event=lambda **kw: calls.append(kw))
        with admitted(A), patch.dict(sys.modules, {personal.__name__: personal}):
            cls.log_inference_telemetry('fixture-model', 'CONFIDENTIAL_PROMPT_FIXTURE', 'PRIVATE_REPLY_FIXTURE')
        self.assertFalse(Path(cls.MASTER_DB).exists())
        self.assertEqual(len(calls), 1)
        self.assertNotIn('CONFIDENTIAL_PROMPT_FIXTURE', json.dumps(calls))
        self.assertNotIn('PRIVATE_REPLY_FIXTURE', json.dumps(calls))
        self.assertNotIn('98.5', json.dumps(calls))

    def test_concurrent_owners_can_use_same_external_archive_id(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            first, second = list(executor.map(self.save, [A, B]))
        self.assertNotEqual(first['vault_item_id'], second['vault_item_id'])
        self.assertEqual({first['owner'], second['owner']}, {A, B})

    def test_corrupt_legacy_retry_cannot_adopt_failed_evidence(self):
        receipt = self.save(owner='local_admin')
        with sqlite3.connect(self.db) as conn:
            conn.execute('UPDATE chat_archive_receipts SET archive_id=?', ('a' * 32,))
            conn.execute('UPDATE vault_items SET owner=NULL,content=? WHERE id=?', ('corrupt fixture', receipt['vault_item_id']))
        with self.assertRaises(ValueError):
            self.save(owner='local_admin')
        with sqlite3.connect(self.db) as conn:
            owner, content = conn.execute('SELECT owner,content FROM vault_items WHERE id=?', (receipt['vault_item_id'],)).fetchone()
        self.assertIsNone(owner)
        self.assertEqual(content, 'corrupt fixture')

    def test_unicode_query_offsets_refer_to_original_characters(self):
        text = '\u00df' * 20000 + ' needle exact source'
        self.owned().store_record(self.db, A, 'Unicode', text, collection='notes')
        row = self.owned().search_records(self.db, A, 'needle', limit=1)[0]
        self.assertEqual(text[row['char_start']:row['char_end']], row['content'])
        self.assertIn('needle', row['content'])
        self.assertEqual(row['content_sha256'], hashlib.sha256(text.encode('utf-8')).hexdigest())

    def test_credential_source_is_retained_but_not_model_context(self):
        secret = 'A' * 10 + 'msh' + 'B' * 40
        record = self.owned().store_record(self.db, A, 'Fixture', 'alpha ' + secret, collection='notes')
        self.assertIn(secret, self.owned().read_record(self.db, A, record['id'])['content'])
        with admitted(A):
            self.assertEqual(self.vault_class().get_unified_context('alpha'), '')

    def test_unavailable_storage_does_not_become_empty_success_or_global_fallback(self):
        cls = self.vault_class()
        cls.VAULT_DB_PATH = self.root / 'missing.sqlite'
        with admitted(A), self.foreign_providers() as calls:
            result = cls.get_unified_context('alpha')
        self.assertIn('OWNED_MEMORY_UNAVAILABLE', result)
        self.assertEqual(calls, [])
        self.assertFalse(cls.VAULT_DB_PATH.exists())

    def test_failed_write_rolls_back_ownership_schema(self):
        other = self.root / 'minimal.sqlite'
        with sqlite3.connect(other) as conn:
            conn.execute('CREATE TABLE vault_items(id INTEGER PRIMARY KEY,title TEXT,content TEXT,collection TEXT,tags TEXT)')
        with self.assertRaises(RuntimeError):
            self.owned().store_record(other, A, 'Fixture', 'alpha')
        with sqlite3.connect(other) as conn:
            names = [r[1] for r in conn.execute('PRAGMA table_info(vault_items)')]
        self.assertNotIn('owner', names)
        self.assertNotIn('is_hidden', names)

    def test_listing_bounds_metadata_without_losing_full_source(self):
        tags = ['metadata-fixture ' * 2000]
        record = self.owned().store_record(self.db, A, 'Metadata', 'alpha full source', tags=tags)
        preview = self.owned().list_records(self.db, A)[0]
        self.assertLessEqual(len(preview['tags']), 1024)
        self.assertTrue(preview['tags_truncated'])
        recovered = self.owned().read_record(self.db, A, record['id'])
        self.assertEqual(json.loads(recovered['tags']), tags)


if __name__ == '__main__':
    unittest.main()
