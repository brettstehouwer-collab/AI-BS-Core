"""Durable transport infrastructure fixtures. Never invoke project bytes."""
import dataclasses
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import threading
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.core.coding_vm_transfer import prepare_vm_transfer
from isolated_workers.protocol import scoped_exchange as codec
from isolated_workers.protocol.retained_inbox import RetainedInbox
from isolated_workers.protocol.test_task_transfer import fixture, artifacts

EVIDENCE = ROOT / 'backups/transfer_lifecycle_20261026_record123/fixtures'


class InterruptedCommit(sqlite3.Connection):
    interruption = None
    committed_changes = 0

    def commit(self):
        if self.total_changes == self.committed_changes:
            return super().commit()
        failure, self.interruption = self.interruption, None
        if failure == 'before':
            raise OSError('synthetic interruption before commit')
        super().commit()
        self.committed_changes = self.total_changes
        if failure == 'after':
            raise OSError('synthetic lost commit acknowledgement')


class SessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module('isolated_workers.protocol.transfer_session')

    def setUp(self):
        self.root = EVIDENCE / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.connections = []
        self.nonce = 0
        self.key = b'synthetic-transport-fixture-key!!'
        self.admission, self.contents = fixture()
        self.plan = prepare_vm_transfer(self.admission, self.contents, self.admission,
                                        direction='host_to_guest')
        self.inbox_connection = self.connect('inbox.sqlite')
        self.inbox = RetainedInbox(self.inbox_connection, create=True)
        self.connection = self.connect('session.sqlite')
        self.session = self.open(create=True)

    def tearDown(self):
        for connection in self.connections:
            try:
                connection.close()
            except sqlite3.Error:
                pass

    def connect(self, name):
        connection = sqlite3.connect(self.root / name, factory=InterruptedCommit, timeout=2)
        self.connections.append(connection)
        return connection

    def open(self, create=False, **overrides):
        params = dict(worker='fixture-worker', owner='fixture-owner',
                      direction='host_to_guest', issued=1000, expires=1300, create=create)
        params.update(overrides)
        return self.module.TransferSession(self.connection, self.inbox, self.admission,
                                           self.plan.manifest_bytes, **params)

    def packet(self, files=None, kind='message', message='', policy=None):
        self.nonce += 1
        return codec.pack(self.key, policy or self.session.policy, kind, message,
                          files or {}, f'{self.nonce:032x}', 1000, 1200)

    def header(self):
        return self.session.receive(self.packet({self.plan.manifest_path:self.plan.manifest_bytes}),
                                    self.key, 1001)

    def parts(self):
        for path, data in self.plan.chunks.items():
            self.session.receive(self.packet({path:data}), self.key, 1001)

    def cancellation(self, **overrides):
        value = dict(transfer_id=self.session.inspect().transfer_id,
                     manifest_sha256=hashlib.sha256(self.plan.manifest_bytes).hexdigest())
        value.update(overrides)
        return json.dumps(value, sort_keys=True, separators=(',', ':'))

    def assert_data_only(self, receipt):
        self.assertFalse(receipt.worker_admitted)
        self.assertFalse(receipt.execution_authorized)
        self.assertFalse(receipt.apply_authorized)
        self.assertEqual(receipt.verification_status, 'not_run')

    def test_manifest_first_complete_and_restart_are_data_only(self):
        self.assertEqual(self.session.inspect().state, 'WAITING_MANIFEST')
        with self.assertRaises(ValueError):
            self.session.complete(1001)
        self.assertEqual(self.header().state, 'RECEIVING')
        first, data = next(iter(self.plan.chunks.items()))
        self.session.receive(self.packet({first:data}), self.key, 1001)
        with self.assertRaises(ValueError):
            self.session.complete(1001)
        for path, data in list(self.plan.chunks.items())[1:]:
            self.session.receive(self.packet({path:data}), self.key, 1001)
        self.assertEqual(self.session.inspect().state, 'RECEIVING')
        receipt = self.session.complete(1001)
        self.assertEqual(receipt.state, 'COMPLETE')
        self.assert_data_only(receipt)
        self.connection.close()
        self.connection = self.connect('session.sqlite')
        recovered = self.open()
        self.assertEqual(recovered.inspect(), receipt)
        self.assertEqual(recovered.read_complete().contents, self.contents)
        with self.assertRaises(ValueError):
            recovered.receive(self.packet(), self.key, 1001)

    def test_authentication_scope_and_expiry_reject_without_progress(self):
        raw = self.packet({self.plan.manifest_path:self.plan.manifest_bytes})
        for key, now in [(b'x'*32, 1001), (self.key, 1201), (self.key, 999)]:
            with self.assertRaises(ValueError):
                self.session.receive(raw, key, now)
        foreign = dataclasses.replace(self.session.policy, owner='another-owner')
        with self.assertRaises(ValueError):
            self.session.receive(self.packet(policy=foreign), self.key, 1001)
        self.assertEqual(self.inbox.usage()['packets'], 0)
        self.assertEqual(self.session.inspect().state, 'WAITING_MANIFEST')

    def test_part_before_manifest_retains_evidence_but_cannot_advance(self):
        path, data = next(iter(self.plan.chunks.items()))
        raw = self.packet({path:data})
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        self.assertEqual(self.inbox.usage()['packets'], 1)
        self.assertEqual(self.session.inspect().received_parts, ())
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        self.header()
        self.parts()
        self.assertEqual(self.session.complete(1001).state, 'COMPLETE')

    def test_malformed_wrong_and_duplicate_parts_do_not_replace_prior_bytes(self):
        self.header()
        path, data = next(iter(self.plan.chunks.items()))
        with self.assertRaises(ValueError):
            self.session.receive(self.packet({path:b'wrong bytes'}), self.key, 1001)
        raw = self.packet({path:data})
        self.session.receive(raw, self.key, 1001)
        for repeated in [raw, self.packet({path:data})]:
            with self.assertRaises(ValueError):
                self.session.receive(repeated, self.key, 1001)
        self.assertEqual(self.session.inspect().received_parts, (path,))
        with self.assertRaises(ValueError):
            self.session.receive(self.packet(dict(self.plan.chunks)), self.key, 1001)

    def test_bound_cancellation_is_terminal_and_preserves_partial_evidence(self):
        self.header()
        path, data = next(iter(self.plan.chunks.items()))
        self.session.receive(self.packet({path:data}), self.key, 1001)
        with self.assertRaises(ValueError):
            self.session.receive(self.packet(kind='cancel', message=self.cancellation(manifest_sha256='f'*64)), self.key, 1001)
        receipt = self.session.receive(self.packet(kind='cancel', message=self.cancellation()), self.key, 1001)
        self.assertEqual(receipt.state, 'CANCELLED')
        self.assertEqual(receipt.received_parts, (path,))
        self.assert_data_only(receipt)
        self.assertEqual(self.open().inspect(), receipt)
        for action in [lambda:self.session.complete(1001), self.session.read_complete,
                       lambda:self.session.receive(self.packet(), self.key, 1001)]:
            with self.assertRaises(ValueError):
                action()

    def test_lost_journal_commit_acknowledgement_is_inspectable_without_replay(self):
        raw = self.packet({self.plan.manifest_path:self.plan.manifest_bytes})
        self.connection.interruption = 'after'
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        self.assertEqual(self.open().inspect().state, 'RECEIVING')
        self.assertEqual(self.inbox.usage()['packets'], 1)
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)

    def test_commit_gap_keeps_retained_packet_and_requires_explicit_fresh_delivery(self):
        raw = self.packet({self.plan.manifest_path:self.plan.manifest_bytes})
        self.connection.interruption = 'before'
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        self.assertEqual(self.inbox.usage()['packets'], 1)
        self.assertEqual(self.open().inspect().state, 'WAITING_MANIFEST')
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        self.assertEqual(self.header().state, 'RECEIVING')

    def test_inbox_commit_ack_gap_does_not_advance_journal(self):
        self.inbox_connection.interruption = 'after'
        with self.assertRaises(ValueError):
            self.header()
        self.assertEqual(self.inbox.usage()['packets'], 1)
        self.assertEqual(self.open().inspect().state, 'WAITING_MANIFEST')

    def test_cancel_commit_gap_blocks_completion_until_explicit_retained_recovery(self):
        self.header()
        self.parts()
        raw = self.packet(kind='cancel', message=self.cancellation())
        nonce = f'{self.nonce:032x}'
        self.connection.interruption = 'before'
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        receipt = self.open().inspect()
        self.assertEqual(receipt.state, 'REVIEW_REQUIRED')
        self.assertIn((nonce, hashlib.sha256(raw).hexdigest()), receipt.pending_packets)
        with self.assertRaises(ValueError):
            self.session.complete(1001)
        with self.assertRaises(ValueError):
            self.session.receive(self.packet(), self.key, 1001)
        recovered = self.session.recover_cancellation(nonce, hashlib.sha256(raw).hexdigest())
        self.assertEqual(recovered.state, 'CANCELLED')
        self.assert_data_only(recovered)

    def test_completion_ack_gap_reopens_as_complete_without_execution(self):
        self.header()
        self.parts()
        self.connection.interruption = 'after'
        with self.assertRaises(ValueError):
            self.session.complete(1001)
        self.assertEqual(self.open().inspect().state, 'COMPLETE')
        self.assertEqual(self.open().read_complete().contents, self.contents)

    def test_expired_session_cannot_accept_or_complete(self):
        self.header()
        self.parts()
        with self.assertRaises(ValueError):
            self.session.complete(1300)
        self.assertEqual(self.session.inspect().state, 'RECEIVING')
        with self.assertRaises(ValueError):
            self.session.receive(self.packet(), self.key, 1300)

    def test_changed_scope_schema_or_caller_transaction_are_not_adopted(self):
        for override in [dict(owner='other'), dict(expires=1299), dict(worker='other')]:
            with self.assertRaises(ValueError):
                self.open(**override)
        self.connection.execute('CREATE TABLE unexpected(x)')
        self.connection.commit()
        with self.assertRaises(ValueError):
            self.session.inspect()
        self.connection.execute('BEGIN')
        with self.assertRaises(ValueError):
            self.session.inspect()
        self.assertTrue(self.connection.in_transaction)
        self.connection.rollback()

    def test_in_memory_and_shared_packet_journal_store_are_refused(self):
        prior = self.connection
        self.connection = sqlite3.connect(':memory:')
        self.connections.append(self.connection)
        with self.assertRaises(ValueError):
            self.open(create=True)
        self.connection = self.inbox_connection
        with self.assertRaises(ValueError):
            self.open(create=True)
        self.connection = prior

    def test_missing_or_corrupt_retained_provenance_prevents_inspection(self):
        self.header()
        self.inbox_connection.execute("UPDATE retained_packets_v1 SET packet=zeroblob(packet_bytes)")
        self.inbox_connection.commit()
        with self.assertRaises(ValueError):
            self.session.inspect()

    def test_forged_complete_state_with_missing_parts_is_not_a_completion_receipt(self):
        self.header()
        self.connection.execute("UPDATE transfer_session_state_v1 SET state='COMPLETE'")
        self.connection.commit()
        with self.assertRaises(ValueError):
            self.session.inspect()

    def test_malformed_unindexed_scope_requires_review_instead_of_foreign_skip(self):
        path, data = next(iter(self.plan.chunks.items()))
        raw = self.packet({path:data})
        self.inbox.receive(raw, self.key, self.session.policy, 1001)
        value = json.loads(raw)
        del value['body']['owner']
        corrupted = codec._canonical(value)
        self.inbox_connection.execute('UPDATE retained_packets_v1 SET packet=?,packet_sha256=?,packet_bytes=?',
                                      (corrupted, hashlib.sha256(corrupted).hexdigest(), len(corrupted)))
        self.inbox_connection.commit()
        self.assertEqual(self.session.inspect().state, 'REVIEW_REQUIRED')
        with self.assertRaises(ValueError):
            self.header()

    def test_structurally_valid_foreign_owner_cancel_does_not_cancel_this_transfer(self):
        foreign = dataclasses.replace(self.session.policy, owner='another-owner')
        raw = self.packet(kind='cancel', message=self.cancellation(), policy=foreign)
        self.inbox.receive(raw, self.key, foreign, 1001)
        self.assertEqual(self.session.inspect().state, 'WAITING_MANIFEST')
        self.assertEqual(self.header().state, 'RECEIVING')

    def test_retained_row_nonce_must_match_the_packet_nonce(self):
        path, data = next(iter(self.plan.chunks.items()))
        raw = self.packet({path:data})
        self.inbox.receive(raw, self.key, self.session.policy, 1001)
        self.inbox_connection.execute('UPDATE retained_packets_v1 SET nonce=?', ('f'*32,))
        self.inbox_connection.commit()
        self.assertEqual(self.session.inspect().state, 'REVIEW_REQUIRED')

    def test_retained_inventory_metadata_length_and_type_fail_closed(self):
        self.header()
        self.inbox_connection.execute('UPDATE retained_packets_v1 SET packet_sha256=?', ('a'*4096,))
        self.inbox_connection.commit()
        with self.assertRaises(ValueError):
            self.inbox.list_receipts()
        with self.assertRaises(ValueError):
            self.session.inspect()

    def test_large_file_contract_is_preserved_as_data(self):
        self.admission, self.contents = fixture({'source/Unicode_\u03bb.txt':b'x'*(2*1024*1024)})
        self.plan = prepare_vm_transfer(self.admission, self.contents, self.admission, direction='host_to_guest')
        self.inbox_connection = self.connect('large_inbox.sqlite')
        self.inbox = RetainedInbox(self.inbox_connection, create=True)
        self.connection = self.connect('large_session.sqlite')
        self.session = self.open(create=True)
        self.header()
        self.parts()
        self.session.complete(1001)
        self.assertEqual(self.session.read_complete().contents, self.contents)

    def test_guest_return_requires_unchanged_trusted_tests(self):
        returned = artifacts(self.admission, self.contents)
        self.plan = prepare_vm_transfer(returned, self.contents, self.admission, direction='guest_to_host')
        self.inbox_connection = self.connect('return_inbox.sqlite')
        self.inbox = RetainedInbox(self.inbox_connection, create=True)
        self.connection = self.connect('return_session.sqlite')
        self.session = self.open(create=True, direction='guest_to_host')
        for path, data in self.plan.transport_files.items():
            self.session.receive(self.packet({path:data}, kind='result'), self.key, 1001)
        self.session.complete(1001)
        self.assertEqual(self.session.read_complete().contents, self.contents)

    def test_complete_twenty_file_sixteen_mebibyte_contract_in_one_direction(self):
        extra = {f'large_{i}.txt':b'x'*(2*1024*1024) for i in range(7)}
        extra['last.txt'] = b'y'*(2*1024*1024-2)
        extra.update({f'empty_{i}.txt':b'' for i in range(10)})
        self.admission, self.contents = fixture(extra)
        self.plan = prepare_vm_transfer(self.admission, self.contents, self.admission, direction='host_to_guest')
        self.inbox_connection = self.connect('full_inbox.sqlite')
        self.inbox = RetainedInbox(self.inbox_connection, create=True)
        self.connection = self.connect('full_session.sqlite')
        self.session = self.open(create=True)
        self.header()
        self.parts()
        receipt = self.session.complete(1001)
        self.assertEqual(receipt.payload_bytes, 16*1024*1024)
        restored = self.session.read_complete()
        self.assertEqual(len(restored.contents), 20)
        self.assertEqual(restored.contents, self.contents)
        self.assertLess(self.inbox.usage()['payload_bytes'], 32*1024*1024)

    def test_recovery_never_calls_receive_or_unpack(self):
        self.header()
        raw = self.packet(kind='cancel', message=self.cancellation())
        nonce = f'{self.nonce:032x}'
        self.connection.interruption = 'before'
        with self.assertRaises(ValueError):
            self.session.receive(raw, self.key, 1001)
        with patch.object(codec, 'unpack', side_effect=AssertionError('must not replay')):
            with patch.object(self.inbox, 'receive', side_effect=AssertionError('must not replay')):
                self.assertEqual(self.session.inspect().state, 'REVIEW_REQUIRED')
                self.assertEqual(self.session.recover_cancellation(nonce, hashlib.sha256(raw).hexdigest()).state, 'CANCELLED')

    def test_cancel_and_complete_concurrent_journal_writers_have_one_terminal_winner(self):
        self.header()
        self.parts()
        raw = self.packet(kind='cancel', message=self.cancellation())
        barrier = threading.Barrier(2)
        results = []
        def run(cancel):
            packet_connection = sqlite3.connect(self.root/'inbox.sqlite', timeout=3)
            journal_connection = sqlite3.connect(self.root/'session.sqlite', timeout=3)
            try:
                inbox = RetainedInbox(packet_connection)
                session = self.module.TransferSession(journal_connection, inbox, self.admission,
                    self.plan.manifest_bytes, worker='fixture-worker', owner='fixture-owner',
                    direction='host_to_guest', issued=1000, expires=1300)
                barrier.wait(timeout=5)
                try:
                    receipt = session.receive(raw, self.key, 1001) if cancel else session.complete(1001)
                    results.append(receipt.state)
                except ValueError:
                    results.append('REFUSED')
            except BaseException as error:
                results.append(type(error).__name__)
            finally:
                journal_connection.close()
                packet_connection.close()
        threads = [threading.Thread(target=run, args=(cancel,)) for cancel in (False, True)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=8)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(results.count('REFUSED'), 1, results)
        self.assertEqual(sum(result in ('COMPLETE', 'CANCELLED') for result in results), 1, results)
        self.assertIn(self.session.inspect().state, ('COMPLETE', 'CANCELLED'))


if __name__ == '__main__':
    unittest.main()
