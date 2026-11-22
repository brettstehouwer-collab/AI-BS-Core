"""Fifteen metadata reader cases with synthetic transport only."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import hmac
import json
import unittest
from unittest.mock import patch

from core.crypto_execution_controls import ControlError
from core.crypto_trial_binding import (CurrentAccountObservation, QualificationAccountObservation,
    read_current_account, qualification_account_observation, is_current_account_observation)


class TrialBindingSmoke(unittest.TestCase):
    uuid='63c61768-33ae-465e-bca9-9b161ba57703'

    def setUp(self):self.saved=[];self.requests=[]

    def response(self, **changes):
        return dict(dict(id=17,method='private/get-accounts',code=0,
            result={'this_account':{'uuid':self.uuid,'hierarchy':'MASTER'},
                    'master_account':{'uuid':self.uuid},'sub_account_list':[]}),**changes)

    def read(self, *, response=None,status=200,transport=None,sink=None,times=None,**changes):
        ticks=iter(times or [1800000000000,1800000000001])
        def fake(url,body):
            self.requests.append((url,body))
            return status,json.dumps(self.response() if response is None else response).encode()
        return read_current_account(credential_provider=lambda:('fixture-key','fixture-secret'),
            private_sink=sink or self.saved.append,request_id=17,clock_ms=lambda:next(ticks),
            qualification_transport=transport or fake,**changes)

    def test_01_metadata_uuid_and_scope(self):
        row=self.read();self.assertIsInstance(row,QualificationAccountObservation)
        self.assertEqual(row.account,'cryptocom-key-metadata:'+self.uuid)
        self.assertIsNone(row.account_id);self.assertEqual(row.scope,'QUALIFICATION_ONLY')
        self.assertEqual(row.to_record()['key_metadata_uuid'],self.uuid)
        self.assertIsNone(row.to_record()['trade_account_id'])

    def test_02_missing_wrong_uuid(self):
        for value in (None,'not-uuid',self.uuid.upper()):
            body=self.response();body['result']['this_account']['uuid']=value
            with self.subTest(value=value),self.assertRaises(ControlError):self.read(response=body)

    def test_03_current_identity_not_master_or_subaccount(self):
        body=self.response();body['result']['master_account']['uuid']='b699f9f6-20c9-44dd-bb37-434b17abca90'
        self.assertEqual(self.read(response=body).to_record()['key_metadata_uuid'],self.uuid)
        del body['result']['this_account']
        with self.assertRaises(ControlError):self.read(response=body)

    def test_04_correlation_and_code(self):
        for changes in ({'id':18},{'id':True},{'method':'private/user-balance'},{'code':1},{'code':False}):
            with self.subTest(changes=changes),self.assertRaises(ControlError):self.read(response=self.response(**changes))

    def test_05_status_and_redirect_refused(self):
        for status in (301,302,403,500):
            with self.subTest(status=status),self.assertRaises(ControlError):self.read(status=status)

    def test_06_nonce_and_interval_bounds(self):
        for ticks in ([True,1800000000001],[1,2],[1800000000000,1799999999999],
                      [1800000000000,1800000010001]):
            with self.subTest(ticks=ticks),self.assertRaises(ControlError):self.read(times=ticks)

    def test_07_fixed_host_method_and_no_extra_params(self):
        self.read();url,raw=self.requests[0];body=json.loads(raw)
        self.assertEqual(url,'https://api.crypto.com/exchange/v1/private/get-accounts')
        self.assertEqual(body['method'],'private/get-accounts');self.assertEqual(body['params'],{})
        self.assertEqual(body['nonce'],'1800000000000')

    def test_08_signature_exact_official_empty_params(self):
        self.read();body=json.loads(self.requests[0][1])
        expected=hmac.new(b'fixture-secret',b'private/get-accounts17fixture-key1800000000000',sha256).hexdigest()
        self.assertEqual(body['sig'],expected)
        self.assertNotIn('fixture-secret',self.requests[0][1].decode())

    def test_09_private_sink_before_issuance(self):
        row=self.read();self.assertEqual(len(self.saved),1)
        self.assertEqual(sha256(self.saved[0]['response_bytes']).hexdigest(),row.to_record()['response_sha256'])
        self.assertEqual(sha256(self.saved[0]['request_bytes']).hexdigest(),row.to_record()['request_sha256'])
        def broken(value):raise OSError('fixture-secret raw private data')
        with self.assertRaises(ControlError) as caught:self.read(sink=broken)
        self.assertNotIn('fixture-secret',str(caught.exception))

    def test_10_failure_redaction_and_no_chained_secret(self):
        def broken(url,body):raise RuntimeError('fixture-secret fixture-key')
        with self.assertRaises(ControlError) as caught:self.read(transport=broken)
        self.assertNotIn('fixture-secret',str(caught.exception));self.assertIsNone(caught.exception.__cause__)

    def test_11_observation_frozen_and_opaque(self):
        row=self.read()
        with self.assertRaises(FrozenInstanceError):row.account_id='changed'
        self.assertFalse(is_current_account_observation(row))
        self.assertTrue(is_current_account_observation(row,qualification=True))
        self.assertFalse(is_current_account_observation(row.to_record(),qualification=True))
        with self.assertRaises(ControlError):CurrentAccountObservation()

    def test_12_factory_never_verified(self):
        row=qualification_account_observation(account_id=self.uuid,started_ms=1800000000000,completed_ms=1800000000001)
        self.assertEqual(row.scope,'QUALIFICATION_ONLY');self.assertFalse(is_current_account_observation(row))

    def test_13_malformed_duplicate_and_oversize_json(self):
        for raw in (b'not-json',b'{"id":17,"id":18}',b'x'*262145):
            with self.subTest(size=len(raw)),self.assertRaises(ControlError):self.read(transport=lambda u,b:(200,raw))

    def test_14_no_raw_metadata_or_credentials_in_record(self):
        row=self.read();rendered=repr(row)+json.dumps(row.to_record())
        self.assertNotIn('fixture-key',rendered);self.assertNotIn('fixture-secret',rendered)
        for key in ('live_dispatch_enabled','ready_for_live','native_order_accepted'):
            self.assertIs(row.to_record()[key],False)
        self.assertEqual(row.to_record()['orders_sent'],0)

    def test_15_builtin_transport_fixed_tls_contract_without_network(self):
        with patch('core.crypto_trial_binding.http.client.HTTPSConnection') as connection:
            connection.return_value.getresponse.return_value.status=200
            connection.return_value.getresponse.return_value.read.return_value=json.dumps(self.response()).encode()
            row=read_current_account(credential_provider=lambda:('fixture-key','fixture-secret'),
                private_sink=self.saved.append,request_id=17)
            self.assertEqual(connection.call_args.args[0],'api.crypto.com')
            self.assertTrue(connection.call_args.kwargs['context'].check_hostname)
            self.assertEqual(connection.return_value.request.call_args.args[:2],('POST','/exchange/v1/private/get-accounts'))
            # Mocked built-in transport is fixture verification, never real Exchange evidence.
            self.assertEqual(row.scope,'VERIFIED_TLS_CURRENT_KEY_METADATA')
            self.assertIsNone(row.account_id)
            self.assertFalse(row.to_record()['account_identity_verified'])


if __name__=='__main__':unittest.main()
