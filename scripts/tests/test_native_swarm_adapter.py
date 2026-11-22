"""Real Qt integration with synthetic workspace and existing EngineBus."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'backend')]
from PyQt6.QtCore import QCoreApplication, QThread
from native_studio.engine import EngineBus
from native_studio.swarm_adapter import SwarmBusAdapter
from core.swarm_orchestration import SwarmRegistry


class NativeSwarmAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'tests').mkdir()
        self.bus = EngineBus(max_threads=2)
        self.registry = SwarmRegistry(self.root)
        self.adapter = SwarmBusAdapter(self.bus, self.registry)
        self.releases = []

    def until(self, condition):
        end = time.monotonic() + 5
        while not condition() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.002)
        self.assertTrue(condition())

    def tearDown(self):
        for event in self.releases:
            event.set()
        self.adapter.begin_shutdown()
        self.bus.shutdown(0)
        self.until(lambda: self.bus.is_drained and self.adapter.is_drained)
        self.tmp.cleanup()

    def test_gui_result_and_actual_drain(self):
        values = []
        def work(*, cancel_event):
            self.assertNotEqual(QThread.currentThread(), self.app.thread())
            return 42
        def result(value):
            self.assertEqual(QThread.currentThread(), self.app.thread())
            values.append(value)
        self.adapter.submit('t1', 'test_runner', ['tests/example.py'], work, on_result=result)
        self.until(lambda: values == [42] and self.adapter.is_drained)

    def test_running_cancel_suppresses_late_result(self):
        started, release = threading.Event(), threading.Event()
        self.releases.append(release)
        values = []
        def work(*, cancel_event):
            started.set()
            release.wait(4)
            return 42
        self.adapter.submit('t1', 'test_runner', ['tests/example.py'], work, on_result=values.append)
        self.until(started.is_set)
        self.adapter.cancel('t1')
        release.set()
        self.until(lambda: self.adapter.is_drained)
        self.assertEqual(values, [])

    def test_bus_cleared_queue_releases_lease_after_barrier(self):
        self.bus.configure_admission(1)
        self.bus.pause_admission()
        called = []
        self.adapter.submit('queued', 'test_runner', ['tests/example.py'],
                            lambda **kw: called.append(True))
        self.adapter.begin_shutdown()
        self.bus.cancel_pending()
        self.until(lambda: self.adapter.is_drained)
        self.assertEqual(called, [])
        self.assertTrue(self.registry.is_drained())

    def test_foreign_thread_submission_rejected(self):
        errors = []
        def attempt():
            try:
                self.adapter.submit('bad', 'test_runner', ['tests/example.py'], lambda **kw: None)
            except RuntimeError:
                errors.append(True)
        thread = threading.Thread(target=attempt)
        thread.start()
        thread.join()
        self.assertEqual(errors, [True])

    def test_cancelled_queue_never_acquires_or_audits_unadmitted_work(self):
        self.bus.pause_admission()
        errors = []
        self.adapter.error.connect(errors.append)
        self.adapter.submit('queued', 'test_runner', ['tests/example.py'], lambda **kw: None)
        (self.root / 'unowned.txt').write_text('unexpected')
        self.bus.cancel_pending()
        self.until(lambda: self.adapter.is_drained)
        self.assertEqual(errors, [])
        self.assertTrue(self.registry.is_drained())

    def test_identity_retained_until_native_barrier(self):
        self.bus.pause_admission()
        self.adapter.submit('queued', 'test_runner', ['tests/example.py'], lambda **kw: None)
        with self.assertRaises(ValueError):
            self.adapter.submit('queued', 'test_runner', ['tests/example.py'], lambda **kw: None)

    def test_admission_hashing_runs_off_gui_and_bad_writes_block_result(self):
        acquire = self.registry.acquire
        seen, values, errors = [], [], []
        def admitted(*args, **kwargs):
            seen.append(QThread.currentThread() != self.app.thread())
            return acquire(*args, **kwargs)
        self.registry.acquire = admitted
        def work(**kwargs):
            (self.root / 'unowned.txt').write_text('unexpected')
            return 42
        self.adapter.submit('bad', 'test_runner', ['tests/example.py'], work,
                            on_result=values.append, on_error=errors.append)
        self.until(lambda: self.adapter.is_drained and bool(errors))
        self.assertEqual(seen, [True])
        self.assertEqual(values, [])

    def test_lazy_work_result_is_rejected(self):
        errors = []
        self.adapter.submit('lazy', 'test_runner', ['tests/example.py'],
            lambda **kwargs: iter([1]), on_error=errors.append)
        self.until(lambda: self.adapter.is_drained and bool(errors))
        self.assertIn('TypeError', errors[0])


if __name__ == '__main__':
    unittest.main()
