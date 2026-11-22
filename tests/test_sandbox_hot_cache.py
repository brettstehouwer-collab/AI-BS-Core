import unittest
import time
import os
import sys

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(_base_dir, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_base_dir, "backend"))

from core.hot_cache import HotCache

class TestSandboxHotCache(unittest.TestCase):
    def setUp(self):
        self.cache = HotCache()
        self.cache._store.clear()
        self.cache._counters.clear()

    def test_set_and_get(self):
        self.cache.set("telemetry:cpu", 42.5, ttl_seconds=10)
        val = self.cache.get("telemetry:cpu")
        self.assertEqual(val, 42.5)

    def test_ttl_expiration(self):
        self.cache.set("short_lived", "temp_value", ttl_seconds=0.05)
        self.assertEqual(self.cache.get("short_lived"), "temp_value")
        time.sleep(0.06)
        self.assertIsNone(self.cache.get("short_lived"))

    def test_get_many_pattern(self):
        self.cache.set("vram:primary", 24.0)
        self.cache.set("vram:allocated", 8.0)
        self.cache.set("crypto:eth", 2700.0)

        vram_keys = self.cache.get_many("vram:*")
        self.assertEqual(len(vram_keys), 2)
        self.assertIn("vram:primary", vram_keys)
        self.assertIn("vram:allocated", vram_keys)

    def test_atomic_increment(self):
        c1 = self.cache.increment("counter:requests", 1)
        c2 = self.cache.increment("counter:requests", 5)
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 6)

if __name__ == "__main__":
    unittest.main()
