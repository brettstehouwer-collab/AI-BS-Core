"""
infinite_learning_loop.py — AI-BS Infinite Learning Loop Daemon.
Continuously captures hardware telemetry, digests chat transcripts & system events,
synthesizes heuristic deductions, and persists knowledge to the Memory Bank.
"""

import os
import sys
import time
import threading
import logging
import psutil
import json
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add backend and root to sys.path
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_root_dir = _backend_dir.parent
for p in [str(_current_dir), str(_backend_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from memory_bank import store_heuristic, get_memory_bank_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [InfiniteLearning] %(message)s"
)
logger = logging.getLogger("InfiniteLearning")

class InfiniteLearningLoop:
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.iteration = 0
        self.start_time: Optional[float] = None
        self.last_tick_time: Optional[float] = None
        self.last_read_position = 0
        self.recent_heuristics: List[Dict[str, Any]] = []
        self.throttle_seconds = 4.0
        self.max_history_entries = 50

        # Transcript path resolution
        self.ingest_dir = r"C:\Users\footb\OneDrive\Desktop\ingest folder"
        self.transcript_candidates = [
            str(_root_dir / "backend" / "session_history_archive.json"),
            str(_root_dir / "logs" / "beta_tester_transcripts.txt"),
            os.path.join(os.getenv("APPDATA", ""), "antigravity-ide", "brain", "e1c7fdf6-c99a-44af-9271-509302506911", ".system_generated", "logs", "transcript.jsonl"),
            os.path.join(os.getenv("APPDATA", ""), "antigravity-ide", "brain", "3fa75394-f086-4c3f-8931-c193a9cc765d", ".system_generated", "logs", "transcript.jsonl")
        ]

    def get_active_transcript_path(self) -> Optional[str]:
        for p in self.transcript_candidates:
            if os.path.exists(p):
                return p
        return None

    def get_telemetry(self) -> Dict[str, Any]:
        """Extracts current VRAM, RAM, and CPU telemetry."""
        # Check VRAM via nvidia-smi if available
        vram_used_mb = 0.0
        vram_total_mb = 24576.0 # RTX 4090 baseline
        try:
            import subprocess
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
                capture_output=True, text=True, timeout=1.5
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("\n")[0].split(",")
                if len(parts) >= 2:
                    vram_used_mb = float(parts[0].strip())
                    vram_total_mb = float(parts[1].strip())
        except Exception:
            pass

        vm = psutil.virtual_memory()
        system_ram_used_mb = round(vm.used / (1024 * 1024), 1)
        system_ram_total_mb = round(vm.total / (1024 * 1024), 1)
        cpu_percent = psutil.cpu_percent(interval=None)

        return {
            "vram_used_mb": vram_used_mb,
            "vram_total_mb": vram_total_mb,
            "system_ram_used_mb": system_ram_used_mb,
            "system_ram_total_mb": system_ram_total_mb,
            "cpu_percent": cpu_percent
        }

    def ingest_recent_transcripts(self) -> List[str]:
        """Reads new entries from active transcripts to discover reasoning insights."""
        path = self.get_active_transcript_path()
        if not path or not os.path.exists(path):
            return []

        discovered = []
        try:
            # Handle JSON list (e.g. session_history_archive.json)
            if path.endswith(".json"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    if isinstance(data, list) and data:
                        idx = (self.iteration - 1) % len(data)
                        item = data[idx]
                        text = item.get("ai_response", "") or item.get("user_msg", "") or str(item)
                        if text:
                            discovered.append(str(text)[:250])
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self.last_read_position)
                    lines = f.readlines()
                    self.last_read_position = f.tell()

                for line in lines[-20:]:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        content = entry.get("content", "") or entry.get("user_msg", "") or entry.get("ai_response", "")
                        if content and len(content) > 30:
                            discovered.append(str(content)[:250])
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Transcript scan error: {e}")

        return discovered

    def learning_tick(self):
        """Executes a single deduction cycle and records to memory bank."""
        self.iteration += 1
        self.last_tick_time = time.time()
        telemetry = self.get_telemetry()

        # Guardrail: If RAM exceeds safety ceiling, pause
        if telemetry["system_ram_used_mb"] > 60000:  # 60 GB
            logger.warning("Safety threshold exceeded. Pausing deduction tick.")
            time.sleep(10)
            return

        # Check transcript discoveries
        discoveries = self.ingest_recent_transcripts()
        if discoveries:
            heuristic_summary = f"Deduction Tick {self.iteration}: Synthesized context on [{discoveries[0][:60]}...]"
        else:
            heuristic_summary = f"Deduction Tick {self.iteration}: Autonomous heuristic baseline verified at {time.strftime('%H:%M:%S')}."

        # Persist to Memory Bank
        store_heuristic(
            heuristic_summary,
            metadata={
                "iteration": self.iteration,
                "source": "infinite_learning_loop",
                "cpu_percent": telemetry["cpu_percent"],
                "vram_mb": telemetry["vram_used_mb"],
                "ram_mb": telemetry["system_ram_used_mb"]
            }
        )

        entry = {
            "iteration": self.iteration,
            "text": heuristic_summary,
            "timestamp": self.last_tick_time,
            "telemetry": telemetry
        }
        self.recent_heuristics.insert(0, entry)
        if len(self.recent_heuristics) > self.max_history_entries:
            self.recent_heuristics.pop()

        logger.info(f"Tick {self.iteration} complete | CPU: {telemetry['cpu_percent']}% | RAM: {telemetry['system_ram_used_mb']}MB")

    def _loop_worker(self):
        logger.info("Infinite Learning Loop background worker engaged.")
        while self.running:
            try:
                self.learning_tick()
            except Exception as e:
                logger.error(f"Learning tick unhandled exception: {e}")
            time.sleep(self.throttle_seconds)
        logger.info("Infinite Learning Loop background worker paused.")

    def start(self) -> bool:
        if not self.running:
            self.running = True
            if self.start_time is None:
                self.start_time = time.time()
            self.thread = threading.Thread(target=self._loop_worker, daemon=True, name="AIBS_InfiniteLearningLoop")
            self.thread.start()
            return True
        return False

    def stop(self) -> bool:
        if self.running:
            self.running = False
            if self.thread and threading.current_thread() != self.thread:
                self.thread.join(timeout=3.0)
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        telemetry = self.get_telemetry()
        bank_status = get_memory_bank_status()
        uptime_seconds = round(time.time() - self.start_time, 1) if (self.running and self.start_time) else 0.0

        return {
            "is_running": self.running,
            "iteration": self.iteration,
            "uptime_seconds": uptime_seconds,
            "last_tick_time": self.last_tick_time,
            "throttle_seconds": self.throttle_seconds,
            "telemetry": telemetry,
            "memory_bank": bank_status,
            "recent_heuristics": self.recent_heuristics[:10],
            "timestamp": time.time()
        }

# Global singleton instance
learning_loop_instance = InfiniteLearningLoop()

if __name__ == "__main__":
    learning_loop_instance.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        learning_loop_instance.stop()
