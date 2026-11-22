"""Native shared admission controls with real Qt worker threads, no services."""
from pathlib import Path
import os
import sys
import threading
import time
import unittest
from unittest.mock import patch

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PyQt6.QtCore import QCoreApplication
from native_studio.engine import EngineBus, Task


class NativeBusAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.bus = EngineBus(max_threads=2)
        self.releases = []

    def tearDown(self):
        for event in self.releases:
            event.set()
        self.bus.shutdown(0)
        self.until(lambda: self.bus.is_drained)
        self.app.processEvents()

    def until(self, condition, seconds=3):
        end = time.monotonic() + seconds
        while not condition() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition(), self.bus.admission_snapshot())

    def held(self):
        started, release = threading.Event(), threading.Event()
        self.releases.append(release)
        def work():
            started.set()
            release.wait(4)
        self.bus.submit(work)
        self.until(started.is_set)
        return release

    def test_default_preserves_qthreadpool_queue_without_gui_pumping(self):
        values = []
        for value in range(5):
            self.bus.submit(lambda value=value: values.append(value))
        self.assertTrue(self.bus.pool.waitForDone(2000))
        self.assertEqual(sorted(values), list(range(5)))
        self.until(lambda: self.bus.active_count == 0)

    def test_worker_limit_and_live_reduction_keep_running_callables(self):
        self.bus.configure_admission(2)
        lock = threading.Lock()
        current = [0]
        maximum = [0]
        done = []
        def work():
            with lock:
                current[0] += 1
                maximum[0] = max(maximum[0], current[0])
            time.sleep(.06)
            with lock:
                current[0] -= 1
                done.append(True)
        for _ in range(4):
            self.bus.submit(work)
        self.bus.configure_admission(1)
        self.until(lambda: len(done) == 4)
        self.assertLessEqual(maximum[0], 2)
        self.assertEqual(len(done), 4)
        self.assertEqual(self.bus.pool.maxThreadCount(), 1)

    def test_pause_withdraws_already_queued_pool_jobs_then_resume(self):
        self.bus.pool.setMaxThreadCount(1)
        release = self.held()
        ran = []
        self.bus.submit(lambda: ran.append('queued'))
        self.bus.pause_admission()
        self.assertEqual(self.bus.admission_snapshot()['queued'], 1)
        release.set()
        self.until(lambda: self.bus.admission_snapshot()['in_flight'] == 0)
        self.assertEqual(ran, [])
        self.bus.resume_admission()
        self.until(lambda: ran == ['queued'])

    def test_start_gap_and_batch_cooldown_are_applied_to_dispatch(self):
        self.bus.configure_admission(2, start_interval_ms=55, batch_size=2, batch_cooldown_ms=90)
        starts = []
        def work():
            starts.append(time.monotonic())
            time.sleep(.015)
        for _ in range(4):
            self.bus.dispatch(work)
        self.until(lambda: len(starts) == 4)
        self.assertGreaterEqual(starts[1] - starts[0], .045)
        self.assertGreaterEqual(starts[2] - starts[1], .085)
        self.assertGreaterEqual(starts[3] - starts[2], .045)

    def test_cancel_pending_cannot_kill_running_work(self):
        self.bus.configure_admission(1)
        release = self.held()
        ran = []
        pending = self.bus.submit(lambda: ran.append('unexpected'))
        self.assertEqual(self.bus.cancel_pending(), 1)
        self.assertTrue(pending.cancel_event.is_set())
        self.assertFalse(self.bus.pool.waitForDone(0))
        release.set()
        self.until(lambda: self.bus.active_count == 0)
        self.assertEqual(ran, [])

    def test_shutdown_after_paused_timer_stop_drains_and_discards_pending(self):
        self.bus.configure_admission(1)
        release = self.held()
        ran = []
        self.bus.pause_admission()
        pending = self.bus.submit(lambda: ran.append('unexpected'))
        self.bus._admission_timer.stop()
        self.bus._drain_timer.stop()
        before = time.monotonic()
        self.assertFalse(self.bus.shutdown(0))
        self.assertLess(time.monotonic() - before, .1)
        self.assertTrue(pending.cancel_event.is_set())
        release.set()
        self.until(lambda: self.bus.is_drained)
        self.assertEqual(ran, [])
        self.assertTrue(self.bus.pool.waitForDone(0))

    def test_invalid_limits_leave_existing_configuration_unchanged(self):
        self.bus.configure_admission(2, 20, 4, 30)
        initial = self.bus.admission_snapshot()
        for values in ((0, 0, 1, 0), (True, 0, 1, 0), (2, -1, 1, 0),
                       (2, 0, 0, 0), (2, 0, 1, -1)):
            with self.assertRaises(ValueError):
                self.bus.configure_admission(*values)
        self.assertEqual(initial, self.bus.admission_snapshot())

    def test_batch_boundary_waits_for_native_return_not_finished_notification(self):
        self.bus.configure_admission(2, batch_size=1, batch_cooldown_ms=20)
        tail, release = threading.Event(), threading.Event()
        self.releases.append(release)
        original = Task.run
        first = [True]
        def delayed_return(task):
            original(task)
            if first[0]:
                first[0] = False
                tail.set()
                release.wait(3)
        ran = []
        with patch.object(Task, 'run', delayed_return):
            self.bus.submit(lambda: None)
            self.bus.submit(lambda: ran.append(True))
            self.until(tail.is_set)
            end = time.monotonic() + .08
            while time.monotonic() < end:
                self.app.processEvents()
                time.sleep(.002)
            self.assertEqual(ran, [])
            self.assertEqual(self.bus.admission_snapshot()['queued'], 1)
            release.set()
            self.until(lambda: ran == [True])

    def test_caller_cancelled_pending_task_is_retired_without_execution(self):
        self.bus.pause_admission()
        ran = []
        task = self.bus.submit(lambda: ran.append(True))
        task.cancel_event.set()
        self.bus.resume_admission()
        self.until(lambda: not self.bus._owned)
        self.assertEqual(ran, [])
        self.assertEqual(self.bus.active_count, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
