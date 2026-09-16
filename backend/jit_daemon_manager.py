import os
import sys
import time
import subprocess
import logging

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [JITDaemonManager] - %(message)s"
)


class JITDaemonManager:
    def __init__(self):
        self.active_processes = {}
        self.thermal_threshold_celsius = 82.0
        logging.info("⚡ JITDaemonManager initialized (On-Demand Allocation Active)")

    def spawn_daemon_jit(self, daemon_name: str, script_relative_path: str):
        if (
            daemon_name in self.active_processes
            and self.active_processes[daemon_name].poll() is None
        ):
            logging.info(
                f"ℹ️ Daemon '{daemon_name}' is already running (PID: {self.active_processes[daemon_name].pid})."
            )
            return self.active_processes[daemon_name].pid

        # Thermal check before allocation
        if self.check_hardware_thermal_throttle():
            logging.warning(
                f"⚠️ [THERMAL GUARD] System temperatures exceed {self.thermal_threshold_celsius}°C. Throttling daemon spawn."
            )
            return -1

        full_path = os.path.join(os.path.dirname(__file__), script_relative_path)
        if not os.path.exists(full_path):
            logging.error(
                f"❌ Cannot spawn '{daemon_name}': File not found: {full_path}"
            )
            return -2

        proc = subprocess.Popen(["python", full_path])
        self.active_processes[daemon_name] = proc
        logging.info(f"✨ JIT Allocated Daemon '{daemon_name}' with PID {proc.pid}")
        return proc.pid

    def check_hardware_thermal_throttle(self):
        # Simulated or psutil temperature guard
        if psutil and hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            if entry.current > self.thermal_threshold_celsius:
                                return True
            except Exception:
                pass
        return False

    def terminate_idle_daemons(self):
        for name, proc in list(self.active_processes.items()):
            if proc.poll() is not None:
                del self.active_processes[name]


if __name__ == "__main__":
    manager = JITDaemonManager()
    pid = manager.spawn_daemon_jit("ResearchAgent", "research_agent_daemon.py")
    print(f"JIT Spawned PID: {pid}")
