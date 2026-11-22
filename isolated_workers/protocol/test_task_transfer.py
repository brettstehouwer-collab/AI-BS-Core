"""Transfer-contract infrastructure tests; no project execution or VM admission."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.core.coding_vm_inputs import validate_vm_inputs
from backend.core.coding_vm_artifacts import validate_vm_artifacts
from isolated_workers.protocol import scoped_exchange as codec


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode('utf-8')


def fixture(extra=None):
    contents = {'main.py': b'1', 'test_main.py': b'2'}
    contents.update(extra or {})
    admission = dict(schema_version=2, task_id='1'*32, request_id='2'*32,
                     attempt_id='3'*32, repository_id='4'*32, commit='5'*40,
                     authorization_ref='6'*32, base_image_sha256='7'*64,
                     files=[dict(relative_path=name, length=len(data),
                                 sha256=hashlib.sha256(data).hexdigest(),
                                 role='editable' if name == 'main.py' else
                                      'verification' if name == 'test_main.py' else 'dependency')
                            for name, data in contents.items()],
                     checks=[{'check_id':'unit', 'argv':['python','-m','unittest','test_main']}],
                     limits={'check_seconds':30, 'total_seconds':180, 'output_bytes':262144})
    return validate_vm_inputs(admission, contents, admission), contents


def artifacts(admission, contents):
    return dict(schema_version=1, task_id=admission['task_id'],
                request_id=admission['request_id'], attempt_id=admission['attempt_id'],
                base_image_sha256=admission['base_image_sha256'],
                input_manifest_sha256=hashlib.sha256(encoded(admission)).hexdigest(),
                files=[dict(relative_path=name, length=len(data), sha256=hashlib.sha256(data).hexdigest())
                       for name, data in contents.items()])


class TaskTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.transfer = importlib.import_module('backend.core.coding_vm_transfer')

    def restore(self, plan, admission, **kwargs):
        return self.transfer.restore_vm_transfer(plan.manifest_bytes, dict(plan.chunks), admission,
                                                 direction=kwargs.pop('direction', 'host_to_guest'), **kwargs)

    def test_original_unicode_dotfiles_and_240_character_path_preserved(self):
        long_path = 'src/' + 'a'*110 + '/' + 'b'*110 + '/' + 'c'*10 + '.txt'
        self.assertEqual(len(long_path), 240)
        admission, contents = fixture({'src/日本語.py':b'Unicode metadata', '.eslintrc.json':b'{}',
                                       '.config/settings.json':b'{}', long_path:b'long path'})
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        result = self.restore(plan, admission)
        self.assertEqual(result.contents, contents)
        self.assertEqual(result.envelope, admission)
        self.assertTrue(all(path.isascii() and len(path) <= 192 for path in plan.transport_files))
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.apply_authorized)
        self.assertEqual(result.verification_status, 'not_run')

    def test_two_mebibyte_file_roundtrip_through_existing_authenticated_codec(self):
        admission, contents = fixture({'assets/large.txt':b'x'*(2*1024*1024)})
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        self.assertTrue(all(len(data) <= 1024*1024 for data in plan.transport_files.values()))
        received = {}
        seen = set()
        def claim(worker, direction, nonce, digest, expires):
            if nonce in seen: return False
            seen.add(nonce); return True
        for index, (path, data) in enumerate(plan.transport_files.items()):
            policy = codec.Policy('fixture-worker', 'fixture-owner', admission['base_image_sha256'],
                                  'host_to_guest', frozenset({path}), {path:hashlib.sha256(data).hexdigest()})
            packet = codec.pack(b'k'*32, policy, 'message', '', {path:data}, f'{index:032x}', 1000, 1100)
            bundle = codec.unpack(packet, b'k'*32, policy, 1001, claim)
            received[bundle.files[0].path] = bundle.files[0].data
            with self.assertRaises(codec.Rejected):
                codec.unpack(packet, b'k'*32, policy, 1001, claim)
        header = received.pop(plan.manifest_path)
        restored = self.transfer.restore_vm_transfer(header, received, admission, direction='host_to_guest')
        self.assertEqual(restored.contents, contents)

    def test_twenty_files_and_exact_sixteen_mebibytes(self):
        extra = {f'large_{i}.txt':b'x'*(2*1024*1024) for i in range(7)}
        extra['last.txt'] = b'y'*(2*1024*1024-2)
        extra.update({f'empty_{i}.txt':b'' for i in range(10)})
        admission, contents = fixture(extra)
        self.assertEqual(len(contents), 20)
        self.assertEqual(sum(map(len, contents.values())), 16*1024*1024)
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        self.assertLessEqual(len(plan.transport_files), 64)
        self.assertEqual(self.restore(plan, admission).contents, contents)

    def test_original_file_count_individual_and_total_overflow_refused(self):
        for extra in [{f'a{i}.txt':b'' for i in range(19)},
                      {'big.txt':b'x'*(2*1024*1024+1)},
                      {f'large{i}.txt':b'x'*(2*1024*1024) for i in range(8)}]:
            contents = {'main.py':b'1', 'test_main.py':b'2', **extra}
            admission, _ = fixture()
            admission['files'] += [dict(relative_path=name, length=len(data), sha256=hashlib.sha256(data).hexdigest(), role='dependency')
                                   for name, data in extra.items()]
            with self.assertRaises(ValueError):
                self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')

    def test_missing_extra_reordered_and_swapped_chunk_bytes(self):
        admission, contents = fixture({'big.txt':b'x'*(1024*1024)+b'y'})
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        original = dict(plan.chunks)
        missing = dict(original); missing.pop(next(iter(missing)))
        extra = {**original, 'inputs/unapproved.bin':b''}
        altered = dict(original); name = next(iter(altered)); altered[name] += b'x'
        for changed in [missing, extra, altered]:
            with self.assertRaises(ValueError):
                self.transfer.restore_vm_transfer(plan.manifest_bytes, changed, admission, direction='host_to_guest')
        self.assertEqual(self.transfer.restore_vm_transfer(plan.manifest_bytes, dict(reversed(list(original.items()))),
                                                         admission, direction='host_to_guest').contents, contents)

    def test_wrong_attempt_base_direction_and_input_binding_refused(self):
        admission, contents = fixture()
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        for field in ['attempt_id','task_id','request_id','base_image_sha256']:
            changed = copy.deepcopy(admission); changed[field] = 'a'*len(changed[field])
            with self.assertRaises(ValueError): self.restore(plan, changed)
        with self.assertRaises(ValueError): self.restore(plan, admission, direction='guest_to_host')

    def test_duplicate_noncanonical_and_oversized_transport_manifest_refused(self):
        admission, contents = fixture()
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        for raw in [plan.manifest_bytes+b' ', b'{"version":1,"version":1}',
                    b'x'*(262144+1), b'\xff', b'{"version":NaN}']:
            with self.assertRaises(ValueError):
                self.transfer.restore_vm_transfer(raw, dict(plan.chunks), admission, direction='host_to_guest')

    def test_chunk_manifest_path_length_hash_and_unknown_fields_refused(self):
        admission, contents = fixture()
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        for change in ['path','length','sha256','extra','reorder']:
            header = json.loads(plan.manifest_bytes)
            if change == 'path': header['parts'][0]['path'] = '../escape'
            elif change == 'length': header['parts'][0]['length'] = True
            elif change == 'sha256': header['parts'][0]['sha256'] = '0'*64
            elif change == 'extra': header['execution_authorized'] = True
            else: header['parts'].reverse()
            with self.assertRaises(ValueError):
                self.transfer.restore_vm_transfer(encoded(header), dict(plan.chunks), admission, direction='host_to_guest')

    def test_artifact_bytes_may_change_only_for_editable_role(self):
        admission, contents = fixture({'dep/日本語.json':b'{}'})
        outputs = {**contents, 'main.py':b'changed editable bytes'}
        envelope = artifacts(admission, outputs)
        validate_vm_artifacts(envelope, outputs, admission)
        plan = self.transfer.prepare_vm_transfer(envelope, outputs, admission, direction='guest_to_host')
        result = self.restore(plan, admission, direction='guest_to_host')
        self.assertEqual(result.contents, outputs)
        self.assertFalse(result.apply_authorized)
        for name in ['test_main.py','dep/日本語.json']:
            changed = {**outputs, name:b'changed immutable'}
            with self.assertRaises(ValueError):
                self.transfer.prepare_vm_transfer(artifacts(admission, changed), changed, admission, direction='guest_to_host')

    def test_final_whole_file_hash_still_required_after_part_hashes(self):
        admission, contents = fixture()
        outputs = {**contents, 'main.py':b'a'}
        plan = self.transfer.prepare_vm_transfer(artifacts(admission, outputs), outputs, admission, direction='guest_to_host')
        header = json.loads(plan.manifest_bytes); chunks = dict(plan.chunks)
        part = header['parts'][0]; chunks[part['path']] = b'b'
        part['sha256'] = hashlib.sha256(b'b').hexdigest()
        with self.assertRaises(ValueError):
            self.transfer.restore_vm_transfer(encoded(header), chunks, admission, direction='guest_to_host')

    def test_no_io_and_detached_results(self):
        admission, contents = fixture()
        with patch('builtins.open', side_effect=AssertionError('unexpected file IO')):
            plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
            restored = self.restore(plan, admission)
        admission['files'][0]['sha256'] = '0'*64
        self.assertNotEqual(restored.envelope['files'][0]['sha256'], '0'*64)
        with self.assertRaises(TypeError): plan.chunks['unexpected'] = b''
        with self.assertRaises(TypeError): restored.contents['unexpected'] = b''

    def test_header_inspection_is_metadata_only_detached_and_has_no_authority(self):
        admission, contents = fixture({'dep/日本語.json':b'{}'})
        plan = self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
        with patch('builtins.open', side_effect=AssertionError('unexpected file IO')):
            inspected = self.transfer.inspect_vm_transfer(plan.manifest_bytes, admission, direction='host_to_guest')
        self.assertEqual(inspected.manifest_path, plan.manifest_path)
        self.assertEqual({part['path'] for part in inspected.parts}, set(plan.chunks))
        self.assertEqual(inspected.envelope, admission)
        self.assertFalse(inspected.worker_admitted)
        self.assertFalse(inspected.execution_authorized)
        self.assertFalse(inspected.apply_authorized)
        self.assertEqual(inspected.verification_status, 'not_run')
        detached = inspected.envelope
        detached['files'][0]['sha256'] = '0'*64
        self.assertEqual(inspected.envelope, admission)
        with self.assertRaises(TypeError): inspected.parts[0]['path'] = '../escape'

    def test_output_header_rejects_unapproved_missing_or_changed_immutable_files_before_chunks(self):
        admission, contents = fixture({'dep/config.json':b'{}'})
        outputs = {**contents, 'main.py':b'changed editable bytes'}
        plan = self.transfer.prepare_vm_transfer(artifacts(admission, outputs), outputs, admission, direction='guest_to_host')
        valid = self.transfer.inspect_vm_transfer(plan.manifest_bytes, admission, direction='guest_to_host')
        self.assertEqual(valid.envelope['files'][0]['length'], len(outputs['main.py']))
        for change in ['unapproved_path', 'missing_file', 'immutable_hash', 'immutable_length']:
            header = json.loads(plan.manifest_bytes)
            if change == 'unapproved_path': header['envelope']['files'][0]['relative_path'] = 'unapproved.py'
            elif change == 'missing_file': header['envelope']['files'].pop()
            elif change == 'immutable_hash': header['envelope']['files'][1]['sha256'] = '0'*64
            else: header['envelope']['files'][1]['length'] += 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.transfer.inspect_vm_transfer(encoded(header), admission, direction='guest_to_host')

    def test_logical_private_store_and_model_names_cannot_hide_behind_opaque_parts(self):
        for name in ['personal_ai_profile.db','aibs_vault.sqlite','aibs_master.sqlite3',
                     'session.db-wal','session.db-shm','base.vdi','model.gguf',
                     'weights.safetensors','fixture.sqlite/nested.txt']:
            with self.subTest(name=name):
                admission, contents = fixture({name:b'synthetic data only'})
                with self.assertRaises(ValueError):
                    self.transfer.prepare_vm_transfer(admission, contents, admission, direction='host_to_guest')
                # Construct an otherwise valid artifact header without asking
                # the sender helper to admit the logically excluded filename.
                envelope = artifacts(admission, contents)
                header = {'version':1, 'direction':'guest_to_host', 'transfer_id':'0'*32,
                          'input_manifest_sha256':hashlib.sha256(encoded(admission)).hexdigest(),
                          'envelope':envelope, 'parts':[]}
                digest, identity, prefix = self.transfer._scope(admission, 'guest_to_host')
                header['transfer_id'] = identity
                with self.assertRaisesRegex(ValueError, 'Private store or model path excluded'):
                    self.transfer.inspect_vm_transfer(encoded(header), admission, direction='guest_to_host')


if __name__ == '__main__':
    unittest.main()
