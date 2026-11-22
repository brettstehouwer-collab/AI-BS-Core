"""Fifteen sealed current-state reader cases; no actual private requests."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import hmac
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_execution_controls import ControlError
from core.crypto_credential_preparation import read_credential_preparation
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from core.crypto_current_snapshot import (CurrentSnapshot,TestCurrentSnapshot,read_current_snapshot,
    is_current_snapshot,validate_current_snapshot,snapshot_status,_builtin_transport)

NOW=1794781200000


class CurrentSnapshotSmoke(unittest.TestCase):
    def setUp(self):
        self.token=bind_memory_principal('local_admin');self.addCleanup(reset_memory_principal,self.token)
        self.saved=[];self.requests=[];self.calls=0;self.trial=str(uuid4())
        ticks=iter([NOW,NOW+1,NOW+2])
        body={'id':1,'method':'private/get-accounts','code':0,
            'result':{'this_account':{'uuid':'bb8ddc69-aea2-4a9d-80cf-0cad120d3011','hierarchy':'MASTER'}}}
        self.preparation=read_credential_preparation(local_trial_uuid=self.trial,
            credential_provider=lambda:('synthetic-key','synthetic-secret'),private_sink=lambda row:None,
            qualification_transport=lambda url,raw:(200,json.dumps(body).encode()),clock_ms=lambda:next(ticks))

    def facts(self):
        balance={'data':[{'instrument_name':'USD','total_available_balance':'100','total_cash_balance':'100',
            'total_borrow':'0','has_risk':False,'is_liquidating':False,'position_balances':[
                {'instrument_name':'CRO','quantity':'0','reserved_qty':'0'},
                {'instrument_name':'USDT','quantity':'100','reserved_qty':'0'}]}]}
        return {'before':balance,'ordinary':{'data':[]},'advanced':{'data':[]},'positions':{'data':[]},
            'fees':{'instrument_name':'CRO_USDT','effective_maker_rate_bps':'25','effective_taker_rate_bps':'50'},'after':balance}

    def provider(self):self.calls+=1;return 'synthetic-key','synthetic-secret'

    def read(self,*,transport=None,sink=None,provider=None,clock=None):
        labels=iter(('before','ordinary','advanced','positions','fees','after'));tick=iter(range(NOW+10,NOW+100))
        def fake(url,raw):
            label=next(labels);body=json.loads(raw);self.requests.append((url,body,raw))
            return 200,json.dumps({'id':int(body['id']),'method':body['method'],'code':0,'result':self.facts()[label]}).encode()
        return read_current_snapshot(preparation=self.preparation,credential_provider=provider or self.provider,
            private_sink=sink or self.saved.append,qualification_transport=transport or fake,clock_ms=clock or (lambda:next(tick)))

    def validate(self,value,**changes):
        preparation=self.preparation.to_record()
        args=dict(principal='local_admin',credential_partition_sha256=preparation['credential_partition_sha256'],
            credential_generation_sha256=preparation['credential_generation_sha256'],local_trial_uuid=self.trial,
            now_ms=NOW+100,allow_test=True);args.update(changes)
        return validate_current_snapshot(value,**args)

    def test_01_six_read_capability_is_nonatomic_and_held(self):
        value=self.read();record=self.validate(value)
        self.assertIsInstance(value,TestCurrentSnapshot);self.assertEqual(len(record['reads']),6)
        self.assertIsNone(record['exchange_account_id']);self.assertFalse(record['atomic_snapshot_verified'])
        self.assertFalse(record['full_order_family_coverage_verified']);self.assertFalse(record['ready_for_live'])
        self.assertEqual(record['source_preparation_receipt_sha256'],self.preparation.to_record()['receipt_sha256'])

    def test_02_exact_methods_pair_once_and_signatures(self):
        self.read();self.assertEqual(self.calls,1)
        methods=['private/user-balance','private/get-open-orders','private/advanced/get-open-orders',
            'private/get-positions','private/get-instrument-fee-rate','private/user-balance']
        self.assertEqual([row[1]['method'] for row in self.requests],methods)
        for index,(url,body,raw) in enumerate(self.requests):
            self.assertEqual(url,'https://api.crypto.com/exchange/v1/'+methods[index])
            params='instrument_nameCRO_USDT' if index==4 else ''
            payload=body['method']+body['id']+body['api_key']+params+body['nonce']
            self.assertEqual(body['sig'],hmac.new(b'synthetic-secret',payload.encode(),sha256).hexdigest())
            self.assertNotIn(b'synthetic-secret',raw)

    def test_03_pair_rotation_refuses_before_transport(self):
        with self.assertRaises(ControlError):self.read(provider=lambda:('synthetic-key','rotated-secret'))
        self.assertEqual(self.requests,[]);self.assertEqual(self.saved,[])

    def test_04_missing_or_changed_principal_before_transport(self):
        for principal in (None,'firebase:p:different'):
            with patch('core.crypto_current_snapshot.current_memory_principal',return_value=principal):
                with self.assertRaises(ControlError):self.read()
        self.assertEqual(self.requests,[])

    def test_05_test_preparation_never_builtin_or_default_authority(self):
        with self.assertRaises(ControlError):read_current_snapshot(preparation=self.preparation,
            credential_provider=self.provider,private_sink=self.saved.append)
        value=self.read();self.assertFalse(is_current_snapshot(value));self.assertTrue(is_current_snapshot(value,allow_test=True))
        with self.assertRaises(ControlError):self.validate(value,allow_test=False)

    def test_06_all_raw_saved_before_facts_projection(self):
        from core.crypto_current_snapshot_facts import project_current_snapshot
        def observed(results):
            self.assertEqual(len(self.saved),6)
            self.assertEqual(set(results),set(self.facts()))
            return project_current_snapshot(results)
        with patch('core.crypto_current_snapshot.project_current_snapshot',side_effect=observed):value=self.read()
        self.assertEqual(len(self.saved),7);self.assertEqual(self.saved[-1]['record'],value.to_record())

    def test_07_correlation_http_code_refuse_raw_retained(self):
        for changes,status in (({'id':99},200),({'method':'private/get-trades'},200),({'code':1},200),({},302)):
            self.saved=[]
            def bad(url,raw):
                body=json.loads(raw);reply={'id':int(body['id']),'method':body['method'],'code':0,'result':self.facts()['before']}
                reply.update(changes);return status,json.dumps(reply).encode()
            with self.subTest(changes=changes,status=status),self.assertRaises(ControlError):self.read(transport=bad)
            self.assertEqual(len(self.saved),1)

    def test_08_malformed_duplicate_json_retained(self):
        for raw in (b'not-json',b'{"id":1,"id":1}'):
            self.saved=[]
            with self.assertRaises(ControlError):self.read(transport=lambda url,body:(200,raw))
            self.assertEqual(self.saved[0]['response_bytes'],raw)

    def test_09_oversize_response_refused(self):
        with self.assertRaises(ControlError):self.read(transport=lambda url,body:(200,b'x'*262145))

    def test_10_sink_failure_redacted(self):
        def fail(row):raise RuntimeError('synthetic-secret private-body')
        with self.assertRaises(ControlError) as caught:self.read(sink=fail)
        self.assertNotIn('synthetic-secret',str(caught.exception))

    def test_11_interval_future_reverse_and_stale_refuse(self):
        for tick in (NOW-1,NOW+60002):
            with self.subTest(tick=tick),self.assertRaises(ControlError):self.read(clock=lambda:tick)
        ticks=iter([NOW+10,NOW+11,NOW+9])
        with self.assertRaises(ControlError):self.read(clock=lambda:next(ticks))

    def test_12_validator_scope_freshness_and_json_forgery(self):
        value=self.read()
        for changes in ({'principal':'firebase:p:other'},{'credential_generation_sha256':'a'*64},
            {'credential_partition_sha256':'b'*64},{'local_trial_uuid':str(uuid4())},{'now_ms':NOW},{'now_ms':NOW+70000}):
            with self.subTest(changes=changes),self.assertRaises(ControlError):self.validate(value,**changes)
        self.assertFalse(is_current_snapshot(value.to_record(),allow_test=True))
        with self.assertRaises(ControlError):CurrentSnapshot()

    def test_13_nested_record_immutable_copy(self):
        value=self.read();original=value.to_record();copy=value.to_record();copy['reads'][0]['method']='changed';copy['private_facts'].clear()
        self.assertEqual(value.to_record(),original)
        with self.assertRaises(FrozenInstanceError):value._payload='changed'

    def test_14_builtin_fixed_tls_contract_without_network(self):
        with patch('core.crypto_current_snapshot.http.client.HTTPSConnection') as connection:
            connection.return_value.getresponse.return_value.status=302
            connection.return_value.getresponse.return_value.read.return_value=b'{}'
            self.assertEqual(_builtin_transport('private/user-balance',b'{}'),(302,b'{}'))
            self.assertEqual(connection.call_args.args[0],'api.crypto.com')
            self.assertTrue(connection.call_args.kwargs['context'].check_hostname)
            self.assertEqual(connection.return_value.request.call_args.args[:2],('POST','/exchange/v1/private/user-balance'))
        with self.assertRaises(ControlError):_builtin_transport('private/create-order',b'{}')

    def test_15_sanitized_status_has_no_private_facts_or_digests(self):
        value=self.read();row=snapshot_status(value,allow_test=True);rendered=json.dumps(row)
        for secret in (self.trial,'local_admin','synthetic-key','synthetic-secret',value.to_record()['credential_generation_sha256']):
            self.assertNotIn(secret,rendered)
        self.assertNotIn('private_facts',row);self.assertFalse(row['ready_for_live']);self.assertEqual(row['orders_sent'],0)


if __name__=='__main__':unittest.main()
