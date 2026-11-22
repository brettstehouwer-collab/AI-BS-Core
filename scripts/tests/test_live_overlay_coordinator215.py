import ast
from pathlib import Path
import unittest


class CoordinatorOverlayContracts(unittest.TestCase):
    def test_default_constructor_keeps_overlay_off_for_test_harnesses(self):
        from backend.core.broadcast_secondary import SecondaryBroadcast
        self.assertFalse(SecondaryBroadcast()._live_overlay)
        self.assertTrue(SecondaryBroadcast(live_overlay=True)._live_overlay)

    def test_explicit_cli_owns_overlay_and_retains_the_existing_capture(self):
        source=(Path(__file__).resolve().parents[2]/'backend/core/broadcast_secondary.py').read_text()
        tree=ast.parse(source)
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        constructors=[n for n in ast.walk(main) if isinstance(n,ast.Call) and getattr(n.func,'id',None)=='SecondaryBroadcast']
        self.assertTrue(any(k.arg=='live_overlay' and isinstance(k.value,ast.Constant) and k.value.value is True
                            for call in constructors for k in call.keywords))
        self.assertIn('follow.capture=OverlayCapture(follow.capture)',source)
