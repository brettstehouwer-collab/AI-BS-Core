"""Ten coupled allocation/intent fault checks; owned temporary stores only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest
from uuid import uuid4

from tests.test_crypto_reinvestment_smoke import ReinvestmentSmoke
from core.crypto_execution_controls import ControlError, OfflineExecutionCoordinator
from core.crypto_reinvestment import OfflineReinvestment


class ReinvestmentAtomicSmoke(unittest.TestCase):
    setUp=ReinvestmentSmoke.setUp
    quote=ReinvestmentSmoke.quote
    reserve=ReinvestmentSmoke.reserve
    dump=ReinvestmentSmoke.dump

    def sql(self, text, args=()):
        with closing(sqlite3.connect(self.path)) as db:
            with db:db.execute(text,args)

    def assert_empty(self):
        self.assertEqual(self.store.snapshot()['orders'],[])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aibs_reinvestment_entries').fetchone()[0],0)

    def cancel(self, client):
        self.store.begin_submission(client,now_ms=self.clock)
        self.store.reconcile(client,exchange_order_id='synthetic-unfilled',state='OPEN',cumulative_quantity='0',authoritative=True)
        self.store.reconcile(client,exchange_order_id='synthetic-unfilled',state='CANCELLED',cumulative_quantity='0',authoritative=True)

    def test_01_allocation_insert_abort_rolls_back_parent_intent_reserves_events(self):
        self.sql("CREATE TRIGGER fail_allocation BEFORE INSERT ON aibs_reinvestment_entries BEGIN SELECT RAISE(ABORT,'synthetic allocation rejection'); END")
        before=self.dump()
        with self.assertRaises((sqlite3.Error,ControlError)):self.reserve()
        self.assertEqual(self.dump(),before)
        self.assert_empty()

    def test_02_event_abort_after_allocation_rolls_back_both(self):
        self.sql("CREATE TRIGGER fail_final_event BEFORE INSERT ON events WHEN NEW.kind='OFFLINE_REINVESTMENT_INTENT_RESERVED' BEGIN SELECT RAISE(ABORT,'synthetic final event rejection'); END")
        before=self.dump()
        with self.assertRaises((sqlite3.Error,ControlError)):self.reserve()
        self.assertEqual(self.dump(),before)
        self.assert_empty()

    def test_03_parent_order_insert_abort_leaves_no_allocation(self):
        self.sql("CREATE TRIGGER fail_parent BEFORE INSERT ON orders BEGIN SELECT RAISE(ABORT,'synthetic parent rejection'); END")
        before=self.dump()
        with self.assertRaises((sqlite3.Error,ControlError)):self.reserve()
        self.assertEqual(self.dump(),before)
        self.assert_empty()

    def crash_child(self, kind, expected):
        folder=Path(self.temp.name).resolve();script=folder/('owned_crash_'+str(expected)+'.py')
        self.assertTrue(script.resolve().is_relative_to(folder))
        script.write_text('''import os,sys
from core.crypto_execution_controls import OfflineExecutionCoordinator
from core.crypto_reinvestment import OfflineReinvestment
class OwnedCrashCoordinator(OfflineExecutionCoordinator):
    @staticmethod
    def _event(db,kind,data):
        OfflineExecutionCoordinator._event(db,kind,data)
        if kind==sys.argv[3]:os._exit(int(sys.argv[4]))
store=OwnedCrashCoordinator(sys.argv[1])
OfflineReinvestment(store).reserve_entry(sys.argv[2],limit_price='0.1',hard_stop='0.05',now_ms=int(sys.argv[5]))
raise SystemExit(99)
''',encoding='utf-8')
        before=self.dump()
        process=subprocess.run([sys.executable,'-B',str(script),str(self.path),str(uuid4()),kind,str(expected),str(self.clock)],
            cwd=folder,stdin=subprocess.DEVNULL,capture_output=True,timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps({'owned_child_kind':kind,'expected_exit':expected,'actual_exit':process.returncode,
            'stdout':process.stdout.decode('utf-8',errors='replace'),'stderr':process.stderr.decode('utf-8',errors='replace')}),flush=True)
        self.assertEqual(process.returncode,expected)
        reopened=OfflineExecutionCoordinator(self.path)
        self.assertEqual(reopened.snapshot()['orders'],[])
        self.assertEqual(self.dump(),before)
        self.assert_empty()

    def test_04_child_exit71_after_parent_insert_before_allocation(self):
        self.crash_child('INTENT_RESERVED',71)

    def test_05_child_exit72_after_allocation_before_commit(self):
        self.crash_child('OFFLINE_REINVESTMENT_INTENT_RESERVED',72)

    def test_06_same_client_concurrency_one_new_one_replayed(self):
        client=str(uuid4());barrier=threading.Barrier(2)
        def run(_):barrier.wait();return self.reserve(client)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
        self.assertEqual(sorted(r['new_reservation'] for r in results),[False,True])
        self.assertEqual(results[0]['receipt'],results[1]['receipt'])
        self.assertEqual(len(self.store.snapshot()['orders']),1)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aibs_reinvestment_entries').fetchone()[0],1)

    def test_07_cancelled_replay_keeps_receipt_and_reports_current_state(self):
        client=str(uuid4());first=self.reserve(client);self.cancel(client)
        replay=self.reserve(client)
        self.assertFalse(replay['new_reservation'])
        self.assertEqual(replay['intent']['state'],'CANCELLED')
        self.assertEqual(replay['receipt'],first['receipt'])
        self.assertFalse(replay['submission_started'])

    def test_08_actual_metadata_limits_change_refused_with_cached_coordinator(self):
        with closing(sqlite3.connect(self.path)) as db:
            limits=json.loads(db.execute("SELECT value FROM metadata WHERE key='limits'").fetchone()[0])
        limits['max_fee_bps']='400'
        self.sql("UPDATE metadata SET value=? WHERE key='limits'",(json.dumps(limits),))
        before=self.dump()
        with self.assertRaises(ControlError):self.reserve()
        self.assertEqual(self.dump(),before)

    def test_09_deleted_cancelled_entry_receipt_blocks_unattributed_capital(self):
        client=str(uuid4());self.reserve(client);self.cancel(client)
        self.sql('DELETE FROM aibs_reinvestment_entries WHERE client_id=?',(client,))
        before=self.dump()
        with self.assertRaises(ControlError):self.reserve()
        self.assertEqual(self.dump(),before)

    def test_10_increased_cash_is_not_profit_or_seed_expansion(self):
        self.sql("UPDATE balances SET total='1000' WHERE asset='USDT'")
        result=self.reserve();receipt=result['receipt']
        self.assertEqual(Decimal(receipt['working_capital_usdt']),Decimal('1.1025'))
        self.assertEqual(Decimal(receipt['net_realized_pnl_usdt']),0)
        self.assertEqual(Decimal(receipt['profit_supported_additional_cro']),0)
        self.assertEqual(Decimal(receipt['quantity_cro']),Decimal('10.5'))
        self.assertFalse(result['live_dispatch_enabled'])
        self.assertEqual(result['orders_sent'],0)


if __name__=='__main__':unittest.main()
