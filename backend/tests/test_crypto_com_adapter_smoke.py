"""Fourteen temporary-store integration cases; no credentials or exchange I/O."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from core.crypto_com_adapter import CryptoComOfflineAdapter
from core.crypto_execution_controls import ControlError, Held, Instrument, OfflineExecutionCoordinator


class CryptoComAdapterSmoke(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'replay.sqlite'
        self.store = OfflineExecutionCoordinator.create(self.path, account='cryptocom-exchange:1234', quote='USD', cash='100')
        self.store.quote_market(Instrument('CRO', 'USD'), bid='10', ask='10', observed_ms=1000, now_ms=1000)
        self.client = str(uuid4())
        self.store.prepare(self.client, symbol='CRO/USD', side='buy', quantity='1', limit_price='10', hard_stop='9', now_ms=1000)
        self.adapter = CryptoComOfflineAdapter(self.store, exchange_account_id='1234')
        self.staged = self.adapter.stage_limit(self.client, now_ms=1000)
        self.trade = dict(account_id='1234', journal_type='TRADING', trade_id='9007199254740993',
                          order_id='9007199254740995', client_oid=self.client, side='BUY',
                          instrument_name='CRO_USD', traded_quantity='1', traded_price='10',
                          fees='-0.01', fee_credits='0', fee_instrument_name='USD', create_time=1100)

    def balances(self):
        return self.store.snapshot()['balances']

    def pending(self, trade):
        before = self.balances()
        with self.assertRaises(Held):
            self.adapter.replay_trade(self.client, trade)
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['balances'], before)
        self.assertEqual(snapshot['fills'][0]['state'], 'PENDING')
        self.assertEqual(snapshot['risk']['halted'], 1)

    def test_01_staged_limit_is_decimal_and_held(self):
        self.assertEqual(self.staged['params'], dict(instrument_name='CRO_USD', side='BUY', type='LIMIT',
                         quantity='1', price='10', client_oid=self.client, time_in_force='GOOD_TILL_CANCEL'))
        self.assertFalse(self.staged['live_dispatch_enabled'])
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'SUBMITTING')
        self.assertEqual(self.balances(), [{'asset': 'USD', 'total': '100'}])

    def test_02_ack_does_not_imply_acceptance_or_fill(self):
        before = self.store.snapshot()
        response = dict(id=9, code=0, method='private/create-order', result=dict(order_id=9007199254740995, client_oid=self.client))
        ack = self.adapter.inspect_acknowledgement(self.client, response, request_id=9)
        self.assertEqual(ack['exchange_order_id'], '9007199254740995')
        self.assertFalse(ack['matching_engine_acceptance_verified'])
        self.assertEqual(self.store.snapshot(), before)

    def test_03_wrong_ack_correlation_rejected(self):
        response = dict(id=9, code=0, method='private/create-order', result=dict(order_id='7', client_oid=str(uuid4())))
        with self.assertRaises(ControlError):
            self.adapter.inspect_acknowledgement(self.client, response, request_id=9)
        response['result']['client_oid'] = self.client
        with self.assertRaises(ControlError):
            self.adapter.inspect_acknowledgement(self.client, response, request_id=10)

    def test_04_partial_then_full_fill_actual_fees(self):
        first = dict(self.trade, traded_quantity='0.4', fees='-0.004')
        self.assertTrue(self.adapter.replay_trade(self.client, first))
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'PARTIAL')
        second = dict(self.trade, trade_id='9007199254740994', traded_quantity='0.6', fees='-0.006', create_time=1200)
        self.assertTrue(self.adapter.replay_trade(self.client, second))
        snapshot = self.store.snapshot()
        self.assertEqual(snapshot['orders'][0]['state'], 'FILLED')
        self.assertEqual({r['asset']: r['total'] for r in snapshot['balances']}, {'CRO': '1', 'USD': '89.99'})
        self.assertEqual(snapshot['positions'][0]['basis'], '10.01')

    def test_05_restart_duplicate_does_not_double_count(self):
        self.adapter.replay_trade(self.client, self.trade)
        before = self.store.snapshot()
        reopened = CryptoComOfflineAdapter(OfflineExecutionCoordinator(self.path), exchange_account_id='1234')
        self.assertFalse(reopened.replay_trade(self.client, self.trade))
        self.assertEqual(self.store.snapshot(), before)

    def test_06_conflicting_duplicate_retains_balances(self):
        self.adapter.replay_trade(self.client, self.trade)
        before = self.balances()
        with self.assertRaises(Held):
            self.adapter.replay_trade(self.client, dict(self.trade, fees='-0.02'))
        self.assertEqual(self.balances(), before)
        self.assertEqual(self.store.snapshot()['risk']['reason'], 'FILL_ID_CONFLICT')

    def test_07_missing_fee_not_assumed_zero(self):
        trade = dict(self.trade); del trade['fees']
        with self.assertRaises(ControlError):
            self.adapter.replay_trade(self.client, trade)
        self.assertEqual(self.store.snapshot()['fills'], [])

    def test_08_third_currency_fee_retained_pending(self):
        self.pending(dict(self.trade, fee_instrument_name='ETH'))

    def test_09_rebate_not_converted_to_deduction(self):
        self.pending(dict(self.trade, fees='0.01'))
        payload = json.loads(self.store.snapshot()['fills'][0]['payload'])
        self.assertEqual(payload['fees'], {'USD': '-0.01'})

    def test_10_credits_and_unknown_credit_coverage_held(self):
        self.pending(dict(self.trade, fee_credits='-0.01'))
        # Independent pure rejection coverage does not reset or unhalt that store.
        trade = dict(self.trade); del trade['fee_instrument_name']
        with self.assertRaises(ControlError):
            self.adapter.replay_trade(self.client, trade)

    def test_11_account_binding_required(self):
        with self.assertRaises(ControlError):
            CryptoComOfflineAdapter(self.store, exchange_account_id='5678')
        with self.assertRaises(ControlError):
            self.adapter.replay_trade(self.client, dict(self.trade, account_id='5678'))
        self.assertEqual(self.store.snapshot()['fills'], [])

    def test_12_intent_and_spot_identity_required(self):
        for changed in [dict(side='SELL'), dict(instrument_name='BTC_USD'), dict(client_oid=str(uuid4())), dict(isolation_id='margin-1')]:
            with self.assertRaises(ControlError):
                self.adapter.replay_trade(self.client, dict(self.trade, **changed))
        self.assertEqual(self.store.snapshot()['fills'], [])

    def test_13_decimal_and_timestamp_validation(self):
        for changed in [dict(traded_price='NaN'), dict(traded_price=10.0), dict(order_id=9007199254740996.0), dict(create_time_ns=1200000000)]:
            with self.assertRaises(ControlError):
                self.adapter.replay_trade(self.client, dict(self.trade, **changed))
        self.assertEqual(self.store.snapshot()['fills'], [])

    def test_14_uncertain_restart_never_resubmits(self):
        self.store.mark_unknown(self.client, 'TIMEOUT')
        reopened = CryptoComOfflineAdapter(OfflineExecutionCoordinator(self.path), exchange_account_id='1234')
        with self.assertRaises(ControlError):
            reopened.stage_limit(self.client, now_ms=1200)
        self.assertEqual(self.store.recovery_orders()[0]['recovery_action'], 'LOOKUP_ONLY_NEVER_RESEND')
        self.assertEqual(self.store.snapshot()['orders'][0]['state'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
