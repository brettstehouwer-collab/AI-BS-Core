import asyncio
import json
from unittest.mock import patch
import uuid
from test_preparation_planning import PlanningTests
from core import coding_preparation as preparation
from core import coding_preparation_planning as planning


class PlanningControlTests(PlanningTests):
    def test_empty_plan_listing_does_not_create_a_namespace(self):
        result=planning.list_plans(self.owner,self.plan['request_id'])
        self.assertEqual(result['items'],[]);self.assertTrue(result['metadata_only'])
        self.assertFalse((self.job()/'planning').exists())

    def test_plan_history_is_metadata_only_without_input_or_proposal_revalidation(self):
        self.generate()
        with patch.object(preparation,'_retained',side_effect=AssertionError('Metadata must not read copied sources')),patch.object(planning,'_validate_output',side_effect=AssertionError('Metadata must not validate model proposal')):
            result=planning.list_plans(self.owner,self.plan['request_id'])
        self.assertEqual(result['items'][0]['state'],'PLAN_PROPOSED')
        self.assertFalse(result['items'][0]['proposal_revalidated'])
        self.assertNotIn('proposal',result['items'][0]);self.assertNotIn('model_payload',result['items'][0])

    def test_plan_history_cursor_preserves_all_ids(self):
        ids=['a'*32,'b'*32,'c'*32]
        for identifier in ids:self.generate(identifier=identifier)
        collected=[];cursor=None
        for _ in ids:
            result=planning.list_plans(self.owner,self.plan['request_id'],limit=1,cursor=cursor)
            collected.extend(item['plan_id'] for item in result['items']);cursor=result['next_cursor']
        self.assertEqual(collected,ids);self.assertIsNone(cursor)

    def test_corrupt_plan_history_is_not_empty_success(self):
        self.generate();(self.folder()/'result.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError):planning.list_plans(self.owner,self.plan['request_id'])

    def test_plan_listing_budget_is_explicit_failure(self):
        self.generate()
        with patch.object(planning,'_list_clock',side_effect=[0,.7]):
            with self.assertRaises(preparation.PreparationEvidenceError):planning.list_plans(self.owner,self.plan['request_id'])

    def test_plan_listing_api_auth_owner_and_query_bounds(self):
        self.generate();path='/api/chat/coding-tasks/preparations/'+self.plan['request_id']+'/plans'
        with self.client() as client:
            self.assertEqual(client.get(path).status_code,403)
            headers={'Authorization':'Bearer alice-fixture'}
            self.assertEqual(client.get(path,headers=headers).json()['items'][0]['plan_id'],self.plan_id)
            for query in ['?limit=0','?limit=51','?cursor=../outside']:
                self.assertEqual(client.get(path+query,headers=headers).status_code,422)
            self.assertEqual(client.get(path,headers={'Authorization':'Bearer bob-fixture'}).status_code,404)

    def test_model_guidance_prefers_no_generic_questions_for_explicit_changes(self):
        import httpx
        original=httpx.AsyncClient;seen=[]
        def handler(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200,json={'done':True,'model':'stehouwer_llm:latest','response':json.dumps(self.proposal)})
        def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
        with patch.object(httpx,'AsyncClient',side_effect=client):asyncio.run(self.http_adapter({}))
        self.assertIn('questions:[]',seen[0]['system'])
        self.assertIn('commit messages',seen[0]['system'])
