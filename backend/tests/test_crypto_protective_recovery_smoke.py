"""Fifteen stored-raw recovery/concurrency cases; synthetic durable fixtures only."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_execution_controls import ControlError, digest, encode
from core.crypto_protective_lifecycle import OfflineProtectiveLifecycle
from core.crypto_trial_binding import qualification_account_observation
from core.crypto_trial_budget import create_baseline
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from tests import test_crypto_protective_lifecycle_smoke as fixture

OUT=Path('C:/AI-BS/backups/crypto_protective_recovery_20261115_v01')
NOW=fixture.NOW


class ProtectiveRecoverySmoke(unittest.TestCase):
    create=fixture.ProtectiveLifecycleSmoke.create
    quote=fixture.ProtectiveLifecycleSmoke.quote
    buy=fixture.ProtectiveLifecycleSmoke.buy
    prepare=fixture.ProtectiveLifecycleSmoke.prepare
    ack=fixture.ProtectiveLifecycleSmoke.ack
    detail=fixture.ProtectiveLifecycleSmoke.detail
    capture=fixture.ProtectiveLifecycleSmoke.capture
    rows=fixture.ProtectiveLifecycleSmoke.rows

    def setUp(self):
        OUT.mkdir(parents=True,exist_ok=True);self.parent=OUT/('fixture_'+uuid4().hex);self.parent.mkdir()
        self.observation=qualification_account_observation(account_id=str(uuid4()),started_ms=NOW-101,completed_ms=NOW-2)
        self.baseline=create_baseline(trial_id=str(uuid4()),account=self.observation.account,started_ms=NOW-1,
            day_start_ms=((NOW-1)//86400000)*86400000,opening_receipt_sha256='c'*64)
        self.owner=self.create();self.life=OfflineProtectiveLifecycle(self.owner);self.buy();self.prepare()

    def pending(self,body=None,kind='ack'):
        with patch.object(self.life,'_interpret',side_effect=SystemExit(75)):
            with self.assertRaises(SystemExit):self.capture(kind,'pending',body or self.ack())
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            return db.execute('SELECT MAX(seq) FROM aibs_protective_inputs').fetchone()[0]

    def sql(self,statement,args=()):
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:db.execute(statement,args)

    def interrupted_child(self,kind,body):
        cfg=dict(root=str(self.owner.root),uuid=self.owner.store_uuid,account=self.observation.account,
            stop_id=self.stop['stop_id'],kind=kind,body=body,request_id=17 if kind=='ack' else 18)
        self.owner.close()
        source='''import json,os,sys
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from core.crypto_protective_lifecycle import OfflineProtectiveLifecycle
c=json.load(sys.stdin)
o=PersistentTrialRuntime.open(c['root'],expected_store_uuid=c['uuid'],expected_account=c['account'],qualification=True)
l=OfflineProtectiveLifecycle(o)
l._interpret=lambda seq:os._exit(75)
l.capture(c['stop_id'],kind=c['kind'],event_id='interrupted',request_id=c['request_id'],raw_response=json.dumps(c['body']).encode(),observed_ms=1794772800021)
'''
        (self.parent/'child.py').write_text(source)
        result=subprocess.run([sys.executable,'-B','-c',source],input=json.dumps(cfg),capture_output=True,text=True,
            cwd=Path(__file__).resolve().parents[1],timeout=20)
        (self.parent/'child-result.json').write_text(json.dumps(dict(code=result.returncode,stdout=result.stdout,stderr=result.stderr)))
        self.assertEqual(result.returncode,75,result.stderr)
        self.owner=PersistentTrialRuntime.open(cfg['root'],expected_store_uuid=cfg['uuid'],expected_account=cfg['account'],qualification=True)
        self.addCleanup(self.owner.close);self.life=OfflineProtectiveLifecycle(self.owner)
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            return db.execute('SELECT MAX(seq) FROM aibs_protective_inputs').fetchone()[0]

    def test_01_actual_child_exit_raw_commit_ack_recovery(self):
        seq=self.interrupted_child('ack',self.ack())
        result=self.life.recover(seq)
        self.assertEqual(result['observed_state'],'REQUEST_RECEIVED');self.assertFalse(result['native_order_accepted'])

    def test_02_actual_child_exit_detail_restart_recovery(self):
        self.capture('ack','ack-1',self.ack());seq=self.interrupted_child('detail',self.detail())
        before=self.owner.coordinator.snapshot();result=self.life.recover(seq)
        self.assertEqual(result['observed_state'],'ACTIVE');self.assertEqual(before,self.owner.coordinator.snapshot())

    def test_03_stored_raw_corruption_refused(self):
        seq=self.pending();self.sql("UPDATE aibs_protective_inputs SET raw_response=? WHERE seq=?",(b'{}',seq))
        with self.assertRaises(ControlError):self.life.recover(seq)

    def test_04_request_context_corruption_refused(self):
        seq=self.pending();self.sql('UPDATE aibs_protective_inputs SET request_id=99 WHERE seq=?',(seq,))
        with self.assertRaises(ControlError):self.life.recover(seq)

    def test_05_observation_context_corruption_refused(self):
        seq=self.pending();self.sql('UPDATE aibs_protective_inputs SET observed_ms=observed_ms+1 WHERE seq=?',(seq,))
        with self.assertRaises(ControlError):self.life.recover(seq)

    def test_06_kind_or_event_context_corruption_refused(self):
        seq=self.pending();self.sql("UPDATE aibs_protective_inputs SET kind='detail',event_id='changed' WHERE seq=?",(seq,))
        with self.assertRaises(ControlError):self.life.recover(seq)

    def test_07_missing_original_binding_not_rebaselined(self):
        seq=self.pending();self.sql('DELETE FROM aibs_protective_integrity WHERE input_seq=?',(seq,))
        with self.assertRaises(ControlError):self.life.recover(seq)

    def test_08_repeat_recovery_idempotent(self):
        seq=self.pending();before=self.owner.coordinator.snapshot();one=self.life.recover(seq);two=self.life.recover(seq)
        self.assertEqual(one,two);self.assertEqual(before,self.owner.coordinator.snapshot())
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aibs_protective_transitions').fetchone()[0],1)

    def race(self,bodies):
        barrier=threading.Barrier(2)
        def call(body):
            barrier.wait()
            try:return self.capture('ack','raced',body)
            except ControlError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(call,bodies))

    def test_09_same_capture_race_single_transition(self):
        before=self.owner.coordinator.snapshot();results=self.race([self.ack(),self.ack()])
        self.assertTrue(all(result is not None for result in results));self.assertEqual(len(self.rows()),1)
        self.assertEqual(before,self.owner.coordinator.snapshot())
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aibs_protective_transitions').fetchone()[0],1)

    def test_10_conflicting_capture_race_always_quarantines(self):
        other=self.ack();other['result']['order_id']='6789';before=self.owner.coordinator.snapshot()
        self.race([self.ack(),other]);self.assertEqual(len(self.rows()),2)
        self.assertTrue(self.life.review(self.stop['stop_id'])['quarantined']);self.assertEqual(before,self.owner.coordinator.snapshot())

    def test_11_duplicate_uses_verified_stored_bytes(self):
        body=self.ack();self.capture('ack','ack-1',body)
        self.sql('UPDATE aibs_protective_inputs SET raw_response=?',(b'{}',))
        with self.assertRaises(ControlError):self.capture('ack','ack-1',body)

    def test_12_state_requires_evidence_causality(self):
        self.capture('ack','ack-1',self.ack())
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            state=json.loads(db.execute('SELECT state FROM aibs_protective_drafts').fetchone()[0])
        state['observed_state']='ACTIVE'
        self.sql('UPDATE aibs_protective_drafts SET state=?,state_sha256=?',(encode(state),digest(state)))
        with self.assertRaises(ControlError):self.life.review(self.stop['stop_id'])

    def test_13_pending_review_does_not_invent_processing(self):
        seq=self.pending();self.assertEqual(self.life.review(self.stop['stop_id'])['observed_state'],'UNSIGNED_DRAFT')
        self.assertEqual(self.life.recover(seq)['observed_state'],'REQUEST_RECEIVED')

    def test_14_invalid_stored_raw_retained_and_never_reaccepted(self):
        seq=self.pending({'id':17,'method':'private/advanced/create-order','code':1})
        with self.assertRaises(ControlError):self.life.recover(seq)
        with self.assertRaises(ControlError):self.life.recover(seq)
        self.assertEqual(self.rows()[0][1],'INVALID_RETAINED')

    def test_15_closed_owner_cannot_recover(self):
        seq=self.pending();self.owner.close()
        with self.assertRaises(ControlError):self.life.recover(seq)


if __name__=='__main__':unittest.main()
