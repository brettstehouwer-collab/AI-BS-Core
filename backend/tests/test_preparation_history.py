import hashlib
import json
from unittest.mock import patch
from test_coding_preparation import PreparationTests
from core import coding_preparation as preparation


class PreparationHistoryTests(PreparationTests):
    def test_identity_is_authenticated_and_storage_free(self):
        with self.client() as client:
            path='/api/chat/coding-tasks/preparations/identity'
            self.assertEqual(client.get(path).status_code,403)
            response=client.get(path,headers={'Authorization':'Bearer alice-fixture'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['owner'],self.owner)
            self.assertEqual(response.json()['repository_ids'],['ai-bs'])
        self.assertFalse(self.requests.exists())

    def test_empty_history_does_not_initialize_storage(self):
        result=preparation.list_preparations(self.owner)
        self.assertEqual(result['items'],[])
        self.assertIsNone(result['next_cursor'])
        self.assertEqual(result['owner'],self.owner)
        self.assertTrue(result['metadata_only'])
        self.assertFalse(self.requests.exists())

    def test_metadata_listing_own_scope_without_payload_readback(self):
        preparation.prepare_request(self.owner,self.payload())
        bob='firebase:fixture:bob'
        preparation.prepare_request(bob,self.payload(bob))
        with patch.object(preparation,'_retained',side_effect=AssertionError('Listing must not read source payloads')):
            result=preparation.list_preparations(self.owner)
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['request_id'],self.plan['request_id'])
        self.assertFalse(result['items'][0]['retained_inputs_revalidated'])
        self.assertNotIn('files',result['items'][0])

    def test_cursor_pages_preserve_all_records(self):
        expected=['a'*32,'b'*32,'c'*32]
        for identifier in expected:
            self.plan['request_id']=identifier
            preparation.prepare_request(self.owner,self.payload())
        result=[]; cursor=None
        for _ in expected:
            page=preparation.list_preparations(self.owner,limit=1,cursor=cursor)
            result.extend(row['request_id'] for row in page['items']);cursor=page['next_cursor']
        self.assertEqual(result,expected)
        self.assertIsNone(cursor)
        owner_root=self.requests/'preparations'/hashlib.sha256(self.owner.encode()).hexdigest()
        self.assertEqual(len(list(owner_root.iterdir())),3)

    def test_bad_metadata_or_query_is_not_empty_success(self):
        preparation.prepare_request(self.owner,self.payload())
        for kwargs in [{'limit':0},{'limit':51},{'limit':True},{'cursor':'../escape'}]:
            with self.assertRaises(ValueError):preparation.list_preparations(self.owner,**kwargs)
        path=self.job()/'preparation.json'
        (self.job()/'original_preparation.json').write_bytes(path.read_bytes())
        path.write_text('{bad fixture',encoding='utf-8')
        with self.client() as client:
            response=client.get('/api/chat/coding-tasks/preparations',headers={'Authorization':'Bearer alice-fixture'})
            self.assertEqual(response.status_code,503)

    def test_listing_deadline_reports_unavailable(self):
        preparation.prepare_request(self.owner,self.payload())
        with patch.object(preparation,'_listing_clock',side_effect=[0,1]):
            with self.assertRaises(preparation.PreparationEvidenceError):preparation.list_preparations(self.owner)

    def test_completion_race_still_never_reads_payloads_in_history(self):
        with patch.object(preparation,'_write_new_file',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):preparation.prepare_request(self.owner,self.payload())
        original_is_file=type(self.repo).is_file
        original_retained=preparation._retained
        completed=False; payload_reads=[]
        def is_file(path):
            nonlocal completed
            found=original_is_file(path)
            if path==self.job()/'preparation.json' and not completed:
                completed=True
                intent=preparation._intent(self.job(),self.owner,self.plan['request_id'])
                for row in intent['snapshot']['files']:
                    target=self.job()/'inputs'/row['relative_path'];target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes((self.repo/row['relative_path']).read_bytes())
                preparation._save_new(path,{'state':'PREPARED','intent_sha256':preparation._hash(intent),'review_digest':intent['review_digest']})
            return found
        def retained(*args):payload_reads.append(True);return original_retained(*args)
        with patch.object(type(self.repo),'is_file',is_file),patch.object(preparation,'_retained',side_effect=retained):
            page=preparation.list_preparations(self.owner)
        self.assertEqual(payload_reads,[],'Metadata listing followed a completion race into full payload verification')
        self.assertFalse(page['items'][0]['retained_inputs_revalidated'])
