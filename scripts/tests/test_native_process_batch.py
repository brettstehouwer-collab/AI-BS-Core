"""Real independent Windows children; no application/provider/source actions."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from PyQt6.QtCore import QCoreApplication

from native_studio.process_batch import BatchLimits, JobSpec, ProcessBatchController


@unittest.skipUnless(os.name == 'nt', 'Windows JobObject containment required')
class ProcessBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aibs_batch_')
        self.controller = ProcessBatchController()

    def tearDown(self):
        self.controller.shutdown()
        self.wait(lambda: self.controller.is_drained, 10)
        self.controller.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def job(self, name, code='import time; time.sleep(.25)', timeout=5):
        return JobSpec(name, str(Path(sys.executable).resolve()), ('-I', '-B', '-c', code),
                       self.temp.name, timeout_seconds=timeout)

    def wait(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertTrue(predicate(), self.controller.snapshot())

    def rows(self):
        return {row['job_id']: row for row in self.controller.snapshot()['jobs']}

    def test_real_concurrent_children_and_live_worker_reduction(self):
        self.controller.configure(BatchLimits(workers=2, start_interval_ms=0))
        self.controller.submit([self.job('a', 'import time; time.sleep(.6)'),
                                self.job('b', 'import time; time.sleep(.6)'), self.job('c')])
        self.wait(lambda: all(self.rows()[x]['state'] == 'running' for x in ('a', 'b')))
        self.assertNotEqual(self.rows()['a']['pid'], self.rows()['b']['pid'])
        self.controller.configure(BatchLimits(workers=1, start_interval_ms=0))
        self.assertEqual(self.rows()['c']['state'], 'queued')
        self.wait(lambda: self.controller.is_drained)
        rows = self.rows()
        self.assertTrue(all(x['state'] == 'passed' and x['job_drained'] for x in rows.values()))
        self.assertGreaterEqual(rows['c']['admitted_at'], max(rows[x]['finished_at'] for x in ('a', 'b')))

    def test_two_same_exit_codes_halt_admission_until_explicit_reset_and_resume(self):
        self.controller.configure(BatchLimits(workers=1, start_interval_ms=0))
        self.controller.submit([self.job('bad-a', 'raise SystemExit(7)'),
                                self.job('bad-b', 'raise SystemExit(7)'), self.job('untouched')])
        self.wait(lambda: self.controller.snapshot()['failure_halted'] and self.controller.snapshot()['running'] == 0)
        self.assertEqual(self.rows()['untouched']['state'], 'queued')
        self.controller.resume()
        self.app.processEvents()
        self.assertEqual(self.rows()['untouched']['state'], 'queued')
        self.controller.reset_failure_halt()
        self.assertTrue(self.controller.snapshot()['paused'])
        self.controller.resume()
        self.wait(lambda: self.controller.is_drained)
        self.assertEqual(self.rows()['untouched']['state'], 'passed')

    def test_throttle_and_interbatch_cooldown(self):
        self.controller.configure(BatchLimits(workers=2, batch_size=2, start_interval_ms=140,
                                              batch_cooldown_ms=180))
        self.controller.submit([self.job(x) for x in ('a', 'b', 'c')])
        self.wait(lambda: self.controller.is_drained)
        a, b, c = (self.rows()[x] for x in ('a', 'b', 'c'))
        self.assertGreaterEqual(b['admitted_at'] - a['admitted_at'], .13)
        self.assertGreaterEqual(c['admitted_at'] - max(a['finished_at'], b['finished_at']), .17)

    def test_pause_preserves_queue_and_resume(self):
        self.controller.configure(BatchLimits(workers=1, start_interval_ms=0))
        self.controller.submit([self.job('a'), self.job('b')])
        self.wait(lambda: self.rows()['a']['state'] == 'running')
        self.controller.pause()
        self.wait(lambda: self.rows()['a']['state'] == 'passed')
        self.assertEqual(self.rows()['b']['state'], 'queued')
        self.assertFalse(self.controller.is_drained)
        self.controller.resume()
        self.wait(lambda: self.controller.is_drained)
        self.assertEqual(self.rows()['b']['state'], 'passed')

    def test_shutdown_restarts_timer_and_cancels_descendant(self):
        pidfile = str(Path(self.temp.name) / 'child.pid')
        code = ("import subprocess,sys,time,pathlib; "
                "p=subprocess.Popen([sys.executable,'-I','-c','import time;time.sleep(60)']); "
                f"pathlib.Path({pidfile!r}).write_text(str(p.pid)); time.sleep(60)")
        self.controller.submit([self.job('parent', code), self.job('queued')])
        self.wait(lambda: Path(pidfile).exists())
        import psutil
        child = psutil.Process(int(Path(pidfile).read_text()))
        self.controller._timer.stop()  # Existing MainWindow close ordering.
        started = time.monotonic()
        self.controller.shutdown()
        self.assertLess(time.monotonic() - started, .1)
        self.wait(lambda: self.controller.is_drained)
        self.assertFalse(child.is_running())
        self.assertEqual(self.rows()['parent']['state'], 'cancelled')
        self.assertEqual(self.rows()['queued']['state'], 'cancelled')

    def test_deadline_output_cap_and_nonzero_failure(self):
        self.controller.configure(BatchLimits(workers=2, start_interval_ms=0, output_limit_bytes=1024))
        self.controller.submit([self.job('timeout', 'import time; time.sleep(60)', .15),
                                self.job('output', "import sys; print('x'*10000); sys.exit(7)")])
        self.wait(lambda: self.controller.is_drained)
        self.assertEqual(self.rows()['timeout']['state'], 'timed_out')
        output = self.rows()['output']
        self.assertEqual(output['state'], 'failed')
        self.assertEqual(output['exit_code'], 7)
        self.assertTrue(output['output_truncated'])
        self.assertLessEqual(len(output['output'].encode()), 1024)

    def test_validation_duplicate_and_closed_admission(self):
        for kwargs in ({'workers': 0}, {'workers': True}, {'batch_size': 129},
                       {'start_interval_ms': -1}, {'max_jobs': 0}):
            with self.assertRaises(ValueError):
                BatchLimits(**kwargs)
        with self.assertRaises(ValueError):
            self.controller.submit([self.job('same'), self.job('same')])
        with self.assertRaises(ValueError):
            self.job('bad', timeout=float('inf'))
        self.controller.shutdown()
        with self.assertRaises(RuntimeError):
            self.controller.submit([self.job('closed')])


if __name__ == '__main__':
    unittest.main()
