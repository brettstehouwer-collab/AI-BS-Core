"""Fifteen temporary-store receipt/restart cases; no network or private values."""
import json
from unittest import TestCase, main
from unittest.mock import patch
from uuid import uuid4

from backend.tests import test_crypto_com_adapter_smoke as fixture
from core import crypto_com_trade_inbox as inbox
from core.crypto_com_adapter import CryptoComOfflineAdapter
from core.crypto_execution_controls import ControlError, Held, OfflineExecutionCoordinator


class TradeInboxSmoke(TestCase):
    def setUp(self):
        fixture.CryptoComAdapterSmoke.setUp(self)
        self.box = inbox.CryptoComTradeInbox.create(self.adapter)
        self.before = self.store.snapshot()

    def capture(self, trades, *, request_id=9, previous=None, **query):
        raw = json.dumps({'id': request_id, 'method': 'private/get-trades', 'code': 0,
                          'result': {'data': trades}}, indent=2).encode() + b'\r\n'
        return self.box.capture(request_id=request_id, start_ns=query.get('start_ns', 1000000000),
            end_ns=query.get('end_ns', 2000000000), limit=query.get('limit', 100),
            instrument_name='CRO_USD', previous_checkpoint=previous, raw_response=raw)

    def reopen(self):
        adapter = CryptoComOfflineAdapter(OfflineExecutionCoordinator(self.path), exchange_account_id='1234')
        return inbox.CryptoComTradeInbox(adapter)

    def unchanged(self):
        self.assertEqual(self.store.snapshot(), self.before)

    def test_01_preserved_bytes_and_full_fill_checkpoint(self):
        reference = self.capture([self.trade])
        record = json.loads((self.box.root / (reference + '.input.json')).read_text())
        self.assertTrue(inbox.base64.b64decode(record['raw_base64']).endswith(b'\r\n'))
        result = self.box.apply(reference)
        self.assertEqual(result['fills'][0]['sequence'], 1)
        self.assertFalse(result['coverage_verified'])
        self.assertEqual(self.box.checkpoint()['last_applied_input'], reference)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'FILLED')

    def test_02_restart_duplicate_page_never_double_counts(self):
        reference = self.capture([self.trade]); first = self.box.apply(reference)
        before = self.store.snapshot()
        with patch.object(self.adapter, 'stage_limit', side_effect=AssertionError('resubmit forbidden')):
            self.assertEqual(self.reopen().apply(reference), first)
        self.assertEqual(self.store.snapshot(), before)

    def test_03_duplicate_fill_on_next_page_reuses_sequence(self):
        first = self.capture([self.trade]); self.box.apply(first)
        before = self.store.snapshot()
        second = self.capture([self.trade], request_id=10, previous=first)
        result = self.box.apply(second)
        self.assertEqual(result['fills'][0]['sequence'], 1)
        self.assertEqual(self.store.snapshot(), before)

    def test_04_unknown_order_preflight_applies_nothing(self):
        unknown = dict(self.trade, client_oid=str(uuid4()), trade_id='12')
        reference = self.capture([dict(self.trade, traded_quantity='0.4'), unknown])
        with self.assertRaises(ControlError): self.box.apply(reference)
        self.unchanged()
        self.assertEqual(self.box.pending_inputs()['inputs'], [reference])

    def test_05_partial_application_then_restart_retains_cursor(self):
        first = dict(self.trade, traded_quantity='0.4', fees='-0.004')
        second = dict(self.trade, trade_id='9007199254740994', traded_quantity='0.6', fees='-0.006')
        reference = self.capture([first, second])
        original = self.adapter.replay_trade
        def interrupted(client_id, trade):
            if trade['trade_id'] == second['trade_id']: raise OSError('synthetic interrupted delivery')
            return original(client_id, trade)
        with patch.object(self.adapter, 'replay_trade', side_effect=interrupted):
            with self.assertRaises(OSError): self.box.apply(reference)
        self.assertIsNone(self.box.checkpoint()['last_applied_input'])
        self.assertEqual(self.store.snapshot()['risk']['last_sequence'], 1)
        result = self.reopen().apply(reference)
        self.assertEqual([r['sequence'] for r in result['fills']], [1, 2])
        self.assertEqual(self.store.snapshot()['positions'][0]['quantity'], '1')

    def test_06_completion_write_failure_replays_committed_fill_once(self):
        reference = self.capture([self.trade]); original = inbox.write_json_record
        def interrupted(path, record, **kwargs):
            if str(path).endswith('.completed.json'): raise OSError('synthetic completion write failure')
            return original(path, record, **kwargs)
        with patch.object(inbox, 'write_json_record', side_effect=interrupted):
            with self.assertRaises(OSError): self.box.apply(reference)
        before = self.store.snapshot()
        self.assertIsNone(self.box.checkpoint()['last_applied_input'])
        self.reopen().apply(reference)
        self.assertEqual(self.store.snapshot(), before)

    def test_07_head_failure_recovery_never_replays_finance(self):
        reference = self.capture([self.trade]); original = inbox.write_json_record
        def interrupted(path, record, **kwargs):
            if path.name == 'head.json': raise OSError('synthetic head write failure')
            return original(path, record, **kwargs)
        with patch.object(inbox, 'write_json_record', side_effect=interrupted):
            with self.assertRaises(OSError): self.box.apply(reference)
        before = self.store.snapshot(); reopened = self.reopen()
        with patch.object(reopened.adapter, 'replay_trade', side_effect=AssertionError('already completed')):
            reopened.apply(reference)
        self.assertEqual(self.store.snapshot(), before)
        self.assertEqual(reopened.checkpoint()['last_applied_input'], reference)

    def test_08_active_page_blocks_branch_after_interruption(self):
        first = self.capture([self.trade]); second = self.capture([], request_id=10)
        with patch.object(self.adapter, 'replay_trade', side_effect=OSError('synthetic interrupt')):
            with self.assertRaises(OSError): self.box.apply(first)
        with self.assertRaises(ControlError): self.reopen().apply(second)
        self.unchanged()

    def test_09_changed_fill_held_and_new_checkpoint_not_advanced(self):
        first = self.capture([self.trade]); self.box.apply(first)
        balances = self.store.snapshot()['balances']
        second = self.capture([dict(self.trade, fees='-0.02')], request_id=10, previous=first)
        with self.assertRaises(Held): self.box.apply(second)
        self.assertEqual(self.box.checkpoint()['last_applied_input'], first)
        self.assertEqual(self.store.snapshot()['balances'], balances)

    def test_10_unsupported_fee_is_pending_with_no_checkpoint(self):
        reference = self.capture([dict(self.trade, fee_instrument_name='ETH')])
        with self.assertRaises(Held): self.box.apply(reference)
        self.assertIsNone(self.box.checkpoint()['last_applied_input'])
        self.assertEqual(self.store.snapshot()['balances'], self.before['balances'])
        self.assertEqual(self.store.snapshot()['fills'][0]['state'], 'PENDING')

    def test_11_empty_page_does_not_prove_history_complete(self):
        reference = self.capture([])
        self.assertFalse(self.box.apply(reference)['coverage_verified'])
        self.assertFalse(self.box.checkpoint()['coverage_verified'])
        self.unchanged()

    def test_12_limit_and_time_boundary_rejections_keep_evidence(self):
        for extra in ({'limit': 1}, {'end_ns': 1100000000}, {'start_ns': 1100000001}):
            trades = [self.trade, self.trade] if 'limit' in extra else [self.trade]
            reference = self.capture(trades, **extra)
            with self.assertRaises(ControlError): self.box.apply(reference)
        self.unchanged()

    def test_13_stale_page_and_input_corruption_refused(self):
        first = self.capture([]); stale = self.capture([self.trade], request_id=10)
        self.box.apply(first)
        with self.assertRaises(ControlError): self.box.apply(stale)
        path = self.box.root / (stale + '.input.json'); path.write_bytes(b'{')
        with self.assertRaises(ControlError): self.box.apply(stale)
        self.unchanged()

    def test_14_malformed_and_duplicate_json_not_applied(self):
        for raw in (b'{', b'{"id":9,"id":10}', b'{"extra":NaN}'):
            reference = self.box.capture(request_id=9, start_ns=1000000000, end_ns=2000000000,
                limit=100, instrument_name='CRO_USD', previous_checkpoint=None, raw_response=raw)
            with self.assertRaises(ControlError): self.box.apply(reference)
        self.unchanged()

    def test_15_completed_evidence_corruption_refused_before_mutation(self):
        reference = self.capture([self.trade]); self.box.apply(reference)
        before = self.store.snapshot()
        path = self.box.root / (reference + '.completed.json'); path.write_bytes(b'{}')
        with self.assertRaises(ControlError): self.reopen().apply(reference)
        self.assertEqual(self.store.snapshot(), before)


if __name__ == '__main__':
    main()
