"""Eleven new order-detail/precision cases over synthetic, temporary records."""
import json
import unittest
from backend.tests import test_crypto_com_adapter_smoke as fixtures
from core.crypto_execution_controls import ControlError, Held


class OrderDetailSmoke(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CryptoComAdapterSmoke()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.detail = dict(account_id='1234', client_oid=self.f.client, order_id='9007199254740995',
                           instrument_name='CRO_USD', side='BUY', order_type='LIMIT', quantity='1',
                           limit_price='10', cumulative_quantity='0', cumulative_value='0', status='ACTIVE')

    def replay(self, **changes):
        response = dict(id=2, code=0, method='private/get-order-detail', result=dict(self.detail, **changes))
        return self.f.adapter.replay_order_detail(self.f.client, response, request_id=2)

    def test_01_active_zero_becomes_open_without_money_change(self):
        before = self.f.balances()
        self.assertEqual(self.replay()['state'], 'OPEN')
        self.assertEqual(self.f.balances(), before)
        self.assertNotEqual(self.f.store.snapshot()['orders'][0]['reserve_amount'], '0')

    def test_02_pending_not_assumed_open(self):
        before = self.f.store.snapshot()
        self.assertEqual(self.replay(status='PENDING')['state'], 'PENDING_ACCEPTANCE')
        self.assertEqual(self.f.store.snapshot(), before)

    def test_03_partial_requires_corresponding_executed_fills(self):
        self.f.adapter.replay_trade(self.f.client, dict(self.f.trade, traded_quantity='0.4', fees='-0.004'))
        self.assertEqual(self.replay(cumulative_quantity='0.4', cumulative_value='4')['state'], 'PARTIAL')

    def test_04_filled_detail_cannot_fabricate_missing_fill(self):
        before = self.f.balances()
        with self.assertRaises(ControlError):
            self.replay(status='FILLED', cumulative_quantity='1', cumulative_value='10')
        self.assertEqual(self.f.balances(), before)
        self.assertNotEqual(self.f.store.snapshot()['orders'][0]['reserve_amount'], '0')

    def test_05_filled_detail_after_real_offline_fill(self):
        self.f.adapter.replay_trade(self.f.client, self.f.trade)
        self.assertEqual(self.replay(status='FILLED', cumulative_quantity='1', cumulative_value='10')['state'], 'FILLED')

    def test_06_cancelled_zero_releases_only_reservation(self):
        before = self.f.balances()
        self.assertEqual(self.replay(status='CANCELED')['state'], 'CANCELLED')
        self.assertEqual(self.f.store.snapshot()['orders'][0]['reserve_amount'], '0')
        self.assertEqual(self.f.balances(), before)

    def test_07_unknown_lifecycle_retains_reservation(self):
        before = self.f.store.snapshot()
        with self.assertRaises(ControlError):
            self.replay(status='EXPIRED')
        self.assertEqual(self.f.store.snapshot(), before)

    def test_08_account_and_instrument_cannot_change(self):
        for changes in [dict(account_id='other'), dict(instrument_name='BTC_USD'), dict(quantity='2')]:
            with self.assertRaises(ControlError):
                self.replay(**changes)

    def test_09_cost_mismatch_cannot_release_reserve(self):
        self.f.adapter.replay_trade(self.f.client, dict(self.f.trade, traded_quantity='0.4', fees='-0.004'))
        before = self.f.store.snapshot()
        with self.assertRaises(ControlError):
            self.replay(status='CANCELED', cumulative_quantity='0.4', cumulative_value='4.01')
        self.assertEqual(self.f.store.snapshot(), before)

    def test_10_full_supported_fee_precision_is_retained_pending(self):
        fees = '-999999999999999999.123456789012345678'
        with self.assertRaises(Held):
            self.f.adapter.replay_trade(self.f.client, dict(self.f.trade, fees=fees))
        payload = json.loads(self.f.store.snapshot()['fills'][0]['payload'])
        self.assertEqual(payload['fees']['USD'], fees[1:])
        self.assertEqual(self.f.balances(), [{'asset': 'USD', 'total': '100'}])

    def test_11_unknown_fee_credit_coverage_retained_pending(self):
        trade = dict(self.f.trade); del trade['fee_credits']
        with self.assertRaises(Held):
            self.f.adapter.replay_trade(self.f.client, trade)
        payload = json.loads(self.f.store.snapshot()['fills'][0]['payload'])
        self.assertFalse(payload['fees_complete'])
        self.assertEqual(self.f.balances(), [{'asset': 'USD', 'total': '100'}])


if __name__ == '__main__':
    unittest.main()
