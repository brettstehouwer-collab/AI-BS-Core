"""Synthetic ownership/admission checks; no live services, providers or databases."""
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from backend.core.swarm_orchestration import (AdmissionError, OwnershipViolation, Policy,
                                              ROLES, SwarmRegistry, load_policy)

ROOT = Path(__file__).resolve().parents[2]


class SwarmTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = SwarmRegistry(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_inert_config_and_invalid_nested_types(self):
        original = json.loads((ROOT / 'config/swarm_orchestration.json').read_text())
        self.assertEqual(load_policy(ROOT / 'config/swarm_orchestration.json'), Policy())
        for section, key, invalid in [('admission','max_active_agents',True),
            ('admission','max_active_agents',5), ('sqlite','busy_timeout_ms',True),
            ('activation','provider_calls',True), ('enforcement','cpu_affinity_enforced',True)]:
            value = json.loads(json.dumps(original)); value[section][key] = invalid
            p = self.root / 'policy.json'; p.write_text(json.dumps(value))
            with self.assertRaises(ValueError): load_policy(p)
        p.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError): load_policy(p)

    def test_four_active_three_workers_and_fifth_role_scheduled(self):
        leases = [self.registry.acquire('lead',ROLES[0], [])]
        leases += [self.registry.acquire(str(i),r,[]) for i,r in enumerate(ROLES[1:4])]
        with self.assertRaises(AdmissionError): self.registry.acquire('db',ROLES[4],[])
        self.registry.finish(leases.pop())
        leases.append(self.registry.acquire('db',ROLES[4],[]))
        self.assertEqual(self.registry.snapshot()['active'],4)
        for lease in leases: self.registry.finish(lease)
        self.assertTrue(self.registry.is_drained())

    def test_reserved_lead_slot_and_single_lead(self):
        for i in range(3): self.registry.acquire(str(i),ROLES[1],[])
        with self.assertRaises(AdmissionError): self.registry.acquire('fourth',ROLES[2],[])
        self.registry.acquire('lead',ROLES[0],[])
        with self.assertRaises(AdmissionError): self.registry.acquire('anotherlead',ROLES[0],[])

    def test_exact_paths_and_database_metadata_protection(self):
        for path in ('../outside.py','/root.py','a/../b.py','a//b.py','.git/config','.Git/config',
                     'backend/aibs_master.db','x.sqlite-wal','file:*','*.py','NUL','COM1.txt','a\\b.py','a.'):
            with self.subTest(path=path), self.assertRaises(OwnershipViolation):
                self.registry.acquire('test',ROLES[1],[path])
        lease = self.registry.acquire('test',ROLES[1],['a.py'])
        with self.assertRaises(OwnershipViolation): self.registry.acquire('peer',ROLES[2],['a.py'])
        (self.root/'a.py').write_text('original')
        self.assertEqual(self.registry.finish(lease),('a.py',))

    def test_unauthorized_write_halts_admission_and_cancels_peers(self):
        lease = self.registry.acquire('a',ROLES[1],['allowed.py'])
        peer = self.registry.acquire('b',ROLES[2],['peer.py'])
        (self.root/'outside.py').write_text('bad')
        with self.assertRaises(OwnershipViolation): self.registry.finish(lease)
        self.assertFalse(lease.cancel_event.is_set())
        self.assertTrue(peer.cancel_event.is_set())
        with self.assertRaises(AdmissionError): self.registry.acquire('c',ROLES[3],[])
        with self.assertRaises(OwnershipViolation): self.registry.finish(peer)
        self.assertTrue(self.registry.is_drained())

    def test_disjoint_overlapping_tasks_finish_in_either_order(self):
        first = self.registry.acquire('a',ROLES[1],['a.py'])
        second = self.registry.acquire('b',ROLES[2],['b.py'])
        (self.root/'a.py').write_text('a'); (self.root/'b.py').write_text('b')
        self.assertEqual(self.registry.finish(first),('a.py',))
        self.assertEqual(self.registry.finish(second),('b.py',))

    def test_owned_parent_directory_creation(self):
        lease = self.registry.acquire('a',ROLES[1],['nested/a.py'])
        (self.root/'nested').mkdir(); (self.root/'nested/a.py').write_text('a')
        self.registry.finish(lease)

    def test_peer_finished_before_original_task_does_not_lose_claim(self):
        first = self.registry.acquire('a',ROLES[1],['a.py'])
        second = self.registry.acquire('b',ROLES[2],['b.py'])
        (self.root/'b.py').write_text('b')
        self.registry.finish(second)
        (self.root/'a.py').write_text('a')
        self.assertEqual(self.registry.finish(first),('a.py',))

    def test_unowned_empty_directory_rejected(self):
        lease = self.registry.acquire('a',ROLES[1],[])
        (self.root/'unowned').mkdir()
        with self.assertRaises(OwnershipViolation): self.registry.finish(lease)

    def test_hardlink_rejected(self):
        (self.root/'a.py').write_text('a'); os.link(self.root/'a.py',self.root/'b.py')
        with self.assertRaises(OwnershipViolation): self.registry.acquire('a',ROLES[1],['a.py'])

    def test_redirect_rejected(self):
        (self.root/'target').mkdir()
        try: (self.root/'link').symlink_to(self.root/'target',target_is_directory=True)
        except OSError: self.skipTest('Symlink creation unavailable')
        with self.assertRaises(OwnershipViolation): self.registry.acquire('a',ROLES[1],['link/a.py'])

    def test_redirect_created_after_admission_fails_audit(self):
        lease = self.registry.acquire('a',ROLES[1],['a.py'])
        (self.root/'target.py').write_text('a')
        os.link(self.root/'target.py',self.root/'a.py')
        with self.assertRaises(OwnershipViolation): self.registry.finish(lease)
        self.assertTrue(self.registry.is_drained())

    def test_cancellation_pause_shutdown_and_drain(self):
        lease = self.registry.acquire('a',ROLES[1],[])
        self.registry.pause()
        with self.assertRaises(AdmissionError): self.registry.acquire('b',ROLES[2],[])
        self.registry.resume(); self.registry.cancel('a')
        with self.assertRaises(AdmissionError): self.registry.check(lease)
        self.assertFalse(self.registry.drain(0))
        self.registry.finish(lease); self.registry.request_shutdown()
        self.assertTrue(self.registry.drain(.01))
        with self.assertRaises(AdmissionError): self.registry.resume()

    def test_gpu_requires_measurement_headroom_and_single_job(self):
        gib = 1024**3
        for required, free in ((16*gib,None),(21*gib,25*gib),(16*gib,19*gib),(True,24*gib)):
            with self.assertRaises(AdmissionError): self.registry.acquire('a',ROLES[1],[],gpu_required_bytes=required,free_vram_bytes=free)
        lease = self.registry.acquire('a',ROLES[1],[],gpu_required_bytes=16*gib,free_vram_bytes=24*gib)
        remote = self.registry.acquire('remote',ROLES[2],[])
        with self.assertRaises(AdmissionError): self.registry.acquire('b',ROLES[3],[],gpu_required_bytes=gib,free_vram_bytes=24*gib)
        self.registry.finish(lease); self.registry.finish(remote)

    def test_two_strikes_operation_scoped_and_success_reset(self):
        for i in range(2):
            lease=self.registry.acquire(str(i),ROLES[1],[],operation='build')
            self.registry.finish(lease,error_identity='exit42')
        with self.assertRaises(AdmissionError): self.registry.acquire('next',ROLES[1],[],operation='build')
        other=self.registry.acquire('other',ROLES[1],[],operation='other'); self.registry.finish(other)
        for i,error in enumerate(('first','different',None,'different')):
            lease=self.registry.acquire('reset'+str(i),ROLES[1],[],operation='reset')
            self.registry.finish(lease,error_identity=error)
        lease=self.registry.acquire('last',ROLES[1],[],operation='reset'); self.registry.finish(lease)

    def test_snapshot_budget_fails_closed(self):
        (self.root/'big.txt').write_text('0123456789')
        registry=SwarmRegistry(self.root,Policy(max_snapshot_bytes=5))
        with self.assertRaises(AdmissionError): registry.acquire('a',ROLES[1],[])
        self.assertTrue(registry.is_drained())

    def test_cancel_is_not_success_and_does_not_reset_failure_history(self):
        first=self.registry.acquire('first',ROLES[1],[],operation='build')
        self.registry.finish(first,error_identity='exit42')
        cancelled=self.registry.acquire('cancelled',ROLES[1],[],operation='build')
        self.registry.cancel(cancelled.task_id); self.registry.finish(cancelled)
        second=self.registry.acquire('second',ROLES[1],[],operation='build')
        self.registry.finish(second,error_identity='exit42')
        with self.assertRaises(AdmissionError): self.registry.acquire('third',ROLES[1],[],operation='build')

    def test_simultaneous_admission_never_exceeds_worker_limit(self):
        ready=threading.Barrier(10); release=threading.Event(); attempted=threading.Event(); admitted=[]; errors=[]
        attempts=[]
        lock=threading.Lock()
        def contender(index):
            ready.wait()
            try:
                lease=self.registry.acquire(str(index),ROLES[1],[])
            except AdmissionError:
                with lock:
                    attempts.append(index)
                    if len(attempts)==10: attempted.set()
                return
            with lock:
                admitted.append(lease); attempts.append(index)
                if len(attempts)==10: attempted.set()
            release.wait(2)
            try: self.registry.finish(lease)
            except Exception as error: errors.append(type(error).__name__)
        threads=[threading.Thread(target=contender,args=(i,))for i in range(10)]
        for thread in threads: thread.start()
        self.assertTrue(attempted.wait(2))
        self.assertEqual(self.registry.snapshot()['workers'],3)
        release.set()
        for thread in threads: thread.join(3); self.assertFalse(thread.is_alive())
        self.assertLessEqual(len(admitted),3)
        self.assertEqual(errors,[]); self.assertTrue(self.registry.is_drained())

    def test_caller_cancellation_event_used_and_pre_cancel_never_snapshots(self):
        from unittest.mock import patch
        event=threading.Event(); event.set()
        with patch.object(self.registry,'_snapshot',side_effect=AssertionError('Must not snapshot')):
            with self.assertRaises(AdmissionError):
                self.registry.acquire('cancelled',ROLES[1],[],cancel_event=event)
        self.assertTrue(self.registry.is_drained())
        event.clear()
        lease=self.registry.acquire('shared',ROLES[1],[],cancel_event=event)
        self.assertIs(lease.cancel_event,event)
        event.set()
        with self.assertRaises(AdmissionError): self.registry.check(lease)
        self.registry.finish(lease)

    def test_cancellation_during_snapshot_never_grants_slot(self):
        from unittest.mock import patch
        event=threading.Event()
        def snapshot(): event.set(); return {}
        with patch.object(self.registry,'_snapshot',side_effect=snapshot):
            with self.assertRaises(AdmissionError):
                self.registry.acquire('cancelled',ROLES[1],[],cancel_event=event)
        self.assertTrue(self.registry.is_drained())
        with self.assertRaises(AdmissionError):
            self.registry.acquire('invalid',ROLES[1],[],cancel_event=object())


if __name__ == '__main__': unittest.main()
