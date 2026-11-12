"""Real Qt pool barriers, queued delivery and cancellation; no services."""
import gc
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch
import weakref

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PyQt6.QtCore import QCoreApplication
from native_studio.engine import EngineBus, Task


class EngineBusShutdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.bus = EngineBus(max_threads=1)
        self.releases = []

    def tearDown(self):
        for event in self.releases:
            event.set()
        self.assertTrue(self.bus.pool.waitForDone(3000), 'Test-owned pool did not join')
        self.bus.shutdown(0)
        for _ in range(5):
            self.app.processEvents()

    def pump_until(self, condition, seconds=2):
        end = time.monotonic() + seconds
        while not condition() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition(), 'Expected GUI-side state was not reached')

    def held(self):
        started, release = threading.Event(), threading.Event()
        self.releases.append(release)
        def work():
            started.set()
            if not release.wait(8):
                raise AssertionError('Test-owned held worker was not released')
            return 'synthetic-result'
        task = self.bus.submit(work)
        self.assertTrue(started.wait(2))
        return task, release

    def test_nonblocking_stop_reports_false_then_emits_drain_once_after_real_join(self):
        task, release = self.held()
        drains = []
        if hasattr(self.bus, 'drained'):
            self.bus.drained.connect(lambda: drains.append(threading.get_ident()))
        before = time.monotonic()
        self.assertIs(self.bus.shutdown(0), False)
        self.assertLess(time.monotonic() - before, .2)
        self.assertTrue(task.cancel_event.is_set())
        self.assertEqual(drains, [])
        with self.assertRaises(RuntimeError):
            self.bus.submit(lambda: 'rejected')
        with self.assertRaises(RuntimeError):
            self.bus.dispatch(lambda: 'rejected')
        release.set()
        self.pump_until(lambda: len(drains) == 1)
        self.assertEqual(drains, [threading.get_ident()])
        self.assertIs(self.bus.shutdown(0), True)
        self.assertIs(self.bus.shutdown(0), True)
        self.assertEqual(len(drains), 1)
        self.assertEqual(self.bus.active_count, 0)

    def test_legacy_default_keeps_3000ms_bound_and_explicitly_reports_incomplete(self):
        _, release = self.held()
        before = time.monotonic()
        self.assertIs(self.bus.shutdown(), False)
        elapsed = time.monotonic() - before
        self.assertGreaterEqual(elapsed, 2.8)
        self.assertLess(elapsed, 4.5)
        self.assertGreater(self.bus.pool.activeThreadCount(), 0)
        release.set()
        self.pump_until(lambda: self.bus.shutdown(0) is True)

    def test_cleared_queued_task_never_runs_and_cannot_keep_active_count_forever(self):
        _, release = self.held()
        ran = []
        queued = self.bus.submit(lambda: ran.append('unexpected'))
        retained = weakref.ref(queued)
        self.assertIs(self.bus.shutdown(0), False)
        del queued
        gc.collect()
        self.assertIsNotNone(retained())
        release.set()
        self.pump_until(lambda: self.bus.shutdown(0) is True)
        self.assertEqual(ran, [])
        self.assertEqual(self.bus.active_count, 0)

    def test_finished_signal_is_not_a_native_runnable_return_barrier(self):
        tail, release = threading.Event(), threading.Event()
        self.releases.append(release)
        original = Task.run
        def delayed_return(task):
            original(task)
            tail.set()
            release.wait(5)
        with patch.object(Task, 'run', delayed_return):
            task = self.bus.submit(lambda: 'synthetic')
            self.assertTrue(tail.wait(2))
            self.pump_until(lambda: self.bus.active_count == 0)
            self.assertGreater(self.bus.pool.activeThreadCount(), 0)
            drains = []
            if hasattr(self.bus, 'drained'):
                self.bus.drained.connect(lambda: drains.append(True))
            self.assertIs(self.bus.shutdown(0), False)
            self.assertEqual(drains, [])
            release.set()
            self.pump_until(lambda: self.bus.shutdown(0) is True)
            self.assertEqual(drains, [True])
            self.assertTrue(task.cancel_event.is_set())

    def test_already_queued_result_is_fenced_before_widget_callback(self):
        delivered = []
        self.bus.submit(lambda: 'queued-before-stop', on_result=delivered.append)
        self.assertTrue(self.bus.pool.waitForDone(2000))
        self.bus.shutdown(0)
        self.app.processEvents()
        self.assertEqual(delivered, [])

    def test_error_queued_before_cancellation_is_fenced(self):
        delivered = []
        def failure():
            raise ValueError('synthetic-error')
        self.bus.submit(failure, on_error=delivered.append)
        self.assertTrue(self.bus.pool.waitForDone(2000))
        self.bus.shutdown(0)
        self.app.processEvents()
        self.assertEqual(delivered, [])

    def test_error_emitted_after_cancellation_is_fenced(self):
        started, release = threading.Event(), threading.Event()
        self.releases.append(release)
        delivered = []
        def failure():
            started.set()
            release.wait(5)
            raise ValueError('synthetic-error-after-stop')
        self.bus.submit(failure, on_error=delivered.append)
        self.assertTrue(started.wait(2))
        self.assertIs(self.bus.shutdown(0), False)
        release.set()
        self.pump_until(lambda: self.bus.is_drained)
        self.app.processEvents()
        self.assertEqual(delivered, [])

    def test_running_result_and_error_callbacks_execute_on_GUI_thread(self):
        delivered = []
        gui = threading.get_ident()
        self.bus.submit(lambda: 'result', on_result=lambda x: delivered.append((x, threading.get_ident())))
        self.pump_until(lambda: len(delivered) == 1)
        def failure():
            raise ValueError('synthetic-error')
        self.bus.submit(failure, on_error=lambda x: delivered.append((x, threading.get_ident())))
        self.pump_until(lambda: len(delivered) == 2)
        self.assertEqual(delivered[0], ('result', gui))
        self.assertEqual(delivered[1], ('ValueError: synthetic-error', gui))


if __name__ == '__main__':
    unittest.main(verbosity=2)
