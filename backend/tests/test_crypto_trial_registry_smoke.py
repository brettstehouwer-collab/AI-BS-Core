"""Fifteen principal-scoped registry status cases; synthetic durable stores only."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import win32security
from tests import test_crypto_trial_runtime_store_smoke as fixture
from core.crypto_execution_controls import ControlError, digest
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from core.crypto_trial_registry import TrialRuntimeRegistry, get_default_registry


FIELDS={'status','registered','stored_state_verified','account_metadata_bound',
    'exchange_account_identity_verified','local_entry_cutoff_enforced','entry_held',
    'production_store_admitted','native_protection_qualified','live_dispatch_enabled',
    'ready_for_live','orders_sent','account_accessed'}


class TrialRegistrySmoke(unittest.TestCase):
    setUp_fixture=fixture.PersistentTrialRuntimeSmoke.setUp
    create_runtime=fixture.PersistentTrialRuntimeSmoke.create

    def setUp(self):
        self.setUp_fixture()
        self.token=bind_memory_principal('local_admin');self.addCleanup(reset_memory_principal,self.token)

    def registered(self, principal='local_admin'):
        owner=self.create_runtime()
        registry=TrialRuntimeRegistry.create(self.parent,'registry',runtime=owner,principal=principal)
        return owner,registry

    def assert_sanitized(self,result):
        self.assertEqual(set(result),FIELDS)
        for key in FIELDS-{'status','orders_sent'}:self.assertIs(type(result[key]),bool)
        self.assertIs(type(result['orders_sent']),int);self.assertEqual(result['orders_sent'],0)
        for key in ('exchange_account_identity_verified','production_store_admitted','native_protection_qualified',
                    'live_dispatch_enabled','ready_for_live','account_accessed'):
            self.assertIs(result[key],False)

    def test_01_default_singleton_has_no_creation_or_status_io_on_construction(self):
        with patch.object(Path,'mkdir',side_effect=AssertionError('no creation')),patch.object(Path,'exists',side_effect=AssertionError('no stat')):
            first=get_default_registry();self.assertIs(get_default_registry(),first)
            self.assertEqual(first.root,Path('C:/AI-BS/saved_data/crypto_trial_registry'))

    def test_02_anonymous_denied_before_any_lease_io(self):
        registry=TrialRuntimeRegistry(self.parent/'absent')
        with patch('core.crypto_trial_registry.current_memory_principal',return_value=None), \
             patch('core.crypto_trial_registry.TrialRootLease.open_for_locator',side_effect=AssertionError('no root read')), \
             patch.object(Path,'exists',side_effect=AssertionError('no stat')):
            result=registry.status()
        self.assertEqual(result['status'],'denied');self.assert_sanitized(result)

    def test_03_missing_registry_does_not_create_files(self):
        root=self.parent/'not-created';registry=TrialRuntimeRegistry(root)
        result=registry.status()
        self.assertEqual(result['status'],'not_registered');self.assertFalse(result['registered'])
        self.assertFalse(root.exists());self.assert_sanitized(result)

    def test_04_active_owner_is_borrowed_never_closed(self):
        owner,registry=self.registered()
        with patch.object(owner,'close',wraps=owner.close) as close:
            result=registry.status();close.assert_not_called()
        self.assertEqual(result['status'],'qualification');self.assertTrue(result['stored_state_verified'])
        self.assertTrue(result['local_entry_cutoff_enforced']);self.assertFalse(owner._closed)
        self.assert_sanitized(result)

    def test_05_closed_owner_reopens_exact_descriptor_and_closes_owned_runtime(self):
        owner,registry=self.registered();owner.close();opened=[]
        original=PersistentTrialRuntime.open
        def opening(*args,**kwargs):
            runtime=original(*args,**kwargs);opened.append(runtime);return runtime
        with patch('core.crypto_trial_registry.PersistentTrialRuntime.open',side_effect=opening):result=registry.status()
        self.assertEqual(result['status'],'qualification');self.assertEqual(len(opened),1)
        self.assertTrue(opened[0]._closed);self.assert_sanitized(result)

    def test_06_principal_mismatch_denied_before_runtime_open(self):
        owner,registry=self.registered();owner.close()
        token=bind_memory_principal('firebase:synthetic:other')
        try:
            with patch('core.crypto_trial_registry.PersistentTrialRuntime.open',side_effect=AssertionError('no runtime read')):
                result=registry.status()
        finally:reset_memory_principal(token)
        self.assertEqual(result['status'],'denied');self.assert_sanitized(result)

    def test_07_corrupt_registry_is_generic_unavailable(self):
        owner,registry=self.registered();(registry.root/'registry.json').write_bytes(b'{SYNTHETIC_PRIVATE_DETAIL')
        result=registry.status();self.assertEqual(result['status'],'unavailable')
        self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL',json.dumps(result));self.assert_sanitized(result)

    def test_08_descriptor_root_identity_binding_cannot_be_rewritten(self):
        owner,registry=self.registered();path=registry.root/'registry.json'
        envelope=json.loads(path.read_text());record=envelope['record'];record['root_identity'][1]+=1
        envelope['sha256']=digest(record);path.write_text(json.dumps(envelope,indent=2))
        result=registry.status();self.assertEqual(result['status'],'unavailable');self.assert_sanitized(result)

    def test_09_root_acl_drift_rejected_without_repair(self):
        owner,registry=self.registered();path=registry.root
        sd=win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION)
        acl=sd.GetSecurityDescriptorDacl();acl.AddAccessAllowedAceEx(win32security.ACL_REVISION,3,0x120089,
            win32security.ConvertStringSidToSid('S-1-5-32-545'))
        win32security.SetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION|win32security.PROTECTED_DACL_SECURITY_INFORMATION,None,None,acl,None)
        result=registry.status();self.assertEqual(result['status'],'unavailable')
        self.assertEqual(win32security.GetNamedSecurityInfo(str(path),win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl().GetAceCount(),4)

    def test_10_busy_runtime_fails_closed_without_borrowing_other_owner(self):
        owner,registry=self.registered();owner.close()
        other=PersistentTrialRuntime.open(owner.root,expected_store_uuid=owner.store_uuid,
            expected_account=self.observation.account,qualification=True);self.addCleanup(other.close)
        result=registry.status();self.assertEqual(result['status'],'unavailable')
        self.assertFalse(other._closed);self.assert_sanitized(result)

    def test_11_missing_accounting_database_not_reinitialized(self):
        owner,registry=self.registered();owner.close()
        path=owner.root/'accounting.sqlite3';path.rename(owner.root/'accounting.retained')
        result=registry.status();self.assertEqual(result['status'],'unavailable')
        self.assertFalse(path.exists());self.assert_sanitized(result)

    def test_12_status_contains_no_descriptors_secrets_or_settings(self):
        owner,registry=self.registered();result=registry.status();encoded=json.dumps(result)
        for value in (str(owner.root),owner.store_uuid,self.observation.account,'local_admin','seed_budget_usdt'):
            self.assertNotIn(value,encoded)
        self.assert_sanitized(result)

    def test_13_registration_requires_matching_current_principal_before_create(self):
        with patch('core.crypto_trial_registry.TrialRootLease.create',side_effect=AssertionError('no creation')):
            with self.assertRaises((ControlError,PermissionError)):
                TrialRuntimeRegistry.create(self.parent,'registry',runtime=None,principal='firebase:synthetic:other')
        self.assertFalse((self.parent/'registry').exists())

    def test_14_firebase_principal_matching_registration_is_scoped(self):
        principal='firebase:synthetic:owner';token=bind_memory_principal(principal)
        try:
            owner,registry=self.registered(principal)
            self.assertEqual(registry.status()['status'],'qualification')
        finally:reset_memory_principal(token)
        self.assertEqual(registry.status()['status'],'denied')

    def test_15_borrowed_runtime_failure_never_closes_it_or_leaks_details(self):
        owner,registry=self.registered()
        with patch.object(owner,'status',side_effect=RuntimeError('SYNTHETIC_PRIVATE_DETAIL')), \
             patch.object(owner,'close',wraps=owner.close) as close:
            result=registry.status();close.assert_not_called()
        self.assertEqual(result['status'],'unavailable');self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL',json.dumps(result))
        self.assertFalse(owner._closed);self.assert_sanitized(result)


if __name__=='__main__':unittest.main()
