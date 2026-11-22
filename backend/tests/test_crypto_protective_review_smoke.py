"""Fifteen server-selected protective metadata review cases; no account I/O."""
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_execution_controls import ControlError, digest, encode
from core.crypto_protective_review_contract import protective_review, validate_protective_review
from core.crypto_protective_lifecycle import OfflineProtectiveLifecycle
from core.crypto_trial_binding import qualification_account_observation
from core.crypto_trial_budget import create_baseline
from core.crypto_trial_registry import TrialRuntimeRegistry
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from tests import test_crypto_protective_lifecycle_smoke as fixture

OUT=Path('C:/AI-BS/backups/crypto_protective_review_20261115_v01')
NOW=fixture.NOW


class ProtectiveReviewSmoke(unittest.TestCase):
    create=fixture.ProtectiveLifecycleSmoke.create
    quote=fixture.ProtectiveLifecycleSmoke.quote
    buy=fixture.ProtectiveLifecycleSmoke.buy
    prepare=fixture.ProtectiveLifecycleSmoke.prepare
    ack=fixture.ProtectiveLifecycleSmoke.ack
    detail=fixture.ProtectiveLifecycleSmoke.detail
    capture=fixture.ProtectiveLifecycleSmoke.capture

    def setUp(self):
        OUT.mkdir(parents=True,exist_ok=True);self.parent=OUT/('fixture_'+uuid4().hex);self.parent.mkdir()
        self.observation=qualification_account_observation(account_id=str(uuid4()),started_ms=NOW-101,completed_ms=NOW-2)
        self.baseline=create_baseline(trial_id=str(uuid4()),account=self.observation.account,started_ms=NOW-1,
            day_start_ms=((NOW-1)//86400000)*86400000,opening_receipt_sha256='c'*64)
        self.owner=self.create();self.token=bind_memory_principal('local_admin')
        self.addCleanup(reset_memory_principal,self.token)
        self.registry=TrialRuntimeRegistry.create(self.parent,'registry',runtime=self.owner,principal='local_admin')

    def tables(self):
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            return db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()

    def prepared(self):
        self.life=OfflineProtectiveLifecycle(self.owner);self.buy();self.prepare()

    def test_01_closed_contract_and_no_private_fields(self):
        row=protective_review('not_registered')
        self.assertEqual(set(row),{'status','draft_count','pending_evidence_count','observed_state','quarantined',
            'native_order_accepted','child_mapping_verified','full_position_protection_verified',
            'live_dispatch_enabled','ready_for_live','account_accessed','orders_sent'})
        self.assertEqual(validate_protective_review(row),row)

    def test_02_strict_contract_bounds_flags_and_types(self):
        for changes in ({'draft_count':True},{'draft_count':10001},{'pending_evidence_count':-1},
                {'observed_state':'PRIVATE_SENTINEL'},{'native_order_accepted':True},{'orders_sent':False},
                {'path':'PRIVATE_SENTINEL'},{'quarantined':1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_protective_review(dict(protective_review('not_registered'),**changes))

    def test_03_principal_precedes_filesystem(self):
        with patch('core.crypto_trial_registry.current_memory_principal',return_value=None),patch('core.crypto_trial_registry.TrialRootLease.open_for_locator',side_effect=AssertionError('filesystem forbidden')):
            self.assertEqual(self.registry.protective_review(),protective_review('denied'))

    def test_04_missing_registry_no_implicit_creation(self):
        missing=self.parent/'absent';registry=TrialRuntimeRegistry(missing)
        self.assertEqual(registry.protective_review(),protective_review('not_registered'));self.assertFalse(missing.exists())

    def test_05_registered_unprepared_has_no_lifecycle_ddl(self):
        before=self.tables();result=self.registry.protective_review()
        self.assertEqual(result,protective_review('not_prepared'));self.assertEqual(self.tables(),before)

    def test_06_active_owner_borrow_preserves_lifetime_lock(self):
        with patch('core.crypto_trial_registry.PersistentTrialRuntime.open',side_effect=AssertionError('must borrow owner')):
            self.assertEqual(self.registry.protective_review()['status'],'not_prepared')
        self.assertFalse(self.owner.status()['ready_for_live'])

    def test_07_closed_owner_reopen_is_read_only(self):
        self.owner.close();self.assertEqual(self.registry.protective_review()['status'],'not_prepared')

    def test_08_unsigned_prepared_metadata(self):
        self.prepared();row=self.registry.protective_review()
        self.assertEqual(row['status'],'qualification');self.assertEqual(row['draft_count'],1)
        self.assertEqual(row['observed_state'],'UNSIGNED_DRAFT');self.assertEqual(row['pending_evidence_count'],0)

    def test_09_receipt_only_ack_metadata(self):
        self.prepared();self.capture('ack','ack',self.ack())
        row=self.registry.protective_review();self.assertEqual(row['observed_state'],'REQUEST_RECEIVED')
        self.assertFalse(row['native_order_accepted'])

    def test_10_active_is_observed_never_native_acceptance(self):
        self.prepared();self.capture('ack','ack',self.ack());self.capture('detail','active',self.detail())
        before=self.owner.coordinator.snapshot();row=self.registry.protective_review()
        self.assertEqual(row['observed_state'],'ACTIVE');self.assertFalse(row['native_order_accepted'])
        self.assertEqual(before,self.owner.coordinator.snapshot());self.assertNotIn(self.observation.account,json.dumps(row))

    def test_11_pending_raw_returns_held_count(self):
        self.prepared()
        with patch.object(self.life,'_interpret',side_effect=SystemExit(75)):
            with self.assertRaises(SystemExit):self.capture('ack','pending',self.ack())
        row=self.registry.protective_review();self.assertEqual(row['status'],'held')
        self.assertEqual(row['pending_evidence_count'],1);self.assertEqual(row['observed_state'],'UNSIGNED_DRAFT')

    def test_12_quarantine_is_held_with_no_raw_or_identity(self):
        self.prepared();body=self.ack();self.capture('ack','ack',body);body['result']['order_id']='6789'
        with self.assertRaises(ControlError):self.capture('ack','ack',body)
        row=self.registry.protective_review();self.assertEqual(row['status'],'held');self.assertTrue(row['quarantined'])
        self.assertNotIn('order_id',row);self.assertNotIn('account',row);self.assertNotIn('raw_response',row)

    def test_13_ambiguous_latest_generation_refuses(self):
        self.prepared()
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            row=db.execute('SELECT * FROM aibs_protective_drafts').fetchone();payload=json.loads(row[1]);identity=str(uuid4())
            payload['stop_id']=identity
            db.execute('INSERT INTO aibs_protective_drafts VALUES(?,?,?,?,?)',(identity,encode(payload),digest(payload),row[3],row[4]))
        self.assertEqual(self.registry.protective_review(),protective_review('unavailable'))

    def test_14_corrupt_retained_evidence_refuses_sanitized(self):
        self.prepared();self.capture('ack','ack',self.ack())
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:db.execute('UPDATE aibs_protective_inputs SET raw_response=?',(b'PRIVATE_SENTINEL',))
        self.assertEqual(self.registry.protective_review(),protective_review('unavailable'))

    def test_15_other_principal_denied_status_api_unchanged(self):
        prior=self.registry.status()
        with patch('core.crypto_trial_registry.current_memory_principal',return_value='different_owner'):
            self.assertEqual(self.registry.protective_review(),protective_review('denied'))
        self.assertEqual(self.registry.status(),prior)


if __name__=='__main__':unittest.main()
