# C:\AI-BS\backend\test_daemon_supervisor.py
"""
Test Suite: DaemonManager Hybrid Supervision, Port Matrix, & Ecosystem Status
Verifies daemon registration, port matrix mapping, hardware metrics, and lifecycle actions.
"""

import sys
import os
import unittest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.daemon_manager import DaemonManager, ECOSYSTEM_PORTS, _ManagedDaemon
from core.tool_schemas import ShellCommand


class TestDaemonSupervisor(unittest.TestCase):
    def setUp(self):
        self.dm = DaemonManager(base_dir=str(backend_dir))

    def test_ecosystem_ports_matrix(self):
        """Verify the 18+ collision-free port matrix contains core ecosystem ports."""
        port_numbers = [p["port"] for p in ECOSYSTEM_PORTS]
        self.assertIn(8080, port_numbers, "FastAPI Port 8080 must be mapped.")
        self.assertIn(8189, port_numbers, "ComfyUI Port 8189 must be mapped.")
        self.assertIn(11434, port_numbers, "Ollama Port 11434 must be mapped.")
        self.assertIn(8000, port_numbers, "Go Gateway Port 8000 must be mapped.")
        self.assertIn(8002, port_numbers, "ChromaDB Port 8002 must be mapped.")
        self.assertIn(8005, port_numbers, "Broadcast Daemon Port 8005 must be mapped.")
        self.assertIn(8010, port_numbers, "SHM Telemetry Port 8010 must be mapped.")
        self.assertGreaterEqual(len(ECOSYSTEM_PORTS), 18, "Collision-free matrix must have >= 18 ports.")

    def test_daemon_registration_with_category(self):
        """Verify registering daemons with static and JIT categories and ports."""
        cmd = ShellCommand(command=sys.executable, cwd=backend_dir, args=["-c", "print('hello')"])
        self.dm.register("test_service", cmd, auto_start=False, port=9999, category="jit", vram_mb_estimate=512)
        
        status = self.dm.status()
        self.assertIn("test_service", status)
        self.assertFalse(status["test_service"]["running"])

        # Check internal dataclass fields
        daemon = self.dm._daemons["test_service"]
        self.assertEqual(daemon.port, 9999)
        self.assertEqual(daemon.category, "jit")
        self.assertEqual(daemon.vram_mb_estimate, 512)

    def test_hardware_metrics(self):
        """Verify hardware metrics extraction (CPU, RAM, GPU)."""
        metrics = self.dm.get_hardware_metrics()
        self.assertIn("cpu_percent", metrics)
        self.assertIn("ram_percent", metrics)
        self.assertIn("gpu", metrics)
        self.assertIn("name", metrics["gpu"])
        self.assertIn("vram_total_mb", metrics["gpu"])

    def test_thermal_throttle_check(self):
        """Verify thermal throttle function runs safely without crashing."""
        is_throttled = self.dm.check_hardware_thermal_throttle()
        self.assertIsInstance(is_throttled, bool)

    def test_full_ecosystem_status_serialization(self):
        """Verify get_full_ecosystem_status outputs structured authoritative metrics."""
        status = self.dm.get_full_ecosystem_status()
        self.assertEqual(status["version"], "v5.266.0")
        self.assertIn("online_ports", status)
        self.assertIn("total_ports", status)
        self.assertIn("ports", status)
        self.assertIn("hardware", status)
        self.assertEqual(len(status["ports"]), len(ECOSYSTEM_PORTS))

        # Check port structure
        first_port = status["ports"][0]
        self.assertIn("port", first_port)
        self.assertIn("name", first_port)
        self.assertIn("tier", first_port)
        self.assertIn("category", first_port)
        self.assertIn("status", first_port)

    def test_listener_registration_and_notification(self):
        """Verify listeners receive state change notifications."""
        events_received = []

        def sample_listener(event_type, daemon_name, payload):
            events_received.append((event_type, daemon_name, payload))

        self.dm.register_listener(sample_listener)
        self.dm._notify_listeners("test_event", "mock_daemon", {"code": 200})

        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0][0], "test_event")
        self.assertEqual(events_received[0][1], "mock_daemon")
        self.assertEqual(events_received[0][2]["code"], 200)


if __name__ == "__main__":
    unittest.main()
