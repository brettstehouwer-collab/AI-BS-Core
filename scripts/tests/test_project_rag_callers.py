"""Actual caller modules with synthetic projects/models and no service requests."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import AsyncMock,patch
import httpx
from fastapi import FastAPI,HTTPException,Request
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from core import adaptation_store,project_rag
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from routers import agent_routing as agents
from routers.conversation_router import require_conversation_owner
from security.screenwriting_access import require_screenwriting_access
OWNER='firebase:caller-fixture:A';OTHER='firebase:caller-fixture:B'

class ProjectRagCallerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='rag-callers-',dir=ROOT/'t');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'Fixture';self.project.mkdir()
        (self.project/'screenplay.fountain').write_text('INT. FIXTURE - DAY\nAuthored source.',encoding='utf8')
        for item in [patch.object(project_rag,'SCREENPLAY_ROOT',self.root),patch.multiple(adaptation_store,_root_provider=lambda:self.root,_store_mutex=threading.RLock(),_parser_factory=None)]:
            item.start();self.addCleanup(item.stop)
        self.token=bind_memory_principal(OWNER);self.addCleanup(reset_memory_principal,self.token)
        self.receipt,_=project_rag._snapshot('Fixture',OWNER)
        self.evidence=dict(status='success',project_name='Fixture',context='{"untrusted_excerpt":"Authored source."}',receipt=self.receipt,
            sources=[{'type':'script_scene','source_revision':self.receipt['sources'][0]['revision']}],retrieval={'returned_passages':1})
        self.model=AsyncMock(return_value=dict(status='success',response='Fixture draft.',generation_verified=True))
        origin=patch.object(agents,'_agent_origin',return_value='http://127.0.0.1:11434')
        self.original_origin=agents._agent_origin
        origin.start();self.addCleanup(origin.stop)

    async def test_configured_local_origin_and_explicit_override_are_validated(self):
        provider=importlib.import_module('routers.ai_providers_router')
        with patch.dict(agents.os.environ,{},clear=True),patch.object(provider,'load_config',return_value={'providers':{'local':{'host':'http://localhost:12345/'}}}):
            self.assertEqual(self.original_origin(),'http://localhost:12345')
            with patch.dict(agents.os.environ,{'OLLAMA_URL':'http://127.0.0.1:11435'}):
                self.assertEqual(self.original_origin(),'http://127.0.0.1:11435')
            with patch.dict(agents.os.environ,{'OLLAMA_URL':'https://example.com'}):
                with self.assertRaises(Exception):self.original_origin()
    async def test_singular_agent_router_requires_real_authentication(self):
        app=FastAPI();app.include_router(agents.router)
        async def denied(request:Request):raise HTTPException(403,'fixture denied')
        app.dependency_overrides[require_screenwriting_access]=denied;app.dependency_overrides[require_conversation_owner]=denied
        with patch.object(agents,'call_ollama',self.model):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://fixture') as client:
                response=await client.post('/api/agent/draft',json={'project_name':'Fixture','prompt':'source'})
        self.assertEqual(response.status_code,403);self.model.assert_not_called()
    async def test_draft_preserves_operator_instructions_and_attaches_checked_inert_context(self):
        with patch.object(project_rag,'retrieve_project_context',AsyncMock(return_value=self.evidence)) as retrieve,patch.object(agents,'call_ollama',self.model):
            result=await agents.route_creative_draft(agents.AgentPromptRequest(project_name='Fixture',prompt='source',system_instruction='Operator direction.'),owner=OWNER)
        self.assertEqual(result['receipt'],self.receipt);self.assertTrue(result['sources'])
        self.assertEqual(retrieve.call_args.kwargs['owner'],OWNER)
        system=self.model.call_args.kwargs['system_prompt'];self.assertIn('Operator direction.',system);self.assertIn('untrusted',system.lower());self.assertIn('Authored source.',system)
    async def test_missing_or_foreign_sources_never_silently_generate(self):
        with patch.object(project_rag,'retrieve_project_context',AsyncMock(return_value={**self.evidence,'status':'stale_index','context':'','sources':[]})),patch.object(agents,'call_ollama',self.model):
            result=await agents.route_creative_draft(agents.AgentPromptRequest(project_name='Fixture',prompt='source'),owner=OWNER)
        self.assertEqual(result['status'],'stale_index');self.model.assert_not_called()
        with patch.object(project_rag,'retrieve_project_context',AsyncMock(side_effect=HTTPException(403,'foreign'))),patch.object(agents,'call_ollama',self.model):
            with self.assertRaises(HTTPException):await agents.route_creative_draft(agents.AgentPromptRequest(project_name='Fixture',prompt='source'),owner=OWNER)
        self.model.assert_not_called()
    async def test_draft_source_changed_during_generation_is_not_qualified(self):
        async def model(**kwargs):
            (self.project/'screenplay.fountain').write_text('Changed source',encoding='utf8')
            return {'status':'success','response':'Old-source answer','generation_verified':True}
        with patch.object(project_rag,'retrieve_project_context',AsyncMock(return_value=self.evidence)),patch.object(agents,'call_ollama',side_effect=model):
            with self.assertRaises(HTTPException) as error:await agents.route_creative_draft(agents.AgentPromptRequest(project_name='Fixture',prompt='source'),owner=OWNER)
        self.assertEqual(error.exception.status_code,409)
    async def test_disabled_optional_controller_keeps_existing_lease_authority(self):
        class Dispatcher:
            @asynccontextmanager
            async def lease(self,*args,**kwargs):yield {'gpu_admitted':False,'execution':'controller_disabled','keep_alive_s':300}
        class Client:
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def post(self,url,**kwargs):return httpx.Response(200,json={'done':True,'message':{'content':'Real fixture response.'}},request=httpx.Request('POST',url))
        with patch.object(agents,'local_ollama_client',return_value=Client()),patch.object(agents,'get_dispatcher',return_value=Dispatcher()):
            result=await agents.call_ollama('fixture','fallback','operator','question',.2,.9)
        self.assertEqual(result['status'],'success');self.assertFalse(result['gpu_admitted']);self.assertEqual(result['execution'],'controller_disabled')

class AudioTranscriptCallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='audio-callers-',dir=ROOT/'t');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'Fixture';self.project.mkdir();(self.project/'audio').mkdir()
        (self.project/'audio'/'fixture.wav').write_bytes(b'synthetic nonplayed audio bytes')
        self.module=importlib.import_module('core.audio_transcriber')
        for item in [patch.object(self.module,'SCREENPLAY_ROOT',self.root),patch.object(project_rag,'SCREENPLAY_ROOT',self.root),patch.multiple(adaptation_store,_root_provider=lambda:self.root,_store_mutex=threading.RLock(),_parser_factory=None)]:
            item.start();self.addCleanup(item.stop)
        self.result={'text':'Current transcript words.','segments':[{'start':0.,'end':1.,'text':'Current transcript words.'}]}
        self.model=types.SimpleNamespace(transcribe=lambda *args,**kwargs:self.result)
        self.whisper_patch=patch.object(self.module,'_load_whisper_model',return_value=self.model,create=True);self.whisper_patch.start();self.addCleanup(self.whisper_patch.stop)
        async def qualified_sync(project_name,owner=None):
            receipt,docs=project_rag._snapshot(project_name,owner)
            return {'status':'success','receipt':receipt,'indexed_docs':len(docs)}
        self.sync=AsyncMock(side_effect=qualified_sync)
        self.sync_patch=patch.object(project_rag,'sync_project_screenplay',self.sync);self.sync_patch.start();self.addCleanup(self.sync_patch.stop)
    def run_worker(self):return self.module.run_transcription_sync('Fixture',owner=OWNER)
    def test_captured_owner_is_required_and_foreign_project_never_loads_a_model(self):
        with self.assertRaises(HTTPException):self.module.run_transcription_sync('Fixture',owner='')
        (self.project/'source_pdf.json').write_text(json.dumps({'contract':'owned-pdf-source-v1','owner':OTHER}),encoding='utf8')
        with self.assertRaises(HTTPException):self.run_worker()
        self.module._load_whisper_model.assert_not_called()
    def test_prior_transcript_bytes_survive_new_version_and_owned_index_sync(self):
        folder=self.project/'transcripts';folder.mkdir();old=folder/'audio_transcript.txt';old.write_bytes(b'Prior raw transcript\r\n')
        self.run_worker();self.assertEqual(old.read_bytes(),b'Prior raw transcript\r\n')
        result=self.module.get_project_transcription('Fixture',owner=OWNER)
        self.assertIn('Current transcript words.',result['transcript_markdown'])
        self.assertEqual(result['task']['indexing_status'],'indexed');self.assertEqual(self.sync.call_args.kwargs['owner'],OWNER)
        receipt,docs=project_rag._snapshot('Fixture',OWNER)
        self.assertEqual(receipt['sources'][0]['type'],'audio_transcript');self.assertIn('Current transcript words.',docs[0]['content'])
    def test_index_failure_does_not_erase_successful_transcription_or_claim_synced(self):
        self.sync.side_effect=HTTPException(503,'synthetic vector service offline');self.run_worker()
        task=self.module.get_transcription_status('Fixture',owner=OWNER)
        self.assertEqual(task['transcription_status'],'complete');self.assertEqual(task['indexing_status'],'failed')
        self.assertNotIn('synced',task['step'].lower());self.assertTrue(self.module.get_project_transcription('Fixture',owner=OWNER)['has_transcript'])
    def test_empty_model_output_is_not_a_success_or_new_current_version(self):
        self.result={'text':'','segments':[]};self.run_worker()
        task=self.module.get_transcription_status('Fixture',owner=OWNER)
        self.assertEqual(task['status'],'error');self.assertFalse((self.project/'transcripts'/'current.json').exists());self.sync.assert_not_called()
    def test_owner_task_keys_and_linked_storage_are_never_shared(self):
        self.run_worker();self.assertEqual(self.module.get_transcription_status('Fixture',owner=OTHER)['status'],'idle')
        with patch.object(self.module,'_plain',side_effect=HTTPException(409,'linked fixture')):
            with self.assertRaises(HTTPException):self.module.get_project_transcription('Fixture',owner=OWNER)

    def test_interrupted_pointer_preserves_previous_current_and_retryable_version(self):
        self.run_worker();pointer=self.project/'transcripts'/'current.json';before=pointer.read_bytes()
        self.result={'text':'Newer transcript words.','segments':[{'start':0.,'end':2.,'text':'Newer transcript words.'}]}
        with patch.object(self.module.os,'replace',side_effect=PermissionError('synthetic publication interruption')):self.run_worker()
        self.assertEqual(pointer.read_bytes(),before);self.assertEqual(self.module.get_transcription_status('Fixture',owner=OWNER)['status'],'error')
        self.run_worker();self.assertNotEqual(pointer.read_bytes(),before)
        self.assertIn('Newer transcript words.',self.module.get_project_transcription('Fixture',owner=OWNER)['transcript_markdown'])
        self.assertGreaterEqual(len(list((self.project/'transcripts'/'versions').iterdir())),2)

    def test_corrupt_current_never_falls_back_to_stale_legacy_transcript(self):
        self.run_worker();current=self.module.read_current_transcript('Fixture',owner=OWNER)
        (self.project/current['source_file']).write_text('Tampered current bytes.',encoding='utf8')
        (self.project/'transcripts'/'audio_transcript.md').write_text('Wrong old fallback.',encoding='utf8')
        with self.assertRaises(HTTPException):self.module.get_project_transcription('Fixture',owner=OWNER)

    def test_ambiguous_audio_reports_an_owned_error_instead_of_old_completion(self):
        (self.project/'audio'/'other.wav').write_bytes(b'second synthetic input')
        self.run_worker();task=self.module.get_transcription_status('Fixture',owner=OWNER)
        self.assertEqual(task['status'],'error');self.assertIn('Several audio',task['message']);self.module._load_whisper_model.assert_not_called()

if __name__=='__main__':unittest.main()
