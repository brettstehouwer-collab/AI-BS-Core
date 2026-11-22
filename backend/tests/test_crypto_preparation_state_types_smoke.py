"""Ten exact-type internal-state fences; monkeypatches are explicit negative inputs."""
import unittest
from unittest.mock import patch
from core.crypto_preparation_status import PreparationStatusReader,preparation_status
from tests.test_crypto_held_preparation_admission_smoke import HeldPreparationAdmissionSmoke as Fixture


class PreparationStateTypesSmoke(unittest.TestCase):
    def setUp(self):
        self.fixture=Fixture('test_01_success_is_local_seed_only_and_never_dispatches')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def reader(self,runtime=None):
        return PreparationStatusReader(active_registry=self.fixture.registry,active_runtime=runtime,allow_test=True)

    def malformed_index(self,key,value):
        original=self.fixture.registry.review();bad=dict(original,**{key:value})
        self.assertEqual(bad,original,'Negative input must expose bool/int equality coercion')
        with patch.object(self.fixture.registry,'review',return_value=bad):
            self.assertEqual(self.reader().status(),preparation_status('unavailable'))
        self.assertFalse(self.fixture.registry._closed)

    def malformed_runtime(self,key,value):
        runtime=self.fixture.create();original=runtime.status();bad=dict(original,**{key:value})
        self.assertEqual(bad,original,'Negative input must expose bool/int equality coercion')
        with patch.object(runtime,'status',return_value=bad):
            self.assertEqual(self.reader(runtime).status(),preparation_status('unavailable'))
        self.assertFalse(runtime._closed)

    def test_01_valid_selected_state_is_accepted(self):
        self.assertEqual(self.reader().status(),preparation_status('selected',test_only=True))

    def test_02_valid_held_state_is_accepted(self):
        runtime=self.fixture.create()
        self.assertEqual(self.reader(runtime).status(),preparation_status('held_preparation',test_only=True))

    def test_03_index_boolean_orders_sent_is_refused(self):self.malformed_index('orders_sent',False)
    def test_04_index_float_orders_sent_is_refused(self):self.malformed_index('orders_sent',0.0)

    def test_05_index_integer_false_flags_are_refused(self):
        for key in ('fresh_authority','account_identity_verified','financial_runtime_created','live_dispatch_enabled','ready_for_live'):
            with self.subTest(key=key):self.malformed_index(key,0)

    def test_06_index_integer_test_flag_is_refused(self):self.malformed_index('test_only',1)
    def test_07_runtime_boolean_orders_sent_is_refused(self):self.malformed_runtime('orders_sent',False)
    def test_08_runtime_float_orders_sent_is_refused(self):self.malformed_runtime('orders_sent',0.0)

    def test_09_runtime_integer_false_flags_are_refused(self):
        runtime=self.fixture.create();original=runtime.status()
        for key in ('fresh_authority','external_funds_reserved','account_identity_verified','native_order_accepted','live_dispatch_enabled','ready_for_live'):
            bad=dict(original,**{key:0});self.assertEqual(bad,original)
            with self.subTest(key=key),patch.object(runtime,'status',return_value=bad):
                self.assertEqual(self.reader(runtime).status(),preparation_status('unavailable'))

    def test_10_runtime_integer_true_flags_are_refused(self):
        runtime=self.fixture.create();original=runtime.status()
        for key in ('test_only','local_seed_allocated'):
            bad=dict(original,**{key:1});self.assertEqual(bad,original)
            with self.subTest(key=key),patch.object(runtime,'status',return_value=bad):
                self.assertEqual(self.reader(runtime).status(),preparation_status('unavailable'))


if __name__=='__main__':unittest.main()
