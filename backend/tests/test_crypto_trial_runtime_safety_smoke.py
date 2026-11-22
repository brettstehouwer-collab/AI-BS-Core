"""Ten controlled durable-runtime lifecycle fault checks; synthetic local files only."""
from contextlib import contextmanager
from pathlib import Path
import os
import subprocess
import unittest
from unittest.mock import patch
from uuid import uuid4

from tests.test_crypto_trial_runtime_store_smoke import PersistentTrialRuntimeSmoke as Fixture
from core.crypto_execution_controls import ControlError
from security.crypto_trial_root import TrialRootError
from core.crypto_trial_runtime_store import PersistentTrialRuntime


class PersistentTrialSafetySmoke(unittest.TestCase):
    setUp=Fixture.setUp
    create=Fixture.create
    reopen=Fixture.reopen
    quote=Fixture.quote

    def closed(self):
        owner=self.create();owner.close();return owner

    def lock_target(self,owner):
        lock=owner.root/'runtime.lock'
        self.assertTrue(lock.exists())
        retained=owner.root/'runtime.lock.original';lock.rename(retained)
        outside=self.parent/'controlled-outside-lock';outside.write_bytes(b'CONTROLLED-FIXTURE-UNCHANGED')
        return lock,outside

    def assert_bad_reopen(self,owner):
        with self.assertRaises((ControlError,OSError,RuntimeError,TrialRootError)):self.reopen(owner)

    def test_01_lock_hardlink_refused_before_external_bytes_change(self):
        owner=self.closed();lock,outside=self.lock_target(owner);os.link(outside,lock)
        self.assert_bad_reopen(owner)
        self.assertEqual(outside.read_bytes(),b'CONTROLLED-FIXTURE-UNCHANGED')

    def test_02_lock_reparse_refused_before_external_bytes_change(self):
        owner=self.closed();lock,outside=self.lock_target(owner)
        os.symlink(outside,lock)
        self.assert_bad_reopen(owner)
        self.assertEqual(outside.read_bytes(),b'CONTROLLED-FIXTURE-UNCHANGED')

    def test_03_lock_alternate_stream_refused_without_stream_change(self):
        owner=self.closed();stream=Path(str(owner.root/'runtime.lock')+':qualification_drift')
        stream.write_bytes(b'RETAINED-ADS')
        self.assert_bad_reopen(owner)
        self.assertEqual(stream.read_bytes(),b'RETAINED-ADS')

    def test_04_oversized_locator_refused_without_rewrite(self):
        owner=self.closed();locator=owner.root/'store.json';raw=b'x'*32769;locator.write_bytes(raw)
        self.assert_bad_reopen(owner)
        self.assertEqual(locator.read_bytes(),raw)

    def test_05_root_acl_drift_refuses_next_transaction(self):
        owner=self.create()
        result=subprocess.run(['icacls',str(owner.root),'/grant','*S-1-5-32-545:(OI)(CI)(RX)'],
            capture_output=True,text=True,check=False)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        with self.assertRaises((ControlError,OSError,RuntimeError,TrialRootError)):owner.coordinator.snapshot()

    def test_06_database_ads_drift_refuses_next_transaction(self):
        owner=self.create();stream=Path(str(owner.root/'accounting.sqlite3')+':qualification_drift')
        stream.write_bytes(b'RETAINED-DB-ADS')
        with self.assertRaises((ControlError,OSError,RuntimeError,TrialRootError)):owner.coordinator.snapshot()
        self.assertEqual(stream.read_bytes(),b'RETAINED-DB-ADS')

    def test_07_stale_coordinator_stays_closed_after_new_owner_reopens(self):
        owner=self.create();stale=owner.coordinator;owner.close();new=self.reopen(owner)
        self.assertEqual(new.coordinator.snapshot()['fills'],[])
        with self.assertRaises((ControlError,OSError,RuntimeError,TrialRootError)):stale.snapshot()
        with self.assertRaises(ControlError):owner.status()

    def test_08_locator_whitespace_is_not_silently_normalized(self):
        owner=self.closed();locator=owner.root/'store.json';raw=locator.read_bytes()+b'\n'
        locator.write_bytes(raw);self.assert_bad_reopen(owner)
        self.assertEqual(locator.read_bytes(),raw)

    def test_09_old_qualification_observation_remains_dated_and_not_production(self):
        owner=self.closed();new=self.reopen(owner);status=new.status()
        self.assertFalse(status['production_store_admitted'])
        self.assertFalse(status['exchange_account_identity_verified'])
        self.assertFalse(status['ready_for_live'])
        self.assertEqual(new._record['observation']['completed_ms'],self.observation.completed_ms)
        self.assertEqual(status['observation_scope'],'QUALIFICATION_ONLY')

    def test_10_failed_lifetime_lock_retains_incomplete_root(self):
        @contextmanager
        def fail_lock(*args,**kwargs):
            raise RuntimeError('controlled lock refusal')
            yield
        with patch('core.crypto_trial_runtime_store.record_lock',fail_lock):
            with self.assertRaises(ControlError):self.create()
        root=self.parent/'trial';self.assertTrue(root.exists())
        before={p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}
        with self.assertRaises((ControlError,OSError,RuntimeError,TrialRootError)):
            PersistentTrialRuntime.open(root,expected_store_uuid=str(uuid4()),
                expected_account=self.observation.account,qualification=True)
        after={p.name:p.read_bytes() for p in root.iterdir() if p.is_file()}
        self.assertEqual(after,before)
        self.assertFalse((root/'accounting.sqlite3').exists())


if __name__=='__main__':unittest.main()

