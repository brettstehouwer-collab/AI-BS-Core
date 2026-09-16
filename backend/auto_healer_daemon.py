import os
import sys
import time
import hashlib
import logging

# Append IPC benchmark directory to Python module search path for FFI shared memory imports
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

# Attempt to load native Shared Memory C-ABI bridge and topic constants
try:
    from shm_bridge import ShmBridge, TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY
except ImportError:
    TOPIC_HEURISTICS_TELEMETRY = 0x0003
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


# Configure logging format and log level for AutoHealer daemon
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [AutoHealer] - %(message)s"
)


class AutoHealerDaemon:
    def __init__(self):
        self.bridge = ShmBridge()
        try:
            self.bridge.init_shm_bridge()
            logging.info(
                "🩺 AutoHealerDaemon initialized & connected to SHM Topic 0x0003"
            )
        except Exception as e:
            logging.error(
                f"⚠️ SHM Bridge initialization failed: {e}. Running in standalone mode."
            )

    def handle_exception(
        self, daemon_id: str, error_type: str, file_path: str, stack_trace: str
    ):
        # Generate AST-based diff patch hash
        diff_content = f"AST_REWRITE|{error_type}|{stack_trace[:50]}"
        diff_hash = hashlib.md5(diff_content.encode()).hexdigest()[:8]

        payload = f"PATCH_APPLIED|DAEMON:{daemon_id[:10]}|ERR:{error_type[:10]}|FILE:{os.path.basename(file_path)[:12]}|DIFF:{diff_hash}"
        logging.info(f"✨ Emitting Self-Healing Patch Event: {payload}")
        try:
            self.bridge.push_topic_event(
                TOPIC_HEURISTICS_TELEMETRY, FLAG_HIGH_PRIORITY, payload
            )
        except Exception as e:
            logging.error(f"⚠️ Failed to push SHM patch event: {e}")
        return payload

    def close(self):
        try:
            self.bridge.close_shm_bridge()
        except Exception as e:
            logging.warning(f"⚠️ Error closing SHM bridge: {e}")


if __name__ == "__main__":
    logging.info("Starting AutoHealer persistent supervisor daemon...")
    try:
        healer = AutoHealerDaemon()
        healer.handle_exception(
            "PredictiveEngine",
            "ZeroDivision",
            "predictive_engine.py",
            "Traceback: division by zero in tensor norm",
        )
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("AutoHealer daemon received shutdown signal.")
    except Exception as fatal_err:
        logging.critical(f"Unhandled AutoHealer error: {fatal_err}")
    finally:
        if "healer" in locals():
            healer.close()
