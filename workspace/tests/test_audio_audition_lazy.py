"""Actual audition method with a fake engine; no audio module imports/devices."""
import ast
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
NOTE = object()


def load_audition():
    path = ROOT / "native_studio/audio_kernel.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    engine = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AudioEngine")
    audition = next(node for node in engine.body if isinstance(node, ast.FunctionDef) and node.name == "audition")
    unit = ast.Module(body=[audition], type_ignores=[])
    ast.fix_missing_locations(unit)
    namespace = {"EV_NOTE": NOTE}
    exec(compile(unit, str(path), "exec"), namespace)
    return namespace["audition"]


class FakeEngine:
    def __init__(self, outcome="success", opened=False):
        self._stream = object() if opened else None
        self._stats = types.SimpleNamespace(mode="stopped", error="", callbacks=7, underflows=2, events_dropped=0)
        self.outcome = outcome
        self.calls = []
        self.events = []

    def start(self):
        self.calls.append(("start",))
        if self.outcome == "raise":
            raise RuntimeError("Synthetic device failure")
        if self.outcome == "unavailable":
            self._stats.mode = "failed"
            self._stats.error = "Synthetic device unavailable"
            return self._stats
        self._stream = object()
        self._stats.mode = "shared"
        if self.outcome == "fallback":
            self._stats.error = "Synthetic fallback warning"
        return self._stats

    def send(self, *event):
        self.calls.append(("send", *event))
        self.events.append(event)
        return True


class AuditionLazyStartTests(unittest.TestCase):
    def setUp(self):
        self.audition = load_audition()

    def test_first_audition_opens_stream_before_queueing_note(self):
        engine = FakeEngine()
        self.audition(engine, 7, 64, 0.5)
        self.assertEqual(engine.calls, [("start",), ("send", NOTE, 7, 64, 0.5)])

    def test_repeated_auditions_do_not_restart_stream(self):
        engine = FakeEngine()
        self.audition(engine, 0)
        self.audition(engine, 1)
        self.assertEqual([call for call in engine.calls if call[0] == "start"], [("start",)])
        self.assertEqual(len(engine.events), 2)

    def test_existing_stream_is_preserved(self):
        engine = FakeEngine(opened=True)
        stream = engine._stream
        self.audition(engine, 3, 72, 0.8)
        self.assertIs(engine._stream, stream)
        self.assertEqual(engine.calls, [("send", NOTE, 3, 72, 0.8)])

    def test_default_note_and_velocity_contract_preserved(self):
        engine = FakeEngine(opened=True)
        self.assertIsNone(self.audition(engine, 2))
        self.assertEqual(engine.events, [(NOTE, 2, -1, 0.9)])

    def test_unavailable_device_drops_note_and_preserves_diagnostics(self):
        engine = FakeEngine(outcome="unavailable")
        self.audition(engine, 7, 60)
        self.assertEqual(engine.calls, [("start",)])
        self.assertEqual(engine.events, [])
        self.assertEqual(engine._stats.mode, "failed")
        self.assertEqual(engine._stats.error, "Synthetic device unavailable")
        self.assertEqual((engine._stats.callbacks, engine._stats.underflows), (7, 2))

    def test_start_exception_is_reported_without_escaping_or_queueing(self):
        engine = FakeEngine(outcome="raise")
        self.audition(engine, 0)
        self.assertEqual(engine.events, [])
        self.assertEqual(engine._stats.mode, "failed")
        self.assertIn("Synthetic device failure", engine._stats.error)
        self.assertEqual((engine._stats.callbacks, engine._stats.underflows), (7, 2))

    def test_failed_note_does_not_burst_when_a_later_audition_succeeds(self):
        engine = FakeEngine(outcome="unavailable")
        self.audition(engine, 7, 60)
        engine.outcome = "success"
        self.audition(engine, 7, 65)
        self.assertEqual(engine.events, [(NOTE, 7, 65, 0.9)])
        self.assertEqual(len([call for call in engine.calls if call[0] == "start"]), 2)

    def test_fallback_warning_is_preserved_on_successful_audition(self):
        engine = FakeEngine(outcome="fallback")
        self.audition(engine, 4)
        self.assertEqual(engine._stats.error, "Synthetic fallback warning")
        self.assertEqual(engine.events, [(NOTE, 4, -1, 0.9)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
