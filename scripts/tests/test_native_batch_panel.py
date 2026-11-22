"""Native controls and actual registered read-only source children, no services."""
import importlib.util
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication, QWidget
from native_studio.engine import EngineBus
from native_studio.process_batch import ProcessBatchController
from native_studio.process_batch_view import ProcessBatchPanel, source_jobs, open_batch_controls

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('native_source_check', ROOT / 'runtime/devtools/native_source_check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class SourceCheckTests(unittest.TestCase):
    def test_source_is_parsed_without_execution_or_rewrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'must-not-exist.txt'
            source = root / 'fixture.py'
            raw = ('from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\n').encode()
            source.write_bytes(raw)
            row = checker.inspect_source(root, source)
            self.assertEqual(row['syntax'], 'PASS')
            self.assertFalse(marker.exists())
            self.assertEqual(source.read_bytes(), raw)

    def test_outside_source_and_oversize_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            target = Path(outside) / 'outside.py'
            target.write_text('pass\n')
            with self.assertRaises(ValueError):
                checker.inspect_source(root, target)
            oversized = root / 'large.py'
            oversized.write_bytes(b'#' * (1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                checker.inspect_source(root, oversized)

    def test_registry_rejects_outside_files_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'outside.py'
            path.write_text('pass\n')
            with self.assertRaises(ValueError):
                source_jobs([path])
        target = ROOT / 'runtime/devtools/native_source_check.py'
        self.assertEqual(len(source_jobs([target, target])), 1)


class BatchPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.bus = EngineBus(max_threads=2)
        self.controller = ProcessBatchController()
        self.panel = ProcessBatchPanel(self.controller, bus=self.bus)

    def pump(self, predicate, seconds=10):
        end = time.monotonic() + seconds
        while not predicate() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.005)
        self.app.processEvents()
        self.assertTrue(predicate())

    def tearDown(self):
        self.controller.shutdown()
        self.pump(lambda: self.controller.is_drained)
        self.bus.shutdown(0)
        self.pump(lambda: self.bus.is_drained)
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_controls_run_real_registered_children_without_source_change(self):
        paths = [ROOT / 'runtime/devtools/native_source_check.py', ROOT / 'native_studio/process_batch_view.py']
        before = {path: path.read_bytes() for path in paths}
        self.panel.workers.setValue(2)
        self.panel.interval.setValue(0)
        self.panel.selected_paths = paths
        self.panel.start_sources()
        self.pump(lambda: self.controller.is_drained)
        jobs = self.controller.snapshot()['jobs']
        self.assertEqual(len(jobs), 2)
        self.assertTrue(all(row['state'] == 'passed' for row in jobs), jobs)
        self.assertEqual(len({row['pid'] for row in jobs}), 2)
        self.assertIn('2 passed', self.panel.status.text())
        for path in paths:
            self.assertEqual(before[path], path.read_bytes())

    def test_native_task_controls_are_connected_to_actual_bus(self):
        self.panel.native_workers.setValue(1)
        self.panel.native_interval.setValue(50)
        self.panel.apply_native_limits()
        self.bus.pause_admission()
        results = []
        self.bus.submit(lambda: 'fixture', on_result=results.append)
        self.app.processEvents()
        self.assertFalse(results)
        self.assertIn('paused', self.panel.native_status.text())
        self.bus.resume_admission()
        self.pump(lambda: results == ['fixture'])

    def test_shared_window_reuses_controller_and_does_not_start_jobs(self):
        owner = QWidget()
        first = open_batch_controls(self.bus, owner)
        second = open_batch_controls(self.bus, owner)
        self.assertIs(first, second)
        self.assertTrue(self.bus._process_batch_controller.is_drained)
        self.assertFalse(self.bus._process_batch_controller.snapshot()['jobs'])
        first.close()
        self.bus._process_batch_controller.shutdown()
        owner.close()


if __name__ == '__main__':
    unittest.main()
