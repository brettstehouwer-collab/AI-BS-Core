"""Fifteen offline native stop draft cases; synthetic facts only."""
import unittest
from core.crypto_execution_controls import ControlError, digest
from core.crypto_com_native_stop import build_native_stop_draft


class NativeStopSmoke(unittest.TestCase):
    def args(self, **changes):
        return dict(dict(account='synthetic', instrument_name='CRO_USDT',
            client_oid='ae31c93b-36a3-47b8-af67-c980419fb071', net_inventory='20',
            available_base='20', quantity='19', quantity_tick='0.1', price_tick='0.001',
            minimum_quantity='1', minimum_notional_quote='1', trigger_price='0.098',
            last_price='0.1', fee_asset='CRO', fee_reserve='0.1', available_fee='20',
            actual_fill_fees_complete=True, reconciliation_complete=True,
            unresolved_orders=False, provenance_sha256='a'*64), **changes)

    def build(self, **changes):
        return build_native_stop_draft(**self.args(**changes))

    def refuse(self, **changes):
        with self.assertRaises(ControlError): self.build(**changes)

    def test_01_exact_native_fields(self):
        draft = self.build()
        self.assertEqual(draft['draft'], {'method':'private/advanced/create-order', 'params':{
            'instrument_name':'CRO_USDT','side':'SELL','type':'STOP_LOSS','quantity':'19',
            'client_oid':self.args()['client_oid'],'ref_price':'0.098',
            'ref_price_type':'LAST_PRICE','fee_instrument_name':'CRO'}})

    def test_02_always_held(self):
        row = self.build()
        for key in ('live_dispatch_enabled','ready_for_live','native_order_accepted'):
            self.assertIs(row[key], False)
        self.assertEqual(row['orders_sent'], 0)
        self.assertEqual(row['scope'], 'UNSIGNED_LOCALLY_VALIDATED_NATIVE_STOP_DRAFT')

    def test_03_missing_actual_fees(self): self.refuse(actual_fill_fees_complete=False)
    def test_04_missing_reconciliation(self): self.refuse(reconciliation_complete=None)
    def test_05_unresolved_orders(self): self.refuse(unresolved_orders=True)
    def test_06_bad_provenance(self): self.refuse(provenance_sha256='A'*64)
    def test_07_canonical_uuid(self): self.refuse(client_oid='not-a-uuid')
    def test_08_strict_numbers(self):
        for value in (True, 0.1, 'NaN', '-1'):
            with self.subTest(value=value): self.refuse(quantity=value)
    def test_09_trigger_below_reference(self):
        for value in ('0.1','0.101','0'):
            with self.subTest(value=value): self.refuse(trigger_price=value)
    def test_10_tick_alignment(self):
        self.refuse(quantity='19.01')
        self.refuse(trigger_price='0.0981')
    def test_11_minimums_no_upsize(self):
        self.refuse(quantity='0.9')
        self.refuse(minimum_notional_quote='2')
    def test_12_inventory_and_cash(self):
        self.refuse(net_inventory='18')
        self.refuse(available_base='18')
    def test_13_base_fee_reservation(self):
        self.refuse(quantity='20')
        self.refuse(available_fee='0.01')
    def test_14_quote_fee_explicit(self):
        self.assertEqual(self.build(fee_asset='USDT',available_fee='0.1')['draft']['params']['fee_instrument_name'],'USDT')
        self.refuse(fee_asset='BTC')
    def test_15_immutable_input_bound_digest_and_residual(self):
        args = self.args()
        before = digest(args)
        row = build_native_stop_draft(**args)
        self.assertEqual(before, digest(args))
        self.assertEqual(row['facts_sha256'], before)
        self.assertEqual(row['unsold_inventory'], '1')
        self.assertFalse(row['full_position_protection_verified'])


if __name__ == '__main__': unittest.main()
