"""Ten bounded derived-accounting precision cases; strict budget/fees retained."""
from decimal import Decimal, localcontext
import unittest
from uuid import uuid4

from core.crypto_execution_controls import ControlError
from core.crypto_trial_budget import create_baseline, assess_daily_budget


class AccountingPrecisionSmoke(unittest.TestCase):
    def setUp(self):
        self.account='synthetic-account';self.trial=str(uuid4())
        self.baseline=create_baseline(trial_id=self.trial,account=self.account,started_ms=1000,
            day_start_ms=0,opening_receipt_sha256='b'*64)
        with localcontext() as context:
            context.prec=96
            self.fraction=Decimal(1)/Decimal(3)

    def outcome(self, gross, fees='0'):
        return dict(event_id='synthetic-close',trial_id=self.trial,account=self.account,
            closed_ms=1500,gross_pnl_usdt=gross,fees_usdt=fees)

    def assess(self, **changes):
        args=dict(now_ms=2000,account=self.account,loss_budget_usdt='1',closed_outcomes=[],
            open_loss_reserve_usdt='0',pending_loss_reserve_usdt='0',
            proposed_loss_reserve_usdt='0',coverage_complete=True)
        return assess_daily_budget(self.baseline,**dict(args,**changes))

    def test_01_repeating_fraction_reserve_preserved_exactly(self):
        result=self.assess(open_loss_reserve_usdt=str(self.fraction))
        self.assertEqual(Decimal(result['used_usdt']),self.fraction)
        self.assertEqual(Decimal(result['loss_reserves_usdt']['open']),self.fraction)

    def test_02_signed_fraction_gross_pnl_preserved(self):
        with localcontext() as context:
            context.prec=96
            negative=-self.fraction
        result=self.assess(closed_outcomes=[self.outcome(str(negative))])
        self.assertEqual(Decimal(result['closed_loss_usdt']),self.fraction)

    def test_03_reserves_and_fee_loss_use_same_96_digit_context(self):
        with localcontext() as context:
            context.prec=96
            gross=-self.fraction
            expected_closed=Decimal('0.01')-gross
            expected_used=expected_closed+self.fraction+Decimal('0.01')
            expected_remaining=Decimal('1')-expected_used
        result=self.assess(closed_outcomes=[self.outcome(gross,'0.01')],
            open_loss_reserve_usdt=self.fraction,pending_loss_reserve_usdt=Decimal('0.01'))
        self.assertEqual(Decimal(result['closed_loss_usdt']),expected_closed)
        self.assertEqual(Decimal(result['used_usdt']),expected_used)
        self.assertEqual(Decimal(result['remaining_usdt']),expected_remaining)

    def test_04_existing_exact_18_decimal_behavior_retained(self):
        value='0.123456789012345678'
        result=self.assess(open_loss_reserve_usdt=value,pending_loss_reserve_usdt=0,
            proposed_loss_reserve_usdt=Decimal(value))
        self.assertEqual(Decimal(result['used_usdt']),Decimal(value))
        self.assertTrue(result['proposed_fits'])

    def test_05_nonfinite_float_bool_and_negative_reserves_rejected(self):
        for field in ('open_loss_reserve_usdt','pending_loss_reserve_usdt','proposed_loss_reserve_usdt'):
            for value in ('NaN','Infinity',Decimal('-Infinity'),0.1,True,'-0.01'):
                with self.subTest(field=field,value=value),self.assertRaises(ControlError):
                    self.assess(**{field:value})
        for gross in ('NaN','Infinity',0.1,False):
            with self.subTest(gross=gross),self.assertRaises(ControlError):
                self.assess(closed_outcomes=[self.outcome(gross)])

    def test_06_accounting_precision_magnitude_exponent_length_bounded(self):
        excessive=('0.'+'1'*129,'1e23','1e-145','0.'+'0'*200+'1')
        for value in excessive:
            with self.subTest(value=value),self.assertRaises(ControlError):
                self.assess(open_loss_reserve_usdt=value)
            with self.subTest(gross=value),self.assertRaises(ControlError):
                self.assess(closed_outcomes=[self.outcome(value)])

    def test_07_budget_and_actual_fee_precision_stay_strict(self):
        beyond='0.1234567890123456789'
        with self.assertRaises(ControlError):self.assess(loss_budget_usdt=beyond)
        with self.assertRaises(ControlError):self.assess(closed_outcomes=[self.outcome('0',beyond)])
        for value in (0.1,True):
            with self.subTest(value=value),self.assertRaises(ControlError):self.assess(loss_budget_usdt=value)

    def test_08_missing_facts_remain_held_with_derived_precision(self):
        result=self.assess(open_loss_reserve_usdt=self.fraction,pending_loss_reserve_usdt=None)
        self.assertFalse(result['proposed_fits'])
        self.assertIsNone(result['used_usdt'])
        self.assertTrue(result['blocking_checks'])

    def test_09_maximum_accounting_magnitude_and_small_exponent_supported(self):
        result=self.assess(open_loss_reserve_usdt=10**22)
        self.assertEqual(Decimal(result['used_usdt']),Decimal('1e22'))
        result=self.assess(proposed_loss_reserve_usdt=Decimal('1e-144'))
        self.assertEqual(Decimal(result['loss_reserves_usdt']['proposed']),Decimal('1e-144'))

    def test_10_precision_never_grants_enforcement_or_order_authority(self):
        result=self.assess(open_loss_reserve_usdt=self.fraction)
        for key in ('daily_cutoff_enforced','ready_for_live','live_dispatch_enabled','inputs_independently_verified'):
            self.assertIs(result[key],False)
        self.assertEqual(result['orders_sent'],0)


if __name__=='__main__':unittest.main()
