"""Fifteen authenticated trial-status bridge/contract cases; no runtime mutation."""
import copy
import unittest
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal, current_memory_principal
from tools.bs_chat_tool_bridge import BSChatToolBridge
from core.crypto_trial_status_contract import trial_status, validate_trial_status


class Registry:
    def __init__(self, result=None):
        self.result=trial_status('qualification') if result is None else result
        self.calls=[]
    def status(self):
        self.calls.append(current_memory_principal())
        return copy.deepcopy(self.result)


class TrialStatusBridgeSmoke(unittest.TestCase):
    def call(self, result=None, args=None):
        registry=Registry(result);bridge=BSChatToolBridge(crypto_trial_registry=registry)
        token=bind_memory_principal('local_admin')
        try:reply=bridge.execute_tool('get_crypto_trial_status',{} if args is None else args)
        finally:reset_memory_principal(token)
        return reply,registry

    def test_01_anonymous_denied_before_provider(self):
        registry=Registry();bridge=BSChatToolBridge(crypto_trial_registry=registry)
        self.assertEqual(bridge.execute_tool('get_crypto_trial_status',{}),{'status':'denied'})
        self.assertEqual(registry.calls,[])

    def test_02_direct_method_requires_verified_context(self):
        registry=Registry();bridge=BSChatToolBridge(crypto_trial_registry=registry)
        with self.assertRaises(PermissionError):bridge.get_crypto_trial_status()
        self.assertEqual(registry.calls,[])

    def test_03_authorized_reply_preserves_principal_and_safe_fields(self):
        result,registry=self.call();self.assertEqual(result,trial_status('qualification'))
        self.assertEqual(registry.calls,['local_admin']);self.assertIsNone(current_memory_principal())

    def test_04_any_client_path_argument_refused_before_provider(self):
        for key in ('path','root','store_uuid','account','principal','qualification','force','seed'):
            with self.subTest(key=key):
                result,registry=self.call(args={key:'C:/private'})
                self.assertEqual(result['status'],'error');self.assertEqual(registry.calls,[])

    def test_05_unknown_status_refused(self):
        result,_=self.call(dict(trial_status('qualification'),status='running_live'))
        self.assertEqual(result,{'status':'error','error':'diagnostic_unavailable'})

    def test_06_zero_order_count_is_exact_integer(self):
        for value in (False,'0',1,0.0):
            with self.subTest(value=value):
                result,_=self.call(dict(trial_status('qualification'),orders_sent=value))
                self.assertEqual(result['status'],'error')

    def test_07_live_ready_or_account_claims_never_pass(self):
        for field in ('exchange_account_identity_verified','production_store_admitted',
                      'native_protection_qualified','live_dispatch_enabled','ready_for_live','account_accessed'):
            with self.subTest(field=field):
                result,_=self.call(dict(trial_status('qualification'),**{field:True}))
                self.assertEqual(result['status'],'error')

    def test_08_extra_provider_metadata_never_echoed(self):
        result,_=self.call(dict(trial_status('qualification'),root='DO_NOT_ECHO_PRIVATE_PATH'))
        self.assertEqual(result['status'],'error');self.assertNotIn('DO_NOT_ECHO',str(result))

    def test_09_nonboolean_status_fields_refused(self):
        for field in ('registered','stored_state_verified','account_metadata_bound','local_entry_cutoff_enforced','entry_held'):
            with self.subTest(field=field):
                result,_=self.call(dict(trial_status('qualification'),**{field:1}))
                self.assertEqual(result['status'],'error')

    def test_10_missing_or_wrong_result_shape_refused(self):
        for value in ({'status':'qualification'},[],None):
            registry=Registry();registry.result=value
            bridge=BSChatToolBridge(crypto_trial_registry=registry);token=bind_memory_principal('local_admin')
            try:result=bridge.execute_tool('get_crypto_trial_status',{})
            finally:reset_memory_principal(token)
            self.assertEqual(result['status'],'error')

    def test_11_provider_failure_has_no_sensitive_exception_detail(self):
        class Broken:
            def status(self):raise RuntimeError('DO_NOT_ECHO_SECRET_PATH')
        bridge=BSChatToolBridge(crypto_trial_registry=Broken());token=bind_memory_principal('local_admin')
        try:result=bridge.execute_tool('get_crypto_trial_status',{})
        finally:reset_memory_principal(token)
        self.assertEqual(result,{'status':'error','error':'diagnostic_unavailable'})

    def test_12_unregistered_and_refused_statuses_are_all_false(self):
        for status in ('not_registered','unavailable','denied'):
            result,_=self.call(trial_status(status));self.assertEqual(result,trial_status(status))
            for field,value in result.items():
                if field not in ('status','orders_sent'):self.assertIs(value,False)

    def test_13_qualification_and_entry_held_remain_separate(self):
        result,_=self.call(trial_status('qualification',entry_held=True))
        self.assertTrue(result['registered']);self.assertTrue(result['entry_held'])
        self.assertFalse(result['live_dispatch_enabled']);self.assertEqual(result['orders_sent'],0)

    def test_14_contract_returns_copy_without_mutating_input(self):
        original=trial_status('held');before=copy.deepcopy(original);result=validate_trial_status(original)
        self.assertEqual(original,before);self.assertEqual(result,before);self.assertIsNot(result,original)

    def test_15_inconsistent_health_flags_refused(self):
        for value in (dict(trial_status('qualification'),stored_state_verified=False),
                      dict(trial_status('not_registered'),registered=True)):
            with self.assertRaises(ValueError):validate_trial_status(value)


if __name__=='__main__':unittest.main()
