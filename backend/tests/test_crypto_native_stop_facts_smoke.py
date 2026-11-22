"""Ten canonical numeric fact hashing cases; no live authority."""
from decimal import Decimal
import unittest
from tests import test_crypto_native_stop_smoke as fixture
from core.crypto_execution_controls import ControlError, digest
from core.crypto_com_native_stop import build_native_stop_draft


class NativeStopFactsSmoke(unittest.TestCase):
    numeric=('net_inventory','available_base','quantity','quantity_tick','price_tick',
        'minimum_quantity','minimum_notional_quote','trigger_price','last_price',
        'fee_reserve','available_fee')

    def args(self, **changes):
        return fixture.NativeStopSmoke.args(self, **changes)

    def build(self, **changes):return build_native_stop_draft(**self.args(**changes))

    def test_01_decimal_all_numeric_facts(self):
        facts=self.args()
        for key in self.numeric:facts[key]=Decimal(facts[key])
        self.assertEqual(build_native_stop_draft(**facts)['facts_sha256'],self.build()['facts_sha256'])

    def test_02_each_decimal_accepted(self):
        for key in self.numeric:
            with self.subTest(key=key):self.assertEqual(self.build(**{key:Decimal(self.args()[key])})['facts_sha256'],self.build()['facts_sha256'])

    def test_03_integer_equivalence(self):
        self.assertEqual(self.build(quantity=19,net_inventory=20,available_base=20,available_fee=20)['facts_sha256'],self.build()['facts_sha256'])

    def test_04_equivalent_scaled_strings(self):
        facts=self.args()
        for key in self.numeric:facts[key]=format(Decimal(facts[key]),'.6f')
        self.assertEqual(build_native_stop_draft(**facts)['facts_sha256'],self.build()['facts_sha256'])

    def test_05_numeric_economics_change_hash(self):
        self.assertNotEqual(self.build(quantity='18')['facts_sha256'],self.build()['facts_sha256'])

    def test_06_identity_and_provenance_preserved(self):
        for change in ({'account':'other'},{'provenance_sha256':'b'*64},
            {'client_oid':'d4725cc8-d8eb-43a3-8da9-1e4f0a8dc03d'}):
            with self.subTest(change=change):self.assertNotEqual(self.build(**change)['facts_sha256'],self.build()['facts_sha256'])

    def test_07_invalid_float_bool_refused(self):
        for value in (0.1,True,False):
            with self.subTest(value=value),self.assertRaises(ControlError):self.build(quantity=value)

    def test_08_nonfinite_decimal_refused(self):
        for value in ('NaN','Infinity','-Infinity'):
            with self.subTest(value=value),self.assertRaises(ControlError):self.build(quantity=Decimal(value))

    def test_09_canonical_digest_exact_and_input_unchanged(self):
        facts=self.args();facts['quantity']=Decimal('19.000')
        original=facts.copy();canonical=self.args()
        self.assertEqual(build_native_stop_draft(**facts)['facts_sha256'],digest(canonical))
        self.assertEqual(facts,original);self.assertIsInstance(facts['quantity'],Decimal)

    def test_10_decimal_envelope_still_held(self):
        row=self.build(quantity=Decimal('19'))
        for key in ('ready_for_live','live_dispatch_enabled','native_order_accepted'):
            self.assertIs(row[key],False)
        self.assertEqual(row['orders_sent'],0)
        self.assertEqual(row['draft']['params']['quantity'],'19')


if __name__=='__main__':unittest.main()
