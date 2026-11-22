"""Actual project RAG inference transports with fake leases/HTTP; no real models/DB."""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock,Mock,patch
import httpx
from fastapi import HTTPException

ROOT=next(parent for parent in Path(__file__).resolve().parents if (parent/'backend').is_dir() and (parent/'scripts/tests').is_dir())
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'backend'))
from scripts.tests.test_local_chat_inference import Admission
from core import local_chat_inference as local
STAGE=Path(os.environ['AIBS_PROJECT_RAG_STAGE_ROOT']) if os.environ.get('AIBS_PROJECT_RAG_STAGE_ROOT') else None
spec=importlib.util.spec_from_file_location('qualified_project_rag',(STAGE or ROOT)/'backend/core/project_rag.py')
rag=importlib.util.module_from_spec(spec);spec.loader.exec_module(rag)
ORIGINAL_SNAPSHOT=rag._snapshot
ORIGINAL_RETRIEVE=rag.retrieve_project_context

class ProjectRagRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.admission=Admission();self.calls=[];self.actual_client=httpx.AsyncClient;self.actual_model=None;self.reason='stop';self.block=None
        self.receipt=dict(schema=rag.SCHEMA,project_name='Synthetic',owner_hash='a'*64,snapshot_sha256='b'*64,complete=True,sources=[dict(revision='c'*64)])
        self.evidence=dict(status='success',project_name='Synthetic',context='Untrusted source excerpt: SYNTHETIC_SEVEN_KEYS.',sources=[dict(source_revision='c'*64)],receipt=self.receipt)
        async def retrieve(*_,**__):return copy.deepcopy(self.evidence)
        async def handler(request):
            data=json.loads(request.content);self.calls.append((str(request.url),data))
            if self.block is not None:
                self.block.set();await asyncio.Event().wait()
            model=self.actual_model or data['model']
            if request.url.path.endswith('/embeddings'):return httpx.Response(200,json=dict(model=model,embedding=[.1,.2,.3]))
            return httpx.Response(200,json=dict(model=model,done=True,done_reason=self.reason,response='The synthetic archive has seven keys.',message=dict(content='The synthetic archive has seven keys.')))
        def client(**kwargs):return self.actual_client(transport=httpx.MockTransport(handler),**kwargs)
        for guard in [patch.object(rag,'get_dispatcher',return_value=self.admission,create=True),patch.object(local,'get_dispatcher',return_value=self.admission),
            patch.object(rag.httpx,'AsyncClient',side_effect=client),patch.object(rag,'retrieve_project_context',side_effect=retrieve),
            patch.object(rag,'_snapshot',return_value=(self.receipt,[]))]:guard.start();self.addCleanup(guard.stop)

    async def test_embedding_has_one_actual_lease_and_provenance_without_gpu_execution_claim(self):
        seen=[];vector=await rag.get_embedding_async('synthetic vector input',receipt_sink=seen.append)
        self.assertEqual(vector,[.1,.2,.3]);self.assertEqual(len(self.calls),1);self.assertEqual(len(self.admission.calls),1)
        self.assertEqual(self.admission.released,1);self.assertFalse(seen[-1]['admission']['gpu_admitted'])
        self.assertEqual(seen[-1]['input_sha256'],hashlib.sha256(b'synthetic vector input').hexdigest())
        self.assertEqual(seen[-1]['dimensions'],3)

    async def test_selected_generation_uses_actual_shared_transport_and_one_lease(self):
        result=await rag.query_project_rag_assistant('Synthetic','How many keys?',custom_model='fixture:latest',owner='synthetic')
        self.assertEqual(len(self.calls),1);self.assertEqual(len(self.admission.calls),1);self.assertEqual(self.admission.released,1)
        self.assertTrue(result['completion_verified']);self.assertEqual(result['requested_model'],'fixture:latest')
        self.assertEqual(result['model'],'fixture:latest');self.assertIn('SYNTHETIC_SEVEN_KEYS',self.calls[-1][1]['system'])

    async def test_wrong_model_never_becomes_selected_generation_success(self):
        self.actual_model='wrong:latest'
        with self.assertRaises(HTTPException):await rag.query_project_rag_assistant('Synthetic','keys',custom_model='fixture:latest',owner='synthetic')
        self.assertEqual(len(self.calls),1)

    async def test_length_output_retained_with_visible_partial_warning_and_false_completion(self):
        self.reason='length';result=await rag.query_project_rag_assistant('Synthetic','keys',custom_model='fixture:latest',owner='synthetic')
        self.assertFalse(result['completion_verified']);self.assertIn('may be incomplete',result['response'])
        self.assertIn('seven keys',result['response'])

    async def test_embedding_cancellation_releases_its_only_lease(self):
        self.block=asyncio.Event();task=asyncio.create_task(rag.get_embedding_async('synthetic'))
        await asyncio.wait_for(self.block.wait(),1);task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(self.admission.released,1);self.assertEqual(self.admission.active,0)

    async def test_embedding_rechecks_admitted_context_before_http(self):
        self.admission.ctx=1024
        with self.assertRaises(HTTPException):await rag.get_embedding_async('x'*2000)
        self.assertEqual(self.calls,[]);self.assertEqual(self.admission.released,1)

    async def test_wrong_reported_embedding_model_is_not_verified_vector(self):
        self.actual_model='wrong-embedding'
        with self.assertRaises(HTTPException):await rag.get_embedding_async('synthetic')
        self.assertEqual(len(self.calls),1)

    async def test_sync_embedding_reuses_admitted_async_path_in_worker(self):
        with patch.object(rag.httpx,'Client',side_effect=AssertionError('Unadmitted sync HTTP must not run')):
            vector=await asyncio.to_thread(rag.get_embedding_sync,'synthetic')
        self.assertEqual(vector,[.1,.2,.3]);self.assertEqual(len(self.admission.calls),1)

    async def test_actual_source_sync_readback_retrieval_generation_use_three_sequential_leases(self):
        from scripts.tests.test_project_rag_takeover import Store
        with tempfile.TemporaryDirectory(prefix='qualified-rag-',dir=ROOT/'t') as temporary:
            root=Path(temporary);project=root/'Synthetic';project.mkdir()
            raw=b'INT. SYNTHETIC ARCHIVE - DAY\nThe synthetic archive has seven keys.'
            (project/'screenplay.fountain').write_bytes(raw);store=Store()
            with patch.object(rag,'_snapshot',ORIGINAL_SNAPSHOT),patch.object(rag,'retrieve_project_context',ORIGINAL_RETRIEVE), \
                    patch.object(rag,'SCREENPLAY_ROOT',root),patch.object(rag,'get_chroma_client',return_value=store):
                indexed=await rag.sync_project_screenplay('Synthetic',owner='synthetic')
                result=await rag.query_project_rag_assistant('Synthetic','How many keys?',custom_model='fixture:latest',owner='synthetic')
            self.assertEqual(indexed['receipt']['sources'][0]['revision'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(len(indexed['embedding_evidence']),1)
            self.assertEqual(indexed['embedding_evidence'][0]['dimensions'],3)
            self.assertTrue(result['completion_verified']);self.assertEqual(len(self.calls),3)
            self.assertEqual(len(self.admission.calls),3);self.assertEqual(self.admission.released,3)

    async def test_sync_embedding_cannot_block_an_active_async_event_loop(self):
        with self.assertRaises(HTTPException):rag.get_embedding_sync('synthetic')
        self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
