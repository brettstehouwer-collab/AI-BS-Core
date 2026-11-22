"""Trusted controller infrastructure only; never imports the retained candidate."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import threading
import unittest
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
from isolated_workers.protocol import verification_grants as g

E = R / 'backups/local_verification_20261026_record125/grant_tests'


class FaultConnection(sqlite3.Connection):
    fault = ''
    interrupt_begin = False

    def execute(self, statement, *args):
        result = super().execute(statement, *args)
        if statement == 'BEGIN IMMEDIATE' and self.interrupt_begin:
            self.interrupt_begin = False
            raise KeyboardInterrupt('synthetic begin acknowledgement interruption')
        return result

    def commit(self):
        if self.fault == 'interrupt_before':
            raise KeyboardInterrupt('synthetic asynchronous interruption')
        if self.fault == 'before':
            raise OSError('synthetic commit interruption')
        if self.fault == 'suppressed':
            return
        super().commit()
        if self.fault == 'after':
            raise OSError('synthetic acknowledgement interruption')
        if self.fault == 'interrupt_after':
            raise KeyboardInterrupt('synthetic asynchronous interruption')
        if self.fault == 'exit_after':
            raise SystemExit('synthetic asynchronous exit')


def fixture():
    # Synthetic bytes, distinct from number-summary-roundtrip-v1.
    contents = {'main.py': b'synthetic implementation', 'test_main.py': b'synthetic immutable tests'}
    admission = dict(schema_version=2, task_id='1'*32, request_id='2'*32,
                     attempt_id='3'*32, repository_id='4'*32, commit='5'*40,
                     authorization_ref='6'*32, base_image_sha256='7'*64,
                     files=[dict(relative_path=p, length=len(b), sha256=hashlib.sha256(b).hexdigest(),
                                 role='verification' if p.startswith('test_') else 'editable')
                            for p, b in contents.items()],
                     checks=[dict(check_id='unit', argv=['python', '-m', 'unittest', 'test_main'])],
                     limits=dict(check_seconds=30, total_seconds=180, output_bytes=262144))
    worker = dict(worker_id='synthetic-worker', vm_id='12345678-1234-1234-1234-123456789abc',
                  image_sha256='7'*64, disposable_image_id='8'*32, account_sid='S-1-5-21-1-2-3-1005')
    runtime = dict(executable_path='C:/ApprovedRuntime/python.exe', executable_sha256='9'*64,
                   runtime_tree_sha256='a'*64, protection_receipt_sha256='b'*64)
    profile = dict(profile_id='synthetic-infrastructure-only', vcpus=2, vm_memory_bytes=2147483648,
                   task_memory_bytes=536870912, task_cpu_rate_percent=25, process_limit=8,
                   check_seconds=30, total_seconds=180, output_bytes=262144,
                   artifact_files=20, artifact_file_bytes=2097152, artifact_total_bytes=16777216,
                   network_policy='deny_all')
    return admission, contents, worker, runtime, profile


class GrantTests(unittest.TestCase):
    def setUp(self):
        self.root = E / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.path = self.root / 'synthetic_attempts.sqlite'
        self.connections = []
        self.key = Ed25519PrivateKey.generate()  # Ephemeral test-only key, never saved.
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.pins = {('synthetic-host', 'ephemeral'): public}
        self.admission, self.contents, self.worker, self.runtime, self.profile = fixture()
        self.scope = self.prepare()
        self.observed = dict(worker=self.worker, runtime=self.runtime)

    def tearDown(self):
        for c in self.connections:
            c.close()

    def prepare(self):
        return g.prepare_scope(self.admission, self.contents, worker=self.worker, runtime=self.runtime,
                               resource_profile=self.profile, environment={'PYTHONUTF8': '1'},
                               fixture_manifest_sha256='c'*64)

    def body(self, **changes):
        b = dict(schema_version=1, domain=g.DOMAIN, authority_domain='infrastructure_test',
                 purpose='bounded_verification', issuer_id='synthetic-host', key_id='ephemeral',
                 grant_id='d'*32, issued_at=1000, expires_at=1200, scope=json.loads(self.scope))
        b.update(changes)
        return b

    def packet(self, body=None):
        b = self.body() if body is None else body
        signature = self.key.sign(g.SIGNING_PREFIX + g.canonical(b)).hex()
        return g.canonical(dict(body=b, signature=signature))

    def verify(self, packet=None, **changes):
        args = dict(pinned_verifiers=self.pins, expected_scope=self.scope, now_utc=1001,
                    authority_domain='infrastructure_test')
        args.update(changes)
        return g.verify_grant(self.packet() if packet is None else packet, **args)

    def registry(self, create=True, factory=sqlite3.Connection, store_id='e'*32, path=None):
        c = sqlite3.connect(path or self.path, timeout=1, check_same_thread=False, factory=factory)
        self.connections.append(c)
        return g.VerificationAttemptRegistry(c, store_id=store_id,
                                            authority_domain='infrastructure_test', create=create)

    def claim(self, registry, packet=None, **changes):
        args = dict(pinned_verifiers=self.pins, expected_scope=self.scope,
                    current_identity=self.observed, clock=lambda: 1001)
        if 'now_utc' in changes:
            timestamp = changes.pop('now_utc'); changes['clock'] = lambda: timestamp
        args.update(changes)
        return registry.claim_once(self.packet() if packet is None else packet, **args)

    def test_valid_signature_returns_detached_data_without_authority(self):
        verified = self.verify()
        self.assertEqual(verified.scope_sha256, hashlib.sha256(self.scope).hexdigest())
        receipt = self.claim(self.registry())
        self.assertEqual(receipt.state, 'ATTEMPT_RESERVED')
        self.assertFalse(receipt.worker_admitted or receipt.execution_authorized or receipt.apply_authorized)
        self.assertEqual(receipt.verification_status, 'not_run')

    def test_tampered_signature_and_wrong_pin(self):
        p = json.loads(self.packet()); p['body']['expires_at'] -= 1
        with self.assertRaises(g.GrantRejected): self.verify(g.canonical(p))
        with self.assertRaises(g.GrantRejected): self.verify(pinned_verifiers={})
        with self.assertRaises(g.GrantRejected): self.verify(pinned_verifiers={('synthetic-host', 'ephemeral'): b'x'*32})

    def test_test_domain_cannot_become_live_grant(self):
        with self.assertRaises(g.GrantRejected): self.verify(authority_domain='disposable_verification')
        for changes in [dict(domain='AI-BS/integration-data/v1'), dict(purpose='project_execution'),
                        dict(purpose='host_apply'), dict(schema_version=True), dict(extra='ignored')]:
            with self.subTest(changes=changes), self.assertRaises(g.GrantRejected):
                self.verify(self.packet(self.body(**changes)))

    def test_expired_future_and_overlong_grants(self):
        for fields in [dict(expires_at=1001), dict(issued_at=1002), dict(expires_at=1601),
                       dict(issued_at=True), dict(expires_at=1000)]:
            with self.subTest(fields=fields), self.assertRaises(g.GrantRejected):
                self.verify(self.packet(self.body(**fields)))

    def test_strict_encoding_and_size(self):
        p = self.packet()
        for bad in [p+b' ', b'{"body":0,"body":1,"signature":"x"}', b'{"body":NaN}',
                    b'['*5000, b'x'*262145, b'\xff', p.decode('utf-8')]:
            with self.subTest(kind=type(bad)), self.assertRaises(g.GrantRejected): self.verify(bad)

    def test_every_exact_scope_field_is_bound(self):
        scope = json.loads(self.scope)
        for field in scope:
            changed = copy.deepcopy(scope); changed[field] = None
            with self.subTest(field=field), self.assertRaises(g.GrantRejected):
                self.verify(self.packet(self.body(scope=changed)))

    def test_independently_expected_scope_must_still_be_complete_and_consistent(self):
        full = json.loads(self.scope)
        cases = [dict(input_manifest=dict(task_id='1'*32, attempt_id='3'*32),
                      worker=self.worker, runtime=self.runtime)]
        for field in full:
            changed = copy.deepcopy(full); changed.pop(field); cases.append(changed)
        changed = copy.deepcopy(full); changed['resource_profile']['process_limit'] += 1; cases.append(changed)
        changed = copy.deepcopy(full); changed['commands'][0]['argv'].append('other'); cases.append(changed)
        changed = copy.deepcopy(full); changed['input_manifest']['files'][1]['role'] = 'editable'; cases.append(changed)
        for scope in cases:
            with self.subTest(fields=list(scope)), self.assertRaises(g.GrantRejected):
                self.verify(self.packet(self.body(scope=scope)), expected_scope=g.canonical(scope))

    def test_changed_input_and_tests_rejected_before_scope(self):
        for name in self.contents:
            original = self.contents[name]; self.contents[name] += b'changed'
            with self.subTest(name=name), self.assertRaises(g.GrantRejected): self.prepare()
            self.contents[name] = original
        self.admission['files'][1]['role'] = 'editable'
        with self.assertRaises(g.GrantRejected): self.prepare()

    def test_resource_limits_strict_and_profile_digest_bound(self):
        for key, bad in [('process_limit', True), ('task_cpu_rate_percent', 0),
                         ('task_memory_bytes', None), ('output_bytes', 1048577),
                         ('artifact_files', 21), ('network_policy', 'nat')]:
            saved = self.profile[key]; self.profile[key] = bad
            with self.subTest(key=key), self.assertRaises(g.GrantRejected): self.prepare()
            self.profile[key] = saved
        old = self.scope; self.profile['process_limit'] += 1
        self.assertNotEqual(old, self.prepare())

    def test_worker_runtime_and_environment_strict(self):
        for key, bad in [('executable_path', 'python'), ('executable_path', '//host/share/python.exe'),
                         ('executable_path', 'C:/x/../python.exe'), ('executable_sha256', 'unknown')]:
            old = self.runtime[key]; self.runtime[key] = bad
            with self.subTest(key=key), self.assertRaises(g.GrantRejected): self.prepare()
            self.runtime[key] = old
        self.worker['image_sha256'] = 'f'*64
        with self.assertRaises(g.GrantRejected): self.prepare()
        self.worker['image_sha256'] = '7'*64
        with self.assertRaises(g.GrantRejected):
            g.prepare_scope(self.admission, self.contents, worker=self.worker, runtime=self.runtime,
                            resource_profile=self.profile, environment={'PATH': 'candidate'},
                            fixture_manifest_sha256='c'*64)

    def test_observation_mismatch_and_expiry_do_not_consume_attempt(self):
        registry = self.registry()
        for section in ['worker', 'runtime']:
            observed = copy.deepcopy(self.observed); observed[section][next(iter(observed[section]))] = 'changed'
            with self.assertRaises(g.GrantRejected): self.claim(registry, current_identity=observed)
        with self.assertRaises(g.GrantRejected): self.claim(registry, now_utc=1200)
        self.claim(registry)

    def test_same_grant_and_reissued_attempt_are_terminal_replays(self):
        registry = self.registry(); self.claim(registry)
        for p in [self.packet(), self.packet(self.body(grant_id='f'*32))]:
            with self.assertRaises(g.GrantRejected): self.claim(registry, p)
        other = self.registry(create=False)
        with self.assertRaises(g.GrantRejected): self.claim(other)

    def test_grant_id_cannot_be_reused_for_new_attempt(self):
        registry = self.registry(); self.claim(registry)
        self.admission['attempt_id'] = 'a'*32; self.scope = self.prepare()
        with self.assertRaises(g.GrantRejected): self.claim(registry)

    def test_attempt_id_cannot_be_reissued_under_another_task(self):
        registry = self.registry(); self.claim(registry)
        self.admission['task_id'] = 'a'*32; self.scope = self.prepare()
        with self.assertRaises(g.GrantRejected): self.claim(registry, self.packet(self.body(grant_id='f'*32)))

    def test_clock_resampled_before_reservation(self):
        registry = self.registry(); times = iter([1001, 1200])
        with self.assertRaises(g.GrantRejected): self.claim(registry, clock=lambda: next(times))
        self.assertIsNone(registry.inspect('1'*32, '3'*32))
        self.claim(registry)

    def test_restart_inspection_is_data_only(self):
        self.claim(self.registry())
        registry = self.registry(create=False)
        receipt = registry.inspect('1'*32, '3'*32)
        self.assertEqual(receipt.state, 'ATTEMPT_RESERVED')
        self.assertFalse(receipt.execution_authorized)
        self.assertIsNone(registry.inspect('1'*32, 'f'*32))

    def test_concurrent_duplicate_only_one_commit(self):
        first = self.registry(); second = self.registry(create=False)
        barrier = threading.Barrier(2); results = []
        def run(registry):
            barrier.wait()
            try: self.claim(registry); results.append('reserved')
            except g.GrantRejected: results.append('denied')
        threads = [threading.Thread(target=run, args=(r,)) for r in [first, second]]
        for t in threads: t.start()
        for t in threads: t.join(timeout=5)
        self.assertEqual(sorted(results), ['denied', 'reserved'])

    def test_unknown_schema_and_store_identity_refused(self):
        self.registry()
        with self.assertRaises(g.GrantRejected): self.registry(create=False, store_id='f'*32)
        with self.assertRaises(g.GrantRejected): self.registry(create=True)
        p = self.root/'unrelated.sqlite'
        with sqlite3.connect(p) as c: c.execute('CREATE TABLE private_data(x)')
        with self.assertRaises(g.GrantRejected): self.registry(path=p)

    def test_memory_and_weak_durability_refused(self):
        c = sqlite3.connect(':memory:'); self.connections.append(c)
        with self.assertRaises(g.GrantRejected):
            g.VerificationAttemptRegistry(c, store_id='e'*32, authority_domain='infrastructure_test', create=True)
        registry = self.registry()
        registry._connection.execute('PRAGMA synchronous=OFF')
        with self.assertRaises(g.GrantRejected): self.claim(registry)

    def test_caller_transaction_never_committed_or_rolled_back(self):
        registry = self.registry(); c = registry._connection; c.execute('BEGIN')
        with self.assertRaises(g.GrantRejected): self.claim(registry)
        self.assertTrue(c.in_transaction); c.rollback()
        self.claim(registry)

    def test_commit_interruption_never_returns_receipt_and_quarantines(self):
        for fault in ['before', 'after', 'suppressed']:
            with self.subTest(fault=fault):
                p = self.root/(fault+'.sqlite'); registry = self.registry(factory=FaultConnection, path=p)
                registry._connection.fault = fault
                with self.assertRaises(g.GrantRejected): self.claim(registry)
                registry._connection.fault = ''
                with self.assertRaises(g.GrantRejected): self.claim(registry)
                reopened = self.registry(create=False, path=p)
                receipt = reopened.inspect('1'*32, '3'*32)
                self.assertEqual(receipt is not None, fault == 'after')
                if fault == 'after':
                    with self.assertRaises(g.GrantRejected): self.claim(reopened)

    def test_locked_store_returns_no_receipt(self):
        registry = self.registry(); other = self.registry(create=False)
        other._connection.execute('BEGIN IMMEDIATE')
        with self.assertRaises(g.GrantRejected): self.claim(registry)
        other._connection.rollback()

    def test_asynchronous_commit_interruption_quarantines(self):
        for fault, error in [('interrupt_before', KeyboardInterrupt), ('interrupt_after', KeyboardInterrupt),
                             ('exit_after', SystemExit)]:
            with self.subTest(fault=fault):
                p = self.root/(fault+'.sqlite'); registry = self.registry(factory=FaultConnection, path=p)
                registry._connection.fault = fault
                with self.assertRaises(error): self.claim(registry)
                registry._connection.fault = ''
                self.assertFalse(registry._connection.in_transaction)
                with self.assertRaises(g.GrantRejected): registry.inspect('1'*32, '3'*32)
                reopened = self.registry(create=False, path=p)
                self.assertEqual(reopened.inspect('1'*32, '3'*32) is not None, fault != 'interrupt_before')

    def test_interrupted_begin_rolls_back_only_its_owned_transaction(self):
        registry = self.registry(factory=FaultConnection)
        registry._connection.interrupt_begin = True
        with self.assertRaises(KeyboardInterrupt): self.claim(registry)
        self.assertFalse(registry._connection.in_transaction)
        with self.assertRaises(g.GrantRejected): registry.inspect('1'*32, '3'*32)


if __name__ == '__main__':
    unittest.main()
