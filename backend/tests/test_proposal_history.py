import json
from unittest.mock import Mock, patch
from test_preparation_proposals import ProposalTests
from core import coding_preparation as preparation
from core import coding_preparation_planning as planning
from core import coding_preparation_proposals as proposals

class ProposalHistoryTests(ProposalTests):
    def listing(self,**kwargs):
        return proposals.list_proposals(self.owner,self.plan['request_id'],self.plan_id,**kwargs)

    def test_empty_history_never_creates_a_namespace(self):
        namespace=self.job()/'planning'/self.plan_id/'proposals'
        self.assertFalse(namespace.exists())
        result=self.listing();self.assertEqual(result['items'],[])
        self.assertTrue(result['metadata_only']);self.assertFalse(result['parent_plan_revalidated'])
        self.assertFalse(namespace.exists())

    def test_history_does_not_read_copied_sources_or_validate_candidate(self):
        self.generate()
        with (patch.object(proposals,'_review',side_effect=AssertionError('No full review')),
             patch.object(proposals,'_context',side_effect=AssertionError('No copied sources')),
             patch.object(proposals,'_validate_output',side_effect=AssertionError('No candidate check')),
             patch.object(planning,'read_plan',side_effect=AssertionError('No full plan check'))):
            result=self.listing()
        self.assertEqual(result['items'],[{'proposal_id':self.proposal_id,'state':'PROPOSAL_READY',
            'proposal_revalidated':False,'execution_authorized':False,'apply_authorized':False,'verification_status':'not_run'}])
        self.assertNotIn('proposal',result['items'][0]);self.assertNotIn('model_payload',result)

    def test_pages_retain_all_sorted_proposal_ids(self):
        identifiers=['a'*32,'b'*32,'c'*32]
        for identifier in identifiers:self.generate(identifier=identifier)
        found=[];cursor=None
        for _ in identifiers:
            page=self.listing(limit=1,cursor=cursor);found.extend(item['proposal_id'] for item in page['items']);cursor=page['next_cursor']
        self.assertEqual(found,identifiers);self.assertIsNone(cursor)

    def test_corrupt_child_is_not_silent_empty_success(self):
        self.generate();(self.folder()/'result.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError):self.listing()

    def test_missing_input_child_is_not_silent_empty_success(self):
        self.folder().mkdir(parents=True)
        with self.assertRaises(preparation.PreparationEvidenceError):self.listing()

    def test_cooperative_budget_fails_explicitly(self):
        self.generate()
        with patch.object(proposals,'_list_clock',side_effect=[0,.7]):
            with self.assertRaises(preparation.PreparationEvidenceError):self.listing()

    def test_history_checks_owner_parent_and_snapshot_bindings(self):
        self.generate();path=self.folder()/'input.json';value=preparation._load(path);value['plan_id']='f'*32
        path.write_text(json.dumps(preparation._sealed(value)),encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError):self.listing()
        with self.assertRaises(preparation.PreparationNotFound):proposals.list_proposals('firebase:fixture:bob',self.plan['request_id'],self.plan_id)

    def test_incomplete_worker_is_not_implicitly_replayed_or_called_running(self):
        original=preparation._save_new
        def fail(path,value):
            if path.name=='result.json':raise OSError('Synthetic storage failure')
            return original(path,value)
        with patch.object(preparation,'_save_new',side_effect=fail):
            with self.assertRaises(OSError):self.generate()
        self.assertEqual(self.listing()['items'][0]['state'],'INCOMPLETE')
        key=(self.owner,self.plan['request_id'],self.plan_id,self.proposal_id)
        with patch.dict(proposals._RUNNING,{key:Mock(done=Mock(return_value=False))}):
            self.assertEqual(self.listing()['items'][0]['state'],'RUNNING')
        self.assertFalse((self.folder()/'result.json').exists())

    def test_history_api_enforces_auth_owner_bounds_and_honest_corruption(self):
        self.generate();url='/api/chat/coding-tasks/preparations/'+self.plan['request_id']+'/plans/'+self.plan_id+'/proposals'
        with self.client() as client:
            self.assertEqual(client.get(url).status_code,403)
            headers={'Authorization':'Bearer alice-fixture'}
            self.assertEqual(client.get(url,headers=headers).json()['items'][0]['proposal_id'],self.proposal_id)
            self.assertEqual(client.get(url,headers={'Authorization':'Bearer bob-fixture'}).status_code,404)
            for query in ['?limit=0','?limit=51','?cursor=../outside']:
                self.assertEqual(client.get(url+query,headers=headers).status_code,422)
            (self.folder()/'result.json').write_text('{}',encoding='utf-8')
            self.assertEqual(client.get(url,headers=headers).status_code,503)

    def test_limits_reject_booleans_and_invalid_cursors(self):
        for options in [{'limit':True},{'limit':0},{'limit':51},{'cursor':'../outside'}]:
            with self.assertRaises(ValueError):self.listing(**options)
