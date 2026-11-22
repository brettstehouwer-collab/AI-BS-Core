"""Ten separate trigger/limit minimum arithmetic cases; no order authority."""
import copy
from decimal import Decimal
import unittest

from core.crypto_execution_controls import ControlError
from core.crypto_spot_preview import preview_cro_spot
from core.crypto_spot_protection import review_cro_protection


class StopLimitMinimumSmoke(unittest.TestCase):
    def setUp(self):
        self.preview = preview_cro_spot(budget_usdt='2', bid='0.1000', ask='0.1001',
            quantity_step='0.1', price_tick='0.0001', minimum_notional_usd='1',
            usdt_usd_index='1', entry_fee_bps='25', exit_fee_bps='50',
            stop_price='0.0980', daily_loss_budget_usdt='1')

    def review(self, **updates):
        args = dict(stop_type='STOP_LIMIT', trigger_reference_type='LAST_PRICE',
            stop_limit_price='0.0400', price_tick='0.0001',
            minimum_notional_usd='1', usdt_usd_index='1')
        return review_cro_protection(self.preview, **dict(args, **updates))

    def test_01_lower_limit_can_fail_while_trigger_passes(self):
        result = self.review()
        self.assertTrue(all(case['stop_minimum_at_assumed_price'] for case in result['fee_currency_cases']))
        self.assertTrue(all(case['stop_limit_minimum_at_assumed_price'] is False for case in result['fee_currency_cases']))
        self.assertIn('STOP_LIMIT_EXECUTION_BELOW_MINIMUM_IN_SOME_SCENARIOS', result['blocking_checks'])
        self.assertIs(result['trigger_minimum_is_not_limit_minimum'], True)

    def test_02_exact_minimum_boundary_is_inclusive(self):
        result = self.review(stop_limit_price='0.0500', minimum_notional_usd='0.995')
        case = next(c for c in result['fee_currency_cases'] if c['entry_fee_asset']=='USDT' and c['exit_fee_asset']=='USDT')
        self.assertEqual(Decimal(case['sell_quantity_cro'])*Decimal('0.0500'), Decimal('0.995'))
        self.assertIs(case['stop_limit_minimum_at_assumed_price'], True)

    def test_03_each_fee_case_uses_its_own_sell_quantity(self):
        result = self.review(stop_limit_price='0.0500', minimum_notional_usd='0.99')
        facts = []
        for case in result['fee_currency_cases']:
            expected = Decimal(case['sell_quantity_cro'])*Decimal('0.0500') >= Decimal('0.99')
            self.assertEqual(case['stop_limit_minimum_at_assumed_price'], expected)
            facts.append(expected)
        self.assertIn(True, facts)
        self.assertIn(False, facts)

    def test_04_usdt_usd_index_affects_execution_minimum(self):
        low = self.review(stop_limit_price='0.0500', usdt_usd_index='0.5')
        high = self.review(stop_limit_price='0.0500', usdt_usd_index='2')
        self.assertTrue(all(c['stop_limit_minimum_at_assumed_price'] is False for c in low['fee_currency_cases']))
        self.assertTrue(all(c['stop_limit_minimum_at_assumed_price'] is True for c in high['fee_currency_cases']))

    def test_05_missing_rules_are_unknown_not_passed(self):
        result = self.review(minimum_notional_usd=None, usdt_usd_index=None)
        self.assertIs(result['stop_limit_minimum_rule_inputs_supplied'], False)
        self.assertTrue(all(c['stop_limit_minimum_at_assumed_price'] is None for c in result['fee_currency_cases']))
        self.assertIn('STOP_LIMIT_EXECUTION_MINIMUM_UNVERIFIED', result['blocking_checks'])

    def test_06_partial_or_nonpositive_rules_rejected(self):
        for update in ({'minimum_notional_usd':None}, {'usdt_usd_index':None},
                       {'minimum_notional_usd':'0'}, {'usdt_usd_index':'-1'}):
            with self.subTest(update=update), self.assertRaises(ControlError):
                self.review(**update)

    def test_07_float_rule_inputs_rejected(self):
        for update in ({'minimum_notional_usd':1.0}, {'usdt_usd_index':1.0}):
            with self.subTest(update=update), self.assertRaises(ControlError):
                self.review(**update)

    def test_08_stop_market_minimum_and_authority_unchanged(self):
        result = self.review(stop_type='STOP_LOSS', stop_limit_price=None)
        baseline = review_cro_protection(self.preview, stop_type='STOP_LOSS', trigger_reference_type='LAST_PRICE')
        self.assertIs(result['trigger_minimum_is_not_limit_minimum'], False)
        for current, prior in zip(result['fee_currency_cases'], baseline['fee_currency_cases']):
            self.assertEqual(current['stop_minimum_at_assumed_price'], prior['stop_minimum_at_assumed_price'])
            self.assertIsNone(current['stop_limit_minimum_at_assumed_price'])
        for key in ('ready_for_live','live_dispatch_enabled','native_order_accepted'):
            self.assertIs(result[key], False)
        self.assertEqual(result['orders_sent'], 0)

    def test_09_input_remains_immutable(self):
        before = copy.deepcopy(self.preview)
        self.review()
        self.assertEqual(before, self.preview)

    def test_10_bridge_supplies_modeled_rules_without_verification_claim(self):
        from datetime import datetime, timezone
        from unittest.mock import Mock, patch
        from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
        from tools.bs_chat_tool_bridge import BSChatToolBridge
        callback = Mock(return_value=dict(bid='0.1000',ask='0.1001',quantity_step='0.1',price_tick='0.0001',
            observed_at_utc=datetime.now(timezone.utc).isoformat()))
        bridge = BSChatToolBridge(crypto_market_provider=callback)
        token = bind_memory_principal('local_admin')
        try:
            with patch('core.crypto_spot_protection.review_cro_protection', wraps=review_cro_protection) as operation:
                result = bridge.execute_tool('preview_crypto_spot', {'stop_type':'STOP_LIMIT','stop_limit_price':'0.0400'})
            self.assertEqual(result['status'], 'preview')
            self.assertEqual(operation.call_args.kwargs['minimum_notional_usd'], '1')
            self.assertEqual(operation.call_args.kwargs['usdt_usd_index'], '1')
            self.assertIs(result['protection_review']['stop_limit_minimum_rule_inputs_supplied'], True)
            self.assertIs(result['preview']['supplied_facts_independently_verified'], False)
            self.assertIs(result['account_accessed'], False)
            self.assertEqual(result['orders_sent'], 0)
        finally:
            reset_memory_principal(token)


if __name__ == '__main__':
    unittest.main()
