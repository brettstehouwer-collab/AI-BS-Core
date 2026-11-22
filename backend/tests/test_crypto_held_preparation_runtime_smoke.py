"""Fifteen durable held-runtime ownership cases; actual issued TEST facts only."""
from pathlib import Path
import json
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_execution_controls import ControlError,Instrument,Fill
from core.crypto_held_preparation_runtime import HeldPreparationRuntime
from core.crypto_credential_preparation_registry import CredentialPreparationRegistry
from core.personal_memory_scope import bind_memory_principal,reset_memory_principal
from tests import test_crypto_held_preparation_admission_smoke as fixture

OUT=Path('C:/AI-BS/backups/crypto_held_preparation_runtime_20261115_v01')
NOW=fixture.NOW


class HeldPreparationRuntimeSmoke(unittest.TestCase):
    prep=fixture.HeldPreparationAdmissionSmoke.prep
    facts=fixture.HeldPreparationAdmissionSmoke.facts
    observe=fixture.HeldPreparationAdmissionSmoke.observe
    args=fixture.HeldPreparationAdmissionSmoke.args
    create=fixture.HeldPreparationAdmissionSmoke.create

    def setUp(self):
        OUT.mkdir(parents=True,exist_ok=True);self.parent=OUT/('fixture_'+uuid4().hex);self.parent.mkdir()
        self.token=bind_memory_principal('local_admin');self.addCleanup(reset_memory_principal,self.token)
        self.owners=[];self.addCleanup(lambda:[owner.close() for owner in reversed(self.owners)])
        self.trial=str(uuid4());self.preparation=self.prep();self.snapshot=self.observe(self.preparation)
        cap=self.preparation.to_record()
        self.registry=CredentialPreparationRegistry.create(self.parent,'index',preparation=self.preparation,
            credential_partition_sha256=cap['credential_partition_sha256'],credential_generation_sha256=cap['credential_generation_sha256'],
            now_ms=NOW+100,allow_test=True);self.owners.append(self.registry)

    def reopen(self,owner):
        result=HeldPreparationRuntime.open(self.registry,expected_store_uuid=owner.store_uuid,allow_test=True)
        self.owners.append(result);return result

    def test_01_root_is_fixed_inside_selected_index(self):
        owner=self.create();self.assertEqual(owner.root,self.registry.path/'held-runtime')
        self.assertTrue((owner.root/'accounting.sqlite3').is_file())
        self.assertEqual(len(list(self.registry.path.rglob('accounting.sqlite3'))),1)

    def test_02_opening_baseline_and_mode_bound_before_financial_store(self):
        owner=self.create();record=owner._record
        self.assertEqual(record['mode'],'HELD_CREDENTIAL_PREPARATION');self.assertNotIn('qualification',record)
        opening=json.loads((owner.root/'opening.json').read_text())['record']
        self.assertEqual(opening['preparation']['receipt_sha256'],self.preparation.to_record()['receipt_sha256'])
        self.assertEqual(opening['snapshot']['receipt_sha256'],self.snapshot.to_record()['receipt_sha256'])
        self.assertEqual(record['account'],'cryptocom-local-trial:'+self.trial)
        self.assertEqual(record['baseline']['started_ms'],self.snapshot.to_record()['completed_ms'])

    def test_03_seed_only_cash_preexisting_cro_excluded(self):
        owner=self.create();snapshot=owner.coordinator.snapshot()
        self.assertEqual(snapshot['balances'],[{'asset':'USDT','total':'2'}])
        self.assertEqual(snapshot['positions'],[])

    def test_04_existing_admission_and_reinvestment_tables_present(self):
        owner=self.create()
        with sqlite3.connect(owner.root/'accounting.sqlite3') as db:
            names={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'aibs_reinvestment_policy','aibs_trial_admission_policy','aibs_trial_entry_hold','aibs_trial_runtime_binding'}<=names)

    def test_05_initial_store_never_auto_prepares_or_submits(self):
        owner=self.create();snapshot=owner.coordinator.snapshot()
        for name in ('orders','fills','unmatched_fills','stops'):self.assertEqual(snapshot[name],[])
        self.assertFalse(owner.status()['ready_for_live'])

    def test_06_normal_reopen_same_uuid_and_opening(self):
        owner=self.create();record=owner._record;owner.close();other=self.reopen(owner)
        self.assertEqual(other.store_uuid,owner.store_uuid);self.assertEqual(other._record,record)
        self.assertFalse(other.status()['fresh_authority'])

    def test_07_duplicate_create_never_resets(self):
        owner=self.create();owner.close();before=(owner.root/'accounting.sqlite3').read_bytes()
        with self.assertRaises(ControlError):self.create()
        self.assertEqual((owner.root/'accounting.sqlite3').read_bytes(),before)

    def test_08_missing_db_is_retained_not_initialized(self):
        owner=self.create();owner.close();db=owner.root/'accounting.sqlite3';db.rename(owner.root/'retained.sqlite3')
        with self.assertRaises(ControlError):self.reopen(owner)
        self.assertFalse(db.exists())

    def test_09_corrupt_db_not_reinitialized(self):
        owner=self.create();owner.close();db=owner.root/'accounting.sqlite3';db.write_bytes(b'fixture-corrupt')
        with self.assertRaises(ControlError):self.reopen(owner)
        self.assertEqual(db.read_bytes(),b'fixture-corrupt')

    def test_10_creating_marker_survives_failed_bootstrap(self):
        with patch('core.crypto_held_preparation_runtime._HeldCoordinator.create',side_effect=ControlError('owned fixture failure')):
            with self.assertRaises(ControlError):self.create()
        marker=self.registry.path/'held-runtime-binding.json';before=marker.read_bytes()
        self.assertEqual(json.loads(before)['record']['state'],'CREATING')
        with self.assertRaises(ControlError):self.create()
        with self.assertRaises(ControlError):HeldPreparationRuntime.open(self.registry,allow_test=True)
        self.assertEqual(marker.read_bytes(),before)

    def test_11_second_runtime_owner_excluded(self):
        owner=self.create()
        with self.assertRaises(ControlError):self.reopen(owner)
        self.assertFalse(owner.status()['ready_for_live'])
        owner.close();lock=owner.root/'runtime.lock';lock.rename(owner.root/'runtime.lock.retained')
        with self.assertRaises(ControlError):self.reopen(owner)
        self.assertFalse(lock.exists())

    def test_12_index_close_revokes_retained_coordinator(self):
        owner=self.create();coordinator=owner.coordinator;self.registry.close()
        with self.assertRaises(ControlError):coordinator.snapshot()
        owner.close()

    def test_13_principal_change_revokes_old_objects(self):
        owner=self.create();token=bind_memory_principal('firebase:project:other-user')
        try:
            with self.assertRaises((ControlError,PermissionError)):owner.coordinator.snapshot()
        finally:reset_memory_principal(token)
        self.assertFalse(owner.status()['ready_for_live'])

    def test_14_index_binding_tamper_is_not_adopted(self):
        owner=self.create();marker=self.registry.path/'held-runtime-binding.json';marker.write_bytes(marker.read_bytes()+b' ')
        with self.assertRaises(ControlError):owner.coordinator.snapshot()

    def test_15_ready_is_read_only_and_does_not_enter_old_factory(self):
        owner=self.create();before=owner.coordinator.snapshot()
        with self.assertRaises(ControlError):owner.coordinator.quote_market(Instrument('CRO','USDT'),bid='0.1',ask='0.1',
            observed_ms=NOW+100,now_ms=NOW+100)
        self.assertEqual(owner.coordinator.snapshot(),before)
        with self.assertRaises(ControlError):owner.coordinator.apply_fill(Fill(fill_id='unmatched-fixture',client_id='unknown-client',
            exchange_order_id='unknown-order',symbol='CRO/USDT',side='buy',quantity='1',cost='0.1',
            fees=(),sequence=1,occurred_ms=NOW+100))
        self.assertEqual(owner.coordinator.snapshot(),before)
        from core.crypto_trial_runtime_store import PersistentTrialRuntime
        owner.close()
        with self.assertRaises(ControlError):PersistentTrialRuntime.open(owner.root,expected_store_uuid=owner.store_uuid,
            expected_account='cryptocom-local-trial:'+self.trial,qualification=False)


if __name__=='__main__':unittest.main()
