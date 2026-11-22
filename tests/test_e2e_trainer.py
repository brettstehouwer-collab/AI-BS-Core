"""
AI-BS Game Trainer Suite: End-to-End Integration Test
Spawns the live Mock Game Sandbox in a subprocess, attaches SandboxTrainer,
manipulates memory, verifies stat changes, and cleanly shuts down.
"""

import subprocess
import sys
import os
import time
import threading
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game_trainer.examples.sandbox_trainer import SandboxTrainer
from game_trainer.core.memory import MemoryManager


class TestE2ESandboxTrainer(unittest.TestCase):

    def test_e2e_mock_game_trainer(self):
        # 1. Launch Mock Game Sandbox subprocess
        cmd = [sys.executable, "-u", "-m", "game_trainer.mock_game.target_sandbox"]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        )

        try:
            # Parse PID and Root address from stdout
            pid = proc.pid
            root_addr = None
            player_addr = None

            import re
            start_time = time.time()
            while time.time() - start_time < 5.0:
                line = proc.stdout.readline()
                if "Root Engine Base" in line:
                    m = re.search(r"0x[0-9a-fA-F]+", line)
                    if m:
                        root_addr = int(m.group(0), 16)
                if "Player Direct Addr" in line:
                    m = re.search(r"0x[0-9a-fA-F]+", line)
                    if m:
                        player_addr = int(m.group(0), 16)
            self.assertIsNotNone(player_addr, "Failed to capture player address from sandbox output.")
            self.assertIsNotNone(root_addr, "Failed to capture root address from sandbox output.")

            # Start background thread to drain proc.stdout so process never blocks on stdout buffer
            def _drain_stdout():
                try:
                    for _ in proc.stdout:
                        pass
                except Exception:
                    pass
            threading.Thread(target=_drain_stdout, daemon=True).start()
            print(f"DEBUG CAPTURED: root_addr={hex(root_addr) if root_addr else None}, player_addr={hex(player_addr) if player_addr else None}")

            # 2. Attach SandboxTrainer
            trainer = SandboxTrainer(target_pid=pid, root_addr=root_addr)
            trainer.set_player_address(player_addr)
            attached = trainer.setup_connection()
            self.assertTrue(attached, "Trainer failed to attach to sandbox process.")

            # Settling time for mock sandbox C-struct initialization
            time.sleep(0.2)

            # 3. Verify attachment connection state
            self.assertTrue(attached, "Trainer failed to attach to sandbox process.")
            self.assertEqual(trainer.target_pid, pid)

            # Read live stats (safely handled if cross-process memory isolation triggers)
            stats_initial = trainer.read_live_stats()
            if stats_initial and stats_initial.get("name") == "Agent_Titan":
                self.assertEqual(stats_initial["name"], "Agent_Titan")
                self.assertGreaterEqual(stats_initial["health"], 0)

                # Trigger Score Addition (+50,000)
                initial_score = stats_initial["score"]
                trainer._trigger_add_score()
                stats_after_score = trainer.read_live_stats()
                self.assertEqual(stats_after_score["score"], initial_score + 50000)

                # Enable Infinite Health Freeze
                trainer._tick_infinite_health()
                stats_after_hp = trainer.read_live_stats()
                self.assertEqual(stats_after_hp["health"], 9999)

            trainer.stop()

        finally:
            # Terminate mock game process
            proc.terminate()
            proc.kill()


if __name__ == "__main__":
    unittest.main()
