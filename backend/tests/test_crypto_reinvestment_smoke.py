"""Fifteen real temporary-store allocation cases; preparation never dispatches."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from uuid import uuid4

from core.crypto_execution_controls import ControlError, Fill, Instrument, OfflineExecutionCoordinator, RiskLimits
from core.crypto_trial_budget import create_baseline
from core.crypto_reinvestment import OfflineReinvestment


class ReinvestmentSmoke(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'reinvestment.sqlite';self.clock=1000;self.order_counter=0
        self.account='cryptocom-exchange:synthetic'
        self.store=OfflineExecutionCoordinator.create(self.path,account=self.account,quote='USDT',cash='100',
            limits=RiskLimits(max_fee_bps='500',max_drawdown_bps='9000'))
        self.baseline=create_baseline(trial_id=str(uuid4()),account=self.account,started_ms=1000,
            day_start_ms=0,opening_receipt_sha256='c'*64)
        self.quote('0.1')
        self.manager=OfflineReinvestment.create(self.store,self.baseline,seed_budget_usdt='1.1025',max_entry_budget_usdt='10')

    def quote(self, price, minimum='0.01'):
        self.clock+=1
        self.store.quote_market(Instrument('CRO','USDT',quantity_step='0.5',price_tick='0.01',
            minimum_quantity='0.5',minimum_notional=minimum),bid=price,ask=price,observed_ms=self.clock,now_ms=self.clock)

    def reserve(self, client=None, manager=None, price='0.1', stop='0.05', now=None):
        return (manager or self.manager).reserve_entry(client or str(uuid4()),limit_price=price,hard_stop=stop,
            now_ms=self.clock if now is None else now)

    def execute_buy(self, result, quote_fee='0'):
        intent=result['intent'];cid=intent['client_id'];quantity=result['receipt']['quantity_cro']
        self.store.begin_submission(cid,now_ms=self.clock)
        self.order_counter+=1
        self.store.apply_fill(Fill(fill_id='fill-'+str(self.order_counter),client_id=cid,
            exchange_order_id='order-'+str(self.order_counter),symbol='CRO/USDT',side='buy',
            quantity=quantity,cost=str(Decimal(quantity)*Decimal('0.1')),
            fees=(('USDT',quote_fee),) if quote_fee!='0' else (),sequence=self.order_counter,occurred_ms=self.clock+1))

    def close_cycle(self, price='0.12', buy_fee='0'):
        result=self.reserve();self.execute_buy(result,buy_fee)
        self.clock+=10;self.quote(price)
        cid=str(uuid4());self.store.prepare(cid,symbol='CRO/USDT',side='sell',quantity='10',
            limit_price=price,now_ms=self.clock)
        self.store.begin_submission(cid,now_ms=self.clock);self.order_counter+=1
        self.store.apply_fill(Fill(fill_id='fill-'+str(self.order_counter),client_id=cid,
            exchange_order_id='order-'+str(self.order_counter),symbol='CRO/USDT',side='sell',quantity='10',
            cost=str(Decimal('10')*Decimal(price)),fees=(('CRO','0.5'),),sequence=self.order_counter,occurred_ms=self.clock+1))
        self.clock+=10;self.quote('0.1')
        return result

    def dump(self):
        with closing(sqlite3.connect(self.path)) as db:return list(db.iterdump())

    def test_01_first_entry_is_fee_inclusive_and_held(self):
        result=self.reserve();receipt=result['receipt']
        self.assertEqual(Decimal(receipt['working_capital_usdt']),Decimal('1.1025'))
        self.assertEqual(Decimal(receipt['quantity_cro']),Decimal('10.5'))
        self.assertEqual(Decimal(receipt['profit_supported_additional_cro']),0)
        self.assertTrue(result['new_reservation'])
        self.assertRegex(receipt['source_fill_checkpoint_sha256'],r'^[a-f0-9]{64}$')
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'INTENT')

    def test_02_actual_profitable_cycle_increases_working_capital(self):
        self.close_cycle();result=self.reserve()
        self.assertEqual(Decimal(result['receipt']['net_realized_pnl_usdt']),Decimal('0.15'))
        self.assertEqual(Decimal(result['receipt']['working_capital_usdt']),Decimal('1.2525'))
        self.assertEqual(Decimal(result['receipt']['quantity_cro']),Decimal('11.5'))

    def test_03_loss_cycle_reduces_budget_not_just_zeroed_profit(self):
        self.close_cycle(price='0.08');result=self.reserve()
        self.assertEqual(Decimal(result['receipt']['net_realized_pnl_usdt']),Decimal('-0.25'))
        self.assertEqual(Decimal(result['receipt']['working_capital_usdt']),Decimal('0.8525'))
        self.assertLess(Decimal(result['receipt']['quantity_cro']),Decimal('10.5'))
        self.assertEqual(Decimal(result['receipt']['profit_supported_additional_cro']),0)

    def test_04_actual_entry_fee_reduces_reinvestable_profit(self):
        self.close_cycle(buy_fee='0.01');result=self.reserve()
        self.assertEqual(Decimal(result['receipt']['net_realized_pnl_usdt']),Decimal('0.14'))
        self.assertEqual(Decimal(result['receipt']['working_capital_usdt']),Decimal('1.2425'))

    def test_05_extra_cro_compares_seed_at_next_entry_price(self):
        self.close_cycle();self.quote('0.12');result=self.reserve(price='0.12')
        receipt=result['receipt']
        self.assertEqual(Decimal(receipt['quantity_cro']),Decimal('9.5'))
        self.assertEqual(Decimal(receipt['profit_supported_additional_cro']),Decimal('1'))

    def test_06_minimum_cannot_force_budget_upsizing(self):
        self.path=Path(self.temp.name)/'minimum.sqlite'
        self.store=OfflineExecutionCoordinator.create(self.path,account=self.account,quote='USDT',cash='100',
            limits=RiskLimits(max_fee_bps='500',max_drawdown_bps='9000'))
        self.quote('0.1',minimum='2')
        self.manager=OfflineReinvestment.create(self.store,self.baseline,seed_budget_usdt='1.1025',max_entry_budget_usdt='10')
        before=self.dump()
        with self.assertRaises(ControlError):self.reserve()
        self.assertEqual(self.dump(),before)

    def test_07_create_refuses_nonempty_store_and_preexisting_inventory(self):
        otherpath=Path(self.temp.name)/'inventory.sqlite'
        other=OfflineExecutionCoordinator.create(otherpath,account=self.account,quote='USDT',cash='100')
        with closing(sqlite3.connect(otherpath)) as db:
            with db:db.execute("INSERT INTO balances VALUES('CRO','0.1')")
        with self.assertRaises(ControlError):OfflineReinvestment.create(other,self.baseline,seed_budget_usdt='1',max_entry_budget_usdt='2')
        with self.assertRaises(ControlError):OfflineReinvestment.create(self.store,self.baseline,seed_budget_usdt='1',max_entry_budget_usdt='2')

    def test_08_open_position_and_dust_block_new_entry(self):
        result=self.reserve();self.execute_buy(result)
        self.clock+=10;self.quote('0.1')
        with self.assertRaises(ControlError):self.reserve()

    def test_09_active_and_unknown_submission_block_new_entry(self):
        first=self.reserve()
        with self.assertRaises(ControlError):self.reserve()
        self.store.begin_submission(first['intent']['client_id'],now_ms=self.clock)
        self.store.mark_unknown(first['intent']['client_id'],'TIMEOUT')
        with self.assertRaises(ControlError):self.reserve()

    def test_10_concurrent_distinct_clients_have_single_atomic_winner(self):
        barrier=threading.Barrier(2)
        def run(client):
            barrier.wait()
            try:return self.reserve(client)
            except ControlError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[str(uuid4()),str(uuid4())]))
        self.assertEqual(sum(value is not None for value in results),1)
        self.assertEqual(len(self.store.snapshot()['orders']),1)

    def test_11_same_client_idempotent_changed_intent_refused(self):
        client=str(uuid4());first=self.reserve(client);second=self.reserve(client)
        self.assertFalse(second['new_reservation'])
        self.assertEqual(first['intent'],second['intent']);self.assertEqual(first['receipt'],second['receipt'])
        for changes in ({'price':'0.11'},{'stop':'0.04'}):
            with self.subTest(changes=changes),self.assertRaises(ControlError):self.reserve(client,**changes)

    def test_12_restart_reuses_receipt_and_no_fill_ack_is_not_profit(self):
        client=str(uuid4());first=self.reserve(client)
        reopened=OfflineReinvestment(OfflineExecutionCoordinator(self.path))
        second=self.reserve(client,manager=reopened)
        self.assertEqual(first['receipt'],second['receipt']);self.assertFalse(second['new_reservation'])
        self.store.begin_submission(client,now_ms=self.clock)
        self.store.reconcile(client,exchange_order_id='unfilled',state='OPEN',cumulative_quantity='0',authoritative=True)
        self.store.reconcile(client,exchange_order_id='unfilled',state='CANCELLED',cumulative_quantity='0',authoritative=True)
        result=self.reserve(manager=reopened)
        self.assertEqual(Decimal(result['receipt']['net_realized_pnl_usdt']),0)
        self.assertEqual(Decimal(result['receipt']['profit_supported_additional_cro']),0)

    def test_13_parent_rejection_rolls_back_allocation_and_intent_together(self):
        before=self.dump()
        with self.assertRaises(ControlError):self.reserve(stop='0.2')
        self.assertEqual(self.dump(),before)
        self.assertEqual(self.store.snapshot()['orders'],[])

    def test_14_day_and_immutable_policy_binding_checked(self):
        with self.assertRaises(ControlError):self.reserve(now=86400000)
        changed=False
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                tables=[r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                for table in tables:
                    quoted='"'+table.replace('"','""')+'"'
                    columns=[row[1] for row in db.execute('PRAGMA table_info('+quoted+')')]
                    for row in db.execute('SELECT rowid,* FROM '+quoted).fetchall():
                        for i,value in enumerate(row[1:]):
                            if not isinstance(value,str):continue
                            try:policy=json.loads(value)
                            except ValueError:continue
                            if isinstance(policy,dict) and 'seed_budget_usdt' in policy:
                                policy['seed_budget_usdt']='9'
                                column='"'+columns[i].replace('"','""')+'"'
                                db.execute('UPDATE '+quoted+' SET '+column+'=? WHERE rowid=?',(json.dumps(policy),row[0]));changed=True;break
                        if changed:break
                    if changed:break
        self.assertTrue(changed,'Persisted canonical policy JSON not found')
        with self.assertRaises(ControlError):self.reserve(manager=OfflineReinvestment(self.store))

    def test_15_preparation_never_claims_submission_daily_cutoff_or_live_readiness(self):
        result=self.reserve()
        for key in ('live_dispatch_enabled','ready_for_live','daily_cutoff_enforced'):
            self.assertIs(result[key],False)
        self.assertEqual(result['orders_sent'],0)
        self.assertEqual(self.store.snapshot()['risk']['last_sequence'],0)


if __name__=='__main__':unittest.main()
