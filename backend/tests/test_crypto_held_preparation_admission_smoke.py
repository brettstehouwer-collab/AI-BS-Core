"""Fifteen independent held-admission fences using issued synthetic capabilities."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_held_preparation_runtime import HeldPreparationRuntime
from core.crypto_credential_preparation import read_credential_preparation
from core.crypto_current_snapshot import read_current_snapshot
from core.crypto_credential_preparation_registry import CredentialPreparationRegistry
from core.crypto_execution_controls import ControlError
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from security.crypto_trial_root import TrialRootError

NOW=1794787200000
REFUSAL=(ControlError,PermissionError,ValueError,TrialRootError)


class HeldPreparationAdmissionSmoke(unittest.TestCase):
    def setUp(self):
        self.parent=Path('C:/AI-BS/backups')/('crypto_held_admission_fixture_'+uuid4().hex)
        self.parent.mkdir();self.token=bind_memory_principal('local_admin')
        self.addCleanup(reset_memory_principal,self.token);self.owners=[]
        self.addCleanup(lambda:[owner.close() for owner in reversed(self.owners)])
        self.trial=str(uuid4());self.preparation=self.prep();self.snapshot=self.observe(self.preparation)
        record=self.preparation.to_record()
        self.registry=CredentialPreparationRegistry.create(self.parent,'test-index',preparation=self.preparation,
            credential_partition_sha256=record['credential_partition_sha256'],
            credential_generation_sha256=record['credential_generation_sha256'],now_ms=NOW+100,allow_test=True)
        self.owners.append(self.registry)

    def prep(self,*,trial=None,key='SYNTHETIC_KEY',secret='SYNTHETIC_SECRET',offset=0):
        def transport(url,raw):
            body=json.loads(raw)
            return 200,json.dumps(dict(id=body['id'],method=body['method'],code=0,
                result={'this_account':{'uuid':'11111111-1111-4111-8111-111111111111','hierarchy':'MASTER'}})).encode()
        ticks=iter((NOW+offset,NOW+offset+1,NOW+offset+2))
        return read_credential_preparation(local_trial_uuid=trial or self.trial,
            credential_provider=lambda:(key,secret),private_sink=lambda record:None,
            qualification_transport=transport,clock_ms=lambda:next(ticks))

    def facts(self):
        balance={'data':[{'has_risk':False,'is_liquidating':False,'total_borrow':'0','isolated_positions':[],
            'position_balances':[{'instrument_name':'USDT','quantity':'100','reserved_qty':'0'},
                {'instrument_name':'CRO','quantity':'7.5','reserved_qty':'0'}]}]}
        return dict(before=deepcopy(balance),after=deepcopy(balance),ordinary={'data':[]},advanced={'data':[]},
            positions={'data':[]},fees={'instrument_name':'CRO_USDT','effective_maker_rate_bps':'25','effective_taker_rate_bps':'50'})

    def observe(self,preparation,*,facts=None,key='SYNTHETIC_KEY',secret='SYNTHETIC_SECRET',offset=10):
        facts=facts or self.facts();labels=iter(('before','ordinary','advanced','positions','fees','after'))
        def transport(url,raw):
            body=json.loads(raw);label=next(labels)
            return 200,json.dumps(dict(id=body['id'],method=body['method'],code=0,result=facts[label])).encode()
        ticks=iter(range(NOW+offset,NOW+offset+100))
        return read_current_snapshot(preparation=preparation,credential_provider=lambda:(key,secret),
            private_sink=lambda record:None,qualification_transport=transport,clock_ms=lambda:next(ticks))

    def args(self,**changes):
        record=self.preparation.to_record()
        args=dict(preparation=self.preparation,snapshot=self.snapshot,
            credential_partition_sha256=record['credential_partition_sha256'],
            credential_generation_sha256=record['credential_generation_sha256'],
            seed_budget_usdt='2',max_entry_budget_usdt='10',daily_loss_budget_usdt='1',now_ms=NOW+100,allow_test=True)
        args.update(changes);return args

    def create(self,**changes):
        owner=HeldPreparationRuntime.create(self.registry,**self.args(**changes));self.owners.append(owner);return owner

    def assert_uncreated(self):
        self.assertFalse((self.registry.path/'held-runtime').exists())
        self.assertFalse((self.registry.path/'held-runtime-binding.json').exists())

    def test_01_success_is_local_seed_only_and_never_dispatches(self):
        with patch('http.client.HTTPSConnection',side_effect=AssertionError('No network in held admission')):
            owner=self.create()
        status=owner.status();self.assertEqual(status['scope'],'HELD_CREDENTIAL_PREPARATION')
        for key in ('fresh_authority','external_funds_reserved','account_identity_verified','native_order_accepted',
                'live_dispatch_enabled','ready_for_live'):self.assertIs(status[key],False)
        self.assertTrue(status['local_seed_allocated']);self.assertTrue(status['test_only'])
        self.assertIsNone(status['exchange_account_id']);self.assertEqual(status['orders_sent'],0)
        self.assertEqual(owner.coordinator.snapshot()['orders'],[])

    def test_02_test_capabilities_cannot_enter_actual_mode(self):
        with self.assertRaises(REFUSAL):self.create(allow_test=False)
        self.assert_uncreated()

    def test_03_wrong_principal_refuses_before_runtime_creation(self):
        token=bind_memory_principal('firebase:project:other-user')
        try:
            with self.assertRaises(REFUSAL):self.create()
        finally:reset_memory_principal(token)
        self.assert_uncreated()

    def test_04_rotated_secret_generation_cannot_reassign_index(self):
        for key,secret in (('SYNTHETIC_KEY','ROTATED_SECRET'),('ROTATED_KEY','SYNTHETIC_SECRET')):
            cap=self.prep(key=key,secret=secret);snap=self.observe(cap,key=key,secret=secret)
            record=cap.to_record()
            with self.subTest(key=key),self.assertRaises(REFUSAL):self.create(preparation=cap,snapshot=snap,
                credential_partition_sha256=record['credential_partition_sha256'],
                credential_generation_sha256=record['credential_generation_sha256'])
            self.assert_uncreated()

    def test_05_different_local_trial_cannot_reassign_index(self):
        cap=self.prep(trial=str(uuid4()));snap=self.observe(cap)
        with self.assertRaises(REFUSAL):self.create(preparation=cap,snapshot=snap)
        self.assert_uncreated()

    def test_06_snapshot_matches_fresh_preparation_and_renewal_survives_index_reopen(self):
        other=self.prep(offset=3);snap=self.observe(other,offset=20)
        self.assertNotEqual(other.to_record()['receipt_sha256'],self.preparation.to_record()['receipt_sha256'])
        with self.assertRaises(REFUSAL):self.create(snapshot=snap)
        self.assert_uncreated()
        path,identity=self.registry.path,self.registry.identity;self.registry.close()
        self.registry=CredentialPreparationRegistry.open(path,expected_identity=identity,allow_test=True)
        self.owners.append(self.registry)
        owner=self.create(preparation=other,snapshot=snap)
        self.assertEqual(owner.status()['scope'],'HELD_CREDENTIAL_PREPARATION')
        self.assertFalse(owner.status()['ready_for_live'])

    def test_07_stale_capabilities_do_not_initialize_runtime(self):
        with self.assertRaises(REFUSAL):self.create(now_ms=NOW+70000)
        self.assert_uncreated()

    def test_08_future_snapshot_does_not_initialize_runtime(self):
        with self.assertRaises(REFUSAL):self.create(now_ms=NOW+5)
        self.assert_uncreated()

    def test_09_explicit_seed_cannot_exceed_observed_free_usdt(self):
        facts=self.facts()
        for label in ('before','after'):facts[label]['data'][0]['position_balances'][0]['quantity']='1'
        snap=self.observe(self.preparation,facts=facts)
        with self.assertRaises(REFUSAL):self.create(snapshot=snap)
        self.assert_uncreated()

    def test_10_unknown_cash_never_becomes_zero_or_invented_cash(self):
        facts=self.facts()
        for label in ('before','after'):facts[label]['data'][0]['position_balances']=facts[label]['data'][0]['position_balances'][1:]
        snap=self.observe(self.preparation,facts=facts)
        self.assertIsNone(snap.to_record()['private_facts']['observed_free_quote_usdt'])
        with self.assertRaises(REFUSAL):self.create(snapshot=snap)
        self.assert_uncreated()

    def test_11_changed_balance_bracket_refuses_allocation(self):
        facts=self.facts();facts['after']['data'][0]['position_balances'][0]['quantity']='99'
        snap=self.observe(self.preparation,facts=facts)
        with self.assertRaises(REFUSAL):self.create(snapshot=snap)
        self.assert_uncreated()

    def test_12_original_cro_and_unallocated_cash_are_excluded(self):
        owner=self.create();snapshot=owner.coordinator.snapshot()
        balances={row['asset']:row['total'] for row in snapshot['balances']}
        self.assertEqual(balances['USDT'],'2');self.assertEqual(balances.get('CRO','0'),'0')
        self.assertEqual(snapshot['positions'],[]);self.assertEqual(snapshot['fills'],[])
        self.assertIsNone(self.snapshot.to_record()['private_facts']['preexisting_cro_basis_usdt'])

    def test_13_duplicate_create_after_reopen_cannot_reset_seed_or_store(self):
        owner=self.create();store_uuid=owner.store_uuid;owner.close()
        reopened=HeldPreparationRuntime.open(self.registry,expected_store_uuid=store_uuid,allow_test=True)
        self.owners.append(reopened);self.assertEqual(reopened.store_uuid,store_uuid)
        before=reopened.coordinator.snapshot()
        with self.assertRaises(REFUSAL):self.create(seed_budget_usdt='3')
        self.assertEqual(reopened.coordinator.snapshot(),before)

    def test_14_historical_index_review_cannot_create_runtime(self):
        path,identity=self.registry.path,self.registry.identity;self.registry.close()
        historical=CredentialPreparationRegistry.open(path,expected_identity=identity,allow_test=True,historical_review=True)
        self.owners.append(historical);self.registry=historical
        with self.assertRaises(REFUSAL):self.create()
        self.assert_uncreated()

    def test_15_serialized_records_never_recreate_issued_authority(self):
        for changes in ({'preparation':self.preparation.to_record()},{'snapshot':self.snapshot.to_record()}):
            with self.subTest(changes=tuple(changes)),self.assertRaises(REFUSAL):self.create(**changes)
        self.assert_uncreated()


if __name__=='__main__':unittest.main()



