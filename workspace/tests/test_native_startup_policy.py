"""Controlled source-method tests: never import the native application or Qt.

Actual class methods execute with fake widgets, timers, audio, bus and telemetry.
No application-module imports, worker execution, devices, GUI or network occur.
"""
import ast
import copy
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
UPDATE_WORKER = object()


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeWidget:
    def __init__(self, *args, **kwargs):
        pass

    def setWindowTitle(self, value):
        pass

    def resize(self, *args):
        pass

    def setMinimumSize(self, *args):
        pass


class FakeButton:
    def setStyleSheet(self, value):
        pass


class FakeTimer:
    pending = []

    def __init__(self, owner=None):
        self.timeout = Signal()
        self.started = False

    def setInterval(self, interval):
        self.interval = interval

    def start(self):
        self.started = True

    @classmethod
    def singleShot(cls, delay, callback):
        cls.pending.append((delay, callback))

    @classmethod
    def advance_all(cls):
        pending, cls.pending = cls.pending, []
        for _, callback in pending:
            callback()


class FakeBus:
    def __init__(self, *args, **kwargs):
        self.submissions = []

    def submit(self, worker, *args, **kwargs):
        # Retain the work identity; deliberately never invoke any worker.
        self.submissions.append((worker, args, kwargs))


class FakeAudio:
    def __init__(self):
        self._stream = None
        self.starts = 0
        self.play_calls = []

    def start(self):
        self.starts += 1
        self._stream = object()

    def play(self, value):
        self.play_calls.append(value)


class FakeHub:
    def __init__(self, probe):
        self.frame = Signal()

    def attach_audio(self, engine):
        self.engine = engine

    def start(self):
        pass


class FakeUpdateDialog:
    opened = []

    def __init__(self, bus, parent):
        self.bus = bus
        self.parent = parent

    def exec(self):
        self.opened.append((self.bus, self.parent))


def load_class(source_path, class_name, namespace):
    """Compile a trusted class definition only; module imports never execute."""
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
    node = next(item for item in tree.body if isinstance(item, ast.ClassDef) and item.name == class_name)
    unit = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), copy.deepcopy(node)], type_ignores=[])
    ast.fix_missing_locations(unit)
    exec(compile(unit, str(source_path), "exec"), namespace)
    return namespace[class_name]


def load_controlled_classes():
    policy = types.ModuleType("controlled_runtime_policy")
    policy_path = ROOT / "native_studio/runtime_policy.py"
    exec(compile(policy_path.read_text(encoding="utf-8-sig"), str(policy_path), "exec"), policy.__dict__)
    namespace = {
        "QWidget": FakeWidget, "QMainWindow": FakeWidget, "QTimer": FakeTimer,
        "EngineBus": FakeBus, "AudioEngine": FakeAudio, "GpuProbe": object,
        "TelemetryHub": FakeHub, "UpdateDialog": FakeUpdateDialog,
        "check_for_updates_worker": UPDATE_WORKER, "__version__": "controlled-fixture",
        **{name: value for name, value in vars(policy).items() if name.startswith("allow_")},
    }
    daw = load_class(ROOT / "native_studio/music_daw_view.py", "MusicDawView", namespace)
    daw._build_ui = lambda self: setattr(self, "btn_play", FakeButton())
    namespace["MusicDawView"] = daw
    window = load_class(ROOT / "native_studio/app.py", "MainWindow", namespace)
    window._build_ui = lambda self: setattr(self, "btn_update", FakeButton())
    return policy, daw, window


class NativeStartupPolicyTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "AI_BS_NATIVE_MANAGE_DAEMONS": "false",
            "AI_BS_NATIVE_EXIT_PROCESS_CLEANUP": "false",
        })
        self.environment.start()
        os.environ.pop("AI_BS_NATIVE_BACKGROUND_UPDATES", None)
        FakeTimer.pending = []
        FakeUpdateDialog.opened = []
        self.policy, self.Daw, self.Window = load_controlled_classes()

    def tearDown(self):
        self.environment.stop()

    def test_default_launch_schedules_no_background_update(self):
        self.Window()
        self.assertEqual(FakeTimer.pending, [])

    def test_advancing_default_startup_timers_submits_no_update_worker(self):
        window = self.Window()
        FakeTimer.advance_all()
        self.assertFalse(any(worker is UPDATE_WORKER for worker, _, _ in window.bus.submissions))

    def test_explicit_background_optin_can_schedule_one_update(self):
        os.environ["AI_BS_NATIVE_BACKGROUND_UPDATES"] = "true"
        window = self.Window()
        self.assertEqual(len(FakeTimer.pending), 1)
        self.assertEqual(FakeTimer.pending[0][0], 10000)
        FakeTimer.advance_all()
        calls = [entry for entry in window.bus.submissions if entry[0] is UPDATE_WORKER]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2]["on_result"], window._on_bg_update_check_result)

    def test_background_permission_revoked_before_timer_prevents_work(self):
        os.environ["AI_BS_NATIVE_BACKGROUND_UPDATES"] = "true"
        window = self.Window()
        os.environ["AI_BS_NATIVE_BACKGROUND_UPDATES"] = "false"
        FakeTimer.advance_all()
        self.assertFalse(any(worker is UPDATE_WORKER for worker, _, _ in window.bus.submissions))

    def test_background_policy_requires_explicit_true(self):
        # The old application behaves as implicit opt-in; this fallback retains
        # that baseline so RED is a behavioral failure rather than ImportError.
        allowed = getattr(self.policy, "allow_background_update_checks", lambda: True)
        for value in ("", "false", "1", "yes", "on"):
            with self.subTest(value=value):
                os.environ["AI_BS_NATIVE_BACKGROUND_UPDATES"] = value
                self.assertFalse(allowed())
        os.environ["AI_BS_NATIVE_BACKGROUND_UPDATES"] = " TrUe "
        self.assertTrue(allowed())

    def test_explicit_update_dialog_remains_available_with_policy_disabled(self):
        window = self.Window()
        window._open_update_dialog()
        self.assertEqual(FakeUpdateDialog.opened, [(window.bus, window)])

    def test_constructing_daw_with_default_engine_does_not_open_audio(self):
        view = self.Daw(FakeBus())
        self.assertEqual(view.engine.starts, 0)
        self.assertIsNone(view.engine._stream)

    def test_constructing_daw_with_injected_engine_does_not_open_audio(self):
        engine = FakeAudio()
        view = self.Daw(FakeBus(), engine)
        self.assertIs(view.engine, engine)
        self.assertEqual(engine.starts, 0)

    def test_stop_never_opens_audio(self):
        view = self.Daw(FakeBus())
        view._toggle_play(False)
        self.assertEqual(view.engine.starts, 0)
        self.assertEqual(view.engine.play_calls, [False])

    def test_explicit_play_starts_once_then_reuses_stream(self):
        view = self.Daw(FakeBus())
        self.assertEqual(view.engine.starts, 0)
        view._toggle_play(True)
        view._toggle_play(True)
        view._toggle_play(False)
        self.assertEqual(view.engine.starts, 1)
        self.assertEqual(view.engine.play_calls, [True, True, False])

    def test_explicit_play_reuses_preopened_injected_stream(self):
        engine = FakeAudio()
        engine._stream = object()
        view = self.Daw(FakeBus(), engine)
        view._toggle_play(True)
        self.assertEqual(engine.starts, 0)
        self.assertEqual(engine.play_calls, [True])

    def test_other_native_lifecycle_permissions_remain_disabled(self):
        self.assertFalse(self.policy.allow_background_daemon_management())
        self.assertFalse(self.policy.allow_exit_process_cleanup())


if __name__ == "__main__":
    unittest.main(verbosity=2)
