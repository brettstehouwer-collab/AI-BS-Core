"""Exercise actual sampler lifecycle with inert Qt/hardware/IPC dependencies."""
import ast
from pathlib import Path
from types import SimpleNamespace
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]


class FakeSignal:
    def __init__(self):
        self.frames = []

    def emit(self, frame):
        self.frames.append(frame)


class FakeThread:
    def __init__(self, parent=None):
        self.wait_result = True
        self.wait_calls = []

    def wait(self, timeout):
        self.wait_calls.append(timeout)
        return self.wait_result


class FakeWriter:
    def __init__(self):
        self.close_calls = 0
        self.close_threads = []
        self.writes = []
        self.on_write = None
        self.write_error = None
        self.close_error = None

    def write(self, values):
        self.writes.append(values)
        if self.write_error:
            raise self.write_error
        if self.on_write:
            self.on_write()

    def close(self):
        self.close_calls += 1
        self.close_threads.append(threading.get_ident())
        if self.close_error:
            raise self.close_error


def actual_class():
    tree = ast.parse((ROOT / 'native_studio/telemetry_hub.py').read_text(encoding='utf-8'))
    declaration = next(node for node in tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'TelemetryHub')
    # Extract the real immutable ABI data without importing or creating any
    # shared-memory writer; the class-only fixture must supply its globals.
    shm_tree = ast.parse((ROOT / 'native_studio/telemetry_shm.py').read_text(encoding='utf-8'))
    port_order = ast.literal_eval(next(node.value for node in shm_tree.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        and node.target.id == 'PORT_ORDER'))
    writer = FakeWriter()
    scope = {
        'QThread': FakeThread,
        'pyqtSignal': lambda *_: FakeSignal(),
        'threading': threading,
        'time': time,
        'TelemetryWriter': lambda: writer,
        'PORT_ORDER': port_order,
        'PORT_MATRIX': {},
        'MIN_FREE_VRAM_GB': 3.5,
        'sample_system': lambda: {'cpu_pct': 1, 'ram_pct': 2, 'ram_used_gb': 3, 'ram_total_gb': 4},
        'probe_ports': lambda: {},
        'ollama_inventory': lambda *_: (_ for _ in ()).throw(AssertionError('No Ollama call expected')),
    }
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
                         names=[ast.alias(name='annotations')], level=0), declaration], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, '<actual-telemetry-lifecycle>', 'exec'), scope)
    hub = scope['TelemetryHub'](SimpleNamespace(sample=lambda: {'detected': False}))
    writer.on_write = hub._stop.set
    return hub, writer, scope


class TelemetryShutdownTests(unittest.TestCase):
    def test_nonblocking_stop_preserves_mapping_until_sampler_releases_it(self):
        hub, writer, _ = actual_class()
        hub.writer = writer
        hub.wait_result = False
        self.assertIs(hub.shutdown(0), False)
        self.assertEqual(hub.wait_calls, [0])
        self.assertTrue(hub._stop.is_set())
        self.assertIs(hub.writer, writer)
        self.assertEqual(writer.close_calls, 0)

    def test_bounded_shutdown_retains_writer_when_thread_has_not_drained(self):
        hub, writer, _ = actual_class()
        hub.writer = writer
        hub.wait_result = False
        self.assertIs(hub.shutdown(), False)
        self.assertEqual(hub.wait_calls, [2000])
        self.assertTrue(hub._stop.is_set())
        self.assertIs(hub.writer, writer)
        self.assertEqual(writer.close_calls, 0)

    def test_successful_sampler_closes_mapping_once_and_shutdown_is_idempotent(self):
        hub, writer, _ = actual_class()
        hub.run()
        self.assertEqual(len(writer.writes), 1)
        self.assertEqual(writer.close_calls, 1)
        self.assertIsNone(hub.writer)
        self.assertIs(hub.shutdown(), True)
        self.assertIs(hub.shutdown(), True)
        self.assertEqual(writer.close_calls, 1)

    def test_stop_before_start_does_not_create_shared_mapping(self):
        hub, writer, scope = actual_class()
        created = []
        scope['TelemetryWriter'] = lambda: created.append(True) or writer
        hub._stop.set()
        hub.run()
        self.assertEqual(created, [])
        self.assertIsNone(hub.writer)

    def test_sampler_write_failure_reports_unavailable_and_releases_mapping(self):
        hub, writer, _ = actual_class()
        writer.write_error = RuntimeError('private diagnostic detail must not escape')
        hub.run()
        self.assertEqual(writer.close_calls, 1)
        self.assertIsNone(hub.writer)
        self.assertIs(hub.latest['telemetry_available'], False)
        self.assertEqual(hub.latest['error_type'], 'RuntimeError')
        self.assertNotIn('private diagnostic', str(hub.latest))
        self.assertEqual(hub.frame.frames[-1], hub.latest)

    def test_mapping_creation_failure_reports_unavailable_without_native_exception(self):
        hub, writer, scope = actual_class()
        def unavailable():
            raise OSError('private mapping detail')
        scope['TelemetryWriter'] = unavailable
        hub.run()
        self.assertIsNone(hub.writer)
        self.assertEqual(writer.close_calls, 0)
        self.assertIs(hub.latest['telemetry_available'], False)
        self.assertEqual(hub.latest['error_type'], 'OSError')

    def test_mapping_close_failure_is_contained_and_reference_cleared(self):
        hub, writer, _ = actual_class()
        writer.close_error = OSError('inert close failure')
        hub.run()
        self.assertEqual(writer.close_calls, 1)
        self.assertIsNone(hub.writer)

    def test_blocked_sampler_keeps_mapping_until_worker_releases_it(self):
        hub, writer, _ = actual_class()
        entered = threading.Event()
        release = threading.Event()
        def sample():
            entered.set()
            if not release.wait(2):
                raise AssertionError('Inert fixture was not released')
            return {'detected': False}
        hub.gpu.sample = sample
        hub.wait_result = False
        thread = threading.Thread(target=hub.run)
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertIs(hub.shutdown(), False)
            self.assertEqual(writer.close_calls, 0)
            self.assertIs(hub.writer, writer)
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(writer.close_calls, 1)
        self.assertEqual(writer.close_threads, [thread.ident])
        self.assertIsNone(hub.writer)

    def test_signal_failure_still_releases_mapping_without_uncaught_qt_callback(self):
        hub, writer, _ = actual_class()
        def unavailable_signal(_):
            raise RuntimeError('Inert deleted Qt target')
        hub.frame.emit = unavailable_signal
        hub.run()
        self.assertEqual(writer.close_calls, 1)
        self.assertIsNone(hub.writer)


if __name__ == '__main__':
    unittest.main()
