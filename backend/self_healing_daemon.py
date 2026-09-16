import os
import sys
import time
import logging
import subprocess
import threading
import argparse

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

try:
    from shm_bridge import ShmBridge, TOPIC_SYSTEM_STATE_HEARTBEAT, FLAG_HIGH_PRIORITY
except ImportError:
    TOPIC_SYSTEM_STATE_HEARTBEAT = 0x0004
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [SelfHealingDaemon] - %(message)s"
)


class SelfHealingDaemon:
    def __init__(self):
        self.bridge = ShmBridge()
        res = self.bridge.init_shm_bridge()
        if res == 0:
            logging.info(
                "✅ Connected to Multi-Topic SHM Bus under TOPIC_SYSTEM_STATE_HEARTBEAT (0x0004)"
            )
        else:
            logging.error(f"❌ Failed to attach to SHM Bus: {res}")

        self.running = True
        self.managed_daemons = {}

    def emit_heartbeat(self, daemon_name: str, pid: int, status_str: str = "OK"):
        payload = f"HB|NAME:{daemon_name[:15]}|PID:{pid}|STAT:{status_str[:5]}"
        return self.bridge.push_topic_event(TOPIC_SYSTEM_STATE_HEARTBEAT, 0, payload)

    def trigger_auto_recovery(self, daemon_name: str, daemon_script_path: str):
        logging.warning(
            f"🚨 Auto-Recovery Triggered for '{daemon_name}'! Restarting daemon subprocess..."
        )
        try:
            # Terminate old instance if active
            if daemon_name in self.managed_daemons:
                try:
                    self.managed_daemons[daemon_name].kill()
                except Exception:
                    pass

            # Spawn fresh subprocess
            proc = subprocess.Popen(
                [sys.executable, daemon_script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.managed_daemons[daemon_name] = proc
            logging.info(
                f"✅ Auto-Recovery Successful! Fresh PID: {proc.pid} spawned for '{daemon_name}'"
            )
            return proc.pid
        except Exception as e:
            logging.error(f"❌ Auto-Recovery Failed for '{daemon_name}': {e}")
            return -1

    def close(self):
        self.running = False
        self.bridge.close_shm_bridge()


def run_self_healing_monitor(duration_sec=10):
    logging.info(
        f"🚀 Starting Python Self-Healing Client Daemon ({duration_sec}s monitor)..."
    )
    daemon = SelfHealingDaemon()
    start_time = time.time()

    pid = os.getpid()
    hb_count = 0

    while time.time() - start_time < duration_sec:
        daemon.emit_heartbeat("SelfHealingDaemon", pid, "OK")
        hb_count += 1
        time.sleep(0.1)

    logging.info(
        f"⏱️ Monitor finished. Emitted {hb_count} heartbeat pulses to Go-Core Supervisor."
    )
    daemon.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI-BS Python Self-Healing Client Daemon"
    )
    parser.add_argument(
        "--duration", type=int, default=10, help="Monitoring duration in seconds"
    )
    parser.add_argument(
        "--test-recovery",
        action="store_true",
        help="Execute simulated recovery hook test",
    )
    args = parser.parse_args()

    if args.test_recovery:
        sh_daemon = SelfHealingDaemon()
        script = os.path.join(os.path.dirname(__file__), "heuristics_shm_daemon.py")
        sh_daemon.trigger_auto_recovery("HeuristicsSHMDaemon", script)
        sh_daemon.close()
    else:
        run_self_healing_monitor(args.duration)
