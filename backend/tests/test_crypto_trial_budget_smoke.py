"""Fifteen pure current-trial budget cases; no I/O or trading authority."""
import copy
from decimal import Decimal
import unittest
from uuid import uuid4

from core.crypto_execution_controls import ControlError, digest
from core.crypto_trial_budget import create_baseline, assess_daily_budget


class TrialBudgetSmoke(unittest.TestCase):
    def setUp(self):
        self.trial = str(uuid4())
        self.account = 'synthetic-account'
        self.baseline = create_baseline(trial_id=self.trial, account=self.account,
            started_ms=1000, day_start_ms=0, opening_receipt_sha256='a'*64)

    def outcome(self, event_id='fill-close-1', **changes):
        row = dict(event_id=event_id, trial_id=self.trial, account=self.account,
                   closed_ms=1500, gross_pnl_usdt='0', fees_usdt='0')
        return dict(row, **changes)

    def assess(self, baseline=None, **changes):
        args = dict(now_ms=2000, account=self.account, loss_budget_usdt='1',
            closed_outcomes=[], open_loss_reserve_usdt='0', pending_loss_reserve_usdt='0',
            proposed_loss_reserve_usdt='0.1', coverage_complete=True)
        return assess_daily_budget(self.baseline if baseline is None else baseline, **dict(args, **changes))

    def test_01_baseline_shape_and_canonical_hash(self):
        self.assertEqual(self.baseline['schema'], 1)
        self.assertEqual(self.baseline['scope'], 'OFFLINE_TRIAL_BASELINE')
        unsigned = {k:v for k,v in self.baseline.items() if k!='baseline_sha256'}
        self.assertEqual(self.baseline['baseline_sha256'], digest(unsigned))
        self.assertEqual(self.baseline['trial_id'], self.trial)
        self.assertEqual(self.baseline['opening_receipt_sha256'], 'a'*64)

    def test_02_strict_baseline_identity_and_receipt(self):
        valid = dict(trial_id=self.trial, account=self.account, started_ms=1000,
                     day_start_ms=0, opening_receipt_sha256='a'*64)
        for changes in ({'trial_id':self.trial.upper()}, {'trial_id':'not-a-uuid'},
                        {'account':''}, {'account':True}, {'opening_receipt_sha256':'A'*64},
                        {'opening_receipt_sha256':'a'*63}):
            with self.subTest(changes=changes), self.assertRaises(ControlError):
                create_baseline(**dict(valid, **changes))

    def test_03_baseline_day_must_be_exact_utc_midnight(self):
        valid = dict(trial_id=self.trial, account=self.account, started_ms=1000,
                     day_start_ms=0, opening_receipt_sha256='a'*64)
        for changes in ({'day_start_ms':1}, {'started_ms':86400000}, {'started_ms':-1},
                        {'started_ms':True}, {'day_start_ms':0.0}):
            with self.subTest(changes=changes), self.assertRaises(ControlError):
                create_baseline(**dict(valid, **changes))
        valid['day_start_ms']=86400000;valid['started_ms']=86400000
        self.assertEqual(create_baseline(**valid)['day_start_ms'], 86400000)

    def test_04_tampered_baseline_refused_before_assessment(self):
        for field,value in (('account','other'), ('started_ms',1001), ('opening_receipt_sha256','b'*64)):
            altered = dict(self.baseline, **{field:value})
            with self.subTest(field=field), self.assertRaises(ControlError):
                self.assess(altered)

    def test_05_fees_create_loss_and_signed_pnl_is_exact(self):
        result = self.assess(closed_outcomes=[self.outcome(gross_pnl_usdt='-0.20',fees_usdt='0.03'),
            self.outcome('second',gross_pnl_usdt='0.01',fees_usdt='0.02')])
        self.assertEqual(Decimal(result['closed_loss_usdt']), Decimal('0.24'))
        self.assertEqual(Decimal(result['remaining_usdt']), Decimal('0.76'))

    def test_06_profits_do_not_replenish_allowance(self):
        result = self.assess(closed_outcomes=[self.outcome(gross_pnl_usdt='-0.40'),
            self.outcome('profit',gross_pnl_usdt='20',fees_usdt='0.01')])
        self.assertEqual(Decimal(result['closed_loss_usdt']), Decimal('0.40'))
        self.assertEqual(Decimal(result['remaining_usdt']), Decimal('0.60'))

    def test_07_open_and_pending_reserves_consume_budget(self):
        result = self.assess(closed_outcomes=[self.outcome(gross_pnl_usdt='-0.2')],
            open_loss_reserve_usdt='0.3',pending_loss_reserve_usdt='0.1',proposed_loss_reserve_usdt='0.4')
        self.assertEqual(Decimal(result['used_usdt']), Decimal('0.6'))
        self.assertEqual(Decimal(result['remaining_usdt']), Decimal('0.4'))
        self.assertIs(result['proposed_fits'], True)

    def test_08_budget_equality_triggers_cutoff_even_zero_proposal(self):
        result = self.assess(open_loss_reserve_usdt='1', proposed_loss_reserve_usdt='0')
        self.assertIs(result['daily_cutoff_triggered'], True)
        self.assertIs(result['proposed_fits'], False)
        self.assertEqual(Decimal(result['remaining_usdt']), 0)

    def test_09_proposal_above_remaining_rejected_without_live_authority(self):
        result = self.assess(pending_loss_reserve_usdt='0.9', proposed_loss_reserve_usdt='0.1001')
        self.assertIs(result['daily_cutoff_triggered'], False)
        self.assertIs(result['proposed_fits'], False)

    def test_10_missing_reserves_or_incomplete_coverage_block(self):
        for changes in ({'open_loss_reserve_usdt':None}, {'pending_loss_reserve_usdt':None},
                        {'proposed_loss_reserve_usdt':None}, {'coverage_complete':False}):
            with self.subTest(changes=changes):
                result = self.assess(**changes)
                self.assertIs(result['proposed_fits'], False)
                self.assertTrue(result['blocking_checks'])

    def test_11_float_bool_and_negative_budget_inputs_refused(self):
        for field in ('loss_budget_usdt','open_loss_reserve_usdt','pending_loss_reserve_usdt','proposed_loss_reserve_usdt'):
            for value in (0.1,True,'-0.1'):
                with self.subTest(field=field,value=value), self.assertRaises(ControlError):
                    self.assess(**{field:value})
        with self.assertRaises(ControlError):self.assess(loss_budget_usdt='0')
        with self.assertRaises(ControlError):self.assess(coverage_complete=1)
        result=self.assess(loss_budget_usdt=Decimal('1'),proposed_loss_reserve_usdt=Decimal('0.1'))
        self.assertTrue(result['proposed_fits'])

    def test_12_wrong_outcome_identity_or_future_timestamp_refused(self):
        for change in ({'account':'other'}, {'trial_id':str(uuid4())}, {'closed_ms':2001},
                       {'closed_ms':999}, {'closed_ms':True}, {'fees_usdt':'-0.01'},
                       {'gross_pnl_usdt':0.1}, {'fees_usdt':False}, {'extra':'unsupported'}):
            with self.subTest(change=change), self.assertRaises(ControlError):
                self.assess(closed_outcomes=[self.outcome(**change)])
        with self.assertRaises(ControlError):self.assess(account='other')

    def test_13_duplicate_event_identity_refused_even_if_identical(self):
        row=self.outcome()
        with self.assertRaises(ControlError):self.assess(closed_outcomes=[row,copy.deepcopy(row)])
        with self.assertRaises(ControlError):self.assess(closed_outcomes=[row,self.outcome(gross_pnl_usdt='-1')])

    def test_14_day_boundary_requires_new_baseline_not_silent_reset(self):
        for now in (999,86400000,True,2000.0):
            with self.subTest(now=now), self.assertRaises(ControlError):self.assess(now_ms=now)
        self.assertIs(self.assess(now_ms=86399999)['proposed_fits'], True)

    def test_15_inputs_unchanged_and_all_live_flags_permanently_false(self):
        baseline=copy.deepcopy(self.baseline);rows=[self.outcome(gross_pnl_usdt='-0.1')];before=copy.deepcopy(rows)
        result=self.assess(closed_outcomes=rows)
        self.assertEqual(self.baseline,baseline);self.assertEqual(rows,before)
        for key in ('live_dispatch_enabled','ready_for_live','daily_cutoff_enforced','inputs_independently_verified'):
            self.assertIs(result[key],False)
        self.assertEqual(result['orders_sent'],0)


if __name__ == '__main__':
    unittest.main()
