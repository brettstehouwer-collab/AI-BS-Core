"""Ten focused followups for risk-budget disclosure; no account or order I/O."""
import unittest
from unittest.mock import patch
from decimal import Decimal
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.tests import test_crypto_spot_preview_smoke as fixture
from core.crypto_spot_preview import preview_cro_spot
from core.crypto_execution_controls import ControlError
from routers.trading_router import router


class SpotRiskSmoke(unittest.TestCase):
    setUp = fixture.SpotPreviewSmoke.setUp
    preview = fixture.SpotPreviewSmoke.preview

    def test_01_missing_daily_budget_is_explicit(self):
        result = self.preview()
        self.assertIsNone(result['risk_choices']['daily_loss_budget'])
        self.assertIn('MISSING_DAILY_LOSS_BUDGET', result['blocking_checks'])
        self.assertIn('DAILY_LOSS_STATE_UNVERIFIED', result['blocking_checks'])

    def test_02_chosen_daily_budget_is_echoed_not_enforced(self):
        result = self.preview(daily_loss_budget_usdt='1')
        self.assertEqual(result['risk_choices']['daily_loss_budget'], '1')
        self.assertFalse(result['risk_budget_evaluation']['daily_cutoff_enforced'])

    def test_03_single_stop_exceeding_daily_budget_warns(self):
        result = self.preview(daily_loss_budget_usdt='0.01')
        self.assertIn('ONE_STOP_SCENARIO_EXCEEDS_DAILY_LOSS_BUDGET', result['blocking_checks'])

    def test_04_missing_stop_never_reports_zero_loss(self):
        result = self.preview(stop_price=None, daily_loss_budget_usdt='1')
        self.assertIsNone(result['risk_budget_evaluation']['maximum_stop_equity_loss_under_supplied_assumptions_usdt'])
        self.assertIn('MISSING_STOP', result['blocking_checks'])

    def test_05_cash_shortfall_is_distinct_from_marked_dust_loss(self):
        evaluation = self.preview()['risk_budget_evaluation']
        cash = Decimal(evaluation['maximum_stop_cash_shortfall_under_supplied_assumptions_usdt'])
        equity = Decimal(evaluation['maximum_stop_equity_loss_under_supplied_assumptions_usdt'])
        self.assertGreater(cash, equity)
        self.assertEqual(equity, Decimal('0.0598'))

    def test_06_budget_does_not_invent_current_daily_state(self):
        result = self.preview(daily_loss_budget_usdt='100')
        self.assertFalse(result['risk_budget_evaluation']['current_day_losses_and_remaining_budget_verified'])
        self.assertFalse(result['ready_for_live'])

    def test_07_zero_fee_stop_math_still_respects_ticks(self):
        result = self.preview(budget_usdt='2', entry_fee_bps='0', exit_fee_bps='0')
        self.assertEqual(result['risk_budget_evaluation']['maximum_stop_equity_loss_under_supplied_assumptions_usdt'], '0.04')

    def test_08_invalid_budget_rejected(self):
        for value in ('0','-1','NaN',1.0):
            with self.assertRaises(ControlError): self.preview(daily_loss_budget_usdt=value)

    def test_09_long_supported_price_precision_keeps_context(self):
        params = dict(self.params, bid='123456789012345678.123456789012345678',
            ask='123456789012345678.123456789012345679', price_tick='0.000000000000000001',
            budget_usdt='1000000000000000000', quantity_step='0.000000000000000001', target_price=None, stop_price=None)
        result = preview_cro_spot(**params)
        self.assertFalse(result['ready_for_live'])

    def test_10_source_route_discloses_risk_state(self):
        app=FastAPI(); app.include_router(router)
        with patch('security.host_control_access.get_admin_principal', return_value='local_admin'):
            with TestClient(app) as client:
                response=client.post('/api/trading/preview', json=dict(self.params,daily_loss_budget_usdt='0.01'))
                self.assertEqual(response.status_code,200)
                self.assertFalse(response.json()['risk_budget_evaluation']['daily_cutoff_enforced'])
                self.assertIn('ONE_STOP_SCENARIO_EXCEEDS_DAILY_LOSS_BUDGET',response.json()['blocking_checks'])


if __name__=='__main__': unittest.main()
