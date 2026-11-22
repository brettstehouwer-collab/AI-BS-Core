"""Composition must validate config without touching original databases/services."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend')]
from core.swarm_runtime import SwarmRuntime


class SwarmRuntimeTests(unittest.TestCase):
    def test_construction_is_inert_and_preserves_distinct_store_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch('sqlite3.connect', side_effect=AssertionError('No activation')):
            root = Path(tmp)
            runtime = SwarmRuntime(root, project_root=root, config_path=ROOT / 'config/swarm_orchestration.json')
            self.assertEqual(runtime.stores['master'].path, root / 'backend/aibs_master.db')
            self.assertEqual(runtime.stores['cdz_audit'].path, root / 'database/aibs_master.db')
            self.assertEqual(list(root.iterdir()), [])
            self.assertTrue(runtime.close())

    def test_shutdown_stops_new_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = SwarmRuntime(tmp, config_path=ROOT / 'config/swarm_orchestration.json')
            runtime.request_shutdown()
            with self.assertRaises(RuntimeError):
                runtime.registry.acquire('late', 'test_runner', ['tests/new.py'])


if __name__ == '__main__':
    unittest.main()
