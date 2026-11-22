"""Explicit PDF references use only synthetic owned stores and mocked models."""
import hashlib
import ast
import asyncio
import json
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from scripts.tests import test_chat_pdf_workflow as workflow
from scripts.tests.test_screenplay_pdf import make_fixture
OWNER, OTHER = workflow.OWNER, workflow.OTHER


class AttachedSourceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        workflow.PdfWorkflowFixture.setUp(self)

    def stage(self, owner=OWNER):
        receipt = self.bridge.stage_pdf(make_fixture(), owner, 'synthetic.pdf')
        return dict(source_id=receipt['source_id'], source_sha256=receipt['source_sha256'])

    def bundle(self, query, refs, max_chars=3500):
        from core.attached_source_context import attached_source_bundle
        token = bind_memory_principal(OWNER)
        try:
            return attached_source_bundle(query, refs, max_chars=max_chars)
        finally:
            reset_memory_principal(token)

    def test_exact_owner_and_source_binding_never_searches_another_filename(self):
        from core import owned_rag_sources as rag
        reference = self.stage()
        rag.ingest_source(self.db, OWNER, 'wrapped UNRELATED_OTHER_PDF',
                          source_name='context_' + 'f' * 32 + '.txt')
        rag.ingest_source(self.db, OTHER, 'wrapped FOREIGN_OWNER_PDF',
                          source_name='context_' + reference['source_id'] + '.txt')
        with patch.object(rag, 'retrieve_source_chunks', side_effect=AssertionError('No ambient filename search')):
            bundle = self.bundle('wrapped', [reference])
        self.assertEqual(bundle['receipt']['status'], 'retrieved')
        self.assertEqual(bundle['receipt']['search_scope'], 'explicit_attached_owner_sources')
        self.assertGreater(bundle['receipt']['returned_passages'], 0)
        self.assertIn('wrapped', bundle['context'])
        self.assertNotIn('UNRELATED_OTHER_PDF', bundle['context'])
        self.assertNotIn('FOREIGN_OWNER_PDF', bundle['context'])
        self.assertLessEqual(len(bundle['context']), 3500)
        packet = self.bridge.read_source(OWNER, reference['source_id'], reference['source_sha256'])[1]
        derived = packet['rag_text'].encode('utf-8')
        for hit in bundle['receipt']['passages']:
            self.assertEqual(hit['source_id'], reference['source_id'])
            self.assertEqual(hit['source_sha256'], reference['source_sha256'])
            self.assertEqual(hashlib.sha256(derived[hit['byte_start']:hit['byte_end']]).hexdigest(), hit['chunk_sha256'])
            self.assertTrue(hit['pdf_pages'])
        self.assertTrue(all('text' not in row and 'content' not in row for row in bundle['receipt']['passages']))
        self.assertNotIn('First wrapped dialogue line', json.dumps(bundle['receipt']))

    def test_foreign_stale_hidden_and_no_principal_never_produce_context(self):
        from core.attached_source_context import AttachedSourceError, attached_source_bundle
        from core.owned_vault import hide_record
        own, foreign = self.stage(), self.stage(OTHER)
        for reference in (foreign, {**own, 'source_sha256':'0' * 64}):
            with self.assertRaises(AttachedSourceError):
                self.bundle('wrapped', [reference])
        with self.assertRaises(AttachedSourceError):
            attached_source_bundle('wrapped', [own])
        manifest = self.bridge.read_source(OWNER, own['source_id'], own['source_sha256'])[0]
        hide_record(self.db, OWNER, manifest['rag_receipt']['vault_item_id'])
        with self.assertRaises(AttachedSourceError):
            self.bundle('wrapped', [own])

    def test_strict_ref_shape_conflicts_and_limits_fail_before_private_read(self):
        from core.attached_source_context import AttachedSourceError, validate_source_references
        good = dict(source_id='a' * 32, source_sha256='b' * 64)
        with patch.object(self.bridge, 'read_source', side_effect=AssertionError('Malformed refs cannot read')):
            for value in ('not a list', [dict(good, owner=OWNER)], [{**good, 'source_id':17}],
                          [good] * 5, [good, {**good, 'source_sha256':'c' * 64}]):
                with self.subTest(value_kind=type(value).__name__), self.assertRaises(AttachedSourceError):
                    validate_source_references(value)
        self.assertEqual(validate_source_references([good, good]), [good])

    def test_no_hit_is_explicit_and_does_not_fall_back_to_unrelated_sources(self):
        reference = self.stage()
        bundle = self.bundle('zzznomatchingpassagezzz', [reference])
        self.assertEqual(bundle['receipt']['status'], 'no_matching_passages')
        self.assertEqual(bundle['receipt']['returned_passages'], 0)
        self.assertIn('No matching passages', bundle['context'])
        self.assertIn('Do not invent', bundle['context'])

    def test_generic_pdf_text_and_budget_receipts_do_not_claim_screenplay_or_full_review(self):
        receipt = self.bridge.stage_pdf(make_fixture(font='Times-Roman'), OWNER, 'ordinary.pdf')
        self.assertFalse(receipt['source_layout_available'])
        refs = [dict(source_id=receipt['source_id'], source_sha256=receipt['source_sha256'])]
        self.assertEqual(self.bundle('wrapped', refs)['receipt']['status'], 'retrieved')
        bounded = self.bundle('wrapped', refs, max_chars=850)
        self.assertEqual(bounded['receipt']['status'], 'context_budget_exhausted')
        self.assertEqual(bounded['receipt']['returned_passages'], 0)
        self.assertLessEqual(len(bounded['context']), 850)

    def test_multiple_sources_report_passage_limit_and_missing_source_coverage(self):
        refs = [self.stage() for _ in range(4)]
        bundle = self.bundle('wrapped', refs)
        receipt = bundle['receipt']
        self.assertEqual(len(receipt['sources']), 4)
        self.assertEqual(receipt['returned_passages'], 2)
        self.assertEqual(receipt['passage_limit'], 2)
        self.assertTrue(receipt['result_truncated'])
        self.assertEqual(sum(row['selected_passages'] == 0 for row in receipt['source_coverage']), 2)
        self.assertIn('other sources or regions may have no supplied evidence', bundle['context'])

    async def test_selected_openai_turn_receives_refs_and_receipt_without_prompt_rewrite(self):
        import types
        from core import bs_chat_provider as provider
        from routers import ai_providers_router as configuration
        reference = self.stage()
        hybrid = types.ModuleType('core.hybrid_reasoning_engine')
        hybrid.detect_tool_intent = lambda _: (None, None)
        completion = AsyncMock(return_value=dict(content='synthetic response', provider='openai', model='fixture', device='fixture'))
        with patch.dict(sys.modules, {'core.hybrid_reasoning_engine':hybrid}), \
                patch.object(configuration, 'load_config', return_value={'active_provider':'openai','providers':{}}), \
                patch.object(configuration, '_openai_credential', return_value=('synthetic-key','fixture')), \
                patch.object(provider, 'openai_completion', completion):
            token = bind_memory_principal(OWNER)
            try:
                result = await provider.bs_chat_reply(dict(provider='openai', prompt='wrapped', user_prompt='wrapped',
                    model='fixture', source_references=[reference]))
            finally:
                reset_memory_principal(token)
        completion.assert_awaited_once()
        self.assertEqual(completion.call_args.kwargs['prompt'], 'wrapped')
        self.assertIn('First wrapped dialogue line', completion.call_args.kwargs['system_prompt'])
        self.assertIn('Untrusted document', completion.call_args.kwargs['system_prompt'])
        self.assertEqual(result['source_retrieval']['status'], 'retrieved')

    async def test_unavailable_and_no_hit_openai_turns_never_dispatch_a_model(self):
        from fastapi import HTTPException
        from core import bs_chat_provider as provider
        from routers import ai_providers_router as configuration
        own, foreign = self.stage(), self.stage(OTHER)
        hybrid = types.ModuleType('core.hybrid_reasoning_engine')
        hybrid.detect_tool_intent = lambda _: (None,None)
        completion = AsyncMock(side_effect=AssertionError('No source evidence, no generated document answer'))
        with patch.dict(sys.modules,{'core.hybrid_reasoning_engine':hybrid}), \
                patch.object(configuration,'load_config',return_value={'active_provider':'openai','providers':{}}), \
                patch.object(configuration,'_openai_credential',return_value=('synthetic-key','fixture')), \
                patch.object(provider,'openai_completion',completion):
            token=bind_memory_principal(OWNER)
            try:
                with self.assertRaises(HTTPException) as denied:
                    await provider.bs_chat_reply(dict(provider='openai',prompt='wrapped',model='fixture',source_references=[foreign]))
                self.assertEqual(denied.exception.status_code,409)
                reply=await provider.bs_chat_reply(dict(provider='openai',prompt='zzzimpossiblezzz',model='fixture',source_references=[own]))
            finally:
                reset_memory_principal(token)
        completion.assert_not_awaited()
        self.assertEqual(reply['source_retrieval']['status'],'no_matching_passages')
        self.assertIn('No model answer',reply['response'])

    async def test_cancelled_readback_stops_model_dispatch_and_does_not_leak_owner_context(self):
        from core.attached_source_context import request_source_bundle, attached_source_bundle, AttachedSourceError
        reference = self.stage()
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        original = self.bridge.read_source
        def slow(*args):
            entered.set()
            try:
                if not release.wait(2):
                    raise AssertionError('Synthetic source read was not released')
                return original(*args)
            finally:
                finished.set()
        token = bind_memory_principal(OWNER)
        try:
            with patch.object(self.bridge, 'read_source', slow):
                task = asyncio.create_task(request_source_bundle('wrapped', [reference]))
                self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                release.set()
                self.assertTrue(await asyncio.to_thread(finished.wait, 2))
                await asyncio.sleep(.02)
        finally:
            release.set()
            reset_memory_principal(token)
        with self.assertRaises(AttachedSourceError):
            attached_source_bundle('wrapped', [reference])

    async def test_parallel_request_owners_do_not_share_source_scope(self):
        from core.attached_source_context import request_source_bundle
        own, other = self.stage(), self.stage(OTHER)
        async def retrieve(owner, reference):
            token = bind_memory_principal(owner)
            try:
                return await request_source_bundle('wrapped', [reference])
            finally:
                reset_memory_principal(token)
        first, second = await asyncio.gather(retrieve(OWNER, own), retrieve(OTHER, other))
        self.assertEqual(first['receipt']['sources'][0]['source_id'], own['source_id'])
        self.assertEqual(second['receipt']['sources'][0]['source_id'], other['source_id'])
        self.assertNotEqual(own['source_id'], other['source_id'])

    async def test_actual_local_dispatcher_injects_explicit_bundle_only_after_tool_checks(self):
        from typing import Any, Dict, List, Optional
        from types import SimpleNamespace
        import httpx
        from scripts.tests import test_local_chat_inference as local_fixture
        reference = self.stage()
        bundle = self.bundle('wrapped', [reference])
        source = ROOT / 'backend/core/sovereign_reasoning/dispatcher.py'
        function = next(node for node in ast.parse(source.read_text(encoding='utf-8-sig')).body
                        if getattr(node, 'name', '') == 'stream_sovereign_response')
        tools = Mock(return_value=None)
        forbidden = Mock(side_effect=AssertionError('Ambient private memory must not replace explicit PDF scope'))
        bus = types.ModuleType('core.sovereign_reasoning.cross_model_bus')
        bus.CrossModelCognitiveBus = SimpleNamespace(call_model_atomic=forbidden)
        matrix = types.ModuleType('core.sovereign_reasoning.model_domain_matrix')
        matrix.ModelDomainMatrix = SimpleNamespace(score_prompt_against_fleet=lambda _: [{'score':3.0,'model':'fixture:latest','title':'Fixture'}])
        knowledge = types.ModuleType('core.sovereign_reasoning.sourcecode_knowledge_engine')
        knowledge.sourcecode_knowledge_engine = SimpleNamespace(inject_codebase_context=forbidden)
        shared = local_fixture.transport
        admission = local_fixture.Admission()
        payloads = []
        actual_client = httpx.AsyncClient
        def handle(request):
            payload = json.loads(request.content)
            payloads.append(payload)
            response = dict(model=payload['model'],response='synthetic final reply' if payload.get('stream') else 'synthetic briefing',done=True,done_reason='stop')
            return httpx.Response(200,content=(json.dumps(response)+'\n').encode())
        def client(**kwargs):
            return actual_client(transport=httpx.MockTransport(handle),**kwargs)
        namespace = dict(__package__='core.sovereign_reasoning',asyncio=asyncio,json=json,Optional=Optional,List=List,Dict=Dict,Any=Any,
            SovereignDocumentEngine=SimpleNamespace(prepare_chat_payload=lambda value:(value,value)),audit_prompt_safety=lambda _:(True,''),
            check_and_execute_system_tools=tools,SovereignMemoryVault=SimpleNamespace(get_unified_context=forbidden),
            personal_memory=SimpleNamespace(format_system_prompt_block=forbidden,log_interaction_and_auto_extract=forbidden),
            inject_safety_directive=lambda value:value,ensure_ollama_running=forbidden,
            OLLAMA_ENDPOINTS=['http://127.0.0.1:11434/api/generate'])
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),namespace)
        with patch.dict(sys.modules,{'core.local_chat_inference':shared,bus.__name__:bus,matrix.__name__:matrix,knowledge.__name__:knowledge}), \
                patch.object(shared,'get_dispatcher',return_value=admission), \
                patch.object(shared.httpx,'AsyncClient',side_effect=client):
            chunks=[chunk async for chunk in namespace['stream_sovereign_response']('wrapped',source_context_bundle=bundle)]
            await asyncio.sleep(.02)
        tools.assert_called_once_with('wrapped')
        forbidden.assert_not_called()
        spec_system=next(payload['system'] for payload in payloads if not payload.get('stream'))
        payload=next(payload for payload in payloads if payload.get('stream'))
        self.assertIn('First wrapped dialogue line',spec_system)
        self.assertIn('First wrapped dialogue line',payload['system'])
        self.assertNotIn('First wrapped dialogue line',payload['prompt'])
        self.assertIn('"source_retrieval"',''.join(chunks))
        self.assertEqual(len(payloads),2)
        self.assertEqual(len(admission.calls),2)
        self.assertEqual(admission.active,0)


if __name__ == '__main__':
    unittest.main()
