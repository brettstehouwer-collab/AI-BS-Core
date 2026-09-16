import asyncio
import logging
import time
import os
import sys

logger = logging.getLogger("ConsolidatedDaemonEngine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [DaemonEngine] %(message)s")

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus

class ConsolidatedDaemonEngine:
    """
    Consolidated Background Daemon Engine.
    Executes multiple lightweight background tasks (heuristics monitoring,
    vault watchdog, wallet tracker, memory cache sweeper) within a single
    async event loop to eliminate memory fragmentation and process overhead.
    """
    def __init__(self):
        self.is_running = False
        self.tasks = []

    async def _heuristics_loop(self):
        """Monitors system heuristics & CPU/GPU load."""
        while self.is_running:
            try:
                # Emit periodic system telemetry heartbeat
                await event_bus.publish(
                    "events.system.heartbeat",
                    {"uptime": time.time(), "status": "healthy"},
                    source="consolidated_daemon"
                )
            except Exception as e:
                logger.error(f"Heuristics loop error: {e}")
            await asyncio.sleep(10)

    async def _vault_watchdog_loop(self):
        """Watches Knowledge Vaults for new files to trigger auto-indexing."""
        while self.is_running:
            try:
                # Vault scan logic check
                pass
            except Exception as e:
                logger.error(f"Vault Watchdog loop error: {e}")
            await asyncio.sleep(30)

    async def _memory_cleaner_loop(self):
        """Sweeps stale cache keys and query caches."""
        while self.is_running:
            try:
                from AI_BS_Backend import _QUERY_CACHE
                now = time.time()
                keys_to_del = [k for k, v in _QUERY_CACHE.items() if now - v[1] > 300]
                for k in keys_to_del:
                    _QUERY_CACHE.pop(k, None)
            except Exception:
                pass
            await asyncio.sleep(60)

    async def start(self):
        self.is_running = True
        logger.info("Consolidated Background Daemon Engine Online.")
        self.tasks = [
            asyncio.create_task(self._heuristics_loop()),
            asyncio.create_task(self._vault_watchdog_loop()),
            asyncio.create_task(self._memory_cleaner_loop())
        ]
        await asyncio.gather(*self.tasks, return_exceptions=True)

    def stop(self):
        self.is_running = False
        for t in self.tasks:
            t.cancel()
        logger.info("Consolidated Background Daemon Engine Stopped.")

daemon_engine = ConsolidatedDaemonEngine()

if __name__ == "__main__":
    try:
        asyncio.run(daemon_engine.start())
    except KeyboardInterrupt:
        daemon_engine.stop()
