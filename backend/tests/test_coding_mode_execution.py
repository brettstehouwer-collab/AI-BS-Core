"""Real retained synthetic candidates, never project-code execution."""
import json
import os
import unittest
import uuid
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import test_preparation_proposals as fixtures
from core import coding_mode_execution as service
from core import coding_preparation as preparation
from routers import coding_mode_router as api
from routers.coding_preparation_router import require_preparation_owner


class CodingModeTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ProposalTests.setUpClass.__func__)
    payload = fixtures.ProposalTests.payload
    job = fixtures.ProposalTests.job
    client = fixtures.ProposalTests.client
    generate = fixtures.ProposalTests.generate
    fresh_plan = fixtures.ProposalTests.fresh_plan

    def prepare_and_plan(self):
        # The legacy fixture nests three 32-character IDs and an owner hash.
        # Keep the retained synthetic journal short on Windows MAX_PATH hosts.
        self.requests = self.root/self.case.name[:6]
        patch.object(preparation, 'REQUESTS', self.requests).start()
        fixtures.ProposalTests.prepare_and_plan(self)

    def setUp(self):
        fixtures.ProposalTests.setUp(self)
        self.generate()
        self.execution = dict(execution_id=uuid.uuid4().hex, request_id=self.plan['request_id'],
                              plan_id=self.plan_id, proposal_id=self.proposal_id)

    def test_retained_candidate_and_checks_block_without_execution(self):
        before = (self.repo/'src/app.py').read_bytes()
        with patch('subprocess.Popen', side_effect=AssertionError('No project process permitted')):
            result = service.prepare_execution(self.owner, self.execution)
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertEqual(result['verification_status'], 'not_run')
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['apply_authorized'])
        self.assertEqual(result['static_checks'][0]['status'], 'passed')
        self.assertTrue(all(check['status'] == 'not_run' for check in result['checks']))
        candidate = service._folder(self.owner, self.execution['execution_id'])/'candidate/src/app.py'
        self.assertEqual(candidate.read_bytes(), b'value = 42\n')
        self.assertEqual((self.repo/'src/app.py').read_bytes(), before)

    def test_retry_is_same_record_and_recovery_cancel_do_not_replay(self):
        first = service.prepare_execution(self.owner, self.execution)
        self.assertEqual(service.prepare_execution(self.owner, self.execution), first)
        self.assertFalse(service.recover_execution(self.owner, self.execution['execution_id'])['replayed'])
        self.assertFalse(service.cancel_execution(self.owner, self.execution['execution_id'])['cancel_requested'])
        self.assertEqual(self.provider.await_count, 1)

    def test_candidate_tamper_cannot_be_reviewed(self):
        service.prepare_execution(self.owner, self.execution)
        candidate = service._folder(self.owner, self.execution['execution_id'])/'candidate/src/app.py'
        candidate.write_bytes(b'value = 999\n')
        with self.assertRaises(preparation.PreparationEvidenceError):
            service.review_execution(self.owner, self.execution['execution_id'])

    def test_resealed_checks_and_diff_cannot_replace_source_authority(self):
        service.prepare_execution(self.owner, self.execution)
        folder = service._folder(self.owner, self.execution['execution_id'])
        value = preparation._load(folder/'input.json')
        value['review_diff'] = 'fabricated passing result'
        value['checks'] = []
        (folder/'input.json').write_text(json.dumps(preparation._sealed(value)), encoding='utf-8')
        result = preparation._load(folder/'result.json')
        result['input_sha256'] = preparation._hash(value)
        (folder/'result.json').write_text(json.dumps(preparation._sealed(result)), encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError):
            service.read_execution(self.owner, self.execution['execution_id'])

    def test_interrupted_partial_candidate_recovers_without_recreating_files(self):
        service.prepare_execution(self.owner, self.execution)
        folder = service._folder(self.owner, self.execution['execution_id'])
        (folder/'result.json').unlink()
        candidate = folder/'candidate/src/app.py'
        candidate.unlink()
        self.assertEqual(service.read_execution(self.owner, self.execution['execution_id'])['state'], 'INCOMPLETE')
        result = service.recover_execution(self.owner, self.execution['execution_id'])
        self.assertEqual(result['state'], 'INTERRUPTED')
        self.assertFalse(result['replayed'])
        self.assertFalse(candidate.exists())
        self.assertEqual(self.provider.await_count, 1)

    def test_foreign_owner_and_stale_id_rejected(self):
        service.prepare_execution(self.owner, self.execution)
        with self.assertRaises(preparation.PreparationNotFound):
            service.read_execution('firebase:fixture:bob', self.execution['execution_id'])
        with self.assertRaises(preparation.PreparationConflict):
            service.prepare_execution(self.owner, {**self.execution, 'proposal_id': uuid.uuid4().hex})

    def test_invalid_syntax_is_retained_but_not_verified(self):
        self.fresh_plan()
        self.output['changes'][0]['hunks'][0]['after'] = 'value = ('
        self.provider.return_value = json.dumps(self.output)
        self.generate()
        self.execution.update(request_id=self.plan['request_id'], plan_id=self.plan_id, proposal_id=self.proposal_id)
        result = service.prepare_execution(self.owner, self.execution)
        self.assertEqual(result['static_checks'][0]['status'], 'failed')
        self.assertEqual(result['state'], 'BLOCKED')

    def test_javascript_candidate_uses_selected_node_check_without_host_execution(self):
        (self.repo/'src/app.js').write_bytes(b'const value = 1;\n')
        (self.repo/'tests/app.test.mjs').write_bytes(b'// selected test, never run\n')
        self.plan['files'] = [{'relative_path':'src/app.js','role':'editable'},
                              {'relative_path':'tests/app.test.mjs','role':'verification'}]
        self.plan['checks'] = [{'check_id':'node','profile':'node_test','targets':['tests/app.test.mjs']}]
        self.fresh_plan()
        self.generate()
        self.execution.update(request_id=self.plan['request_id'], plan_id=self.plan_id, proposal_id=self.proposal_id)
        result = service.prepare_execution(self.owner, self.execution)
        self.assertIn(result['static_checks'][0]['status'], {'passed', 'not_run'})
        self.assertEqual(result['checks'][0]['argv'], ['node','--test','tests/app.test.mjs'])

    def test_history_discovers_owner_records_without_reading_source(self):
        service.prepare_execution(self.owner, self.execution)
        with patch.object(service, '_candidate_inputs', side_effect=AssertionError('History must be metadata only')):
            result = service.list_executions(self.owner)
        self.assertTrue(result['metadata_only'])
        self.assertEqual(result['items'][0]['execution_id'], self.execution['execution_id'])
        self.assertEqual(service.list_executions('firebase:fixture:bob')['items'], [])

    def test_history_cursor_and_input_bounds(self):
        one = {**self.execution, 'execution_id': '1'*32}
        two = {**self.execution, 'execution_id': '2'*32}
        service.prepare_execution(self.owner, one)
        service.prepare_execution(self.owner, two)
        first = service.list_executions(self.owner, limit=1)
        self.assertEqual(first['next_cursor'], one['execution_id'])
        second = service.list_executions(self.owner, limit=1, cursor=first['next_cursor'])
        self.assertEqual(second['items'][0]['execution_id'], two['execution_id'])
        self.assertIsNone(second['next_cursor'])
        for kwargs in ({'limit': True}, {'limit': 0}, {'cursor': '../bad'}):
            with self.assertRaises(ValueError): service.list_executions(self.owner, **kwargs)

    def test_history_does_not_call_tampered_result_verified(self):
        service.prepare_execution(self.owner, self.execution)
        folder = service._folder(self.owner, self.execution['execution_id'])
        value = preparation._load(folder/'result.json')
        value['state'] = 'VERIFIED'
        (folder/'result.json').write_text(json.dumps(preparation._sealed(value)), encoding='utf-8')
        with self.assertRaises(preparation.PreparationEvidenceError): service.list_executions(self.owner)

    def test_application_is_always_blocked(self):
        service.prepare_execution(self.owner, self.execution)
        with self.assertRaises(preparation.PreparationConflict):
            service.apply_execution(self.owner, self.execution['execution_id'])
        self.assertEqual((self.repo/'src/app.py').read_bytes(), b'value = 1\n')

    def test_routes_disabled_default_and_independently_authenticated(self):
        app = FastAPI()
        app.include_router(api.router, prefix='/api/chat/coding-tasks')
        client = TestClient(app)
        with patch.dict(os.environ, {'AI_BS_CODING_MODE':'0'}):
            self.assertEqual(client.get('/api/chat/coding-tasks/mode/capabilities').status_code, 403)
            app.dependency_overrides[require_preparation_owner] = lambda: self.owner
            capabilities = client.get('/api/chat/coding-tasks/mode/capabilities').json()
            self.assertFalse(capabilities['enabled'])
            self.assertEqual(client.post('/api/chat/coding-tasks/mode/executions', json=self.execution).status_code, 404)
        with patch.dict(os.environ, {'AI_BS_CODING_MODE':'1'}):
            self.assertEqual(client.post('/api/chat/coding-tasks/mode/executions', json=self.execution).status_code, 200)
            root = '/api/chat/coding-tasks/mode/executions/'+self.execution['execution_id']
            self.assertEqual(client.get(root).json()['state'], 'BLOCKED')
            self.assertEqual(client.post(root+'/apply').status_code, 409)
            app.dependency_overrides.clear()
            for suffix in ('/review','/cancel','/recover','/apply'):
                self.assertEqual(client.post(root+suffix).status_code, 403)
