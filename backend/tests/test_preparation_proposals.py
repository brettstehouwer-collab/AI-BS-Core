"""Bounded proposal evidence from synthetic retained inputs; never runs proposed code."""
import asyncio
import copy
import hashlib
import json
import unittest
from unittest.mock import AsyncMock, patch
import uuid

from test_coding_preparation import PreparationTests
from core import coding_preparation as preparation
from core import coding_preparation_planning as planning
try:
    from core import coding_preparation_proposals as proposals
except ImportError:
    proposals = None


class ProposalTests(unittest.TestCase):
    setUpClass = classmethod(PreparationTests.setUpClass.__func__)
    payload = PreparationTests.payload
    job = PreparationTests.job
    client = PreparationTests.client

    def setUp(self):
        self.assertIsNotNone(proposals, 'Retained multi-file proposal service is missing')
        PreparationTests.setUp(self)
        # Three opaque IDs plus the owner hash otherwise exceed MAX_PATH on
        # Windows before the mocked provider is entered. Keep the journal
        # short while retaining full, real owner/request/plan/proposal IDs.
        self.requests = self.root / self.case.name[:8]
        patch.object(preparation, 'REQUESTS', self.requests).start()
        self.plan['objective'] = 'Change value from1 to42; preserve all tests and dependencies.'
        self.plan_id = uuid.uuid4().hex
        self.proposal_id = uuid.uuid4().hex
        self.plan_provider = patch.object(planning, '_http_plan', new_callable=AsyncMock).start()
        self.http_adapter = proposals._http_proposal
        self.provider = patch.object(proposals, '_http_proposal', new_callable=AsyncMock).start()
        self.prepare_and_plan()

    def prepare_and_plan(self):
        preparation.prepare_request(self.owner, self.payload())
        steps = [{'path': item['relative_path'], 'change': 'Change the selected value to42.'}
                 for item in self.plan['files'] if item['role'] == 'editable']
        self.plan_provider.return_value = json.dumps({'summary': 'Change only selected implementation values.',
                                                     'steps': steps, 'questions': []})
        asyncio.run(planning.generate_plan(self.owner, self.plan['request_id'], self.plan_id))
        self.review = proposals.review_plan(self.owner, self.plan['request_id'], self.plan_id)
        self.output = {'summary': 'Selected implementations now return42.', 'changes': []}
        for item in self.plan['files']:
            if item['role'] == 'editable':
                raw = (self.repo / item['relative_path']).read_bytes()
                self.output['changes'].append({'path': item['relative_path'], 'base_sha256': hashlib.sha256(raw).hexdigest(),
                    'hunks': [{'before': 'value = 1', 'after': 'value = 42'}]})
        self.provider.return_value = json.dumps(self.output)

    def fresh_plan(self):
        self.plan['request_id'] = uuid.uuid4().hex
        self.plan_id = uuid.uuid4().hex
        self.proposal_id = uuid.uuid4().hex
        self.prepare_and_plan()

    def generate(self, owner=None, identifier=None, digest=None):
        return asyncio.run(proposals.generate_proposal(owner or self.owner, self.plan['request_id'], self.plan_id,
            identifier or self.proposal_id, self.review['reviewed_plan_sha256'] if digest is None else digest))

    def read(self):
        return proposals.read_proposal(self.owner, self.plan['request_id'], self.plan_id, self.proposal_id)

    def folder(self):
        return self.job() / 'planning' / self.plan_id / 'proposals' / self.proposal_id

    def test_review_binds_plan_and_success_preserves_all_originals_without_execution(self):
        before = {item['relative_path']: (self.repo / item['relative_path']).read_bytes() for item in self.plan['files']}
        self.assertEqual(self.review['state'], 'PLAN_REVIEW_READY')
        self.assertEqual(len(self.review['reviewed_plan_sha256']), 64)
        result = self.generate()
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['apply_authorized'])
        self.assertEqual(result['verification_status'], 'not_run')
        self.assertEqual(result['reviewed_plan_sha256'], self.review['reviewed_plan_sha256'])
        file = result['proposal']['files'][0]
        self.assertEqual(file['path'], 'src/app.py')
        self.assertEqual(file['content'], 'value = 42\n')
        self.assertEqual(file['proposed_sha256'], hashlib.sha256(b'value = 42\n').hexdigest())
        self.assertIn('-value = 1', result['proposal']['diff'])
        self.assertIn('+value = 42', result['proposal']['diff'])
        self.assertEqual(before, {name: (self.repo / name).read_bytes() for name in before})
        self.assertFalse((self.job() / 'request.json').exists())
        self.assertNotIn('review_token', result)

    def test_full_source_keeps_crlf_and_tail_beyond_old_planning_excerpt(self):
        raw = b'# retained prefix\r\n' + b'# long but bounded unchanged context\r\n' * 125 + b'value = 1\r\n# keep final tail\r\n'
        (self.repo / 'src/app.py').write_bytes(raw)
        self.fresh_plan()
        result = self.generate()
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        content = result['proposal']['files'][0]['content']
        self.assertEqual(content.encode('utf-8'), raw.replace(b'value = 1', b'value = 42'))
        source = next(item for item in self.provider.call_args.args[0]['source_files'] if item['path'] == 'src/app.py')
        self.assertTrue(source['source_complete'])
        self.assertEqual(source['content'].encode('utf-8'), raw)
        self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest())

    def test_python_and_jsx_proposals_keep_checks_and_dependency_inputs(self):
        jsx = b'export default function App() { const value = 1; return <span>{value}</span>; }\n'
        (self.repo / 'src/App.jsx').write_bytes(jsx)
        self.plan['files'] += [{'relative_path': 'src/App.jsx', 'role': 'editable'},
                              {'relative_path': 'package.json', 'role': 'dependency'},
                              {'relative_path': 'package-lock.json', 'role': 'dependency'}]
        self.plan['checks'].append({'check_id': 'frontend', 'profile': 'npm_script', 'targets': ['test']})
        self.fresh_plan()
        result = self.generate()
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        self.assertEqual({item['path'] for item in result['proposal']['files']}, {'src/app.py', 'src/App.jsx'})
        data = self.provider.call_args.args[0]
        self.assertEqual(len(data['source_files']), 5)
        self.assertEqual(len(data['checks']), 2)
        self.assertTrue(all(item['source_complete'] for item in data['source_files']))
        self.assertEqual((self.repo / 'src/App.jsx').read_bytes(), jsx)
        self.assertEqual((self.repo / 'package.json').read_bytes(), b'{"scripts":{"test":"do-not-execute"}}')

    def test_review_rejects_unanswered_plan_questions(self):
        identifier = uuid.uuid4().hex
        self.plan_provider.return_value = json.dumps({'summary': 'Value choice unresolved.',
            'steps': [{'path': 'src/app.py', 'change': 'Change only after clarification.'}],
            'questions': ['Should this use42 or43?']})
        asyncio.run(planning.generate_plan(self.owner, self.plan['request_id'], identifier))
        with self.assertRaises((ValueError, preparation.PreparationConflict)):
            proposals.review_plan(self.owner, self.plan['request_id'], identifier)
        self.provider.assert_not_awaited()

    def test_stale_review_digest_and_forged_identity_reject_before_provider(self):
        with self.assertRaises(preparation.PreparationConflict):
            self.generate(digest='0' * 64)
        with self.assertRaises(preparation.PreparationNotFound):
            self.generate(owner='firebase:fixture:bob')
        self.provider.assert_not_awaited()
        self.assertFalse(self.folder().exists())

    def test_same_id_returns_identical_evidence_without_new_inference(self):
        first = self.generate()
        self.assertEqual(self.generate(), first)
        self.assertEqual(self.read(), first)
        self.assertEqual(self.provider.await_count, 1)
        with self.assertRaises(preparation.PreparationConflict):
            self.generate(digest='0' * 64)
        self.assertEqual(self.provider.await_count, 1)

    def test_invalid_identifiers_reject_before_provider(self):
        for identifier in ['../escape', 'Z' * 32, 'a' * 31]:
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                self.generate(identifier=identifier)
        self.provider.assert_not_awaited()

    def test_incomplete_full_source_budget_rejects_without_silently_truncating(self):
        (self.repo / 'src/app.py').write_bytes(b'# input larger than complete-source budget\n' + b'# x\n' * 6000 + b'value = 1\n')
        self.plan['request_id'] = uuid.uuid4().hex
        self.plan_id = uuid.uuid4().hex
        preparation.prepare_request(self.owner, self.payload())
        self.plan_provider.return_value = json.dumps({'summary': 'Change selected value.',
            'steps': [{'path': 'src/app.py', 'change': 'Change1 to42.'}], 'questions': []})
        asyncio.run(planning.generate_plan(self.owner, self.plan['request_id'], self.plan_id))
        with self.assertRaises(ValueError):
            review = proposals.review_plan(self.owner, self.plan['request_id'], self.plan_id)
            asyncio.run(proposals.generate_proposal(self.owner, self.plan['request_id'], self.plan_id,
                self.proposal_id, review['reviewed_plan_sha256']))
        self.provider.assert_not_awaited()

    def test_invalid_model_json_fields_hashes_and_scope_are_failed_attempts(self):
        outputs = ['not JSON', '{"summary":"a","summary":"b","changes":[]}',
                   json.dumps(dict(self.output, tool_call={'name': 'execute'})), json.dumps(dict(self.output, changes=[]))]
        for path in ['tests/test_app.py', 'package.json', '../outside.py']:
            altered = copy.deepcopy(self.output)
            altered['changes'][0]['path'] = path
            outputs.append(json.dumps(altered))
        altered = copy.deepcopy(self.output)
        altered['changes'][0]['base_sha256'] = '0' * 64
        outputs.append(json.dumps(altered))
        altered = copy.deepcopy(self.output)
        altered['changes'] *= 2
        outputs.append(json.dumps(altered))
        for raw in outputs:
            with self.subTest(raw=raw[:45]):
                self.provider.return_value = raw
                result = self.generate(identifier=uuid.uuid4().hex)
                self.assertEqual(result['state'], 'FAILED')
                self.assertIsNone(result['proposal'])
                self.assertEqual(result['error_code'], 'invalid_model_output')

    def test_missing_ambiguous_overlapping_empty_and_noop_hunks_are_rejected(self):
        cases = [[{'before': 'missing source', 'after': 'changed'}],
                 [{'before': '', 'after': 'changed'}],
                 [{'before': 'value = 1', 'after': 'value = 1'}],
                 [{'before': 'value = 1', 'after': 'value = 42'}, {'before': '= 1', 'after': '= 43'}]]
        for hunks in cases:
            raw = copy.deepcopy(self.output)
            raw['changes'][0]['hunks'] = hunks
            self.provider.return_value = json.dumps(raw)
            result = self.generate(identifier=uuid.uuid4().hex)
            self.assertEqual(result['state'], 'FAILED')
            self.assertEqual(result['error_code'], 'invalid_model_output')
        (self.repo / 'src/app.py').write_bytes(b'value = 1\n# repeated value = 1\n')
        self.fresh_plan()
        self.assertEqual(self.generate()['state'], 'FAILED')

    def test_disjoint_hunks_use_original_offsets_instead_of_mutated_source(self):
        (self.repo / 'src/app.py').write_bytes(b'value = 1\nlabel = "old"\n')
        self.fresh_plan()
        self.output['changes'][0]['hunks'] = [{'before': 'value = 1', 'after': 'value = 42'},
                                            {'before': 'label = "old"', 'after': 'label = "new"'}]
        self.provider.return_value = json.dumps(self.output)
        result = self.generate()
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        self.assertEqual(result['proposal']['files'][0]['content'], 'value = 42\nlabel = "new"\n')

    def test_known_secrets_do_not_enter_public_or_retained_response(self):
        secret = 'synthetic-private-proposal-token46'
        with patch.dict('os.environ', {'PROPOSAL_FIXTURE_TOKEN': secret}):
            self.provider.return_value = json.dumps(dict(self.output, summary=secret))
            result = self.generate()
        self.assertEqual(result['state'], 'FAILED')
        self.assertIsNone(result['proposal'])
        self.assertNotIn(secret, (self.folder() / 'result.json').read_text(encoding='utf-8'))

    def test_retained_source_tamper_stops_before_inference(self):
        (self.job() / 'inputs/src/app.py').write_bytes(b'value = 999\n')
        with self.assertRaises(preparation.PreparationEvidenceError):
            self.generate()
        self.provider.assert_not_awaited()

    def test_retained_source_tamper_during_inference_cannot_be_ready(self):
        async def changed(_):
            (self.job() / 'inputs/src/app.py').write_bytes(b'value = 999\n')
            return json.dumps(self.output)
        self.provider.side_effect = changed
        with self.assertRaises(preparation.PreparationEvidenceError):
            self.generate()
        self.assertNotEqual(preparation._load(self.folder() / 'result.json')['state'], 'PROPOSAL_READY')

    def test_current_original_change_does_not_rewrite_retained_source_status(self):
        (self.repo / 'src/app.py').write_bytes(b'value = 999\n')
        result = self.generate()
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        self.assertFalse(result['current_sources_rechecked'])
        self.assertEqual(result['source_status'], 'retained_inputs')
        self.assertEqual(result['proposal']['files'][0]['content'], 'value = 42\n')
        self.assertEqual((self.repo / 'src/app.py').read_bytes(), b'value = 999\n')

    def test_partial_completion_recovers_dead_worker_without_replay(self):
        self.generate()
        (self.folder() / 'result.json').rename(self.folder() / 'retained_original_result.json')
        self.assertEqual(self.generate()['state'], 'INCOMPLETE')
        self.assertEqual(self.provider.await_count, 1)
        with patch.object(preparation, '_alive', return_value=False):
            result = proposals.recover_proposal(self.owner, self.plan['request_id'], self.plan_id, self.proposal_id)
        self.assertEqual(result['state'], 'INTERRUPTED')
        self.assertEqual(self.read(), result)
        self.assertEqual(self.provider.await_count, 1)

    def test_terminal_result_tamper_is_evidence_error(self):
        self.generate()
        (self.folder() / 'result.json').write_bytes(b'{}')
        with self.assertRaises(preparation.PreparationEvidenceError):
            self.read()

    def test_global_coding_gate_prevents_new_attempt(self):
        from core.coding_chat import _ACTIVE
        self.assertTrue(_ACTIVE.acquire(False))
        try:
            with self.assertRaises(preparation.PreparationConflict):
                self.generate()
        finally:
            _ACTIVE.release()
        self.provider.assert_not_awaited()
        self.assertFalse(self.folder().exists())

    def test_cancel_during_provider_wait_is_terminal_and_retry_never_replays(self):
        async def scenario():
            entered = asyncio.Event()
            async def stalled(_):
                entered.set()
                await asyncio.sleep(2)
            self.provider.side_effect = stalled
            task = asyncio.create_task(proposals.generate_proposal(self.owner, self.plan['request_id'], self.plan_id,
                self.proposal_id, self.review['reviewed_plan_sha256']))
            entry = asyncio.create_task(entered.wait())
            try:
                done, _ = await asyncio.wait({entry, task}, timeout=2, return_when=asyncio.FIRST_COMPLETED)
                if task in done:
                    await task  # Surface setup/admission failure instead of waiting forever.
                    self.fail('Proposal finished before entering the provider')
                self.assertIn(entry, done, 'Mock provider was not entered within the test deadline')
            finally:
                entry.cancel()
                await asyncio.gather(entry, return_exceptions=True)
            cancel = proposals.cancel_proposal(self.owner, self.plan['request_id'], self.plan_id, self.proposal_id)
            self.assertTrue(cancel['cancel_requested'])
            result = await task
            self.assertEqual(result['state'], 'CANCELLED')
            self.assertIsNone(result['proposal'])
            return result
        result = asyncio.run(scenario())
        self.assertEqual(self.generate(), result)
        self.assertEqual(self.provider.await_count, 1)

    def test_provider_deadline_is_retained_without_a_ready_proposal(self):
        async def stalled(_):
            await asyncio.sleep(2)
        self.provider.side_effect = stalled
        with patch.object(proposals, '_DEADLINE_SECONDS', .01):
            result = self.generate()
        self.assertEqual(result['state'], 'TIMED_OUT')
        self.assertIsNone(result['proposal'])
        calls = self.provider.await_count
        self.assertLessEqual(calls, 1)  # Deadline may expire during native journal checks before first scheduling.
        self.assertEqual(self.generate(), result)
        self.assertEqual(self.provider.await_count, calls)

    def test_no_final_newline_diff_has_separate_lines_and_explicit_markers(self):
        (self.repo/'src/app.py').write_bytes(b'value = 1')
        self.fresh_plan()
        result = self.generate()
        self.assertEqual(result['proposal']['files'][0]['content'], 'value = 42')
        self.assertIn('-value = 1\n\\ No newline at end of file\n', result['proposal']['diff'])
        self.assertIn('+value = 42\n\\ No newline at end of file\n', result['proposal']['diff'])

    def test_sources_are_held_against_writes_through_result_publication(self):
        original = proposals._terminal
        blocked = []
        def terminal(folder, value, state, *args, **kwargs):
            if state == 'PROPOSAL_READY':
                try:
                    (self.job()/'inputs/src/app.py').write_bytes(b'value = 999\n')
                except PermissionError:
                    blocked.append(True)
                else:
                    blocked.append(False)
            return original(folder, value, state, *args, **kwargs)
        with patch.object(proposals, '_terminal', side_effect=terminal):
            result = self.generate()
        self.assertEqual(blocked, [True])
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        self.assertEqual(self.read(), result)

    def test_lost_result_write_preserves_intent_and_never_replays(self):
        original = preparation._save_new
        def save(path, value):
            if path.name == 'result.json':
                raise OSError('Synthetic proposal result storage failure')
            return original(path, value)
        with patch.object(preparation, '_save_new', side_effect=save):
            with self.assertRaises(OSError):
                self.generate()
        self.assertTrue((self.folder()/'input.json').exists())
        self.assertEqual(self.generate()['state'], 'INCOMPLETE')
        self.assertEqual(self.provider.await_count, 1)

    def test_cancel_at_result_admission_wins_and_terminal_cancel_is_noop(self):
        original = proposals._terminal
        def terminal(folder, value, state, *args, **kwargs):
            if state == 'PROPOSAL_READY':
                proposals.cancel_proposal(self.owner, self.plan['request_id'], self.plan_id, self.proposal_id)
            return original(folder, value, state, *args, **kwargs)
        with patch.object(proposals, '_terminal', side_effect=terminal):
            result = self.generate()
        self.assertEqual(result['state'], 'CANCELLED')
        self.assertIsNone(result['proposal'])
        terminal_cancel = proposals.cancel_proposal(self.owner, self.plan['request_id'], self.plan_id, self.proposal_id)
        self.assertFalse(terminal_cancel['cancel_requested'])
        self.assertEqual(self.generate(), result)

    def test_resealed_proposal_content_is_reconstructed_before_read(self):
        self.generate()
        path = self.folder()/'result.json'
        record = preparation._load(path)
        record['proposal']['files'][0]['content'] = 'value = 9000\n'
        path.rename(self.folder()/'original_result.json')
        preparation._save_new(path, record)
        with self.assertRaises(preparation.PreparationEvidenceError):
            self.read()

    def test_disjoint_hunks_use_original_offsets_and_preserve_bom(self):
        raw = b'\xef\xbb\xbfvalue = 1\r\nother = 2\r\n'
        (self.repo/'src/app.py').write_bytes(raw)
        self.fresh_plan()
        self.output['changes'][0]['hunks'] = [
            {'before':'other = 2','after':'other = 2000'},
            {'before':'value = 1','after':'value = 42'}]
        self.provider.return_value = json.dumps(self.output)
        result = self.generate()
        self.assertEqual(result['state'], 'PROPOSAL_READY')
        self.assertEqual(result['proposal']['files'][0]['content'].encode('utf-8'),
                         raw.replace(b'value = 1',b'value = 42').replace(b'other = 2',b'other = 2000'))

    def test_actual_provider_adapter_has_fixed_local_wire_and_bounded_envelope(self):
        import httpx
        original = httpx.AsyncClient
        requests = []
        envelope = {'done':True,'model':'stehouwer_llm:latest','response':json.dumps(self.output)}
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=envelope)
        def client(**kwargs):
            self.assertFalse(kwargs['trust_env'])
            self.assertFalse(kwargs['follow_redirects'])
            return original(transport=httpx.MockTransport(handler), **kwargs)
        with patch.object(httpx, 'AsyncClient', side_effect=client):
            self.assertEqual(asyncio.run(self.http_adapter({'source_files':[]})), envelope['response'])
            self.assertEqual(str(requests[0].url), 'http://127.0.0.1:11434/api/generate')
            body = json.loads(requests[0].content)
            self.assertEqual(body['model'], 'stehouwer_llm:latest')
            self.assertFalse(body['stream'])
            self.assertNotIn('tools', body)
            for invalid in [[], dict(envelope, done=False), dict(envelope, model='other'),
                            dict(envelope, response='x'*40000)]:
                envelope = invalid
                with self.assertRaises(ValueError):
                    asyncio.run(self.http_adapter({}))

    def test_independently_authenticated_api_rejects_owner_and_extra_authority(self):
        base = '/api/chat/coding-tasks/preparations/' + self.plan['request_id'] + '/plans/' + self.plan_id
        body = {'proposal_id': self.proposal_id, 'reviewed_plan_sha256': self.review['reviewed_plan_sha256']}
        with self.client() as client:
            operations = [('GET', base + '/proposal-review', None), ('POST', base + '/proposals', body),
                ('GET', base + '/proposals/' + self.proposal_id, None),
                ('POST', base + '/proposals/' + self.proposal_id + '/recover', None),
                ('POST', base + '/proposals/' + self.proposal_id + '/cancel', None)]
            for method, path, data in operations:
                response = client.request(method, path, **({'json': data} if data else {}))
                self.assertEqual(response.status_code, 403, (method, path))
            headers = {'Authorization': 'Bearer alice-fixture'}
            self.assertEqual(client.get(base + '/proposal-review', headers=headers).json()['reviewed_plan_sha256'],
                             self.review['reviewed_plan_sha256'])
            for extra in [{'owner': 'local_admin'}, {'execution_backend': 'trusted_host'}, {'files': []}]:
                self.assertEqual(client.post(base + '/proposals', headers=headers, json=dict(body, **extra)).status_code, 422)
            wrong = dict(body, reviewed_plan_sha256='0' * 64)
            self.assertEqual(client.post(base + '/proposals', headers=headers, json=wrong).status_code, 409)
            response = client.post(base + '/proposals', headers=headers, json=body)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['state'], 'PROPOSAL_READY')
            self.assertEqual(client.get(base + '/proposals/' + self.proposal_id, headers=headers).json(), response.json())
            self.assertEqual(client.get(base + '/proposals/' + self.proposal_id,
                headers={'Authorization': 'Bearer bob-fixture'}).status_code, 404)


if __name__ == '__main__':
    unittest.main()
