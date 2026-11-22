"""Grounded planning only; synthetic retained source, no project execution."""
import asyncio
import hashlib
import json
import unittest
from unittest.mock import AsyncMock,patch
import uuid

from test_coding_preparation import PreparationTests
from core import coding_preparation as preparation
try:
    from core import coding_preparation_planning as planning
except ImportError:
    planning=None


class PlanningTests(unittest.TestCase):
    setUpClass=classmethod(PreparationTests.setUpClass.__func__)
    payload=PreparationTests.payload
    job=PreparationTests.job
    client=PreparationTests.client

    def setUp(self):
        self.assertIsNotNone(planning,'Grounded preparation planning is missing')
        PreparationTests.setUp(self)
        self.plan['objective']='Explain how to change the returned value to42 and keep the existing checks.'
        preparation.prepare_request(self.owner,self.payload())
        self.plan_id=uuid.uuid4().hex
        self.proposal={'summary':'Update the selected implementation only.',
            'steps':[{'path':'src/app.py','change':'Return42 instead of the previous value.'}],'questions':[]}
        self.http_adapter=planning._http_plan
        self.provider=patch.object(planning,'_http_plan',new_callable=AsyncMock).start()
        self.provider.return_value=json.dumps(self.proposal)

    def generate(self,owner=None,identifier=None):
        return asyncio.run(planning.generate_plan(owner or self.owner,self.plan['request_id'],identifier or self.plan_id))

    def folder(self):return self.job()/'planning'/self.plan_id

    def test_grounded_plan_preserves_exact_inputs_and_never_executes(self):
        original=(self.repo/'src/app.py').read_bytes()
        result=self.generate()
        self.assertEqual(result['state'],'PLAN_PROPOSED');self.assertEqual(result['proposal'],self.proposal)
        self.assertFalse(result['execution_authorized']);self.assertEqual(result['verification_status'],'not_run')
        self.assertEqual((self.repo/'src/app.py').read_bytes(),original)
        data=self.provider.call_args.args[0]
        self.assertEqual(data['objective'],self.plan['objective'])
        self.assertEqual({f['path'] for f in data['source_files']},{'src/app.py','tests/test_app.py'})
        self.assertEqual(data['checks'][0]['argv'],['python','-m','unittest','tests.test_app'])
        self.assertTrue(all('sha256' in f and 'excerpt_complete' in f for f in data['source_files']))
        self.assertFalse((self.requests/self.plan_id/'request.json').exists())

    def test_questions_stay_unresolved_without_success(self):
        self.proposal['questions']=['Should42 apply to every caller?'];self.provider.return_value=json.dumps(self.proposal)
        self.assertEqual(self.generate()['state'],'NEEDS_CLARIFICATION')

    def test_coordinated_python_and_react_plan_preserves_all_check_inputs(self):
        (self.repo/'src/App.jsx').write_bytes(b'export default function App() { return <span>1</span>; }\n')
        self.plan['request_id']=uuid.uuid4().hex
        self.plan['files'] += [{'relative_path':'src/App.jsx','role':'editable'},
            {'relative_path':'package.json','role':'dependency'},{'relative_path':'package-lock.json','role':'dependency'}]
        self.plan['checks'].append({'check_id':'frontend','profile':'npm_script','targets':['test']})
        preparation.prepare_request(self.owner,self.payload())
        self.proposal['steps'].append({'path':'src/App.jsx','change':'Display42 while preserving component behavior.'})
        self.provider.return_value=json.dumps(self.proposal)
        self.assertEqual(self.generate()['state'],'PLAN_PROPOSED')
        context=self.provider.call_args.args[0]
        self.assertEqual(set(context['editable_paths']),{'src/app.py','src/App.jsx'})
        self.assertEqual(len(context['checks']),2)
        self.assertEqual((self.repo/'package.json').read_bytes(),b'{"scripts":{"test":"do-not-execute"}}')

    def test_retry_reads_identical_result_without_another_model_call(self):
        first=self.generate();self.assertEqual(self.generate(),first);self.assertEqual(self.provider.await_count,1)
        self.assertEqual(planning.read_plan(self.owner,self.plan['request_id'],self.plan_id),first)

    def test_cross_owner_missing_preparation_cannot_invoke_model(self):
        with self.assertRaises(preparation.PreparationNotFound):self.generate(owner='firebase:fixture:bob')
        self.provider.assert_not_awaited()

    def test_invalid_identifiers_and_missing_preparation_do_not_call_model(self):
        for identifier in ['../escape','Z'*32,'a'*31]:
            with self.assertRaises(ValueError):self.generate(identifier=identifier)
        with self.assertRaises(preparation.PreparationNotFound):asyncio.run(planning.generate_plan(self.owner,'0'*32,self.plan_id))
        self.provider.assert_not_awaited()

    def test_malformed_duplicate_unknown_or_incomplete_output_is_failed(self):
        outputs=['not JSON','{"summary":"a","summary":"b","steps":[],"questions":[]}',
            json.dumps(dict(self.proposal,tool_call={'name':'execute'})),
            json.dumps(dict(self.proposal,steps=[])),
            json.dumps(dict(self.proposal,steps=[{'path':'tests/test_app.py','change':'Weaken tests'}])),
            json.dumps(dict(self.proposal,steps=[{'path':'../outside.py','change':'Edit'}])),
            json.dumps(dict(self.proposal,steps=self.proposal['steps']*2))]
        for output in outputs:
            with self.subTest(output=output[:35]):
                self.provider.return_value=output
                result=self.generate(identifier=uuid.uuid4().hex)
                self.assertEqual(result['state'],'FAILED');self.assertIsNone(result['proposal'])
                self.assertEqual(result['error_code'],'invalid_model_output')

    def test_known_credentials_are_excluded_from_public_and_retained_response(self):
        secret='synthetic-owned-secret-for-planning44'
        with patch.dict('os.environ',{'PLANNING_FIXTURE_TOKEN':secret}):
            self.provider.return_value=json.dumps(dict(self.proposal,summary=secret))
            result=self.generate();self.assertEqual(result['state'],'FAILED')
            self.assertNotIn(secret,(self.folder()/'result.json').read_text(encoding='utf-8'))

    def test_retained_input_tamper_stops_before_model(self):
        (self.job()/'inputs/src/app.py').write_text('value = 999\n',encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError):self.generate()
        self.provider.assert_not_awaited()

    def test_input_tamper_during_inference_is_not_a_proposal(self):
        async def changed(_):
            (self.job()/'inputs/src/app.py').write_text('value = 999\n',encoding='utf-8')
            return json.dumps(self.proposal)
        self.provider.side_effect=changed
        with self.assertRaises(preparation.PreparationEvidenceError):self.generate()
        stored=preparation._load(self.folder()/'result.json')
        self.assertEqual(stored['state'],'FAILED');self.assertEqual(stored['error_code'],'retained_evidence_changed')

    def test_current_original_changes_do_not_relabel_the_retained_snapshot(self):
        original=(self.job()/'inputs/src/app.py').read_bytes()
        (self.repo/'src/app.py').write_text('value = 99\n',encoding='utf-8')
        result=self.generate();self.assertEqual(result['state'],'PLAN_PROPOSED')
        self.assertEqual(result['source_status'],'retained_inputs');self.assertFalse(result['current_sources_rechecked'])
        self.assertEqual(self.provider.call_args.args[0]['source_files'][0]['sha256'],hashlib.sha256(original).hexdigest())

    def test_excerpt_budget_is_explicit_and_does_not_change_retained_source(self):
        (self.repo/'src/app.py').write_text('value = "'+'x'*20000+'"\n',encoding='utf-8')
        self.plan['request_id']=uuid.uuid4().hex;preparation.prepare_request(self.owner,self.payload())
        self.generate();files=self.provider.call_args.args[0]['source_files']
        self.assertLessEqual(sum(len(f['excerpt']) for f in files),16000)
        self.assertTrue(any(not f['excerpt_complete'] for f in files))

    def test_partial_intent_is_inspectable_and_never_replayed(self):
        self.generate();(self.folder()/'result.json').rename(self.folder()/'retained_original_result.json')
        result=self.generate();self.assertEqual(result['state'],'INCOMPLETE')
        self.assertEqual(self.provider.await_count,1)
        self.assertEqual(planning.recover_plan(self.owner,self.plan['request_id'],self.plan_id)['state'],'INCOMPLETE')

    def test_dead_incomplete_worker_recovers_without_replay(self):
        self.generate();(self.folder()/'result.json').rename(self.folder()/'retained_original_result.json')
        with patch.object(preparation,'_alive',return_value=False):
            result=planning.recover_plan(self.owner,self.plan['request_id'],self.plan_id)
        self.assertEqual(result['state'],'INTERRUPTED');self.assertEqual(self.provider.await_count,1)
        self.assertEqual(planning.read_plan(self.owner,self.plan['request_id'],self.plan_id),result)

    def test_global_coding_gate_prevents_second_inference_and_new_records(self):
        from core.coding_chat import _ACTIVE
        self.assertTrue(_ACTIVE.acquire(False))
        try:
            with self.assertRaises(preparation.PreparationConflict):self.generate()
        finally:_ACTIVE.release()
        self.provider.assert_not_awaited();self.assertFalse(self.folder().exists())

    def test_deadline_cancels_provider_and_retains_terminal_result(self):
        cancelled=[]
        async def stalled(_):
            try:await asyncio.sleep(2)
            finally:cancelled.append(True)
        self.provider.side_effect=stalled
        with patch.object(planning,'_DEADLINE_SECONDS',.03):result=self.generate()
        self.assertEqual(result['state'],'TIMED_OUT');self.assertTrue(cancelled)
        self.assertEqual(self.generate(),result);self.assertEqual(self.provider.await_count,1)

    def test_explicit_cancellation_stops_local_client_and_does_not_replay(self):
        async def scenario():
            entered=asyncio.Event()
            async def stalled(_):entered.set();await asyncio.sleep(2)
            self.provider.side_effect=stalled
            task=asyncio.create_task(planning.generate_plan(self.owner,self.plan['request_id'],self.plan_id))
            entry=asyncio.create_task(entered.wait())
            try:
                done,_=await asyncio.wait({entry,task},timeout=2,return_when=asyncio.FIRST_COMPLETED)
                if task in done:
                    await task
                    self.fail('Planning finished before entering the provider')
                self.assertIn(entry,done,'Mock provider was not entered within the test deadline')
            finally:
                entry.cancel()
                await asyncio.gather(entry,return_exceptions=True)
            self.assertEqual(planning.read_plan(self.owner,self.plan['request_id'],self.plan_id)['state'],'RUNNING')
            receipt=planning.cancel_plan(self.owner,self.plan['request_id'],self.plan_id)
            self.assertTrue(receipt['cancel_requested'])
            result=await task;self.assertEqual(result['state'],'CANCELLED')
            return result
        result=asyncio.run(scenario());self.assertEqual(self.generate(),result);self.assertEqual(self.provider.await_count,1)

    def test_terminal_result_tamper_is_an_error_not_success(self):
        self.generate();(self.folder()/'result.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError):planning.read_plan(self.owner,self.plan['request_id'],self.plan_id)

    def test_cancellation_recorded_at_result_admission_wins(self):
        original=planning._terminal
        def terminal(folder,value,state,*args,**kwargs):
            if state=='PLAN_PROPOSED':planning.cancel_plan(self.owner,self.plan['request_id'],self.plan_id)
            return original(folder,value,state,*args,**kwargs)
        with patch.object(planning,'_terminal',side_effect=terminal):result=self.generate()
        self.assertEqual(result['state'],'CANCELLED');self.assertIsNone(result['proposal'])

    def test_unexpected_provider_error_is_retained_as_failure(self):
        self.provider.side_effect=RuntimeError('Synthetic unexpected provider failure')
        result=self.generate();self.assertEqual(result['state'],'FAILED')
        self.assertEqual(result['error_code'],'internal_planning_error')
        self.assertEqual(self.generate(),result);self.assertEqual(self.provider.await_count,1)

    def test_invalid_retained_proposal_is_evidence_error(self):
        self.generate();path=self.folder()/'result.json';value=preparation._load(path)
        value['proposal']['steps'][0]['path']='other.py'
        path.rename(self.folder()/'original_valid_result.json');preparation._save_new(path,value)
        with self.assertRaises(preparation.PreparationEvidenceError):planning.read_plan(self.owner,self.plan['request_id'],self.plan_id)

    def test_preparation_binding_changed_after_inference_is_failure(self):
        original=preparation._confirm;count=[]
        def confirm(*args):
            result=original(*args);count.append(True)
            if len(count)>1:result['review_digest']='0'*64
            return result
        with patch.object(preparation,'_confirm',side_effect=confirm):
            with self.assertRaises(preparation.PreparationEvidenceError):self.generate()
        self.assertEqual(preparation._load(self.folder()/'result.json')['state'],'FAILED')

    def test_non_object_provider_envelope_is_protocol_error(self):
        import httpx
        original=httpx.AsyncClient
        def client(**kwargs):return original(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=[])),**kwargs)
        with patch.object(httpx,'AsyncClient',side_effect=client):
            with self.assertRaises(ValueError):asyncio.run(self.http_adapter({}))

    def test_storage_failure_preserves_inputs_and_cannot_acknowledge_completion(self):
        original=preparation._save_new
        def save(path,value):
            if path.name=='result.json':raise OSError('Synthetic result write failure')
            return original(path,value)
        with patch.object(preparation,'_save_new',side_effect=save):
            with self.assertRaises(OSError):self.generate()
        self.assertTrue((self.folder()/'input.json').exists())
        self.assertEqual(self.generate()['state'],'INCOMPLETE');self.assertEqual(self.provider.await_count,1)

    def test_api_owner_body_and_all_four_operation_auth_boundaries(self):
        base='/api/chat/coding-tasks/preparations/'+self.plan['request_id']+'/plans'
        with self.client() as client:
            for method,path,body in [('POST',base,{'plan_id':self.plan_id}),('GET',base+'/'+self.plan_id,None),('POST',base+'/'+self.plan_id+'/recover',None),('POST',base+'/'+self.plan_id+'/cancel',None)]:
                self.assertEqual(client.request(method,path,**({'json':body} if body else {})).status_code,403)
            headers={'Authorization':'Bearer alice-fixture'}
            self.assertEqual(client.post(base,headers=headers,json={'plan_id':self.plan_id,'owner':'forged'}).status_code,422)
            result=client.post(base,headers=headers,json={'plan_id':self.plan_id})
            self.assertEqual(result.status_code,200);self.assertEqual(result.json()['owner'],self.owner)
            self.assertEqual(client.get(base+'/'+self.plan_id,headers=headers).json(),result.json())
            self.assertEqual(client.post(base+'/'+self.plan_id+'/recover',headers=headers).json(),result.json())
            self.assertFalse(client.post(base+'/'+self.plan_id+'/cancel',headers=headers).json()['cancel_requested'])
            self.assertEqual(client.get(base+'/'+self.plan_id,headers={'Authorization':'Bearer bob-fixture'}).status_code,404)

    def test_actual_http_adapter_uses_only_loopback_and_rejects_incomplete_or_oversized_output(self):
        import httpx
        original=httpx.AsyncClient
        requests=[]
        payload={'done':True,'model':'stehouwer_llm:latest','response':json.dumps(self.proposal)}
        def handler(request):
            requests.append(request)
            return httpx.Response(200,json=payload)
        def client(**kwargs):
            self.assertFalse(kwargs['trust_env']);self.assertFalse(kwargs['follow_redirects'])
            self.assertEqual(kwargs['timeout'].read,planning._DEADLINE_SECONDS)
            return original(transport=httpx.MockTransport(handler),**kwargs)
        adapter=self.http_adapter
        with patch.object(httpx,'AsyncClient',side_effect=client):
            response=asyncio.run(adapter({'objective':'Synthetic bounded input','source_files':[]}))
            self.assertEqual(response,json.dumps(self.proposal))
            self.assertEqual(str(requests[0].url),'http://127.0.0.1:11434/api/generate')
            body=json.loads(requests[0].content);self.assertEqual(body['model'],'stehouwer_llm:latest')
            self.assertFalse(body['stream']);self.assertNotIn('tools',body)
            payload['done']=False
            with self.assertRaises(ValueError):asyncio.run(adapter({}))
            payload['done']=True;payload['response']='x'*65537
            with self.assertRaises(ValueError):asyncio.run(adapter({}))
