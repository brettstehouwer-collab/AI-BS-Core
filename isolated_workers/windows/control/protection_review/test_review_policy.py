"""Synthetic policy-review cases only; no OS access tests or worker acceptance."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name('review_policy.py')


def fixture():
    root = r'C:\ProgramData\AI-BS-WorkerControl'
    controller = 'S-1-5-21-1-2-3-1001'
    worker = 'S-1-5-21-1-2-3-1005'
    admin, system = 'S-1-5-32-544', 'S-1-5-18'
    names = ['deployment', 'state', 'sealed_inputs', 'incoming_outputs', 'receipts']
    policy = {'schema_version': 1, 'mode': 'review_only', 'root': root,
              'controller_sid': controller, 'vm_worker_sid': worker,
              'roots': {name: root + '\\' + name for name in names},
              'files': [{'path': root + r'\deployment\python.exe',
                         'sha256': 'a' * 64, 'kind': 'runtime',
                         'signer': 'Python Software Foundation'}]}
    def node(path, writers):
        return {'path': path, 'exists': True, 'owner_sid': admin,
                'protected_dacl': True, 'reparse': False,
                'grants': [{'sid': sid, 'rights': rights, 'type': 'Allow'}
                           for sid, rights in writers]}
    nodes = [node(root, [(admin, 'FullControl'), (system, 'FullControl')])]
    for name, path in policy['roots'].items():
        writers = [(admin, 'FullControl'), (system, 'FullControl')]
        if name in {'state', 'sealed_inputs', 'receipts', 'incoming_outputs'}:
            writers.append((controller, 'Modify'))
        if name == 'incoming_outputs':
            writers.append((worker, 'Modify'))
        nodes.append(node(path, writers))
    file = node(policy['files'][0]['path'], [(admin, 'FullControl'), (system, 'FullControl')])
    file.update({'sha256': 'a' * 64, 'signature_valid': True,
                 'signer': 'Python Software Foundation'})
    nodes.append(file)
    return policy, {'schema_version': 1, 'nodes': nodes}


class ReviewPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('review_policy_fixture', SOURCE)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def review(self, policy=None, snapshot=None):
        p, s = fixture()
        return self.module.review(policy or p, snapshot or s)

    def test_clean_synthetic_metadata_never_grants_authority(self):
        result = self.review()
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['state'], 'REVIEW_ONLY')
        for name in ['worker_admitted', 'execution_authorized', 'apply_authorized']:
            self.assertIs(result[name], False)
        self.assertEqual(result['verification_status'], 'not_run')
        self.assertTrue(result['required_native_checks'])

    def test_missing_deployment_blocks_review_without_creating_it(self):
        p, s = fixture(); s['nodes'][1] = {'path': p['roots']['deployment'], 'exists': False}
        self.assertIn('MISSING_PATH', {x['code'] for x in self.review(p, s)['findings']})

    def test_broad_and_capability_writes_are_rejected_on_code(self):
        for sid in ['S-1-5-11', 'S-1-1-0', 'S-1-15-3-123', 'S-1-3-0']:
            with self.subTest(sid=sid):
                p, s = fixture(); s['nodes'][1]['grants'].append({'sid': sid, 'rights': 'Modify', 'type': 'Allow'})
                self.assertIn('UNAPPROVED_WRITER', {x['code'] for x in self.review(p, s)['findings']})

    def test_task_owner_or_unprotected_code_dacl_is_flagged(self):
        p, s = fixture(); s['nodes'][1]['owner_sid'] = p['vm_worker_sid']
        s['nodes'][1]['protected_dacl'] = False
        codes = {x['code'] for x in self.review(p, s)['findings']}
        self.assertTrue({'UNAPPROVED_OWNER', 'DACL_NOT_PROTECTED'} <= codes)

    def test_receipts_cannot_be_written_by_delivery_worker(self):
        p, s = fixture()
        node = next(n for n in s['nodes'] if n['path'] == p['roots']['receipts'])
        node['grants'].append({'sid': p['vm_worker_sid'], 'rights': 'Modify', 'type': 'Allow'})
        self.assertIn('UNAPPROVED_WRITER', {x['code'] for x in self.review(p, s)['findings']})

    def test_changed_or_unsigned_runtime_is_flagged(self):
        p, s = fixture(); s['nodes'][-1]['sha256'] = 'b' * 64
        s['nodes'][-1]['signature_valid'] = False
        codes = {x['code'] for x in self.review(p, s)['findings']}
        self.assertTrue({'FILE_HASH_MISMATCH', 'RUNTIME_SIGNATURE_MISMATCH'} <= codes)

    def test_root_alias_escape_and_overlap_are_rejected(self):
        for value in [r'C:\AI-BS', r'C:\ProgramData\AI-BS-WorkerControl\..\other', r'\\server\share', r'C:\ProgramData\AI-BS-WorkerControl.']:
            p, s = fixture(); p['root'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.review(p, s)
        p, s = fixture(); p['roots']['receipts'] = p['roots']['state']
        with self.assertRaises(ValueError): self.review(p, s)

    def test_manifest_cannot_add_activation_or_unapproved_fields(self):
        p, s = fixture(); p['execution_authorized'] = True
        with self.assertRaises(ValueError): self.review(p, s)

    def test_unexpected_snapshot_paths_and_duplicate_aliases_are_rejected(self):
        p, s = fixture(); s['nodes'].append(deepcopy(s['nodes'][0]))
        with self.assertRaises(ValueError): self.review(p, s)
        p, s = fixture(); s['nodes'].append({'path': r'C:\Users\private', 'exists': False})
        with self.assertRaises(ValueError): self.review(p, s)

    def test_unrecognized_ace_semantics_are_not_treated_as_safe(self):
        for change in [{'rights': 'Read, UnknownBit'}, {'type': 'Deny'}, {'rights': -536805376}]:
            p, s = fixture(); s['nodes'][1]['grants'][0].update(change)
            self.assertIn('UNSUPPORTED_ACE', {x['code'] for x in self.review(p, s)['findings']})

    def test_duplicate_json_keys_are_refused(self):
        with self.assertRaises(ValueError): self.module.parse_json('{"x":1,"x":2}')

    def test_broad_readers_cannot_read_controller_state(self):
        p, s = fixture()
        node = next(n for n in s['nodes'] if n['path'] == p['roots']['state'])
        node['grants'].append({'sid': 'S-1-1-0', 'rights': 'ReadAndExecute', 'type': 'Allow'})
        self.assertIn('UNAPPROVED_READER', {x['code'] for x in self.review(p, s)['findings']})

    def test_missing_path_observation_cannot_hide_extra_authority_fields(self):
        p, s = fixture()
        s['nodes'][0] = {'path': p['root'], 'exists': False, 'execution_authorized': True}
        with self.assertRaises(ValueError): self.review(p, s)

    def test_actual_review_template_is_unprovisioned_and_never_ready(self):
        policy = self.module.parse_json(SOURCE.with_name('policy.review.json').read_text(encoding='utf-8'))
        result = self.module.review(policy, {'schema_version': 1, 'nodes': []})
        self.assertEqual(len(result['findings']), 1 + len(policy['roots']) + len(policy['files']))
        self.assertTrue(all(x['code'] == 'MISSING_PATH' for x in result['findings']))
        self.assertFalse(result['execution_authorized'])


if __name__ == '__main__':
    unittest.main()
