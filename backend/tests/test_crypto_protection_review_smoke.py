"""Fifteen current-trial protection review cases; no history, accounts or orders."""
import copy
from decimal import Decimal
import unittest

from core.crypto_execution_controls import ControlError
from core.crypto_spot_preview import preview_cro_spot
from core.crypto_spot_protection import review_cro_protection


class ProtectionReviewSmoke(unittest.TestCase):
    def setUp(self):
        self.params = dict(budget_usdt='2', bid='0.1000', ask='0.1001',
            quantity_step='0.1', price_tick='0.0001', minimum_notional_usd='1',
            usdt_usd_index='1', entry_fee_bps='25', exit_fee_bps='50',
            stop_price='0.0980', target_price=None, daily_loss_budget_usdt='1')

    def preview(self, **updates):
        return preview_cro_spot(**dict(self.params, **updates))

    def reject(self, value):
        with self.assertRaises((ControlError, ValueError, TypeError)):
            review_cro_protection(value)

    def test_01_scope_and_trial_choices_copied(self):
        result = review_cro_protection(self.preview())
        self.assertEqual(result['scope'], 'PROTECTION_REVIEW_NOT_AN_ORDER')
        self.assertEqual(Decimal(result['budget_all_in_usdt']), Decimal('2'))
        self.assertEqual(Decimal(result['trigger_price']), Decimal('0.0980'))
        self.assertEqual(Decimal(result['daily_loss_budget_usdt']), Decimal('1'))

    def test_02_four_unique_fee_asset_cases_preserved(self):
        preview = self.preview()
        result = review_cro_protection(preview)
        cases = result['fee_currency_cases']
        self.assertEqual(len(cases), 4)
        self.assertEqual({(c['entry_fee_asset'], c['exit_fee_asset']) for c in cases},
                         {('USDT','USDT'),('USDT','CRO'),('CRO','USDT'),('CRO','CRO')})
        for case in cases:
            source = next(c for c in preview['fee_currency_scenarios']
                if c['entry_fee_asset'] == case['entry_fee_asset'] and c['exit_fee_asset'] == case['exit_fee_asset'])
            self.assertEqual(case['sell_quantity_cro'], source['sell_quantity_cro'])
            self.assertEqual(case['residual_cro_after_assumed_exit'], source['residual_cro_after_assumed_exit'])

    def test_03_static_candidate_is_conservative_minimum(self):
        preview = self.preview()
        result = review_cro_protection(preview)
        self.assertEqual(Decimal(result['static_quantity_candidate_cro']),
                         min(Decimal(c['sell_quantity_cro']) for c in preview['fee_currency_scenarios']))
        self.assertFalse(result['full_position_protection_verified'])

    def test_04_base_fee_residual_never_disappears(self):
        result = review_cro_protection(self.preview())
        case = next(c for c in result['fee_currency_cases']
                    if c['entry_fee_asset'] == 'CRO' and c['exit_fee_asset'] == 'CRO')
        self.assertGreater(Decimal(case['residual_cro_after_assumed_exit']), 0)

    def test_05_minimum_failures_remain_visible(self):
        result = review_cro_protection(self.preview(stop_price='0.0400'))
        self.assertTrue(all(c['stop_minimum_at_assumed_price'] is False for c in result['fee_currency_cases']))
        self.assertFalse(result['ready_for_live'])
        self.assertTrue(any('MINIMUM' in check for check in result['blocking_checks']))

    def test_06_missing_stop_is_explicit_and_held(self):
        result = review_cro_protection(self.preview(stop_price=None))
        self.assertIsNone(result['trigger_price'])
        self.assertTrue(any('STOP' in check and 'MISSING' in check for check in result['blocking_checks']))
        self.assertTrue(all(c['stop_minimum_at_assumed_price'] is None for c in result['fee_currency_cases']))

    def test_07_target_never_invented(self):
        self.assertIsNone(review_cro_protection(self.preview())['target_price'])
        result = review_cro_protection(self.preview(target_price='0.1030'))
        self.assertEqual(Decimal(result['target_price']), Decimal('0.1030'))

    def test_08_stop_mode_and_limit_remain_unselected(self):
        result = review_cro_protection(self.preview())
        self.assertIsNone(result['selected_stop_type'])
        self.assertEqual({option['type'] for option in result['stop_options']}, {'STOP_LOSS','STOP_LIMIT'})
        self.assertIsNone(next(o for o in result['stop_options'] if o['type'] == 'STOP_LIMIT')['limit_price'])

    def test_09_no_live_or_partial_protection_claim(self):
        result = review_cro_protection(self.preview())
        for key in ('full_position_protection_verified', 'partial_fill_protection_verified',
                    'daily_cutoff_enforced', 'ready_for_live', 'live_dispatch_enabled'):
            self.assertIs(result[key], False)
        self.assertEqual(result['orders_sent'], 0)

    def test_10_current_trial_replaces_historical_profit_gate(self):
        preview = self.preview()
        self.assertNotIn('HISTORY_COVERAGE_UNVERIFIED', preview['blocking_checks'])
        self.assertIn('TRIAL_OPENING_STATE_UNVERIFIED', preview['blocking_checks'])
        result = review_cro_protection(preview)
        self.assertIs(result['historical_profit_review_required'], False)
        self.assertIs(result['opening_state_required'], True)
        self.assertIn('CURRENT_TRIAL_OPENING_STATE_UNVERIFIED', result['blocking_checks'])

    def test_11_preview_input_unchanged(self):
        preview = self.preview()
        before = copy.deepcopy(preview)
        review_cro_protection(preview)
        self.assertEqual(preview, before)

    def test_12_wrong_scope_symbol_or_authority_flags_rejected(self):
        for update in ({'scope':'LIVE'}, {'symbol':'CRO/USD'}, {'ready_for_live':True},
                       {'live_dispatch_enabled':True}, {'orders_sent':1}):
            with self.subTest(update=update):
                self.reject(dict(self.preview(), **update))

    def test_13_missing_duplicate_or_foreign_fee_cases_rejected(self):
        for mode in ('missing','duplicate','foreign'):
            preview = self.preview()
            if mode == 'missing': preview['fee_currency_scenarios'].pop()
            elif mode == 'duplicate': preview['fee_currency_scenarios'][1] = copy.deepcopy(preview['fee_currency_scenarios'][0])
            else: preview['fee_currency_scenarios'][0]['entry_fee_asset'] = 'USD'
            with self.subTest(mode=mode): self.reject(preview)

    def test_14_invalid_quantity_residual_or_stop_row_rejected(self):
        for field, value in (('sell_quantity_cro','-1'), ('sell_quantity_cro','NaN'),
                             ('residual_cro_after_assumed_exit','-1')):
            preview = self.preview();preview['fee_currency_scenarios'][0][field] = value
            with self.subTest(field=field,value=value): self.reject(preview)
        preview = self.preview()
        level = next(row for row in preview['fee_currency_scenarios'][0]['levels'] if row['assumed_execution']=='stop')
        level['price'] = '0.0970'
        self.reject(preview)

    def test_15_chat_formats_protection_review_without_history_gate(self):
        from core.crypto_preview_chat import _format
        preview = self.preview()
        result = {'status':'preview','preview':preview,
            'protection_review':review_cro_protection(preview),
            'market':{'bid':'0.1000','ask':'0.1001','observed_at_utc':'2026-11-15T00:00:00Z'}}
        text = _format(result)
        self.assertIn('Protection review', text)
        self.assertNotIn('account exposure/history', text)
        self.assertIn('not', text.lower())


if __name__ == '__main__':
    unittest.main()
