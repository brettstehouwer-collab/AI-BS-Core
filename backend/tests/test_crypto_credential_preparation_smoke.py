"""Fifteen typed credential preparation cases; synthetic responses only."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import hmac
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_execution_controls import ControlError, digest
from core.crypto_credential_preparation import (CredentialPreparation, TestCredentialPreparation,
    read_credential_preparation,is_credential_preparation,validate_preparation,preparation_status)
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal

NOW=1794781200000


class CredentialPreparationSmoke(unittest.TestCase):
    def setUp(self):
        self.token=bind_memory_principal('local_admin');self.addCleanup(reset_memory_principal,self.token)
        self.trial=str(uuid4());self.saved=[];self.provider_calls=0

    def provider(self):
        self.provider_calls+=1
        return 'synthetic-key','synthetic-secret'

    def read(self,*,trial=None,times=None,sink=None,body=None,provider=None):
        ticks=iter(times or [NOW,NOW+1,NOW+2])
        response=body or {'id':1,'method':'private/get-accounts','code':0,
            'result':{'this_account':{'uuid':'bb8ddc69-aea2-4a9d-80cf-0cad120d3011','hierarchy':'MASTER'}}}
        return read_credential_preparation(local_trial_uuid=trial or self.trial,credential_provider=provider or self.provider,
            private_sink=sink or self.saved.append,qualification_transport=lambda url,raw:(200,json.dumps(response).encode()),
            clock_ms=lambda:next(ticks))

    def validate(self,value,**changes):
        record=value.to_record()
        args=dict(principal='local_admin',credential_partition_sha256=record['credential_partition_sha256'],
            credential_generation_sha256=record['credential_generation_sha256'],now_ms=NOW+2,allow_test=True)
        args.update(changes)
        return validate_preparation(value,**args)

    def test_01_local_trial_namespace_not_exchange_identity(self):
        value=self.read();record=self.validate(value)
        self.assertEqual(record['local_trial_uuid'],self.trial);self.assertIsNone(record['exchange_account_id'])
        self.assertFalse(record['account_identity_verified']);self.assertEqual(record['principal'],'local_admin')
        self.assertNotIn('cash',record);self.assertNotIn('account',record)
        self.assertEqual(record['request_sha256'],sha256(self.saved[0]['request_bytes']).hexdigest())
        self.assertEqual(record['response_sha256'],sha256(self.saved[0]['response_bytes']).hexdigest())

    def test_02_provider_invoked_once_and_private_sink_receipts(self):
        value=self.read();self.assertEqual(self.provider_calls,1);self.assertEqual(len(self.saved),2)
        self.assertEqual(self.saved[1]['record'],value.to_record())

    def test_03_partition_and_generation_private_fingerprints(self):
        record=self.read().to_record()
        self.assertEqual(record['credential_partition_sha256'],digest({'provider':'CRYPTOCOM_EXCHANGE_V1','api_key':'synthetic-key'}))
        expected=hmac.new(b'synthetic-secret',b'AI-BS/credential-preparation-generation/v1\0synthetic-key',sha256).hexdigest()
        self.assertEqual(record['credential_generation_sha256'],expected)
        self.assertNotIn('synthetic-key',json.dumps(record));self.assertNotIn('synthetic-secret',json.dumps(record))

    def test_04_injected_transport_distinct_and_rejected_by_default(self):
        value=self.read();self.assertIsInstance(value,TestCredentialPreparation)
        self.assertFalse(is_credential_preparation(value));self.assertTrue(is_credential_preparation(value,allow_test=True))
        with self.assertRaises(ControlError):self.validate(value,allow_test=False)

    def test_05_missing_principal_before_credentials(self):
        with patch('core.crypto_credential_preparation.current_memory_principal',return_value=None):
            with self.assertRaises(ControlError):self.read()
        self.assertEqual(self.provider_calls,0);self.assertEqual(self.saved,[])
        principal='firebase:long-project:'+('u'*128)
        token=bind_memory_principal(principal)
        try:
            value=self.read();self.assertEqual(value.to_record()['principal'],principal)
            self.assertEqual(self.validate(value,principal=principal)['principal'],principal)
        finally:reset_memory_principal(token)
        with patch('core.crypto_credential_preparation.current_memory_principal',return_value='firebase:p:x'+chr(127)):
            with self.assertRaises(ControlError):self.read()

    def test_06_principal_switch_during_read_refused(self):
        def sink(record):
            self.saved.append(record)
            if len(self.saved)==1:bind_memory_principal('firebase:project:different_owner')
        with self.assertRaises(ControlError):self.read(sink=sink)

    def test_07_cross_principal_validation_refused(self):
        value=self.read()
        with self.assertRaises(ControlError):self.validate(value,principal='different_owner')

    def test_08_cross_key_or_rotation_validation_refused(self):
        value=self.read()
        for changes in ({'credential_partition_sha256':'a'*64},{'credential_generation_sha256':'b'*64}):
            with self.subTest(changes=changes),self.assertRaises(ControlError):self.validate(value,**changes)
        rotated=self.read(provider=lambda:('synthetic-key','rotated-synthetic-secret'))
        before,after=value.to_record(),rotated.to_record()
        self.assertEqual(before['credential_partition_sha256'],after['credential_partition_sha256'])
        self.assertNotEqual(before['credential_generation_sha256'],after['credential_generation_sha256'])
        with self.assertRaises(ControlError):self.validate(rotated,credential_generation_sha256=before['credential_generation_sha256'])

    def test_09_freshness_future_reverse_and_stale_refused(self):
        value=self.read()
        for now in (NOW-1,NOW+60002,True):
            with self.subTest(now=now),self.assertRaises(ControlError):self.validate(value,now_ms=now)
        for times in ([NOW,NOW-1,NOW],[NOW,NOW+1,NOW],[NOW,NOW+1,NOW+60002]):
            with self.subTest(times=times),self.assertRaises(ControlError):self.read(times=times)

    def test_10_explicit_canonical_local_uuid(self):
        for trial in ('not-uuid',self.trial.upper()):
            with self.subTest(trial=trial),self.assertRaises(ControlError):self.read(trial=trial)

    def test_11_serialized_or_direct_capability_forgery_refused(self):
        value=self.read()
        self.assertFalse(is_credential_preparation(value.to_record(),allow_test=True))
        with self.assertRaises(ControlError):CredentialPreparation()
        with self.assertRaises(ControlError):validate_preparation(value.to_record(),principal='local_admin',
            credential_partition_sha256='a'*64,credential_generation_sha256='b'*64,now_ms=NOW+2,allow_test=True)

    def test_12_immutable_and_private_record_copy(self):
        value=self.read();before=value.to_record();changed=value.to_record();changed['principal']='changed'
        self.assertEqual(value.to_record(),before)
        with self.assertRaises(FrozenInstanceError):value._record=()

    def test_13_bad_metadata_does_not_issue_preparation(self):
        with self.assertRaises(ControlError):self.read(body={'id':2,'method':'private/get-accounts','code':0,'result':{}})

    def test_14_private_sink_failure_and_provider_error_redacted(self):
        def bad(value):raise RuntimeError('synthetic-secret')
        with self.assertRaises(ControlError) as caught:self.read(sink=bad)
        self.assertNotIn('synthetic-secret',str(caught.exception))
        def provider():raise RuntimeError('synthetic-secret')
        with self.assertRaises(ControlError) as caught:self.read(provider=provider)
        self.assertNotIn('synthetic-secret',str(caught.exception))

    def test_15_public_status_never_leaks_private_scope_or_authority(self):
        value=self.read();row=preparation_status(value,allow_test=True);rendered=json.dumps(row)
        for secret in (self.trial,'local_admin','synthetic-key','synthetic-secret',
                value.to_record()['credential_generation_sha256'],value.to_record()['credential_partition_sha256']):
            self.assertNotIn(secret,rendered)
        for key in ('live_dispatch_enabled','ready_for_live','native_order_accepted','account_identity_verified'):
            self.assertIs(row[key],False)
        self.assertEqual(row['orders_sent'],0)


if __name__=='__main__':unittest.main()
