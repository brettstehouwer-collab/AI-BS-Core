"""Preparation-only API/storage tests using synthetic source repositories."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_repository_snapshot import RepositorySnapshotTests

try:
    from core import coding_preparation as preparation
    from routers import coding_preparation_router as api
except ImportError:
    preparation = api = None


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RepositorySnapshotTests.setUpClass()
        cls.root,cls.template = RepositorySnapshotTests.root,RepositorySnapshotTests.template

    def setUp(self):
        self.assertTrue(callable(getattr(preparation,'preview_preparation',None)),'Preparation service is missing')
        self.assertIsNotNone(api,'Independently authenticated preparation API is missing')
        self.case = self.root / uuid.uuid4().hex
        self.repo = self.case / 'repo'
        shutil.copytree(self.template,self.repo)
        self.requests = self.case / 'requests'
        self.addCleanup(patch.stopall)
        patch.object(preparation,'REQUESTS',self.requests).start()
        patch.object(preparation,'REPOSITORIES',{'ai-bs':self.repo}).start()
        self.plan = {'request_id':uuid.uuid4().hex,'repository_id':'ai-bs','objective':'Prepare current code without executing it.',
            'files':[{'relative_path':'src/app.py','role':'editable'},{'relative_path':'tests/test_app.py','role':'verification'}],
            'checks':[{'check_id':'python','profile':'python_unittest','targets':['tests.test_app']}]}
        self.owner = 'firebase:fixture:alice'

    def payload(self,owner=None):
        preview = preparation.preview_preparation(owner or self.owner,self.plan)
        return dict(self.plan,review_digest=preview['review_digest'])

    def job(self,owner=None):
        key = hashlib.sha256((owner or self.owner).encode('utf-8')).hexdigest()
        return self.requests / 'preparations' / key / self.plan['request_id']

    def client(self):
        from security import firebase_auth
        patch.dict(os.environ,{'AI_BS_ADMIN_KEY':'synthetic-local-key-42'}).start()
        patch.object(firebase_auth,'firebase_admin_principal',side_effect=lambda t: 'firebase:fixture:' + t.split('-')[0] if t in {'alice-fixture','bob-fixture'} else None).start()
        app = FastAPI()
        app.include_router(api.router,prefix='/api/chat/coding-tasks')
        return TestClient(app)

    def test_preview_read_only_exact_files_and_fixed_checks(self):
        (self.repo / 'src/app.py').write_bytes(b'value = 42\r\n')
        preview = preparation.preview_preparation(self.owner,self.plan)
        self.assertEqual(preview['checks'][0]['argv'],['python','-m','unittest','tests.test_app'])
        self.assertEqual(preview['files'][0]['sha256'],hashlib.sha256(b'value = 42\r\n').hexdigest())
        self.assertFalse(self.requests.exists())
        self.assertFalse(preview['execution_authorized'])
        self.assertEqual(preview['verification_status'],'not_run')

    def test_prepared_real_bytes_and_independent_receipt(self):
        payload = self.payload()
        result = preparation.prepare_request(self.owner,payload)
        self.assertEqual(result['state'],'PREPARED')
        self.assertTrue(result['durable'])
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['verification_status'],'not_run')
        self.assertNotIn('review_token',result)
        self.assertNotIn('base_image_sha256',result)
        for entry in self.plan['files']:
            self.assertEqual((self.job() / 'inputs' / entry['relative_path']).read_bytes(),(self.repo / entry['relative_path']).read_bytes())
        self.assertEqual(preparation.read_preparation(self.owner,self.plan['request_id']),result)
        self.assertFalse((self.job() / 'request.json').exists(),'Legacy unscoped recovery must not read this record kind')

    def test_repeated_preview_stable_despite_capture_timestamp(self):
        one = preparation.preview_preparation(self.owner,self.plan)
        two = preparation.preview_preparation(self.owner,self.plan)
        self.assertEqual(one['review_digest'],two['review_digest'])

    def test_changed_source_rejects_before_journal_creation(self):
        payload = self.payload()
        (self.repo / 'src/app.py').write_bytes(b'value = 99\n')
        with self.assertRaises(preparation.PreparationConflict): preparation.prepare_request(self.owner,payload)
        self.assertFalse(self.requests.exists())

    def test_changed_objective_or_checks_requires_new_preview(self):
        payload = self.payload()
        payload['objective'] = 'Changed request after review'
        with self.assertRaises(preparation.PreparationConflict): preparation.prepare_request(self.owner,payload)
        self.assertFalse(self.requests.exists())

    def test_unknown_repository_and_extra_authority_fields_rejected(self):
        cases = [dict(self.plan,repository_id='unapproved')]
        for key,value in [('owner','local_admin'),('allowed_roots',['C:/']),('repository','C:/'),('execution_backend','trusted_host'),('base_image_sha256','0'*64)]:
            cases.append(dict(self.plan,**{key:value}))
        for plan in cases:
            with self.subTest(keys=list(plan)):
                with self.assertRaises((ValueError,PermissionError)): preparation.preview_preparation(self.owner,plan)
        self.assertFalse(self.requests.exists())

    def test_test_role_command_and_language_gates_reused(self):
        for change in ['editable_test','unselected_test','raw_argv','wrong_profile']:
            plan = copy.deepcopy(self.plan)
            if change == 'editable_test': plan['files'][1]['role'] = 'editable'
            if change == 'unselected_test': plan['checks'][0]['targets'] = ['tests.missing']
            if change == 'raw_argv': plan['checks'][0]['argv'] = ['cmd.exe','/c','anything']
            if change == 'wrong_profile': plan['checks'][0]['profile'] = 'shell'
            with self.subTest(change=change):
                with self.assertRaises(ValueError): preparation.preview_preparation(self.owner,plan)
        self.assertFalse(self.requests.exists())

    def test_invalid_limits_counts_ids_and_large_plan_rejected(self):
        cases = [dict(self.plan,request_id='../bad'),dict(self.plan,objective='x'*8001),dict(self.plan,limits={'check_seconds':True}),
                 dict(self.plan,limits={'check_seconds':120,'total_seconds':1,'output_bytes':1024})]
        for plan in cases:
            with self.subTest(plan_fields=list(plan)):
                with self.assertRaises(ValueError): preparation.preview_preparation(self.owner,plan)
        self.assertFalse(self.requests.exists())

    def test_owner_required_before_capture_or_storage(self):
        with patch.object(preparation,'capture_repository_snapshot') as capture:
            for owner in [None,'brett','',42]:
                with self.assertRaises(PermissionError): preparation.preview_preparation(owner,self.plan)
            capture.assert_not_called()
        self.assertFalse(self.requests.exists())

    def test_same_external_id_separate_owners_and_foreign_read_denied(self):
        alice = preparation.prepare_request(self.owner,self.payload())
        bob = 'firebase:fixture:bob'
        with self.assertRaises(preparation.PreparationNotFound): preparation.read_preparation(bob,self.plan['request_id'])
        bob_result = preparation.prepare_request(bob,self.payload(bob))
        self.assertEqual(alice['request_id'],bob_result['request_id'])
        self.assertNotEqual(alice['owner'],bob_result['owner'])
        self.assertTrue((self.job(bob) / 'preparation.json').is_file())

    def test_completed_retry_never_recaptures_or_overwrites(self):
        payload = self.payload()
        one = preparation.prepare_request(self.owner,payload)
        old = (self.job() / 'preparation.json').read_bytes()
        (self.repo / 'src/app.py').write_bytes(b'newer user edit\n')
        with patch.object(preparation,'capture_repository_snapshot') as capture:
            self.assertEqual(preparation.prepare_request(self.owner,payload),one)
            capture.assert_not_called()
        self.assertEqual((self.job() / 'preparation.json').read_bytes(),old)
        self.assertIs(one['current_sources_rechecked'],False)

    def test_changed_retry_conflicts_and_keeps_evidence(self):
        payload = self.payload()
        preparation.prepare_request(self.owner,payload)
        before = (self.job() / 'intent.json').read_bytes()
        payload['objective'] = 'changed'
        with self.assertRaises(preparation.PreparationConflict): preparation.prepare_request(self.owner,payload)
        self.assertEqual((self.job() / 'intent.json').read_bytes(),before)

    def test_copied_input_tampering_not_success(self):
        preparation.prepare_request(self.owner,self.payload())
        path = self.job() / 'inputs/src/app.py'
        shutil.copy2(path,self.job() / 'original_app.py')
        path.write_bytes(b'corrupted retained source\n')
        with self.assertRaises(preparation.PreparationEvidenceError): preparation.read_preparation(self.owner,self.plan['request_id'])

    def test_partial_write_retained_and_retry_cannot_resume(self):
        payload = self.payload()
        write = preparation._write_new_file
        def fail(path,data):
            if path.name == 'test_app.py': raise OSError('synthetic copy failure')
            return write(path,data)
        with patch.object(preparation,'_write_new_file',side_effect=fail):
            with self.assertRaises(OSError): preparation.prepare_request(self.owner,payload)
        self.assertTrue((self.job() / 'intent.json').is_file())
        self.assertTrue((self.job() / 'inputs/src/app.py').is_file())
        self.assertFalse((self.job() / 'preparation.json').exists())
        self.assertEqual(preparation.read_preparation(self.owner,self.plan['request_id'])['state'],'FAILED')
        with self.assertRaises(preparation.PreparationConflict): preparation.prepare_request(self.owner,payload)

    def test_lost_final_readback_retry_confirms_without_duplicate_copy(self):
        payload = self.payload()
        with patch.object(preparation,'_confirm',side_effect=OSError('synthetic lost readback')):
            with self.assertRaises(OSError): preparation.prepare_request(self.owner,payload)
        self.assertTrue((self.job() / 'preparation.json').is_file())
        with patch.object(preparation,'capture_repository_snapshot') as capture:
            self.assertEqual(preparation.prepare_request(self.owner,payload)['state'],'PREPARED')
            capture.assert_not_called()

    def test_dead_interrupted_copy_recovers_without_replay(self):
        payload = self.payload()
        with patch.object(preparation,'worker_identity',return_value={'pid':2147483000,'created':0}),patch.object(preparation,'_write_new_file',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): preparation.prepare_request(self.owner,payload)
        with patch.object(preparation,'capture_repository_snapshot') as capture:
            result = preparation.recover_preparation(self.owner,self.plan['request_id'])
            self.assertEqual(result['state'],'INTERRUPTED')
            capture.assert_not_called()
        before = (self.job() / 'recovery.json').read_bytes()
        self.assertEqual(preparation.recover_preparation(self.owner,self.plan['request_id'])['state'],'INTERRUPTED')
        self.assertEqual((self.job() / 'recovery.json').read_bytes(),before)

    def test_live_incomplete_worker_not_declared_interrupted(self):
        with patch.object(preparation,'_write_new_file',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): preparation.prepare_request(self.owner,self.payload())
        self.assertEqual(preparation.recover_preparation(self.owner,self.plan['request_id'])['state'],'PREPARING')
        self.assertFalse((self.job() / 'recovery.json').exists())

    def test_api_independent_auth_and_forged_fields(self):
        with self.client() as client,patch.object(preparation,'capture_repository_snapshot') as capture:
            for headers in [{},{'X-Admin-Key':'invalid'}]:
                response = client.post('/api/chat/coding-tasks/preparations/preview',json=self.plan,headers=headers)
                self.assertEqual(response.status_code,403)
                self.assertEqual(client.post('/api/chat/coding-tasks/preparations',json=dict(self.plan,review_digest='0'*64),headers=headers).status_code,403)
                self.assertEqual(client.get('/api/chat/coding-tasks/preparations/'+self.plan['request_id'],headers=headers).status_code,403)
                self.assertEqual(client.post('/api/chat/coding-tasks/preparations/'+self.plan['request_id']+'/recover',headers=headers).status_code,403)
            capture.assert_not_called()
            response = client.post('/api/chat/coding-tasks/preparations/preview',json=dict(self.plan,owner='forged'),headers={'X-Admin-Key':'synthetic-local-key-42'})
            self.assertEqual(response.status_code,422)
        self.assertFalse(self.requests.exists())

    def test_actual_api_preview_prepare_read_recover_owner_and_conflict(self):
        with self.client() as client:
            headers = {'Authorization':'Bearer alice-fixture'}
            base = '/api/chat/coding-tasks/preparations'
            preview = client.post(base+'/preview',json=self.plan,headers=headers)
            self.assertEqual(preview.status_code,200)
            body = dict(self.plan,review_digest=preview.json()['review_digest'])
            saved = client.post(base,json=body,headers=headers)
            self.assertEqual(saved.status_code,200)
            self.assertEqual(saved.json()['owner'],self.owner)
            self.assertEqual(client.get(base+'/'+self.plan['request_id'],headers={'Authorization':'Bearer bob-fixture'}).status_code,404)
            self.assertEqual(client.get(base+'/'+self.plan['request_id'],headers=headers).json(),saved.json())
            self.assertEqual(client.post(base+'/'+self.plan['request_id']+'/recover',headers=headers).json(),saved.json())
            body['objective'] = 'changed request'
            self.assertEqual(client.post(base,json=body,headers=headers).status_code,409)

    def test_parent_mount_preserves_existing_route_functions(self):
        tree = ast.parse((Path(__file__).parents[1] / 'routers/coding_review_router.py').read_text(encoding='utf-8'))
        self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr == 'include_router' and n.args and isinstance(n.args[0],ast.Name) and n.args[0].id == 'coding_preparation_router' for n in ast.walk(tree)))

    def test_immutable_journal_under_locked_directory_never_overwrites(self):
        from core.coding_journal import write_json_record
        from core.coding_vm_staging import _locked_directory
        directory = self.case / 'immutable'
        directory.mkdir()
        target = directory / 'entry.json'
        with _locked_directory(directory):
            write_json_record(target,{'fixture':True},exclusive=True)
            original = target.read_bytes()
            with self.assertRaises(FileExistsError): write_json_record(target,{'fixture':False},exclusive=True)
        self.assertEqual(target.read_bytes(),original)

    def test_exclusive_sync_failure_retains_bytes_and_propagates_error(self):
        from core import coding_journal
        target = self.case / 'unsynced.json'
        with patch.object(coding_journal.os,'fsync',side_effect=OSError('synthetic sync failure')):
            with self.assertRaises(OSError): coding_journal.write_json_record(target,{'fixture':True},exclusive=True)
        self.assertTrue(target.exists())
        with self.assertRaises(FileExistsError): coding_journal.write_json_record(target,{'fixture':True},exclusive=True)

    def test_single_process_gate_rejects_overlap_before_capture(self):
        preparation._ACTIVE.acquire()
        try:
            with patch.object(preparation,'capture_repository_snapshot') as capture:
                with self.assertRaises(preparation.PreparationConflict): preparation.preview_preparation(self.owner,self.plan)
                capture.assert_not_called()
        finally: preparation._ACTIVE.release()
        self.assertFalse(self.requests.exists())

    def test_other_owner_cannot_reuse_preview_digest(self):
        payload = self.payload()
        with self.assertRaises(preparation.PreparationConflict): preparation.prepare_request('firebase:fixture:bob',payload)
        self.assertFalse(self.requests.exists())

    def test_hardlinked_journal_evidence_is_not_confirmed(self):
        preparation.prepare_request(self.owner,self.payload())
        os.link(self.job() / 'intent.json',self.job() / 'linked_intent.json')
        with self.assertRaises(preparation.PreparationEvidenceError): preparation.read_preparation(self.owner,self.plan['request_id'])

    def test_namespace_junction_cannot_redirect_retained_sources(self):
        import subprocess
        parent = self.requests / 'preparations'
        parent.mkdir(parents=True)
        outside = self.case / 'outside'
        outside.mkdir()
        owner_name = hashlib.sha256(self.owner.encode('utf-8')).hexdigest()
        linked = subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(parent / owner_name),str(outside)],capture_output=True,timeout=5)
        self.assertEqual(linked.returncode,0)
        with self.assertRaises(preparation.PreparationEvidenceError): preparation.prepare_request(self.owner,self.payload())
        self.assertEqual(list(outside.iterdir()),[])

    def test_native_node_and_jsx_npm_profiles_prepare_without_execution(self):
        (self.repo / 'src/app.js').write_bytes(b'export const value = 1;\n')
        (self.repo / 'tests/test_app.js').write_bytes(b'throw Error("must never execute");\n')
        (self.repo / 'src/UI.jsx').write_bytes(b'export default () => <div>Fixture</div>;\n')
        for jsx in [False,True]:
            plan = copy.deepcopy(self.plan)
            plan['request_id'] = uuid.uuid4().hex
            if jsx:
                plan['files'] = [{'relative_path':'src/UI.jsx','role':'editable'},{'relative_path':'package.json','role':'dependency'},{'relative_path':'package-lock.json','role':'dependency'}]
                plan['checks'] = [{'check_id':'jsx','profile':'npm_script','targets':['test']}]
                argv = ['npm','run','test']
            else:
                plan['files'] = [{'relative_path':'src/app.js','role':'editable'},{'relative_path':'tests/test_app.js','role':'verification'}]
                plan['checks'] = [{'check_id':'js','profile':'node_test','targets':['tests/test_app.js']}]
                argv = ['node','--test','tests/test_app.js']
            preview = preparation.preview_preparation(self.owner,plan)
            result = preparation.prepare_request(self.owner,dict(plan,review_digest=preview['review_digest']))
            self.assertEqual(result['checks'][0]['argv'],argv)
            self.assertEqual(result['verification_status'],'not_run')

    def test_tampered_metadata_is_unavailable_through_api(self):
        preparation.prepare_request(self.owner,self.payload())
        path = self.job() / 'intent.json'
        shutil.copy2(path,self.job() / 'untampered_intent.json')
        value = json.loads(path.read_text(encoding='utf-8'))
        value['plan']['objective'] = 'forged local journal bytes'
        path.write_text(json.dumps(value),encoding='utf-8')
        with self.client() as client:
            response = client.get('/api/chat/coding-tasks/preparations/'+self.plan['request_id'],headers={'Authorization':'Bearer alice-fixture'})
            self.assertEqual(response.status_code,503)

    def test_preparation_namespace_does_not_consume_legacy_history_limit(self):
        from core import coding_recovery
        legacy = self.requests / ('c'*32)
        legacy.mkdir(parents=True)
        (legacy / 'request.json').write_text(json.dumps({'request_id':'c'*32,'state':'FAILED'}),encoding='utf-8')
        namespace = self.requests / 'preparations'
        namespace.mkdir()
        os.utime(legacy,(100,100)); os.utime(namespace,(200,200))
        with patch.object(coding_recovery,'REQUESTS',self.requests),patch.object(coding_recovery,'STORE',self.case / 'tasks'):
            rows = coding_recovery.list_coding_records(limit=1)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['id'],'c'*32)

