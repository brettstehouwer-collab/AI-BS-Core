"""Twelve bounded conflict/restart cases added after focused candidate review."""
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from backend.tests import test_crypto_com_acknowledgements_smoke as fixture
from core import crypto_com_acknowledgements as receipts
from core.crypto_execution_controls import ControlError


class CryptoAcknowledgementConflictSmoke(unittest.TestCase):
    setUp = fixture.CryptoAcknowledgementSmoke.setUp
    new_store = fixture.CryptoAcknowledgementSmoke.new_store
    capture = fixture.CryptoAcknowledgementSmoke.capture
    recover = fixture.CryptoAcknowledgementSmoke.recover
    reopen = fixture.CryptoAcknowledgementSmoke.reopen
    unchanged = fixture.CryptoAcknowledgementSmoke.unchanged

    def second(self, *, order_id=9007199254740995, request_id=8):
        response = dict(self.response, id=request_id, result=dict(self.response['result'], order_id=order_id))
        return self.box.capture(self.client_id, request_id=request_id, raw_response=json.dumps(response).encode())

    def held(self):
        with self.assertRaises(ControlError): self.recover(self.reopen())
        self.unchanged()

    def test_01_new_request_same_exchange_order_is_consistent(self):
        self.capture(); self.second()
        self.assertEqual(self.recover()['acknowledgement']['exchange_order_id'], '9007199254740995')
        self.assertEqual(list(self.box.root.glob('*.quarantine.json')), [])
        self.unchanged()

    def test_02_cross_request_exchange_identity_conflict_quarantined(self):
        self.capture(); self.second(order_id=9007199254740996)
        self.held()
        marker = json.loads(next(self.box.root.glob('*.quarantine.json')).read_text())
        self.assertEqual(marker['reason'], 'CLIENT_EXCHANGE_ORDER_CONFLICT')
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 2)

    def test_03_failed_quarantine_write_still_discovered_on_restart(self):
        self.capture()
        original = receipts.write_json_record
        def interrupted(path, record, **kwargs):
            if str(path).endswith('.quarantine.json'): raise OSError('synthetic marker failure')
            return original(path, record, **kwargs)
        with patch.object(receipts, 'write_json_record', side_effect=interrupted):
            with self.assertRaises(OSError): self.capture(self.raw + b' ')
        self.assertEqual(list(self.box.root.glob('*.quarantine.json')), [])
        self.held()
        self.assertEqual(len(list(self.box.root.glob('*.quarantine.json'))), 1)

    def test_04_orphan_conflicting_response_cannot_be_ignored(self):
        self.capture()
        original = receipts.write_json_record
        def interrupted(path, record, **kwargs):
            if str(path).endswith('.binding.json'): raise OSError('synthetic binding failure')
            return original(path, record, **kwargs)
        with patch.object(receipts, 'write_json_record', side_effect=interrupted):
            with self.assertRaises(OSError): self.second(order_id=9007199254740996)
        self.held()
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 2)

    def test_05_prior_verified_receipt_does_not_mask_later_conflict(self):
        self.capture(); self.recover()
        saved = next(self.box.root.glob('*.verified.json')); before = saved.read_bytes()
        self.second(order_id=9007199254740996)
        self.held()
        self.assertEqual(saved.read_bytes(), before)

    def test_06_quarantined_client_can_retain_more_evidence(self):
        self.capture(); self.second(order_id=9007199254740996); self.held()
        self.second(request_id=9)
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 3)
        self.held()

    def test_07_other_client_in_same_offline_store_is_separate(self):
        # Preserve the coordinator's global unresolved-submission barrier. This
        # separate-client case starts from a synthetic known OPEN first order.
        self.store.reconcile(self.client_id, exchange_order_id='9007199254740995',
                             state='OPEN', cumulative_quantity='0', authoritative=True)
        self.before = self.store.snapshot()
        self.capture(); self.second(order_id=9007199254740996); self.held()
        other = str(uuid4())
        self.store.prepare(other, symbol='CRO/USD', side='buy', quantity='1', limit_price='10', hard_stop='9', now_ms=1000)
        self.adapter.stage_limit(other, now_ms=1000)
        before = self.store.snapshot()
        response = dict(self.response, result=dict(self.response['result'], client_oid=other, order_id=12))
        self.box.capture(other, request_id=7, raw_response=json.dumps(response).encode())
        self.assertEqual(self.box.recover(other, request_id=7)['acknowledgement']['exchange_order_id'], '12')
        self.assertEqual(self.store.snapshot(), before)

    def test_08_malformed_other_request_is_not_silently_skipped(self):
        self.capture()
        self.box.capture(self.client_id, request_id=8, raw_response=b'{')
        self.held()

    def test_09_changed_scope_refused_without_financial_mutation(self):
        self.capture()
        scope = self.box.root / 'scope.json'
        data = json.loads(scope.read_text()); data['account_id'] = '9999'
        scope.write_text(json.dumps(data))
        with self.assertRaises(ControlError): self.reopen()
        self.unchanged()

    def test_10_unsafe_binding_reference_refused(self):
        self.capture()
        path = next(self.box.root.glob('*.binding.json'))
        data = json.loads(path.read_text())
        for value in ([], '../outside', 'z' * 64):
            data['input_sha256'] = value; path.write_text(json.dumps(data))
            self.held()

    def test_11_more_than_64_inputs_require_review(self):
        self.capture()
        for request_id in range(8, 72): self.second(request_id=request_id)
        self.assertEqual(len(list(self.box.root.glob('*.input.json'))), 65)
        self.held()

    def test_12_partial_verified_receipt_is_not_replaced(self):
        self.capture(); self.recover()
        path = next(self.box.root.glob('*.verified.json')); path.write_bytes(b'{')
        self.held()
        self.assertEqual(path.read_bytes(), b'{')


if __name__ == '__main__':
    unittest.main()
