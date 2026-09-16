"""
unified_stehouwer_launcher.py — Master boot sequence for the AI-BS ecosystem.

Boot order
----------
1. DaemonManager starts all registered background daemons (trainer_daemon, etc.)
   and begins watchdog supervision.
2. InfiniteLearningLoop thread is started.
3. Swarm orchestrator + MemoryService are initialized.
4. Electron UI is launched (optional — skipped gracefully if .exe is missing).
5. Main thread blocks until Ctrl+C, then shuts everything down cleanly.
"""

import os
import sys

_base_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.join(_base_dir, "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

import subprocess
import time
import logging

try:
    from infinite_learning_loop import InfiniteLearningLoop
except ImportError:
    InfiniteLearningLoop = None

try:
    from bullshit_orchestrator import AsyncCoreEngine, SwarmOrchestrator
except ImportError:
    AsyncCoreEngine, SwarmOrchestrator = None, None

from daemon_manager import build_default_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


class UnifiedStehouwerLauncher:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.frontend_exe = os.path.join(
            self.base_dir,
            os.getenv("FRONTEND_EXE", "AI-BS.exe"),
        )
        self.learning_loop = None
        self.daemon_manager = build_default_manager(base_dir=self.base_dir)

    # ------------------------------------------------------------------
    # Boot sequence
    # ------------------------------------------------------------------

    def boot_sequence(self):
        print("=" * 50)
        print("    INITIALIZING UNIFIED STEHOUWER ECOSYSTEM")
        print("=" * 50)

        # ── 1. Background daemons ──────────────────────────────────────
        print(
            "\n[1/4] Starting background daemons via DaemonManager (with pre-flight port sweep)..."
        )
        self.daemon_manager.start_all(target_ports=[8000, 8001, 11434, 8188, 4067])
        time.sleep(1)  # give daemons a moment to initialize
        status = self.daemon_manager.status()
        for name, info in status.items():
            state = "RUNNING" if info["running"] else "FAILED"
            pid_str = f" (PID {info['pid']})" if info["pid"] else ""
            print(f"         {name}: [{state}]{pid_str}")

        # ── 2. Infinite learning thread ───────────────────────────────
        print("\n[2/4] Booting Telemetry & Infinite Learning Daemon...")
        self.learning_loop = InfiniteLearningLoop()
        self.learning_loop.start()
        time.sleep(1)

        # ── 3. Swarm orchestrator ─────────────────────────────────────
        print("\n[3/4] Initializing Swarm Engine Logic...")
        try:
            AsyncCoreEngine()
            SwarmOrchestrator()
            print("      Swarm topology and multi-agent systems loaded.")
        except Exception as e:
            print(f"      [Warning] Orchestrator init failed: {e}")

        # ── 4. Electron UI ────────────────────────────────────────────
        print("\n[4/4] Launching AI-BS User Interface...")
        if os.path.exists(self.frontend_exe):
            subprocess.Popen([self.frontend_exe])
            print(f"      Launched: {self.frontend_exe}")
        else:
            print(f"      [Warning] UI executable not found: {
                    self.frontend_exe}")
            print("      Background matrix is running; attach a UI manually.")

        print("\n" + "=" * 50)
        print("    ECOSYSTEM ONLINE — Press Ctrl+C to shut down")
        print("=" * 50 + "\n")

        # ── Keep-alive ────────────────────────────────────────────────
        try:
            while True:
                time.sleep(5)
                # Periodic health log (DEBUG level — won't clutter console)
                logger.debug("Daemon health: %s", self.daemon_manager.health_check())
        except KeyboardInterrupt:
            self._shutdown()

    # ------------------------------------------------------------------
    # Graceful shutdown
    # ------------------------------------------------------------------

    def _shutdown(self):
        print("\n\nShutting down Unified Ecosystem...")

        if self.learning_loop:
            print("  Stopping learning loop...")
            self.learning_loop.stop()

        print("  Stopping all daemons...")
        self.daemon_manager.stop_all()

        print("  Shutdown complete.")


if __name__ == "__main__":
    launcher = UnifiedStehouwerLauncher()
    launcher.boot_sequence()
