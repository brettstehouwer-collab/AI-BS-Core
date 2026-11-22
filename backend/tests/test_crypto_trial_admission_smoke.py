"""Fifteen local entry-only admission cases; no Exchange/transport authority."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import threading
import unittest
from uuid import uuid4

from tests import test_crypto_reinvestment_smoke as fixture
from core.crypto_execution_controls import ControlError, Fill, Held, Instrument, OfflineExecutionCoordinator, RiskLimits
from core.crypto_reinvestment import OfflineReinvestment
from core.crypto_trial_admission import OfflineTrialAdmission, TrialEntryHeld, modeled_entry_risk


class TrialAdmissionSmoke(unittest.TestCase):
    quote=fixture.ReinvestmentSmoke.quote
    reserve=fixture.ReinvestmentSmoke.reserve
    execute_buy=fixture.ReinvestmentSmoke.execute_buy
    dump=fixture.ReinvestmentSmoke.dump

    def setUp(self):
        fixture.ReinvestmentSmoke.setUp(self)
        self.store=OfflineTrialAdmission.register(self.store,daily_loss_budget_usdt='1')
        self.manager=OfflineReinvestment(self.store)

    def fresh(self, daily):
        self.path=Path(self.temp.name)/(uuid4().hex+'.sqlite');self.clock=1000;self.order_counter=0
        base=OfflineExecutionCoordinator.create(self.path,account=self.account,quote='USDT',cash='100',
            limits=RiskLimits(max_fee_bps='500',max_drawdown_bps='9000'))
        self.store=base;self.quote('0.1')
        OfflineReinvestment.create(base,self.baseline,seed_budget_usdt='1.1025',max_entry_budget_usdt='10')
        self.store=OfflineTrialAdmission.register(base,daily_loss_budget_usdt=daily)
        self.manager=OfflineReinvestment(self.store)

    def sql(self, sql, args=()):
        with closing(sqlite3.connect(self.path)) as db:
            with db:db.execute(sql,args)

    def test_01_manager_reservation_and_submission_are_local_only(self):
        result=self.reserve(stop='0.08')
        self.store.begin_submission(result['intent']['client_id'],now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'SUBMITTING')
        self.assertFalse(result['live_dispatch_enabled']);self.assertEqual(result['orders_sent'],0)

    def test_02_proposed_risk_over_allowance_refused_before_reservation(self):
        self.fresh('0.01')
        with self.assertRaises(ControlError):self.reserve(stop='0.08')
        self.assertEqual(self.store.snapshot()['orders'],[])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aibs_reinvestment_entries').fetchone()[0],0)

    def test_03_closed_loss_cutoff_persists_without_global_halt(self):
        fixture.ReinvestmentSmoke.close_cycle(self,price='0.01',buy_fee='0.0525')
        self.assertEqual(Decimal(self.store.snapshot()['positions'][0]['realized']),Decimal('-1.0025'))
        with self.assertRaises(TrialEntryHeld):self.reserve(stop='0.08')
        self.assertEqual(self.store.snapshot()['risk']['halted'],0)
        reopened=OfflineTrialAdmission(self.path)
        self.assertTrue(reopened.entry_status()['entry_held'])
        with self.assertRaises(TrialEntryHeld):
            OfflineReinvestment(reopened).reserve_entry(str(uuid4()),limit_price='0.1',hard_stop='0.08',now_ms=self.clock)

    def test_04_entry_latch_does_not_block_reducing_sell(self):
        self.fresh('0.5');result=self.reserve(stop='0.08');self.execute_buy(result,'0.0525')
        self.clock+=10;self.quote('0.01');client=str(uuid4())
        self.store.prepare(client,symbol='CRO/USDT',side='sell',quantity='5',limit_price='0.01',now_ms=self.clock)
        self.store.begin_submission(client,now_ms=self.clock);self.order_counter+=1
        self.store.apply_fill(Fill(fill_id='fill-'+str(self.order_counter),client_id=client,
            exchange_order_id='partial-exit',symbol='CRO/USDT',side='sell',quantity='5',cost='0.05',
            fees=(('CRO','0.25'),),sequence=self.order_counter,occurred_ms=self.clock+1))
        self.clock+=10;self.quote('0.01')
        self.assertTrue(self.store.refresh_entry_hold(now_ms=self.clock)['entry_held'])
        reducing=str(uuid4())
        self.store.prepare(reducing,symbol='CRO/USDT',side='sell',quantity='5',limit_price='0.01',now_ms=self.clock)
        self.store.begin_submission(reducing,now_ms=self.clock)
        self.assertEqual(next(o for o in self.store.snapshot()['orders'] if o['client_id']==reducing)['state'],'SUBMITTING')
        self.assertEqual(self.store.snapshot()['risk']['halted'],0)

    def test_05_next_day_submission_refused_before_state_change(self):
        result=self.reserve(stop='0.08')
        with self.assertRaises(ControlError):self.store.begin_submission(result['intent']['client_id'],now_ms=86400000)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'INTENT')

    def test_06_changed_allocation_receipt_rejected_before_submission(self):
        result=self.reserve(stop='0.08')
        with closing(sqlite3.connect(self.path)) as db:
            raw=db.execute('SELECT receipt FROM aibs_reinvestment_entries').fetchone()[0]
        receipt=json.loads(raw);receipt['quantity_cro']='99'
        self.sql('UPDATE aibs_reinvestment_entries SET receipt=?',(json.dumps(receipt),))
        with self.assertRaises(ControlError):self.store.begin_submission(result['intent']['client_id'],now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'INTENT')

    def test_07_changed_parent_fingerprint_rejected(self):
        result=self.reserve(stop='0.08');self.sql("UPDATE orders SET fingerprint='changed'")
        with self.assertRaises(ControlError):self.store.begin_submission(result['intent']['client_id'],now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'INTENT')

    def test_08_public_buy_bypass_refused(self):
        with self.assertRaises(ControlError):
            self.store.prepare(str(uuid4()),symbol='CRO/USDT',side='buy',quantity='1',
                limit_price='0.1',hard_stop='0.08',now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'],[])

    def test_09_same_client_cannot_submit_twice(self):
        result=self.reserve(stop='0.08');client=result['intent']['client_id']
        self.store.begin_submission(client,now_ms=self.clock)
        with self.assertRaises(ControlError):self.store.begin_submission(client,now_ms=self.clock)

    def test_10_unknown_and_pending_facts_never_admit_new_entry(self):
        result=self.reserve(stop='0.08');client=result['intent']['client_id']
        self.store.begin_submission(client,now_ms=self.clock);self.store.mark_unknown(client,'TIMEOUT')
        with self.assertRaises(ControlError):self.reserve(stop='0.08')
        self.sql("UPDATE orders SET state='INTENT'")
        self.sql("INSERT INTO unmatched_fills VALUES('synthetic-unmatched','{}','synthetic')")
        with self.assertRaises(ControlError):self.store.begin_submission(client,now_ms=self.clock)

    def test_11_admission_policy_is_immutable(self):
        changed=False
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                for (table,) in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
                    quoted='"'+table.replace('"','""')+'"';columns=[r[1] for r in db.execute('PRAGMA table_info('+quoted+')')]
                    for row in db.execute('SELECT rowid,* FROM '+quoted).fetchall():
                        for i,value in enumerate(row[1:]):
                            if not isinstance(value,str):continue
                            try:record=json.loads(value)
                            except ValueError:continue
                            if isinstance(record,dict) and 'daily_loss_budget_usdt' in record:
                                record['daily_loss_budget_usdt']='100'
                                col='"'+columns[i].replace('"','""')+'"'
                                db.execute('UPDATE '+quoted+' SET '+col+'=? WHERE rowid=?',(json.dumps(record),row[0]));changed=True;break
                        if changed:break
                    if changed:break
        self.assertTrue(changed)
        with self.assertRaises(ControlError):self.reserve(stop='0.08')

    def model(self, **changes):
        request=dict(quantity='10.5',limit_price='0.1',hard_stop='0.08');request.update(changes)
        return modeled_entry_risk(request,Instrument('CRO','USDT',quantity_step='0.5',price_tick='0.01',
            minimum_quantity='0.5',minimum_notional='0.01').normalized(),max_fee_bps='500',max_slippage_bps='50')

    def test_12_four_fee_cases_and_worst_shortfall_modeled(self):
        result=self.model()
        self.assertEqual(len(result['fee_cases']),4)
        self.assertEqual(Decimal(result['assumed_exit_price']),Decimal('0.07'))
        self.assertGreater(Decimal(result['loss_reserve_usdt']),0)
        self.assertFalse(result['guaranteed_maximum_loss'])

    def test_13_invalid_stop_and_below_minimum_exit_refused(self):
        for stop in ('0','0.001','0.11'):
            with self.subTest(stop=stop),self.assertRaises(ControlError):self.model(hard_stop=stop)
        spec=Instrument('CRO','USDT',quantity_step='0.5',price_tick='0.01',minimum_quantity='0.5',minimum_notional='1').normalized()
        with self.assertRaises(ControlError):modeled_entry_risk(dict(quantity='10.5',limit_price='0.1',hard_stop='0.08'),spec,
            max_fee_bps='500',max_slippage_bps='50')

    def test_14_two_concurrent_submission_attempts_have_one_winner(self):
        client=self.reserve(stop='0.08')['intent']['client_id'];barrier=threading.Barrier(2)
        def submit(_):
            barrier.wait()
            try:self.store.begin_submission(client,now_ms=self.clock);return True
            except ControlError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,range(2)))
        self.assertEqual(sorted(results),[False,True])
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'SUBMITTING')

    def test_15_local_enforcement_is_not_exchange_protection_or_live_authority(self):
        result=self.store.entry_status()
        self.assertEqual(result['scope'],'OFFLINE_DAILY_ENTRY_ADMISSION')
        self.assertTrue(result['local_cutoff_enforced'])
        for key in ('live_daily_cutoff_enforced','native_protection_qualified','guaranteed_maximum_loss',
                    'live_dispatch_enabled','ready_for_live'):
            self.assertIs(result[key],False)
        self.assertEqual(result['orders_sent'],0)
        self.assertTrue(issubclass(TrialEntryHeld,Held))


if __name__=='__main__':unittest.main()
