"""Actual common adapter + existing reviewed route fixture; isolated records only."""
import asyncio,copy,hashlib,importlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,Mock,patch
from fastapi import HTTPException
from fastapi.responses import JSONResponse,StreamingResponse

ROOT=Path('C:/AI-BS');sys.path.insert(0,str(ROOT))
from scripts.tests import test_bs_chat_openai as routes
from scripts.tests import test_ai_provider_environment as environment
OWNER='firebase:program-status-integration:owner'


class ProgramStatusIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'t',prefix='status-integration-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.put('version.txt','v1.2.345\n')
        self.put('frontend/public/version.json',json.dumps(dict(version='v1.2.345',artifact_scope='application-source')))
        self.put('docs/CODEX_HANDOFF.md','## TAKEOVER-20261110-01 — 2026-11-10T01:00:00Z\nFixture only; not real documents.\n')
        job='a'*32
        self.put('state/project_maintenance/current-api.json',json.dumps(dict(job_id=job)))
        self.put('state/project_maintenance/'+job+'/state.json',json.dumps(dict(job_id=job,state='succeeded',lane='all',operation='build_update',completed_at='2026-11-10T02:00:00Z',message='PRIVATE_FIELD_NOT_FOR_RESPONSE')))
        # Reuse the existing full-source provider/router loader and its complete
        # reviewed legacy definition scope. Do not invent a smaller AST scope.
        self.fixture=routes.BsChatOpenAITests('runTest');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        # The legacy JSON handler calls coding admission for all text turns.
        # Exercise its actual early-refusal function, rather than treating the
        # old fixture's classification-call log as executed host work.
        self.coding=environment.load_source('backend/core/coding_chat.py','core.coding_chat')
        self.coding_results=[]
        real_admission=self.coding.coding_request
        def admission(body):
            result=real_admission(body);self.coding_results.append(result);return result
        self.start(patch.object(self.coding,'coding_request',Mock(side_effect=admission)))
        self.coding_task=self.start(patch.object(self.coding,'run_coding_task',side_effect=AssertionError('No coding task')))
        self.coding_admit=self.start(patch.object(self.coding,'admit_request',side_effect=AssertionError('No coding request mutation')))
        self.program=importlib.import_module('core.program_status_readonly')
        self.scope=importlib.import_module('core.personal_memory_scope')
        real=self.program.resolve_program_update_status
        self.resolve=Mock(side_effect=lambda body,**fields:real(body,root=self.root,**fields))
        self.start(patch.object(self.program,'resolve_program_update_status',self.resolve))
        self.start(patch.object(self.fixture.guard,'get_admin_principal',lambda key,authorization:OWNER if key==environment.ADMIN_KEY else None))
        self.credential=self.start(patch.object(self.fixture.gateway,'_openai_credential',side_effect=AssertionError('No key resolution for status')))
        self.generation=self.start(patch.object(self.fixture.helper,'openai_completion',new=AsyncMock(side_effect=AssertionError('No provider generation'))))
        self.process_trap=self.start(patch('subprocess.Popen',side_effect=AssertionError('No host process')))
        # The existing fixture replaces HTTP with MockTransport. Windows'
        # Proactor loop legitimately connects its private socketpair, so guard
        # external name resolution rather than breaking the loop's own IPC.
        self.dns_trap=self.start(patch('socket.getaddrinfo',side_effect=AssertionError('No external resolution')))
        for app in {id(client.app):client.app for client in (self.fixture.hybrid_client,self.fixture.normal_client,self.fixture.legacy_client)}.values():
            @app.middleware('http')
            async def bind_verified_owner(request,call_next):
                try:principal=await self.fixture.guard.require_host_admin(request)
                except HTTPException as error:return JSONResponse({'detail':error.detail},status_code=error.status_code)
                token=self.scope.bind_memory_principal(principal)
                try:return await call_next(request)
                finally:self.scope.reset_memory_principal(token)
        self.before=self.snapshot();self.config_before=copy.deepcopy(self.fixture.cfg)
        self.addCleanup(self.assert_preserved)
    def start(self,setting):
        value=setting.start();self.addCleanup(setting.stop);return value
    def put(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    def snapshot(self):return {str(path.relative_to(self.root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in self.root.rglob('*') if path.is_file()}
    def assert_preserved(self):
        print('PROGRAM_STATUS_INTEGRATION_EVIDENCE '+json.dumps(dict(case=self.id().split('.')[-1],
            legacy_coding_admission_checks=len(self.coding_results),all_admission_results_none=all(result is None for result in self.coding_results),
            actual_coding_tasks=self.coding_task.call_count,coding_request_writes=self.coding_admit.call_count,
            subprocesses=self.process_trap.call_count,provider_generation=self.generation.await_count,
            credential_resolutions=self.credential.call_count,http_mock_requests=len(self.fixture.outbound),
            external_dns=self.dns_trap.call_count,provider_config_saves=self.fixture.save.call_count,
            fixture_record_hashes_unchanged=self.snapshot()==self.before,local_branch_markers=len(self.fixture.local_calls)),sort_keys=True))
        self.assertEqual(self.snapshot(),self.before);self.assertEqual(self.fixture.cfg,self.config_before)
        self.fixture.save.assert_not_called();self.credential.assert_not_called();self.generation.assert_not_awaited()
        self.assertEqual(self.fixture.outbound,[]);self.assertTrue(all(result is None for result in self.coding_results))
        self.coding_task.assert_not_called();self.coding_admit.assert_not_called()
        self.process_trap.assert_not_called();self.dns_trap.assert_not_called()
    def direct(self,**fields):
        token=self.scope.bind_memory_principal(OWNER)
        try:return asyncio.run(self.fixture.helper.bs_chat_reply({'prompt':'whats new?','user_prompt':'whats new?',**fields}))
        finally:self.scope.reset_memory_principal(token)
    def targets(self):
        return ((self.fixture.hybrid_client,'/api/v1/hybrid-chat/stream'),(self.fixture.normal_client,'/api/chat'),
                (self.fixture.legacy_client,'/api/v1/hybrid-chat/stream'),(self.fixture.legacy_client,'/api/chat'),
                (self.fixture.legacy_client,'/v1/chat/completions'))
    def post(self,client,path,**fields):
        return client.post(path,headers=self.fixture.headers,json={'prompt':'whats new?','user_prompt':'whats new?','stream':False,**fields})
    def test_actual_common_local_and_openai_status_need_no_generation_or_credential(self):
        for provider in ('local','openai'):
            reply=self.direct(provider=provider,model='selected-model-preserved')
            self.assertEqual(reply['model'],'program-status-records');self.assertIn('v1.2.345',reply['response'])
            self.assertIn('2026-11-10T02:00:00Z',reply['response']);self.assertIn(str(self.root),reply['response'])
        self.assertEqual(self.fixture.local_calls,[])
    def test_existing_active_and_legacy_asgi_routes_serve_exact_status_without_model_tools(self):
        for client,path in self.targets():
            for provider in ('local','openai'):
                with self.subTest(path=path,provider=provider):
                    response=self.post(client,path,provider=provider)
                    self.assertEqual(response.status_code,200,response.text);self.assertIn('Source version: v1.2.345',response.text)
                    self.assertIn('Recorded local maintenance: succeeded',response.text);self.assertNotIn('PRIVATE_FIELD_NOT_FOR_RESPONSE',response.text)
        self.assertEqual(self.fixture.local_calls,[])
    def test_unsupported_provider_still_fails_before_program_status_reads(self):
        calls=self.resolve.call_count
        with self.assertRaises(HTTPException) as error:self.direct(provider='unsupported')
        self.assertEqual(error.exception.status_code,400)
        for client,path in self.targets():self.assertEqual(self.post(client,path,provider='unsupported').status_code,400)
        self.assertEqual(self.resolve.call_count,calls);self.assertEqual(self.fixture.local_calls,[])
    def test_explicit_source_scope_reaches_existing_local_source_path(self):
        attached=importlib.import_module('core.attached_source_context')
        refs=[{'source_id':'b'*32,'source_sha256':'c'*64}];bundle={'context':'fixture source only','receipt':{'status':'retrieved'}}
        capture=AsyncMock(return_value=bundle)
        with patch.object(attached,'request_source_bundle',capture):
            response=self.fixture.post_hybrid(provider='local',prompt='whats new?',user_prompt='whats new?',source_references=refs)
        self.assertEqual(response.status_code,200);self.assertIn('fixture local path',response.text);self.assertNotIn('program-status-records',response.text)
        capture.assert_awaited_once();self.assertEqual(self.fixture.local_source_bundle,bundle)
    def test_legacy_inline_attachment_and_current_user_prompt_keep_normal_local_flow(self):
        for fields in ({'prompt':'[ATTACHED FILE: fixture.pdf]\nwhats new?','user_prompt':'whats new?'},
                       {'prompt':'whats new?','user_prompt':'Explain this current question','messages':[{'role':'user','content':'whats new?'}]}):
            response=self.fixture.post_hybrid(provider='local',**fields)
            self.assertEqual(response.status_code,200);self.assertIn('fixture local path',response.text);self.assertNotIn('program-status-records',response.text)
        self.assertEqual(len(self.fixture.local_calls),2)
    def test_web_vm_and_plan_routes_preserve_existing_behavior(self):
        async def web(body):return StreamingResponse(iter(['fixture explicit web response']),media_type='text/plain') if body.get('use_web_search') else None
        self.fixture.research.web_search_response=AsyncMock(side_effect=web)
        response=self.fixture.post_hybrid(provider='local',prompt='whats new?',user_prompt='whats new?',use_web_search=True)
        self.assertIn('fixture explicit web response',response.text)
        self.assertIsNone(self.direct(provider='local',use_web_search=True))
        for fields,label in (({'execution_backend':'windows_vm'},'ISOLATION_UNAVAILABLE'),({'plan_only':True},'Plan/review'),({'mode':'review'},'Plan/review')):
            response=self.fixture.post_hybrid(provider='local',prompt='whats new?',user_prompt='whats new?',**fields)
            self.assertEqual(response.status_code,200);self.assertIn(label,response.text);self.assertNotIn('program-status-records',response.text)
            self.assertIn(label,self.direct(provider='local',**fields)['response'])
        self.assertEqual(self.fixture.local_calls,[])
    def test_existing_asgi_auth_and_common_owner_guard_precede_record_reads(self):
        calls=self.resolve.call_count
        for client,path in self.targets():
            self.assertEqual(client.post(path,json={'prompt':'whats new?','user_prompt':'whats new?'}).status_code,403)
        self.assertEqual(self.resolve.call_count,calls)
        with self.assertRaises(HTTPException) as error:asyncio.run(self.fixture.helper.bs_chat_reply({'prompt':'whats new?','user_prompt':'whats new?','provider':'local'}))
        self.assertEqual(error.exception.status_code,403)
    def test_build_upgrade_and_execute_imperatives_are_not_status_authorization(self):
        for prompt in ('build AI-BS','upgrade AI-BS','execute latest update','whats new? build it now'):
            self.assertIsNone(self.direct(provider='local',prompt=prompt,user_prompt=prompt))
        self.assertEqual(self.fixture.local_calls,[])


if __name__=='__main__':unittest.main(verbosity=2)
