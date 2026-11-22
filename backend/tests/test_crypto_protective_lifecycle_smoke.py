"""Fifteen same-database protective replay cases; qualification evidence only."""
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from uuid import uuid4

from core.crypto_execution_controls import ControlError, Fill, Held
from core.crypto_trial_binding import qualification_account_observation
from core.crypto_trial_budget import create_baseline
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from core.crypto_protective_lifecycle import OfflineProtectiveLifecycle
from tests import test_crypto_trial_runtime_store_smoke as fixture

NOW=1794772800001
OUT=Path('C:/AI-BS/backups/crypto_protective_lifecycle_20261115_v01')


class ProtectiveLifecycleSmoke(unittest.TestCase):
    create=fixture.PersistentTrialRuntimeSmoke.create
    quote=fixture.PersistentTrialRuntimeSmoke.quote

    def setUp(self):
        OUT.mkdir(parents=True,exist_ok=True);self.parent=OUT/('fixture_'+uuid4().hex);self.parent.mkdir()
        self.observation=qualification_account_observation(account_id=str(uuid4()),started_ms=NOW-101,completed_ms=NOW-2)
        self.baseline=create_baseline(trial_id=str(uuid4()),account=self.observation.account,started_ms=NOW-1,
            day_start_ms=((NOW-1)//86400000)*86400000,opening_receipt_sha256='c'*64)
        self.owner=self.create();self.life=OfflineProtectiveLifecycle(self.owner)

    def buy(self,*,quantity=None,fees=(),complete=True):
        self.quote(self.owner);self.client=str(uuid4())
        self.entry=self.owner.reinvestment.reserve_entry(self.client,limit_price='0.1',hard_stop='0.08',now_ms=NOW)
        self.owner.coordinator.begin_submission(self.client,now_ms=NOW)
        quantity=quantity or self.entry['receipt']['quantity_cro']
        self.owner.coordinator.apply_fill(Fill(fill_id='entry',client_id=self.client,exchange_order_id='entry-order',
            symbol='CRO/USDT',side='buy',quantity=quantity,cost='0.05' if quantity=='0.5' else '1.05',
            fees=fees,fees_complete=complete,sequence=1,occurred_ms=NOW+1))
        self.quote(self.owner,now=NOW+10)

    def prepare(self):
        self.stop=self.life.prepare(self.client,request_id=17,fee_asset='USDT',fee_reserve='0.01',
            rule_receipt_sha256='d'*64,now_ms=NOW+10)
        return self.stop

    def ack(self,**changes):
        return dict(dict(id=17,method='private/advanced/create-order',code=0,
            result={'order_id':'12345','client_oid':self.stop['stop_id']}),**changes)

    def detail(self,**changes):
        params=self.stop['draft']['params']
        row=dict(account_id=self.observation.account_id,order_id='12345',client_oid=self.stop['stop_id'],
            instrument_name='CRO_USDT',side='SELL',order_type='STOP_LOSS',quantity=params['quantity'],
            ref_price='0.08',ref_price_type='LAST_PRICE',cumulative_quantity='0',cumulative_value='0',
            cumulative_fee='0',fee_instrument_name='USDT',create_time=NOW+10,update_time=NOW+11,
            status='ACTIVE',exchange_order_id='UNMAPPED_ACCEPTED_LEG')
        row.update(changes)
        return {'id':18,'method':'private/advanced/get-order-detail','code':0,'result':row}

    def capture(self,kind,key,body,request_id=None,observed_ms=NOW+20):
        return self.life.capture(self.stop['stop_id'],kind=kind,event_id=key,
            request_id=request_id or (17 if kind=='ack' else 18),raw_response=json.dumps(body).encode(),observed_ms=observed_ms)

    def rows(self):
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            return db.execute('SELECT raw_response,outcome FROM aibs_protective_inputs ORDER BY seq').fetchall()

    def test_01_full_applied_fill_derivation_and_held_flags(self):
        self.buy()
        from core import crypto_protective_lifecycle as module
        original=module._project_trial_snapshot
        def unrelated_inventory(*args,**kwargs):
            result=original(*args,**kwargs)
            # Fault only after the real projection: consumer must independently
            # refuse sweeping inventory outside this terminal parent policy.
            for row in args[2]['balances']:
                if row['asset']=='CRO':row['total']='11'
            return result
        with patch.object(module,'_project_trial_snapshot',side_effect=unrelated_inventory):
            with self.assertRaises(ControlError):self.prepare()
        stop=self.prepare();self.assertEqual(stop['draft']['params']['quantity'],'10.5')
        self.assertEqual(stop['draft']['method'],'private/advanced/create-order')
        for key in ('ready_for_live','live_dispatch_enabled','native_order_accepted','child_mapping_verified'):
            self.assertIs(stop[key],False)
        self.assertEqual(stop['orders_sent'],0)

    def test_02_actual_base_entry_fee_subtracted(self):
        self.buy(fees=(('CRO','0.5'),));self.assertEqual(self.prepare()['draft']['params']['quantity'],'10')

    def test_03_existing_base_reservation_refuses_competing_protection(self):
        self.buy();self.owner.coordinator.prepare(str(uuid4()),symbol='CRO/USDT',side='sell',quantity='5',limit_price='0.1',now_ms=NOW+10)
        before=self.owner.coordinator.snapshot()
        with self.assertRaises(ControlError):self.prepare()
        self.assertEqual(before,self.owner.coordinator.snapshot())

    def test_04_terminal_partial_below_current_minimum_refuses(self):
        self.buy(quantity='0.5',fees=(('CRO','0.025'),))
        self.owner.coordinator.reconcile(self.client,exchange_order_id='entry-order',state='CANCELLED',cumulative_quantity='0.5',authoritative=True)
        with self.assertRaises(ControlError):self.prepare()

    def test_05_active_partial_entry_is_uncovered_hold(self):
        self.buy(quantity='0.5')
        with self.assertRaises(ControlError):self.prepare()

    def test_06_incomplete_fee_fill_never_funds_draft(self):
        with self.assertRaises(Held):self.buy(complete=False)
        with self.assertRaises(ControlError):self.prepare()

    def test_07_local_draft_tamper_refused(self):
        self.buy();self.prepare()
        with sqlite3.connect(self.owner.root/'accounting.sqlite3') as db:
            db.execute("UPDATE aibs_protective_drafts SET payload='{}'")
        with self.assertRaises(ControlError):self.life.review(self.stop['stop_id'])

    def test_08_ack_receipt_is_not_protection(self):
        self.buy();self.prepare();result=self.capture('ack','ack-1',self.ack())
        self.assertEqual(result['observed_state'],'REQUEST_RECEIVED')
        self.assertFalse(result['native_order_accepted']);self.assertEqual(len(self.rows()),1)

    def test_09_advanced_identity_mismatch_retained_before_refusal(self):
        self.buy();self.prepare();self.capture('ack','ack-1',self.ack())
        for index,changes in enumerate(({'account_id':'wrong'},{'client_oid':str(uuid4())},{'ref_price':'0.09'},
                {'order_type':'STOP_LIMIT'},{'quantity':'9'},{'order_id':'6789'})):
            body=self.detail(**changes)
            with self.assertRaises(ControlError):self.capture('detail','bad-'+str(index),body)
        self.assertEqual(len(self.rows()),7)

    def test_10_duplicate_replay_idempotent(self):
        self.buy();self.prepare();body=self.ack()
        first=self.capture('ack','ack-1',body);again=self.capture('ack','ack-1',body)
        self.assertEqual(first,again);self.assertEqual(len(self.rows()),1)

    def test_11_conflicting_event_quarantined_evidence_retained(self):
        self.buy();self.prepare();self.capture('ack','ack-1',self.ack())
        body=self.ack();body['result']['order_id']='6789'
        with self.assertRaises(ControlError):self.capture('ack','ack-1',body)
        self.assertEqual(len(self.rows()),2);self.assertTrue(self.life.review(self.stop['stop_id'])['quarantined'])

    def test_12_stale_detail_retained_without_state_regression(self):
        self.buy();self.prepare();self.capture('ack','ack-1',self.ack())
        self.capture('detail','new',self.detail(update_time=NOW+15))
        self.capture('detail','old',self.detail(update_time=NOW+12,status='PENDING'))
        self.assertEqual(self.life.review(self.stop['stop_id'])['observed_state'],'ACTIVE')
        self.assertEqual(self.rows()[-1][1],'STALE_RETAINED')

    def test_13_reject_cancel_expiry_never_release_accounting(self):
        self.buy();self.prepare();self.capture('ack','ack-1',self.ack());before=self.owner.coordinator.snapshot()
        for i,state in enumerate(('REJECTED','CANCELED','EXPIRED')):
            if i==0:self.capture('detail',state,self.detail(status=state,update_time=NOW+11+i))
            else:
                with self.assertRaises(ControlError):self.capture('detail',state,self.detail(status=state,update_time=NOW+11+i))
        self.assertTrue(self.life.review(self.stop['stop_id'])['quarantined'])
        self.assertEqual(self.life.review(self.stop['stop_id'])['observed_state'],'REJECTED')
        self.assertEqual(before,self.owner.coordinator.snapshot());self.assertFalse(self.life.review(self.stop['stop_id'])['native_order_accepted'])

    def test_14_partial_protective_execution_is_unmapped_not_applied(self):
        self.buy();self.prepare();self.capture('ack','ack-1',self.ack());before=self.owner.coordinator.snapshot()
        result=self.capture('detail','partial',self.detail(cumulative_quantity='5',cumulative_value='0.4'))
        self.assertEqual(result['replayed_cumulative_quantity'],'5');self.assertFalse(result['child_mapping_verified'])
        self.assertEqual(result['verified_covered_quantity_cro'],'0');self.assertEqual(before,self.owner.coordinator.snapshot())
        for status,quantity,value in (('FILLED','0','0'),('PENDING','1','0.08'),('NEW','1','0.08')):
            self.parent=self.parent/status;self.parent.mkdir();self.owner=self.create();self.life=OfflineProtectiveLifecycle(self.owner)
            self.buy();self.prepare();self.capture('ack','ack-1',self.ack())
            with self.assertRaises(ControlError):self.capture('detail','contradiction',self.detail(status=status,cumulative_quantity=quantity,cumulative_value=value))
            self.assertTrue(self.life.review(self.stop['stop_id'])['quarantined'])

    def test_15_restart_preserves_raw_receipt_and_unqualified_state(self):
        self.buy();self.prepare();self.capture('ack','ack-1',self.ack());self.capture('detail','active',self.detail())
        root=self.owner.root;identity=self.owner.store_uuid;before=self.life.review(self.stop['stop_id']);raw=self.rows()
        self.owner.close();reopened=PersistentTrialRuntime.open(root,expected_store_uuid=identity,expected_account=self.observation.account,qualification=True)
        self.addCleanup(reopened.close);life=OfflineProtectiveLifecycle(reopened)
        self.assertEqual(life.review(self.stop['stop_id']),before)
        with sqlite3.connect(root/'accounting.sqlite3') as db:
            self.assertEqual(db.execute('SELECT raw_response,outcome FROM aibs_protective_inputs ORDER BY seq').fetchall(),raw)


if __name__=='__main__':unittest.main()
