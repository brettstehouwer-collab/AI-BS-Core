"""Real dispatcher selection and local transport; synthetic HTTP and admission only."""
import asyncio
import copy
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

import httpx

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.tests import test_chat_context_budget as context_tests
transport=context_tests.actual_transport


class Admission:
    def __init__(self):self.active=0;self.released=0
    @asynccontextmanager
    async def lease(self,*args,**kwargs):
        self.active+=1
        try:yield dict(gpu_admitted=False,execution='synthetic',num_ctx=8192,keep_alive_s=0)
        finally:self.active-=1;self.released+=1


class HistoryTransportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls=[];self.status=200;self.stream=None;self.admission=Admission()
        self.data=dict(model='fixture:latest',message=dict(content='Synthetic Ω answer'),done=True,done_reason='stop')
        self.actual_client=httpx.AsyncClient
        def handler(request):
            self.calls.append((str(request.url),json.loads(request.content)))
            if self.stream is not None:return httpx.Response(self.status,stream=self.stream)
            body=json.dumps(self.data)+'\n'
            return httpx.Response(self.status,content=body.encode())
        def client(**kwargs):return self.actual_client(transport=httpx.MockTransport(handler),**kwargs)
        for guard in (patch.object(transport,'get_dispatcher',return_value=self.admission),
                      patch.object(transport.httpx,'AsyncClient',side_effect=client),
                      patch.dict(os.environ,{'AIBS_USE_OLLAMA_CHAT':'1'})):
            guard.start();self.addCleanup(guard.stop)
        self.namespace,self.modules,_,_,_=context_tests.DispatcherContextTests.setup_dispatcher(self,Mock(return_value=''))
        self.modules['core.local_chat_inference'].stream_local=transport.stream_local
        attached=types.ModuleType('core.attached_source_context')
        attached.source_unavailable_reply=lambda _:None
        self.modules[attached.__name__]=attached
        self.bundle=dict(context='[ATTACHED_SOURCE_REFERENCES]\nSOURCE_PRIVATE_SENTINEL Ω exact evidence.'+'Ω'*1400,
                         receipt=dict(schema='aibs.attached_source_retrieval.v1',status='retrieved',
                                      sources=[dict(source_id='a'*32,source_sha256='b'*64)],passages=[]))
        self.history=[dict(role='user',content='OLD_PRIVATE_SENTINEL_'+'x'*7000),
                      dict(role='assistant',content='Recent reply'),dict(role='user',content='Hello Ω')]

    async def collect(self,history=None):
        with patch.dict(sys.modules,self.modules):
            return ''.join([c async for c in self.namespace['stream_sovereign_response']('Hello Ω',
                self.history if history is None else history,source_context_bundle=self.bundle,primary_model='fixture:latest')])

    def receipts(self,text):
        return [json.loads(part.split('-->',1)[0]) for part in text.split('<!--AI-BS-METADATA:')[1:]]

    async def test_real_chat_payload_reserves_exact_attachment_and_hides_private_roles_from_metrics(self):
        original=copy.deepcopy(self.history)
        text=await self.collect()
        self.assertEqual(self.history,original)
        self.assertEqual(len(self.calls),1)
        url,payload=self.calls[0]
        self.assertTrue(url.endswith('/api/chat'))
        self.assertEqual(payload['model'],'fixture:latest')
        self.assertEqual(payload['messages'][1:],[self.history[1],dict(role='user',content='Hello Ω')])
        self.assertIn(self.bundle['context'],payload['messages'][0]['content'])
        self.assertIn('1 earlier conversation turn(s) were excluded',text)
        receipt=self.receipts(text)[-1]
        self.assertEqual(receipt['transport_mode'],'chat')
        actual_bytes=sum(len(m['content'].encode()) for m in payload['messages'])
        self.assertEqual(receipt['context_budget']['input_utf8_bytes'],actual_bytes)
        selection=receipt['steps'][0]['history_selection']
        self.assertEqual(selection['input_utf8_bytes_estimate'],actual_bytes)
        self.assertTrue(selection['chat_transport_enabled'])
        self.assertLessEqual(actual_bytes+512+1024,8192)
        for marker in ('SOURCE_PRIVATE_SENTINEL','OLD_PRIVATE_SENTINEL','Recent reply','admitted_chat_messages'):
            self.assertNotIn(marker,json.dumps(self.receipts(text)))
        self.assertTrue(receipt['completion_verified'])
        self.assertEqual(self.admission.released,1)

    async def test_generate_option_uses_matching_payload_accounting(self):
        self.data=dict(model='fixture:latest',response='Synthetic answer',done=True,done_reason='stop')
        with patch.dict(os.environ,{'AIBS_USE_OLLAMA_CHAT':'0'}):text=await self.collect()
        url,payload=self.calls[0]
        self.assertTrue(url.endswith('/api/generate'))
        receipt=self.receipts(text)[-1]
        actual_bytes=len(payload['prompt'].encode())+len(payload['system'].encode())
        self.assertEqual(receipt['context_budget']['input_utf8_bytes'],actual_bytes)
        self.assertEqual(receipt['steps'][0]['history_selection']['input_utf8_bytes_estimate'],actual_bytes)
        self.assertFalse(receipt['steps'][0]['history_selection']['chat_transport_enabled'])
        self.assertIn(self.bundle['context'],payload['system'])

    async def test_chat_without_attachment_preserves_genuine_repeated_turns_and_final_accounting(self):
        self.bundle=None
        self.namespace['personal_memory'].log_interaction_and_auto_extract=Mock(return_value=None)
        history=[dict(role='user',content='Hello Ω'),dict(role='assistant',content='Earlier reply'),
                 dict(role='user',content='Hello Ω')]
        text=await self.collect(history)
        payload=self.calls[0][1]
        self.assertEqual(payload['messages'][1:],history)
        self.assertTrue(payload['messages'][0]['content'].endswith(context_tests.TOOL_BOUNDARY))
        receipt=self.receipts(text)[-1]
        actual_bytes=sum(len(m['content'].encode()) for m in payload['messages'])
        self.assertEqual(receipt['context_budget']['input_utf8_bytes'],actual_bytes)
        self.assertEqual(receipt['steps'][0]['history_selection']['input_utf8_bytes_estimate'],actual_bytes)
        self.assertEqual(receipt['steps'][1]['context_selection']['admitted_input_utf8_bytes'],actual_bytes)
        self.assertEqual(receipt['steps'][1]['context_selection']['prompt_representation'],'chat_content_concatenation')
        self.assertLessEqual(actual_bytes+512+1024,8192)
        self.assertNotIn('earlier conversation turn(s) were excluded',text)

    async def test_mandatory_request_and_source_too_large_fail_before_http(self):
        self.bundle['context']='Ω'*3000
        with patch.dict(sys.modules,self.modules),self.assertRaises(transport.LocalInferenceError) as caught:
            _=[c async for c in self.namespace['stream_sovereign_response']('Ω'*1000,[],
                source_context_bundle=self.bundle,primary_model='fixture:latest')]
        self.assertEqual(caught.exception.code,'context_budget_exceeded')
        self.assertTrue(caught.exception.receipt['authored_input_preserved'])
        self.assertTrue(caught.exception.receipt['mandatory_source_preserved'])
        self.assertEqual(self.calls,[])
        self.assertEqual(self.admission.active,0)

    async def test_chat_http_and_bad_response_errors_do_not_retry_or_confirm(self):
        for status,data in ((500,self.data),(200,dict(model='fixture:latest',message=None,done=True)),
                            (200,dict(model='other:latest',message=dict(content='wrong model'),done=True))):
            with self.subTest(status=status,data=data):
                self.calls.clear();self.status=status;self.data=data
                text=await self.collect()
                self.assertEqual(len(self.calls),1)
                self.assertEqual(self.receipts(text)[-1]['status'],'error')
                self.assertFalse(self.receipts(text)[-1]['completion_verified'])

    async def test_partial_chat_disconnect_never_replays(self):
        class Broken(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield b'{"model":"fixture:latest","message":{"content":"partial"},"done":false}\n'
                raise httpx.ReadError('synthetic disconnect')
        self.stream=Broken()
        text=await self.collect()
        self.assertIn('partial',text)
        self.assertIn('no replay was attempted',text)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.receipts(text)[-1]['status'],'error')
        self.assertEqual(self.admission.active,0)

    async def test_cancelled_chat_closes_transport_and_releases_without_replay(self):
        class Blocked(httpx.AsyncByteStream):
            def __init__(self):self.entered=asyncio.Event();self.closed=False
            async def __aiter__(self):
                yield b'{"model":"fixture:latest","message":{"content":"partial"},"done":false}\n'
                self.entered.set();await asyncio.Event().wait()
            async def aclose(self):self.closed=True
        self.stream=Blocked()
        task=asyncio.create_task(self.collect())
        await asyncio.wait_for(self.stream.entered.wait(),2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertTrue(self.stream.closed)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.admission.released,1)
        self.assertEqual(self.admission.active,0)


if __name__=='__main__':unittest.main(verbosity=2)
