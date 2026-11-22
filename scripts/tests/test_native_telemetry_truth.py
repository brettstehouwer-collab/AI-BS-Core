"""Execute only extracted class methods with inert Qt fixtures; never import app/engine."""
import ast
import os
from pathlib import Path
import types
import unittest

ROOT = Path(os.environ.get('AIBS_SOURCE_ROOT', 'C:/AI-BS'))
SOURCE = ROOT / 'native_studio/web_telemetry_view.py'

class Widget:
    values = []
    timers = []
    def __init__(self, *args, **kwargs):
        self.active = False
        self.timeout = self.clicked = self
        if args and isinstance(args[0], str): self.values.append(args[0])
    def __getattr__(self, name):
        return lambda *args, **kwargs: self
    def start(self, *args): self.active = True; self.timers.append(self)
    def stop(self): self.active = False
    def isActive(self): return self.active

class NativeTelemetryTruth(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WebTelemetryNativeView')
        # Keep all class methods and port configuration; exclude every import/module side effect.
        selected = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PORTS_18' for t in n.targets)]
        selected.append(cls)
        names = {n.id for n in ast.walk(cls) if isinstance(n, ast.Name)}
        env = {name: Widget for name in names if name.startswith('Q') or name in ('QWidget',)}
        env.update({'EngineBus': object, 'PALETTE': {}, 'Optional': __import__('typing').Optional,
                    'Qt': Widget(), 'QHeaderView': types.SimpleNamespace(ResizeMode=types.SimpleNamespace(Stretch=0, ResizeToContents=1)),
                    'datetime': __import__('datetime').datetime, 'random': __import__('random'), 'hashlib': __import__('hashlib'), 'time': __import__('time')})
        Widget.values = []; Widget.timers = []
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), 'exec'), env)
        self.cls = env['WebTelemetryNativeView']
    def test_construction_never_seeds_capture_evidence_or_starts_synthetic_feed(self):
        view = self.cls(object())
        self.assertEqual(view._traffic_records, [])
        self.assertEqual(Widget.timers, [])
    def test_legacy_feed_callbacks_cannot_manufacture_packets(self):
        view = object.__new__(self.cls)
        view._traffic_records = []
        view.wire_table = Widget()
        for name in ('_seed_wire_traffic', '_add_live_packet'):
            if hasattr(view, name): getattr(view, name)()
        self.assertEqual(view._traffic_records, [])

    def test_all_subviews_show_absent_measurements_instead_of_seeded_identity_and_health(self):
        view = self.cls(object())
        values = " ".join(Widget.values)
        self.assertFalse("@" in values, "no seeded user identity may appear as a session")
        self.assertNotIn("OPTIMAL", values)
        self.assertNotIn("18/18 Online", values)
        self.assertTrue(all(value == "Unavailable" for _, value, _, _ in view.kpi_cards_data))

if __name__ == '__main__': unittest.main()
