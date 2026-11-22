"""Fourteen offline restart/evidence cases; no keys, network or live records."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from core import crypto_com_acknowledgements as receipts
from core.crypto_com_adapter import CryptoComOfflineAdapter
from core.crypto_execution_controls import ControlError, Instrument, OfflineExecutionCoordinator


class CryptoAcknowledgementSmoke(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'replay.sqlite'
        self.client_id = str(uuid4())
        self.store, self.adapter = self.new_store(self.path)
        self.box = receipts.CryptoComAcknowledgements.create(self.adapter)
        self.response = {'id': 7, 'method': 'private/create-order', 'code': 0,
                         'result': {'client_oid': self.client_id, 'order_id': 9007199254740995}}
        self.raw = (json.dumps(self.response, indent=2) + '\r\n').encode()
        self.before = self.store.snapshot()

    def new_store(self, path):
        store = OfflineExecutionCoordinator.create(path, account='cryptocom-exchange:1234', quote='USD', cash='100')
        store.quote_market(Instrument('CRO', 'USD'), bid='10', ask='10', observed_ms=1000, now_ms=1000)
        store.prepare(self.client_id, symbol='CRO/USD', side='buy', quantity='1', limit_price='10', hard_stop='9', now_ms=1000)
        adapter = CryptoComOfflineAdapter(store, exchange_account_id='1234')
        adapter.stage_limit(self.client_id, now_ms=1000)
        return store, adapter

    def capture(self, raw=None):
        return self.box.capture(self.client_id, request_id=7, raw_response=self.raw if raw is None else raw)

    def recover(self, box=None):
        return (box or self.box).recover(self.client_id, request_id=7)

    def reopen(self):
        adapter = CryptoComOfflineAdapter(OfflineExecutionCoordinator(self.path), exchange_account_id='1234')
        return receipts.CryptoComAcknowledgements(adapter)

    def unchanged(self):
        self.assertEqual(self.store.snapshot(), self.before)

    def test_01_restart_recovers_exact_bytes_without_resend(self):
        self.assertTrue(self.capture())
        reopened = self.reopen()
        with patch.object(reopened.adapter, 'stage_limit', side_effect=AssertionError('resubmission forbidden')):
            result = self.recover(reopened)
        self.assertFalse(result['live_dispatch_enabled'])
        self.assertFalse(result['acknowledgement']['matching_engine_acceptance_verified'])
        self.assertEqual(result['acknowledgement']['recovery_action'], 'LOOKUP_ONLY_NEVER_RESEND')
        record = json.loads(next(self.box.root.glob('*.input.json')).read_text())
        self.assertEqual(receipts.base64.b64decode(record['raw_base64']), self.raw)
        self.assertEqual(self.recover(), result)
        self.unchanged()

    def test_02_identical_capture_reuses_immutable_evidence(self):
        self.capture(); before = {p.name: p.read_bytes() for p in self.box.root.iterdir()}
        self.assertFalse(self.capture())
        self.assertEqual({p.name: p.read_bytes() for p in self.box.root.iterdir()}, before)
        self.unchanged()

    def test_03_changed_response_retained_without_rebinding(self):
        self.capture()
        binding = next(self.box.root.glob('*.binding.json')); before = binding.read_bytes()
        changed = dict(self.response, result=dict(self.response['result'], order_id=9007199254740996))
        with self.assertRaises(ControlError):
            self.capture(json.dumps(changed).encode())
        self.assertEqual(binding.read_bytes(), before)
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 2)
        with self.assertRaises(ControlError): self.recover(self.reopen())
        self.assertEqual(len(list(self.box.root.glob('*.quarantine.json'))), 1)
        self.unchanged()

    def test_04_malformed_original_retained_before_parsing(self):
        self.capture(b'\xffnot-json')
        with self.assertRaises(ControlError): self.recover()
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 1)
        self.assertEqual(list(self.box.root.glob('*.verified.json')), [])
        self.unchanged()

    def test_05_duplicate_json_members_refused(self):
        raw = self.raw.replace(b'"code": 0', b'"code": 9, "code": 0')
        self.capture(raw)
        with self.assertRaises(ControlError): self.recover()
        self.unchanged()

    def test_06_nonfinite_json_refused(self):
        self.capture(self.raw.replace(b'"code": 0', b'"extra": NaN, "code": 0'))
        with self.assertRaises(ControlError): self.recover()
        self.unchanged()

    def test_07_wrong_request_correlation_retained(self):
        self.capture(json.dumps(dict(self.response, id=8)).encode())
        with self.assertRaises(ControlError): self.recover()
        self.unchanged()

    def test_08_wrong_client_correlation_retained(self):
        response = dict(self.response, result=dict(self.response['result'], client_oid=str(uuid4())))
        self.capture(json.dumps(response).encode())
        with self.assertRaises(ControlError): self.recover()
        self.unchanged()

    def test_09_copied_sidecar_rejected_by_other_store(self):
        self.capture()
        _, other = self.new_store(self.path.with_name('other.sqlite'))
        shutil.copytree(self.box.root, other.coordinator.path.with_name('other.sqlite.acks'))
        with self.assertRaises(ControlError): receipts.CryptoComAcknowledgements(other)
        self.unchanged()

    def test_10_modified_input_checksum_refused(self):
        self.capture()
        entry = next(self.box.root.glob('*.input.json'))
        record = json.loads(entry.read_text()); record['raw_bytes'] += 1
        entry.write_text(json.dumps(record))
        with self.assertRaises(ControlError): self.recover()
        self.unchanged()

    def test_11_interruption_after_input_preserves_orphan(self):
        original = receipts.write_json_record
        def interrupted(path, record, **kwargs):
            if str(path).endswith('.binding.json'): raise OSError('synthetic interrupted binding')
            return original(path, record, **kwargs)
        with patch.object(receipts, 'write_json_record', side_effect=interrupted):
            with self.assertRaises(OSError): self.capture()
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 1)
        reopened = self.reopen()
        with self.assertRaises(FileNotFoundError): self.recover(reopened)
        self.assertTrue(reopened.capture(self.client_id, request_id=7, raw_response=self.raw))
        self.recover(reopened); self.unchanged()

    def test_12_failed_verification_write_retains_input(self):
        self.capture()
        original = receipts.write_json_record
        def interrupted(path, record, **kwargs):
            if str(path).endswith('.verified.json'): raise OSError('synthetic verification write failure')
            return original(path, record, **kwargs)
        with patch.object(receipts, 'write_json_record', side_effect=interrupted):
            with self.assertRaises(OSError): self.recover()
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 1)
        self.recover(self.reopen()); self.unchanged()

    def test_13_partial_binding_is_not_overwritten(self):
        self.capture()
        binding = next(self.box.root.glob('*.binding.json')); binding.write_bytes(b'{')
        with self.assertRaises(ControlError): self.capture()
        self.assertEqual(binding.read_bytes(), b'{')
        self.unchanged()

    def test_14_input_bounds_before_evidence_write(self):
        before = set(self.box.root.iterdir())
        for request_id, raw in ((True, self.raw), (-1, self.raw), (7, b''), (7, b'x' * (receipts.MAX_RESPONSE_BYTES + 1))):
            with self.assertRaises(ControlError):
                self.box.capture(self.client_id, request_id=request_id, raw_response=raw)
        self.assertEqual({p for p in self.box.root.iterdir() if p.name != 'receipts.lock'}, before)
        self.unchanged()


if __name__ == '__main__':
    unittest.main()
