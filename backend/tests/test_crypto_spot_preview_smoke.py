"""Fifteen arithmetic and mounted-source-route checks; no account or order I/O."""
from decimal import Decimal
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.crypto_execution_controls import ControlError
from core.crypto_spot_preview import preview_cro_spot
from routers.trading_router import router


class SpotPreviewSmoke(unittest.TestCase):
    def setUp(self):
        self.params = dict(budget_usdt='2.01', bid='10', ask='10.01', quantity_step='0.01',
            price_tick='0.01', minimum_notional_usd='1', usdt_usd_index='1',
            entry_fee_bps='50', exit_fee_bps='50', target_price='10.30', stop_price='9.80')

    def preview(self, **updates):
        return preview_cro_spot(**dict(self.params, **updates))

    def scenario(self, result, buy='USDT', sell='USDT'):
        return next(row for row in result['fee_currency_scenarios'] if row['entry_fee_asset']==buy and row['exit_fee_asset']==sell)

    def test_01_quantity_and_worst_cash_fit_all_in_budget(self):
        result = self.preview()
        self.assertEqual(result['entry']['quantity_cro'], '0.2')
        self.assertEqual(result['entry']['maximum_quote_debit_usdt'], '2.01')
        self.assertEqual(len(result['fee_currency_scenarios']), 4)
        self.assertLessEqual(Decimal(result['entry']['maximum_quote_debit_usdt']), Decimal(self.params['budget_usdt']))

    def test_02_base_buy_fee_preserves_unsellable_dust(self):
        case = self.scenario(self.preview(), buy='CRO')
        self.assertEqual(case['base_received_cro'], '0.199')
        self.assertEqual(case['sell_quantity_cro'], '0.19')
        self.assertEqual(case['residual_cro_after_assumed_exit'], '0.009')
        target = next(level for level in case['levels'] if level['assumed_execution']=='target')
        self.assertLess(Decimal(target['cash_pnl_excluding_residual_value_usdt']), 0)
        self.assertGreater(Decimal(target['equity_pnl_including_unsold_residual_usdt']), 0)

    def test_03_base_sell_fee_never_oversells_holdings(self):
        for case in self.preview()['fee_currency_scenarios']:
            debit = Decimal(case['sell_quantity_cro']) * (Decimal('1.005') if case['exit_fee_asset']=='CRO' else 1)
            self.assertLessEqual(debit, Decimal(case['base_received_cro']))
            self.assertGreaterEqual(Decimal(case['residual_cro_after_assumed_exit']), 0)

    def test_04_quote_fee_cash_math_known_example(self):
        case = self.scenario(self.preview())
        target = next(level for level in case['levels'] if level['assumed_execution']=='target')
        self.assertEqual(target['cash_received_usdt'], '2.0497')
        self.assertEqual(target['cash_pnl_excluding_residual_value_usdt'], '0.0397')
        self.assertEqual(case['cash_break_even_price_excluding_residual'], '10.11')

    def test_05_minimum_is_not_rounded_above_budget(self):
        with self.assertRaises(ControlError):
            self.preview(budget_usdt='1', bid='0.04', ask='0.04001', price_tick='0.00001', quantity_step='1', target_price=None, stop_price=None)

    def test_06_usdt_index_conversion_changes_minimum(self):
        with self.assertRaises(ControlError):
            self.preview(budget_usdt='1.10', bid='0.04', ask='0.04001', price_tick='0.00001', quantity_step='1',
                         usdt_usd_index='0.9', target_price=None, stop_price=None)

    def test_07_invalid_target_and_stop_not_silently_adjusted(self):
        for updates in ({'target_price':'10'}, {'stop_price':'10.01'}, {'stop_price':'9.805'}):
            with self.assertRaises(ControlError): self.preview(**updates)

    def test_08_stop_exit_below_minimum_is_visible(self):
        result = self.preview(stop_price='4')
        self.assertIn('SOME_EXIT_SCENARIOS_BELOW_MINIMUM', result['blocking_checks'])
        self.assertFalse(result['protection_verified'])
        self.assertTrue(result['assumed_exit_prices_are_not_guaranteed_fills_or_maximum_losses'])

    def test_09_missing_risk_choices_stay_unset(self):
        result = self.preview(target_price=None, stop_price=None)
        for flag in ['MISSING_TARGET','MISSING_STOP','MISSING_EXPOSURE_CAP','MISSING_DAILY_LOSS_BUDGET']:
            self.assertIn(flag, result['blocking_checks'])

    def test_10_supplied_choices_never_establish_live_readiness(self):
        result = self.preview(max_exposure_usdt='10', daily_loss_budget_usdt='1')
        self.assertFalse(result['ready_for_live'])
        self.assertFalse(result['live_dispatch_enabled'])
        self.assertFalse(result['supplied_facts_independently_verified'])
        self.assertEqual(result['orders_sent'], 0)

    def test_11_tiny_profit_target_cannot_hide_fee_loss(self):
        result = self.preview(target_price='10.01')
        self.assertIn('TARGET_CASH_PROFIT_NOT_POSITIVE_IN_SOME_FEE_SCENARIOS', result['blocking_checks'])

    def test_12_proposed_exposure_cap_is_checked(self):
        result = self.preview(max_exposure_usdt='1.99')
        self.assertIn('PROPOSED_EXPOSURE_CAP_EXCEEDED', result['blocking_checks'])

    def test_13_invalid_numeric_and_crossed_book_refused(self):
        for updates in ({'budget_usdt':2.0},{'bid':'NaN'},{'entry_fee_bps':'10000'}, {'ask':'9.99'},
                        {'bid':'10.001'}, {'quantity_step':'0'}, {'daily_loss_budget_usdt':'-1'}):
            with self.assertRaises(ControlError): self.preview(**updates)

    def test_14_mounted_admin_preview_and_unchanged_order_hold(self):
        app = FastAPI(); app.include_router(router)
        with patch('security.host_control_access.get_admin_principal', return_value='local_admin'):
            with TestClient(app) as client:
                response = client.post('/api/trading/preview', json=self.params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['scope'], 'ARITHMETIC_PREVIEW_NOT_ACCOUNT_OR_ORDER')
                self.assertEqual(response.headers['cache-control'], 'private, no-store')
                self.assertFalse(response.json()['live_dispatch_enabled'])
                held = client.post('/api/trading/order', json={'pair':'CRO/USDT','action':'BUY','amount_usd':2})
                self.assertEqual(held.status_code, 503)

    def test_15_auth_precedes_parse_and_schema_is_strict(self):
        app = FastAPI(); app.include_router(router)
        with TestClient(app) as client:
            with patch('security.host_control_access.get_admin_principal', return_value=None):
                denied = client.post('/api/trading/preview', content=b'{')
                self.assertEqual(denied.status_code, 403)
            with patch('security.host_control_access.get_admin_principal', return_value='local_admin'):
                for updates in ({'budget_usdt':2.0}, {'send_order':True}):
                    response = client.post('/api/trading/preview', json=dict(self.params, **updates))
                    self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    unittest.main()
