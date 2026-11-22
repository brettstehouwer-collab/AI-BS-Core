"""Ten modeled exit-rule cases; no native protection or transport claim."""
from decimal import Decimal
import unittest

from core.crypto_execution_controls import ControlError, Instrument
from core.crypto_trial_admission import modeled_entry_risk


class TrialRiskRulesSmoke(unittest.TestCase):
    def model(self, *, quantity='11', minimum_quantity='0.5', step='0.5',
              minimum_notional='0.01', fee='500', slip='50', stop='0.08', tick='0.01', **spec_changes):
        spec=Instrument('CRO','USDT',quantity_step='0.5',price_tick='0.01',
            minimum_quantity='0.5',minimum_notional='0.01').normalized()
        spec.update(quantity_step=step,minimum_quantity=minimum_quantity,
                    minimum_notional=minimum_notional,price_tick=tick,**spec_changes)
        return modeled_entry_risk(dict(quantity=quantity,limit_price='0.1',hard_stop=stop),spec,
            max_fee_bps=fee,max_slippage_bps=slip)

    def test_01_minimum_quantity_above_all_exits_refused_even_notional_passes(self):
        with self.assertRaises(ControlError):self.model(minimum_quantity='12')

    def test_02_quote_buy_base_exit_fee_case_must_meet_minimum_quantity(self):
        # First USDT/USDT case sells11; second USDT/CRO sells10 at5%fee.
        with self.assertRaises(ControlError):self.model(minimum_quantity='11')

    def test_03_base_buy_quote_exit_fee_case_must_meet_minimum_quantity(self):
        # At10%fee: first11,second10,third9.5CRO; min10 fails thirdcase.
        with self.assertRaises(ControlError):self.model(minimum_quantity='10',fee='1000')

    def test_04_base_buy_base_exit_fee_case_must_meet_minimum_quantity(self):
        # At5%fee: first11,second10,third10,fourth9.5CRO; min10 fails fourth.
        with self.assertRaises(ControlError):self.model(minimum_quantity='10')

    def test_05_valid_all_case_minimum_and_step_are_preserved(self):
        result=self.model(minimum_quantity='9.5')
        self.assertEqual(len(result['fee_cases']),4)
        for case in result['fee_cases']:
            quantity=Decimal(case['modeled_sell_quantity_cro'])
            self.assertGreaterEqual(quantity,Decimal('9.5'))
            self.assertEqual(quantity%Decimal('0.5'),0)

    def test_06_invalid_minimum_quantity_rejected(self):
        for value in ('0','-1','NaN','Infinity',0.5,True,None):
            with self.subTest(value=value),self.assertRaises(ControlError):self.model(minimum_quantity=value)

    def test_07_invalid_step_or_minimum_notional_rejected(self):
        for field in ('step','minimum_notional'):
            for value in ('0','-0.1','NaN',0.5,False):
                with self.subTest(field=field,value=value),self.assertRaises(ControlError):self.model(**{field:value})

    def test_08_zero_fee_reserve_is_entry_debit_less_modeled_cash(self):
        result=self.model(fee='0',minimum_quantity='11')
        self.assertEqual(Decimal(result['loss_reserve_usdt']),Decimal('0.33'))
        self.assertTrue(all(Decimal(c['modeled_sell_quantity_cro'])==11 for c in result['fee_cases']))
        self.assertTrue(all(Decimal(c['cash_loss_reserve_usdt'])==Decimal('0.33') for c in result['fee_cases']))

    def test_09_stop_floor_boundary_never_rounds_up_or_to_zero(self):
        self.assertEqual(Decimal(self.model(stop='0.08',slip='0')['assumed_exit_price']),Decimal('0.08'))
        self.assertEqual(Decimal(self.model(stop='0.08',slip='1')['assumed_exit_price']),Decimal('0.07'))
        with self.assertRaises(ControlError):self.model(stop='0.01',slip='1')

    def test_10_valid_model_never_claims_native_or_guaranteed_execution(self):
        result=self.model()
        self.assertEqual(result['scope'],'MODELED_STOP_CASH_SHORTFALL_NOT_NATIVE_PROTECTION')
        for field in ('guaranteed_maximum_loss','live_dispatch_enabled','ready_for_live'):
            self.assertIs(result[field],False)


if __name__=='__main__':unittest.main()
