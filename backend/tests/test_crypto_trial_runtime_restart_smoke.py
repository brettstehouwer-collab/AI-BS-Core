"""Ten true fresh-process durable-store cases; owned synthetic fixtures retained."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

from core.crypto_execution_controls import Fill, RiskLimits
from core.crypto_trial_binding import qualification_account_observation
from core.crypto_trial_budget import create_baseline
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from core.crypto_trial_admission import TrialEntryHeld
from tests import test_crypto_trial_runtime_store_smoke as fixture


EVIDENCE=Path('C:/AI-BS/backups/crypto_trial_runtime_store_20261115_v01/restart')
NOW=1794772800001
PRELUDE='''import json,os,sys
from pathlib import Path
from core.crypto_trial_runtime_store import PersistentTrialRuntime
from core.crypto_execution_controls import ControlError
c=json.load(sys.stdin)
def reopen():
 return PersistentTrialRuntime.open(c['root'],expected_store_uuid=c['uuid'],expected_account=c['account'],qualification=c.get('qualification',True))
'''


class TrialRuntimeRestartSmoke(unittest.TestCase):
    create=fixture.PersistentTrialRuntimeSmoke.create
    quote=fixture.PersistentTrialRuntimeSmoke.quote

    def setUp(self):
        EVIDENCE.mkdir(parents=True,exist_ok=True)
        self.parent=EVIDENCE/('fixture_'+uuid4().hex);self.parent.mkdir()
        self.observation=qualification_account_observation(account_id=str(uuid4()),
            started_ms=1794772799900,completed_ms=1794772799999)
        self.baseline=create_baseline(trial_id=str(uuid4()),account=self.observation.account,
            started_ms=1794772800000,day_start_ms=(1794772800000//86400000)*86400000,
            opening_receipt_sha256='c'*64)

    def config(self,owner,**changes):
        return dict(dict(root=str(owner.root),uuid=owner.store_uuid,account=self.observation.account),**changes)

    def child(self,script,cfg,expected=0):
        source=PRELUDE+script
        index=len(list(self.parent.glob('child-*.py')))+1
        (self.parent/f'child-{index}.py').write_text(source)
        result=subprocess.run([sys.executable,'-B','-c',source],input=json.dumps(cfg),
            text=True,capture_output=True,cwd=str(Path(__file__).resolve().parents[1]),timeout=20)
        (self.parent/f'child-{index}.json').write_text(json.dumps(dict(returncode=result.returncode,
            stdout=result.stdout,stderr=result.stderr),indent=2))
        self.assertEqual(result.returncode,expected,result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def intent(self,owner):
        self.quote(owner);client=str(uuid4())
        return owner.reinvestment.reserve_entry(client,limit_price='0.1',hard_stop='0.08',now_ms=NOW)

    def fingerprints(self,owner):
        return {name:sha256((owner.root/name).read_bytes()).hexdigest()
            for name in ('accounting.sqlite3','store.json')}

    def refused_child(self,owner,**changes):
        before=self.fingerprints(owner)
        self.child('''try:
 o=reopen()
except Exception:
 print(json.dumps({'refused':True}))
else:
 o.close();sys.exit(90)
''',self.config(owner,**changes))
        self.assertEqual(self.fingerprints(owner),before)

    def test_01_fresh_normal_reopen_keeps_uuid_intent_and_flags(self):
        owner=self.create();result=self.intent(owner);cfg=self.config(owner);owner.close()
        record=self.child('''with reopen() as o:
 print(json.dumps({'uuid':o.store_uuid,'snapshot':o.coordinator.snapshot(),'status':o.status()}))
''',cfg)
        self.assertEqual(record['uuid'],cfg['uuid'])
        self.assertEqual(record['snapshot']['orders'][0]['client_id'],result['intent']['client_id'])
        self.assertEqual(record['snapshot']['orders'][0]['state'],'INTENT')
        for key in ('live_dispatch_enabled','ready_for_live','production_store_admitted','exchange_account_identity_verified'):
            self.assertIs(record['status'][key],False)
        self.assertEqual(record['status']['orders_sent'],0)

    def test_02_abrupt_child_exit_releases_lifetime_lock(self):
        owner=self.create();self.intent(owner);cfg=self.config(owner);owner.close()
        self.child("o=reopen();o.status();os._exit(73)\n",cfg,expected=73)
        with PersistentTrialRuntime.open(owner.root,expected_store_uuid=cfg['uuid'],
                expected_account=cfg['account'],qualification=True) as reopened:
            self.assertEqual(len(reopened.coordinator.snapshot()['orders']),1)

    def test_03_exit_after_creating_publish_never_reinitializes(self):
        cfg=dict(parent=str(self.parent),account_id=self.observation.account_id)
        self.child('''from core import crypto_trial_runtime_store as runtime
from core.crypto_trial_binding import qualification_account_observation
from core.crypto_trial_budget import create_baseline
from uuid import uuid4
original=runtime._publish
def exit_after_publish(root,record,**kwargs):
 original(root,record,**kwargs)
 if record['state']=='CREATING':os._exit(74)
runtime._publish=exit_after_publish
obs=qualification_account_observation(account_id=c['account_id'],started_ms=1794772799900,completed_ms=1794772799999)
baseline=create_baseline(trial_id=str(uuid4()),account=obs.account,started_ms=1794772800000,day_start_ms=(1794772800000//86400000)*86400000,opening_receipt_sha256='c'*64)
runtime.PersistentTrialRuntime.create(c['parent'],'incomplete',observation=obs,baseline=baseline,seed_budget_usdt='1',max_entry_budget_usdt='2',daily_loss_budget_usdt='1',qualification=True)
''',cfg,expected=74)
        root=self.parent/'incomplete';raw=(root/'store.json').read_bytes()
        self.assertEqual(json.loads(raw)['record']['state'],'CREATING')
        cfg=dict(root=str(root),uuid=str(uuid4()),account=self.observation.account)
        self.child('''try:reopen()
except Exception:print(json.dumps({'refused':True}))
else:sys.exit(90)
''',cfg)
        self.assertEqual((root/'store.json').read_bytes(),raw)
        self.assertFalse((root/'accounting.sqlite3').exists())

    def test_04_parent_owner_excludes_fresh_child(self):
        owner=self.create();self.refused_child(owner)
        self.assertFalse(owner.status()['ready_for_live'])

    def test_05_wrong_store_uuid_refuses_unchanged(self):
        owner=self.create();owner.close();self.refused_child(owner,uuid=str(uuid4()))

    def test_06_wrong_account_refuses_unchanged(self):
        owner=self.create();owner.close();self.refused_child(owner,account='wrong-account')

    def test_07_wrong_mode_refuses_unchanged(self):
        owner=self.create();owner.close();self.refused_child(owner,qualification=False)

    def test_08_same_client_child_receipt_never_reserves_twice(self):
        owner=self.create();result=self.intent(owner);cfg=self.config(owner,client=result['intent']['client_id']);owner.close()
        record=self.child('''with reopen() as o:
 a=o.reinvestment.reserve_entry(c['client'],limit_price='0.1',hard_stop='0.08',now_ms=1794772800001)
 b=o.reinvestment.reserve_entry(c['client'],limit_price='0.1',hard_stop='0.08',now_ms=1794772800001)
 print(json.dumps({'a':a,'b':b,'orders':len(o.coordinator.snapshot()['orders'])}))
''',cfg)
        self.assertEqual(record['orders'],1);self.assertFalse(record['a']['new_reservation'])
        self.assertFalse(record['b']['new_reservation'])
        self.assertEqual(record['a']['receipt'],result['receipt']);self.assertEqual(record['b']['receipt'],result['receipt'])

    def test_09_entry_cutoff_latch_survives_fresh_process(self):
        owner=self.create();entry=self.intent(owner);buy=entry['intent']['client_id']
        owner.coordinator.begin_submission(buy,now_ms=NOW)
        owner.coordinator.apply_fill(Fill(fill_id='buy',client_id=buy,exchange_order_id='buy-order',
            symbol='CRO/USDT',side='buy',quantity=entry['receipt']['quantity_cro'],cost='1.05',
            fees=(('USDT','0.0525'),),sequence=1,occurred_ms=NOW+1))
        self.quote(owner,'0.01',NOW+10);sell=str(uuid4())
        owner.coordinator.prepare(sell,symbol='CRO/USDT',side='sell',quantity='10',limit_price='0.01',now_ms=NOW+10)
        owner.coordinator.begin_submission(sell,now_ms=NOW+10)
        owner.coordinator.apply_fill(Fill(fill_id='sell',client_id=sell,exchange_order_id='sell-order',
            symbol='CRO/USDT',side='sell',quantity='10',cost='0.1',fees=(('CRO','0.5'),),sequence=2,occurred_ms=NOW+11))
        self.quote(owner,'0.1',NOW+20)
        with self.assertRaises(TrialEntryHeld):owner.reinvestment.reserve_entry(str(uuid4()),limit_price='0.1',hard_stop='0.08',now_ms=NOW+20)
        cfg=self.config(owner);owner.close()
        record=self.child('''with reopen() as o:
 print(json.dumps({'entry':o.coordinator.entry_status(),'snapshot':o.coordinator.snapshot()}))
''',cfg)
        self.assertTrue(record['entry']['entry_held']);self.assertEqual(record['snapshot']['risk']['halted'],0)
        self.assertEqual(len(record['snapshot']['fills']),2)

    def test_10_byte_identical_replaced_database_refused(self):
        owner=self.create();self.intent(owner);owner.close();db=owner.root/'accounting.sqlite3'
        raw=db.read_bytes();db.rename(owner.root/'accounting.sqlite3.original');db.write_bytes(raw)
        self.refused_child(owner)
        self.assertEqual(db.read_bytes(),raw)


if __name__=='__main__':unittest.main()
