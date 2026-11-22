"""Joint-budget preservation using synthetic context and a no-I/O dispatcher fixture."""
import ast
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import types
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from core.chat_context_budget import ChatContextBudgetError, CORE_EVIDENCE, TOOL_BOUNDARY, plan_chat_context
from core import local_chat_inference as actual_transport


class ChatContextBudgetTests(unittest.TestCase):
    def test_full_unicode_current_history_and_sources_remain_exact(self):
        class HistoryPrompt(str):
            history_projection = {'authored': 'preserved'}
        prompt = HistoryPrompt('[HISTORY]\nEarlier Ω exact punctuation!\n[CURRENT]\nHello 🛠')
        source = '[SOURCE]\nExact source Ω 🛠.\n'
        result = plan_chat_context(prompt, 'identity', [('memory', 'private body')],
                                   mandatory_source=source, mandatory_suffix=TOOL_BOUNDARY)
        self.assertIs(result['prompt'], prompt)
        self.assertEqual(result['prompt'].history_projection, {'authored': 'preserved'})
        self.assertIn(source, result['system'])
        self.assertTrue(result['system'].endswith(TOOL_BOUNDARY))
        self.assertEqual(result['receipt']['prompt_sha256'], hashlib.sha256(prompt.encode()).hexdigest())
        self.assertNotIn('private body', json.dumps(result['receipt']))

    def test_optional_blocks_are_selected_whole_in_declared_priority(self):
        result = plan_chat_context('P', 'M', [('first', 'a'*20), ('too_big', 'b'*100),
                                              ('later_small', 'c'*5)],
                                   num_ctx=50, output_tokens=10, framing_reserve=0)
        self.assertIn('a'*20, result['system'])
        self.assertNotIn('b', result['system'])
        self.assertIn('c'*5, result['system'])
        self.assertEqual(result['receipt']['omitted_labels'], ['too_big'])
        self.assertEqual(result['receipt']['optional_blocks'][1]['status'], 'omitted_whole')

    def test_suffix_is_reserved_and_remains_last_even_after_legacy_authority(self):
        suffix = '\nReceipt boundary Ω'
        legacy = 'old unrestricted authority'
        size = len(('P'+'M'+'\n\n'+legacy+suffix).encode())
        result = plan_chat_context('P', 'M', [('legacy', legacy)], mandatory_suffix=suffix,
                                   num_ctx=size+1, output_tokens=1, framing_reserve=0)
        self.assertTrue(result['system'].endswith(suffix))
        self.assertEqual(result['receipt']['admitted_input_utf8_bytes'], size)
        self.assertEqual(len(result['system'].encode())+1, size)
        self.assertEqual(result['receipt']['omitted_labels'], [])
        smaller = plan_chat_context('P', 'M', [('legacy', legacy)], mandatory_suffix=suffix,
                                    num_ctx=size, output_tokens=1, framing_reserve=0)
        self.assertEqual(smaller['receipt']['omitted_labels'], ['legacy'])
        self.assertTrue(smaller['system'].endswith(suffix))

    def test_oversized_mandatory_input_rejects_without_slicing(self):
        with self.assertRaises(ChatContextBudgetError) as caught:
            plan_chat_context('x'*7000, 'identity', mandatory_source='exact source')
        self.assertEqual(caught.exception.code, 'context_budget_exceeded')
        self.assertEqual(caught.exception.receipt['status'], 'mandatory_over_budget')
        self.assertTrue(caught.exception.receipt['authored_input_preserved'])
        self.assertEqual(caught.exception.receipt['mandatory_source_sha256'],
                         hashlib.sha256(b'exact source').hexdigest())

    def test_oversized_source_cannot_be_demoted_to_optional(self):
        with self.assertRaises(ChatContextBudgetError):
            plan_chat_context('Hello', 'identity', [('small', 'optional')], mandatory_source='Ω'*4000)

    def test_deterministic_byte_limit_and_empty_retrieval(self):
        args = ('Hello', 'Identity', [('missing_memory', ''), ('memory', 'Ω'*2000)])
        first = plan_chat_context(*args, mandatory_suffix=TOOL_BOUNDARY)
        self.assertEqual(first, plan_chat_context(*args, mandatory_suffix=TOOL_BOUNDARY))
        self.assertEqual(first['receipt']['optional_blocks'][0]['status'], 'empty')
        self.assertLessEqual(first['receipt']['admitted_input_utf8_bytes']+512+1024, 8192)

    def test_invalid_unicode_or_limits_fail_without_normalizing_authored_text(self):
        with self.assertRaises(ChatContextBudgetError):
            plan_chat_context('\ud800', 'identity')
        for kwargs in ({'num_ctx': True}, {'output_tokens': -1}, {'framing_reserve': -1}):
            with self.assertRaises(ChatContextBudgetError):
                plan_chat_context('Hello', 'identity', **kwargs)


class DispatcherContextTests(unittest.IsolatedAsyncioTestCase):
    def setup_dispatcher(self, memory=None):
        path = ROOT/'backend/core/sovereign_reasoning/dispatcher.py'
        functions = [n for n in ast.parse(path.read_text(encoding='utf-8')).body
                     if getattr(n, 'name', None) in {'_select_history_prompt', 'stream_sovereign_response'}]
        base_tree = ast.parse((ROOT/'backend/core/pipeline_context_injector.py').read_text(encoding='utf-8'))
        identity = next(ast.literal_eval(n.value) for n in base_tree.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name)and t.id=='AIBS_SOVEREIGN_SYSTEM_PROMPT'for t in n.targets))
        safety_tree = ast.parse((ROOT/'backend/core/safety_guardrails.py').read_text(encoding='utf-8'))
        safety = next(ast.literal_eval(n.value) for n in safety_tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name)and t.id=='STEHOUWER_SAFETY_DIRECTIVE'for t in n.targets))
        calls = []
        shared = types.ModuleType('core.local_chat_inference')
        shared.LocalInferenceError = actual_transport.LocalInferenceError
        shared.conversation_prompt = actual_transport.conversation_prompt
        shared.conversation_chat_messages = actual_transport.conversation_chat_messages
        shared.source_system = actual_transport.source_system
        shared.context_profile = actual_transport.context_profile
        shared.metadata_chunk = lambda value: '\n<!--AI-BS-METADATA:'+json.dumps(value)+'-->\n'
        async def stream(**kwargs):
            calls.append(kwargs)
            prompt_bytes = (sum(len(row['content'].encode()) for row in kwargs['chat_messages'])
                            if kwargs.get('chat_messages') is not None else len(kwargs['prompt'].encode()))
            self.assertLessEqual(prompt_bytes+len(kwargs['system'].encode())+512+1024,8192)
            yield 'Synthetic answer; no model request.'
        shared.stream_local = stream
        shared.complete_local = Mock(side_effect=AssertionError('No specialist inference in fixture'))
        matrix = types.ModuleType('core.sovereign_reasoning.model_domain_matrix')
        matrix.ModelDomainMatrix = SimpleNamespace(score_prompt_against_fleet=lambda _: [])
        bus = types.ModuleType('core.sovereign_reasoning.cross_model_bus')
        bus.CrossModelCognitiveBus = SimpleNamespace()
        knowledge = types.ModuleType('core.sovereign_reasoning.sourcecode_knowledge_engine')
        knowledge.sourcecode_knowledge_engine = SimpleNamespace(inject_codebase_context=lambda _: '')
        rag = types.ModuleType('core.owned_rag_sources');rag.source_reference_context=lambda *a,**k:''
        pipeline = types.ModuleType('core.pipeline_context_injector')
        pipeline.AIBS_SOVEREIGN_SYSTEM_PROMPT=identity;pipeline.disambiguate_prompt_text=lambda value:value
        memory = memory if memory is not None else Mock(return_value='PINNED_PRIVATE_FIXTURE_'+'x'*6000)
        namespace = dict(__package__='core.sovereign_reasoning',asyncio=asyncio,json=json,os=os,
            _CTX_LOG=logging.getLogger('synthetic.dispatcher'),_PRIMARY_NUM_CTX=8192,_PRIMARY_OUTPUT=1024,_FRAMING_RESERVE=512,
            Optional=Optional,List=List,Dict=Dict,Any=Any,
            SovereignDocumentEngine=SimpleNamespace(prepare_chat_payload=lambda value:(value,value)),
            audit_prompt_safety=lambda _:(True,''),check_and_execute_system_tools=lambda _:None,
            SovereignMemoryVault=SimpleNamespace(get_unified_context=lambda _:''),
            personal_memory=SimpleNamespace(format_system_prompt_block=memory,
                log_interaction_and_auto_extract=Mock(side_effect=AssertionError('No memory writes'))),
            inject_safety_directive=lambda value:value+'\n\n'+safety,
            ensure_ollama_running=Mock(side_effect=AssertionError('No process activation')),
            OLLAMA_ENDPOINTS=['http://127.0.0.1:11434/api/generate'])
        exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),namespace)
        modules={m.__name__:m for m in (shared,matrix,bus,knowledge,rag,pipeline)}
        return namespace, modules, calls, identity, safety

    async def test_actual_hello_dispatcher_projects_large_pinned_context_without_network(self):
        namespace, modules, calls, identity, safety = self.setup_dispatcher()
        # Even the base identity+pinned fixture already fails the old joint
        # transport guard; the old additional legacy text only increases it.
        self.assertGreater(len((identity+'x'*6000+'Hello').encode())+512+1024,8192)
        with patch.dict(sys.modules,modules):
            chunks=[c async for c in namespace['stream_sovereign_response']('Hello',primary_model='fixture:latest')]
        self.assertEqual(len(calls),1)
        self.assertIn('optional background', ''.join(chunks))
        self.assertIn('stored memory was not deleted', ''.join(chunks))
        self.assertEqual(calls[0]['model'],'fixture:latest')
        self.assertEqual(calls[0]['options']['num_ctx'],8192)
        self.assertIn(identity,calls[0]['system'])
        self.assertIn(safety,calls[0]['system'])
        self.assertIn(CORE_EVIDENCE,calls[0]['system'])
        self.assertTrue(calls[0]['system'].endswith(TOOL_BOUNDARY))
        selection=calls[0]['stages'][-1]['context_selection']
        self.assertIn('personal_memory_references',selection['omitted_labels'])
        self.assertNotIn('PINNED_PRIVATE_FIXTURE_',json.dumps(selection))

    async def test_automatic_sources_cannot_block_a_self_contained_request(self):
        namespace, modules, calls, _, _ = self.setup_dispatcher(Mock(return_value=''))
        modules['core.owned_rag_sources'].source_reference_context = lambda *a, **k: 'OPTIONAL_SOURCE_' + 'x'*6000
        prompt = 'Solve the CPU/GPU dependency schedule. ' + 'Task description. '*100
        with patch.dict(sys.modules, modules):
            chunks = [c async for c in namespace['stream_sovereign_response'](prompt, [], primary_model='fixture:latest')]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['chat_messages'][-1]['content'], prompt)
        self.assertNotIn('OPTIONAL_SOURCE_', calls[0]['system'])
        self.assertIn('automatic_source_references', calls[0]['stages'][-1]['context_selection']['omitted_labels'])
        self.assertIn('optional background', ''.join(chunks))

    async def test_large_optional_specialist_proposal_does_not_reject_current_request(self):
        namespace, modules, calls, _, _ = self.setup_dispatcher(Mock(return_value=''))
        fn = namespace['_select_history_prompt']
        prompt = 'Exact authored request.'
        with patch.dict(sys.modules, modules):
            built, metrics, chat = fn(prompt, [], prompt, 5000, 6656, lambda value: value, 'S'*3000)
        self.assertTrue(metrics['specialist_briefing_omitted'])
        self.assertEqual(chat[-1]['content'], prompt)
        self.assertLessEqual(metrics['input_utf8_bytes_estimate'], 6656)

    async def test_incomplete_specialist_output_is_not_primary_context(self):
        namespace, modules, calls, _, _ = self.setup_dispatcher(Mock(return_value=''))
        modules['core.sovereign_reasoning.model_domain_matrix'].ModelDomainMatrix.score_prompt_against_fleet = lambda _: [dict(model='specialist:latest',score=4,title='fixture')]
        async def incomplete(**kwargs):
            self.assertIsNotNone(kwargs['chat_messages'])
            return dict(text='UNFINISHED_SPECIALIST_'+'x'*5000, receipt=dict(steps=[],completion_verified=False))
        modules['core.local_chat_inference'].complete_local = incomplete
        with patch.dict(sys.modules, modules):
            chunks = [c async for c in namespace['stream_sovereign_response']('Solve the schedule', [], primary_model='fixture:latest')]
        self.assertEqual(len(calls), 1)
        self.assertNotIn('UNFINISHED_SPECIALIST_', str(calls[0]))
        self.assertIn('Specialist output was incomplete', ''.join(chunks))

    async def test_failed_retrieval_still_fails_without_inference_or_fabricated_memory(self):
        failed = Mock(side_effect=OSError('synthetic storage unavailable'))
        namespace,modules,calls,_,_=self.setup_dispatcher(failed)
        with patch.dict(sys.modules,modules),self.assertRaises(OSError):
            _=[c async for c in namespace['stream_sovereign_response']('Hello')]
        self.assertEqual(calls,[])

    async def test_chat_history_omission_is_visible_without_optional_background_omissions(self):
        namespace,modules,calls,_,_=self.setup_dispatcher(Mock(return_value=''))
        history=[dict(role='user',content='OLD_PRIVATE_SENTINEL_'+'x'*7000),
                 dict(role='assistant',content='Recent Ω reply'),dict(role='user',content='Hello')]
        original=json.dumps(history)
        with patch.dict(sys.modules,modules),patch.dict(os.environ,{'AIBS_USE_OLLAMA_CHAT':'1'}):
            chunks=[c async for c in namespace['stream_sovereign_response']('Hello',history,primary_model='fixture:latest')]
        self.assertIn('1 earlier conversation turn(s) were excluded',''.join(chunks))
        self.assertIn('stored conversation history was not changed',''.join(chunks))
        self.assertNotIn('optional background',''.join(chunks))
        self.assertEqual(json.dumps(history),original)
        self.assertEqual(calls[0]['chat_messages'],[history[1],dict(role='user',content='Hello')])
        metrics=calls[0]['stages'][0]['history_selection']
        self.assertTrue(metrics['chat_transport_enabled'])
        self.assertNotIn('OLD_PRIVATE_SENTINEL_',json.dumps(metrics))
        self.assertNotIn('Recent Ω reply',json.dumps(metrics))
        self.assertNotIn('admitted_chat_messages',metrics)

    async def test_generate_history_and_mandatory_oversize_fail_closed(self):
        namespace,modules,calls,_,_=self.setup_dispatcher(Mock(return_value=''))
        with patch.dict(sys.modules,modules),patch.dict(os.environ,{'AIBS_USE_OLLAMA_CHAT':'0'}):
            chunks=[c async for c in namespace['stream_sovereign_response']('Hello',
                [dict(role='user',content='x'*7000)],primary_model='fixture:latest')]
            self.assertIn('earlier conversation turn(s) were excluded',''.join(chunks))
            self.assertIsNone(calls[0]['chat_messages'])
            with self.assertRaises(actual_transport.LocalInferenceError) as caught:
                _=[c async for c in namespace['stream_sovereign_response']('Ω'*4000,[],primary_model='fixture:latest')]
        self.assertEqual(caught.exception.code,'context_budget_exceeded')
        self.assertEqual(caught.exception.receipt['rejection_stage'],'mandatory_admission')
        self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main(verbosity=2)
