"""Ten cooperative API-writer fence cases over real temporary offline stores."""
from contextlib import closing
import sqlite3
import unittest
from uuid import uuid4

from tests.test_crypto_trial_admission_smoke import TrialAdmissionSmoke as Fixture
from core.crypto_execution_controls import ControlError, OfflineExecutionCoordinator, encode
from core.crypto_trial_admission import OfflineTrialAdmission


class TrialAdmissionFenceSmoke(unittest.TestCase):
    setUp=Fixture.setUp
    quote=Fixture.quote
    reserve=Fixture.reserve
    execute_buy=Fixture.execute_buy
    dump=Fixture.dump
    sql=Fixture.sql

    def base(self):
        return OfflineExecutionCoordinator(self.path)

    def prepared(self):
        return self.reserve(stop='0.08')['intent']['client_id']

    def assert_base_submit_blocked(self, client):
        before=self.store.snapshot()['risk']['submission_sequence']
        with self.assertRaises(sqlite3.IntegrityError):
            self.base().begin_submission(client,now_ms=self.clock)
        snapshot=self.store.snapshot()
        self.assertEqual(snapshot['risk']['submission_sequence'],before)
        self.assertEqual(next(row for row in snapshot['orders'] if row['client_id']==client)['state'],'INTENT')

    def forge_submission(self, client, **changes):
        with closing(sqlite3.connect(self.path)) as db:
            fingerprint=db.execute('SELECT fingerprint FROM orders WHERE client_id=?',(client,)).fetchone()[0]
            sequence=db.execute('SELECT last_sequence,submission_sequence FROM risk WHERE id=1').fetchone()
        approval=dict(client_id=client,phase='SUBMISSION',checked_ms=self.clock,
            baseline_sha256=self.baseline['baseline_sha256'],request_sha256=fingerprint,
            last_sequence=sequence[0],expected_submission_sequence=sequence[1]+1,
            closed_loss_usdt='0',modeled_loss_reserve_usdt='0.1',guaranteed_maximum_loss=False)
        approval.update(changes)
        self.sql('INSERT INTO events(kind,payload) VALUES(?,?)',('OFFLINE_TRIAL_ENTRY_ADMITTED',encode(approval)))

    def test_01_base_buy_insert_is_blocked_without_allocation(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.base().prepare(str(uuid4()),symbol='CRO/USDT',side='buy',quantity='1',
                limit_price='0.1',hard_stop='0.08',now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'],[])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aibs_reinvestment_entries').fetchone()[0],0)

    def test_02_base_cannot_submit_manager_prepared_buy(self):
        self.assert_base_submit_blocked(self.prepared())

    def test_03_registered_subclass_can_submit(self):
        client=self.prepared()
        self.store.begin_submission(client,now_ms=self.clock)
        self.assertEqual(self.store.snapshot()['orders'][0]['state'],'SUBMITTING')

    def test_04_other_client_preparation_event_cannot_authorize_insert(self):
        self.prepared()
        with self.assertRaises(sqlite3.IntegrityError):
            self.base().prepare(str(uuid4()),symbol='CRO/USDT',side='buy',quantity='1',
                limit_price='0.1',hard_stop='0.08',now_ms=self.clock)
        self.assertEqual(len(self.store.snapshot()['orders']),1)

    def test_05_preparation_phase_cannot_authorize_submission(self):
        client=self.prepared()
        self.forge_submission(client,phase='PREPARATION')
        self.assert_base_submit_blocked(client)

    def test_06_wrong_request_hash_cannot_authorize_submission(self):
        client=self.prepared()
        self.forge_submission(client,request_sha256='0'*64)
        self.assert_base_submit_blocked(client)

    def test_07_wrong_fill_sequence_cannot_authorize_submission(self):
        client=self.prepared()
        self.forge_submission(client,last_sequence=999)
        self.assert_base_submit_blocked(client)

    def test_08_wrong_submission_sequence_cannot_authorize_submission(self):
        client=self.prepared()
        self.forge_submission(client,expected_submission_sequence=999)
        self.assert_base_submit_blocked(client)

    def test_09_base_reducing_sell_remains_available(self):
        result=self.reserve(stop='0.08');self.execute_buy(result)
        self.clock+=10;self.quote('0.1');client=str(uuid4())
        base=self.base()
        base.prepare(client,symbol='CRO/USDT',side='sell',quantity='1',limit_price='0.1',now_ms=self.clock)
        base.begin_submission(client,now_ms=self.clock)
        self.assertEqual(next(row for row in base.snapshot()['orders'] if row['client_id']==client)['state'],'SUBMITTING')

    def test_10_missing_guard_is_detected_on_status_and_reopen(self):
        self.sql('DROP TRIGGER IF EXISTS aibs_trial_buy_prepare_guard')
        with self.assertRaises(ControlError):self.store.entry_status()
        with self.assertRaises(ControlError):OfflineTrialAdmission(self.path)


if __name__=='__main__':unittest.main()
