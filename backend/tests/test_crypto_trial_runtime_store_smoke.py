"""Fifteen durable qualification-store cases; no account transport or live orders."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from uuid import uuid4

from core.crypto_execution_controls import ControlError, Fill, Instrument, RiskLimits
from core.crypto_trial_budget import create_baseline
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from core.crypto_trial_binding import qualification_account_observation
from core.crypto_trial_admission import TrialEntryHeld


class PersistentTrialRuntimeSmoke(unittest.TestCase):
    def setUp(self):
        self.parent=Path('C:/AI-BS/backups')/('crypto_runtime_store_fixtures_'+uuid4().hex)
        self.parent.mkdir()
        self.observation=qualification_account_observation(account_id=str(uuid4()),
            started_ms=1794772799900,completed_ms=1794772799999)
        self.baseline=create_baseline(trial_id=str(uuid4()),account=self.observation.account,
            started_ms=1794772800000,day_start_ms=(1794772800000//86400000)*86400000,opening_receipt_sha256='c'*64)

    def create(self, **changes):
        args=dict(observation=self.observation,baseline=self.baseline,seed_budget_usdt='1.1025',
            max_entry_budget_usdt='10',daily_loss_budget_usdt='1',qualification=True,initial_cash_usdt='100',
            limits=RiskLimits(max_fee_bps='500',max_drawdown_bps='9000'))
        args.update(changes)
        owner=PersistentTrialRuntime.create(self.parent,'trial',**args)
        self.addCleanup(owner.close)
        return owner

    def reopen(self, owner, **changes):
        args=dict(expected_store_uuid=owner.store_uuid,expected_account=self.observation.account,qualification=True)
        args.update(changes)
        result=PersistentTrialRuntime.open(owner.root,**args)
        self.addCleanup(result.close)
        return result

    def quote(self, owner,price='0.1',now=1794772800001):
        owner.coordinator.quote_market(Instrument('CRO','USDT',quantity_step='0.5',price_tick='0.01',
            minimum_quantity='0.5',minimum_notional='0.01'),bid=price,ask=price,observed_ms=now,now_ms=now)

    def test_01_create_reopen_retains_identity_and_policies(self):
        owner=self.create();identity=owner.store_uuid;root=owner.root
        with sqlite3.connect(root/'accounting.sqlite3') as db:
            policies=db.execute("SELECT payload FROM aibs_reinvestment_policy").fetchall()
        owner.close();other=self.reopen(owner)
        self.assertEqual(other.root,root);self.assertEqual(other.store_uuid,identity)
        with sqlite3.connect(root/'accounting.sqlite3') as db:
            self.assertEqual(db.execute("SELECT payload FROM aibs_reinvestment_policy").fetchall(),policies)

    def test_02_baseline_account_mismatch_refused(self):
        baseline=create_baseline(trial_id=str(uuid4()),account='wrong-account',started_ms=1794772800000,
            day_start_ms=(1794772800000//86400000)*86400000,opening_receipt_sha256='c'*64)
        with self.assertRaises(ControlError):self.create(baseline=baseline)

    def test_03_default_rejects_qualification_observation(self):
        with self.assertRaises(ControlError):self.create(qualification=False)

    def test_04_second_owner_is_excluded(self):
        owner=self.create()
        with self.assertRaises((ControlError,OSError,RuntimeError)):self.reopen(owner)

    def test_05_missing_database_is_not_reinitialized(self):
        owner=self.create();owner.close();db=owner.root/'accounting.sqlite3'
        db.rename(owner.root/'accounting.sqlite3.retained')
        with self.assertRaises((ControlError,OSError,RuntimeError)):self.reopen(owner)
        self.assertFalse(db.exists())

    def test_06_corrupt_database_is_not_reinitialized(self):
        owner=self.create();owner.close();db=owner.root/'accounting.sqlite3'
        db.write_bytes(b'not a SQLite database')
        with self.assertRaises((ControlError,OSError,RuntimeError,sqlite3.Error)):self.reopen(owner)
        self.assertEqual(db.read_bytes(),b'not a SQLite database')

    def test_07_expected_store_uuid_mismatch_refused(self):
        owner=self.create();owner.close()
        with self.assertRaises(ControlError):self.reopen(owner,expected_store_uuid=str(uuid4()))

    def test_08_expected_account_mismatch_refused(self):
        owner=self.create();owner.close()
        with self.assertRaises(ControlError):self.reopen(owner,expected_account='wrong-account')

    def test_09_locator_tamper_is_refused_and_preserved(self):
        owner=self.create();owner.close();path=owner.root/'store.json'
        original=path.read_bytes();path.write_bytes(original+b' ')
        with self.assertRaises((ControlError,OSError,RuntimeError)):self.reopen(owner)
        self.assertEqual(path.read_bytes(),original+b' ')

    def test_10_database_identity_replacement_is_refused(self):
        owner=self.create();owner.close();db=owner.root/'accounting.sqlite3';raw=db.read_bytes()
        db.rename(owner.root/'accounting.sqlite3.original');db.write_bytes(raw)
        with self.assertRaises((ControlError,OSError,RuntimeError)):self.reopen(owner)

    def test_11_root_identity_replacement_is_refused(self):
        owner=self.create();owner.close();root=owner.root
        root.rename(root.with_name('trial.original'));root.mkdir()
        for name in ('store.json','accounting.sqlite3'):
            source=root.with_name('trial.original')/name
            (root/name).write_bytes(source.read_bytes())
        with self.assertRaises((ControlError,OSError,RuntimeError)):self.reopen(owner)

    def test_12_unready_or_missing_locator_refused_without_empty_init(self):
        root=self.parent/'incomplete';root.mkdir();(root/'creation.partial').write_text('retained')
        with self.assertRaises((ControlError,OSError,RuntimeError)):
            PersistentTrialRuntime.open(root,expected_store_uuid=str(uuid4()),
                expected_account=self.observation.account,qualification=True)
        self.assertEqual((root/'creation.partial').read_text(),'retained')
        self.assertFalse((root/'accounting.sqlite3').exists())

    def test_13_closed_cycle_and_entry_latch_survive_reopen(self):
        owner=self.create();self.quote(owner);client=str(uuid4())
        result=owner.reinvestment.reserve_entry(client,limit_price='0.1',hard_stop='0.08',now_ms=1794772800001)
        owner.coordinator.begin_submission(client,now_ms=1794772800001)
        owner.coordinator.apply_fill(Fill(fill_id='buy',client_id=client,exchange_order_id='buy-order',
            symbol='CRO/USDT',side='buy',quantity=result['receipt']['quantity_cro'],cost='1.05',
            fees=(('USDT','0.0525'),),sequence=1,occurred_ms=1794772800002))
        self.quote(owner,'0.01',1794772800011);sell=str(uuid4())
        owner.coordinator.prepare(sell,symbol='CRO/USDT',side='sell',quantity='10',limit_price='0.01',now_ms=1794772800011)
        owner.coordinator.begin_submission(sell,now_ms=1794772800011)
        owner.coordinator.apply_fill(Fill(fill_id='sell',client_id=sell,exchange_order_id='sell-order',
            symbol='CRO/USDT',side='sell',quantity='10',cost='0.1',fees=(('CRO','0.5'),),
            sequence=2,occurred_ms=1794772800012))
        self.quote(owner,'0.1',1794772800021)
        with self.assertRaises(TrialEntryHeld):
            owner.reinvestment.reserve_entry(str(uuid4()),limit_price='0.1',hard_stop='0.08',now_ms=1794772800021)
        owner.close();other=self.reopen(owner)
        self.assertTrue(other.coordinator.entry_status()['entry_held'])
        self.assertEqual(other.coordinator.snapshot()['risk']['halted'],0)
        self.assertEqual(len(other.coordinator.snapshot()['fills']),2)

    def test_14_closed_owner_refuses_stale_coordinator(self):
        owner=self.create();coordinator=owner.coordinator;owner.close()
        with self.assertRaises((ControlError,OSError,RuntimeError)):coordinator.snapshot()

    def test_15_durable_private_root_and_explicit_unqualified_status(self):
        owner=self.create();status=owner.status()
        self.assertEqual(owner.root.parent,self.parent)
        self.assertNotIn(Path(tempfile.gettempdir()),owner.root.parents)
        self.assertTrue(status['account_metadata_bound'])
        for key in ('exchange_coverage_verified','exchange_account_identity_verified','live_dispatch_enabled','ready_for_live'):
            self.assertIs(status[key],False)
        self.assertEqual(status['orders_sent'],0)
        temporary=Path(tempfile.gettempdir())/('crypto_runtime_forbidden_'+uuid4().hex)
        with self.assertRaises((ControlError,OSError,RuntimeError,ValueError)):
            PersistentTrialRuntime.create(temporary,'trial',observation=self.observation,
                baseline=self.baseline,seed_budget_usdt='1.1025',max_entry_budget_usdt='10',
                daily_loss_budget_usdt='1',qualification=True,initial_cash_usdt='100',
            limits=RiskLimits(max_fee_bps='500',max_drawdown_bps='9000'))


if __name__=='__main__':unittest.main()



