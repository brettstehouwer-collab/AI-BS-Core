"""Fifteen projections over real temporary coordinator stores; never live I/O."""
from decimal import Decimal
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import uuid4

from core.crypto_execution_controls import (ControlError, Fill, Instrument,
    OfflineExecutionCoordinator, RiskLimits, digest, encode)
from core.crypto_trial_budget import create_baseline
from core.crypto_trial_projection import project_trial_budget


class TrialProjectionSmoke(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'projection.sqlite'
        self.account = 'cryptocom-exchange:synthetic'
        self.store = OfflineExecutionCoordinator.create(self.path, account=self.account,
            quote='USDT', cash='100', limits=RiskLimits(max_fee_bps='500',max_drawdown_bps='9000'))
        self.baseline = create_baseline(trial_id=str(uuid4()),account=self.account,
            started_ms=1000,day_start_ms=0,opening_receipt_sha256='a'*64)
        self.clients=[];self.clock=1000

    def prepare(self, side='buy', quantity='10', price='0.1', submit=False):
        self.clock+=10;cid=str(uuid4());self.clients.append(cid)
        self.store.quote_market(Instrument('CRO','USDT'),bid=price,ask=price,
            observed_ms=self.clock,now_ms=self.clock)
        self.store.prepare(cid,symbol='CRO/USDT',side=side,quantity=quantity,
            limit_price=price,now_ms=self.clock,hard_stop='0.01' if side=='buy' else None)
        if submit:self.store.begin_submission(cid,now_ms=self.clock)
        return cid

    def fill(self, cid, side='buy', quantity='10', cost='1', fees=()):
        sequence=self.store.snapshot()['risk']['last_sequence']+1
        self.store.apply_fill(Fill(fill_id='synthetic-fill-'+str(sequence),client_id=cid,
            exchange_order_id=str(100+len(self.clients)),symbol='CRO/USDT',side=side,
            quantity=quantity,cost=cost,fees=fees,sequence=sequence,occurred_ms=self.clock+1))

    def buy(self, quantity='10', cost='1', fees=()):
        cid=self.prepare(quantity=quantity,submit=True)
        self.fill(cid,quantity=quantity,cost=cost,fees=fees)
        return cid

    def sell(self, quantity='5',price='0.09',cost='0.45',fees=()):
        cid=self.prepare('sell',quantity,price,submit=True)
        self.fill(cid,'sell',quantity,cost,fees)
        return cid

    def project(self, **changes):
        args=dict(trial_client_ids=self.clients,now_ms=2000,loss_budget_usdt='1',
            proposed_loss_reserve_usdt='0.1',coverage_complete=True)
        return project_trial_budget(self.store,self.baseline,**dict(args,**changes))

    def mutate(self, sql, parameters=()):
        with closing(sqlite3.connect(self.path)) as db:
            with db:
                db.execute(sql,parameters)

    def test_01_real_sell_loss_includes_quote_fees_once(self):
        self.buy(fees=(('USDT','0.01'),));self.sell(fees=(('USDT','0.0045'),))
        result=self.project();outcome=result['closed_outcomes'][0]
        self.assertEqual(Decimal(outcome['gross_pnl_usdt']),Decimal('-0.055'))
        self.assertEqual(Decimal(outcome['fees_usdt']),Decimal('0.0045'))
        self.assertEqual(Decimal(result['assessment']['closed_loss_usdt']),Decimal('0.0595'))
        self.assertEqual(Decimal(result['open_loss_reserve_usdt']),Decimal('0.505'))

    def test_02_base_fees_remove_quantity_and_basis_proportionally_once(self):
        self.buy(fees=(('CRO','0.1'),));self.sell(quantity='4',price='0.1',cost='0.4',fees=(('CRO','0.04'),))
        result=self.project();outcome=result['closed_outcomes'][0]
        expected=Decimal('0.4')-Decimal('4.04')/Decimal('9.9')
        self.assertLess(abs(Decimal(outcome['gross_pnl_usdt'])-expected),Decimal('0.00000000000000000001'))
        self.assertEqual(Decimal(outcome['fees_usdt']),0)

    def test_03_partial_buy_fills_carry_weighted_basis(self):
        cid=self.prepare(quantity='10',submit=True)
        self.fill(cid,quantity='4',cost='0.4');self.fill(cid,quantity='6',cost='0.6')
        self.sell(quantity='2',price='0.1',cost='0.2')
        result=self.project()
        self.assertEqual(len(result['source_fills']),3)
        self.assertEqual(Decimal(result['open_loss_reserve_usdt']),Decimal('0.8'))
        self.assertEqual(Decimal(result['closed_outcomes'][0]['gross_pnl_usdt']),0)

    def test_04_profitable_sell_does_not_replenish_closed_loss_allowance(self):
        self.buy();self.sell(quantity='2',price='0.09',cost='0.18')
        self.sell(quantity='2',price='0.2',cost='0.4')
        result=self.project()
        self.assertEqual(len(result['closed_outcomes']),2)
        self.assertEqual(Decimal(result['assessment']['closed_loss_usdt']),Decimal('0.02'))

    def test_05_pending_buy_uses_coordinator_reservation(self):
        self.prepare(quantity='10')
        result=self.project()
        self.assertEqual(Decimal(result['pending_loss_reserve_usdt']),Decimal('1.05'))
        self.assertTrue(result['assessment']['daily_cutoff_triggered'])

    def test_06_membership_must_cover_exact_store_orders(self):
        self.buy()
        for clients in ([],self.clients+[str(uuid4())],self.clients+self.clients):
            with self.subTest(clients=clients),self.assertRaises(ControlError):self.project(trial_client_ids=clients)

    def test_07_baseline_account_and_quote_must_match(self):
        other=create_baseline(trial_id=str(uuid4()),account='other',started_ms=1000,
            day_start_ms=0,opening_receipt_sha256='a'*64)
        with self.assertRaises(ControlError):project_trial_budget(self.store,other,trial_client_ids=[],
            now_ms=2000,loss_budget_usdt='1',proposed_loss_reserve_usdt='0',coverage_complete=True)
        usd=OfflineExecutionCoordinator.create(Path(self.temp.name)/'usd.sqlite',account=self.account,quote='USD',cash='100')
        with self.assertRaises(ControlError):project_trial_budget(usd,self.baseline,trial_client_ids=[],
            now_ms=2000,loss_budget_usdt='1',proposed_loss_reserve_usdt='0',coverage_complete=True)

    def test_08_prestart_and_future_activity_refused(self):
        self.buy()
        later=create_baseline(trial_id=self.baseline['trial_id'],account=self.account,
            started_ms=1500,day_start_ms=0,opening_receipt_sha256='a'*64)
        with self.assertRaises(ControlError):project_trial_budget(self.store,later,trial_client_ids=self.clients,
            now_ms=2000,loss_budget_usdt='1',proposed_loss_reserve_usdt='0',coverage_complete=True)
        with self.assertRaises(ControlError):self.project(now_ms=1010)

    def test_09_pending_fill_and_unmatched_receipt_refused(self):
        self.buy();self.mutate("UPDATE fills SET state='PENDING'")
        with self.assertRaises(ControlError):self.project()
        self.mutate("UPDATE fills SET state='APPLIED'")
        self.mutate('INSERT INTO unmatched_fills VALUES(?,?,?)',('unmatched','{}',digest({})))
        with self.assertRaises(ControlError):self.project()

    def test_10_payload_hash_and_application_sequence_checked(self):
        self.buy()
        row=self.store.snapshot()['fills'][0];payload=json.loads(row['payload']);payload['sequence']=2
        self.mutate('UPDATE fills SET payload=?',(encode(payload),))
        with self.assertRaises(ControlError):self.project()
        self.mutate('UPDATE fills SET fingerprint=?',(digest(payload),))
        with self.assertRaises(ControlError):self.project()

    def test_11_unknown_and_submitting_orders_refused(self):
        self.prepare(submit=True)
        with self.assertRaises(ControlError):self.project()
        self.mutate("UPDATE orders SET state='UNKNOWN'")
        with self.assertRaises(ControlError):self.project()

    def test_12_extra_inventory_or_position_drift_refused(self):
        self.buy();self.mutate("UPDATE balances SET total='11' WHERE asset='CRO'")
        with self.assertRaises(ControlError):self.project()
        self.mutate("UPDATE balances SET total='10' WHERE asset='CRO'")
        self.mutate("INSERT INTO balances VALUES('BTC','0.01')")
        with self.assertRaises(ControlError):self.project()
        self.mutate("DELETE FROM balances WHERE asset='BTC'")
        self.mutate("UPDATE positions SET basis='2'")
        with self.assertRaises(ControlError):self.project()

    def test_13_restart_projection_and_receipt_identity_are_stable(self):
        self.buy();self.sell()
        before=self.store.snapshot();first=self.project()
        reopened=OfflineExecutionCoordinator(self.path)
        second=project_trial_budget(reopened,self.baseline,trial_client_ids=tuple(self.clients),now_ms=2000,
            loss_budget_usdt='1',proposed_loss_reserve_usdt='0.1',coverage_complete=True)
        self.assertEqual(first,second);self.assertEqual(self.store.snapshot(),before)
        rows=before['fills']
        for source in first['source_fills']:
            self.assertTrue({'fill_id','receipt_key','sequence','fingerprint'} <= set(source))
            row=next(r for r in rows if r['fill_id']==source['receipt_key'])
            self.assertEqual(source['fingerprint'],row['fingerprint'])
        sellrow=next(row for row in rows if json.loads(row['payload'])['side']=='sell')
        self.assertEqual(first['closed_outcomes'][0]['event_id'],digest({'receipt_key':sellrow['fill_id']}))

    def test_14_missing_coverage_is_held_even_with_complete_arithmetic(self):
        self.buy(quantity='2',cost='0.2')
        result=self.project(coverage_complete=False)
        self.assertFalse(result['assessment']['proposed_fits'])
        self.assertFalse(result['assessment']['daily_cutoff_enforced'])
        self.assertFalse(result['assessment']['live_dispatch_enabled'])
        self.assertEqual(result['assessment']['orders_sent'],0)

    def test_15_full_principal_reserve_exceeds_one_usdt_budget(self):
        self.buy(quantity='20',cost='2')
        result=self.project()
        self.assertEqual(Decimal(result['open_loss_reserve_usdt']),Decimal('2'))
        self.assertFalse(result['assessment']['proposed_fits'])
        self.assertTrue(result['assessment']['daily_cutoff_triggered'])
        self.assertFalse(result['assessment']['ready_for_live'])


if __name__ == '__main__':unittest.main()
