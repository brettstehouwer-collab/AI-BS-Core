import os
import sys
import time
import json
import logging
import argparse

# Ensure sandbox_scratch/ipc_benchmark is on sys.path for ShmBridge
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

try:
    from shm_bridge import ShmBridge
except ImportError:
    # Inline fallback if imported standalone
    import ctypes
    from ctypes import wintypes

    AIBS_SHM_MAGIC = 0xA1B51996
    AIBS_SHM_NAME = "Local\\AI_BS_IPC_SHM_RING"
    AIBS_RING_SLOTS = 64
    AIBS_SLOT_PAYLOAD_SIZE = 62
    AIBS_SHM_TOTAL_SIZE = 4224

    class RingSlot(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ("length", ctypes.c_uint16),
            ("payload", ctypes.c_uint8 * AIBS_SLOT_PAYLOAD_SIZE),
        ]

    class ShmRingBuffer(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ("magic", ctypes.c_uint32),
            ("version", ctypes.c_uint32),
            ("head", ctypes.c_uint64),
            ("tail", ctypes.c_uint64),
            ("total_pushed", ctypes.c_uint64),
            ("total_popped", ctypes.c_uint64),
            ("padding", ctypes.c_uint8 * 24),
            ("slots", RingSlot * AIBS_RING_SLOTS),
        ]

    class ShmBridge:
        def __init__(self, shm_name=AIBS_SHM_NAME):
            self.shm_name = shm_name
            self.hMapFile = None
            self.ring_ptr = None
            self.ring = None
            self.k32 = ctypes.windll.kernel32

        def init_shm_bridge(self):
            if self.ring:
                return 0
            self.hMapFile = self.k32.CreateFileMappingW(
                -1, None, 0x04, 0, AIBS_SHM_TOTAL_SIZE, self.shm_name
            )
            if not self.hMapFile:
                return -1
            self.ring_ptr = self.k32.MapViewOfFile(
                self.hMapFile, 0xF001F, 0, 0, AIBS_SHM_TOTAL_SIZE
            )
            if not self.ring_ptr:
                return -2
            self.ring = ShmRingBuffer.from_address(self.ring_ptr)
            if self.ring.magic != AIBS_SHM_MAGIC:
                self.ring.magic = AIBS_SHM_MAGIC
                self.ring.version = 1
                self.ring.head = 0
                self.ring.tail = 0
                self.ring.total_pushed = 0
                self.ring.total_popped = 0
            return 0

        def push_event(self, data: str):
            if not self.ring:
                return -1
            payload_bytes = data.encode("utf-8")[:AIBS_SLOT_PAYLOAD_SIZE]
            spin = 0
            while (self.ring.head - self.ring.tail) >= AIBS_RING_SLOTS:
                spin += 1
                time.sleep(0.000001)
                if spin > 1000:
                    return -2
            slot_idx = self.ring.head % AIBS_RING_SLOTS
            slot = self.ring.slots[slot_idx]
            slot.length = len(payload_bytes)
            for i, b in enumerate(payload_bytes):
                slot.payload[i] = b
            self.ring.head += 1
            self.ring.total_pushed += 1
            return 0

        def close_shm_bridge(self):
            if self.ring_ptr:
                self.k32.UnmapViewOfFile(self.ring_ptr)
            if self.hMapFile:
                self.k32.CloseHandle(self.hMapFile)
            self.ring = None


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [PredictiveEngineSHM] - %(message)s"
)


class PredictiveEngineSHMClient:
    def __init__(self):
        self.bridge = ShmBridge()
        res = self.bridge.init_shm_bridge()
        if res == 0:
            logging.info(
                "✅ Connected to Go-Core SHM Ring Bus (Local\\AI_BS_IPC_SHM_RING)"
            )
        else:
            logging.error(f"❌ Failed to connect to SHM Ring Bus: {res}")

    def emit_tensor_metric(
        self, intent: str, sentiment: str, latency_ms: float, confidence: float
    ):
        # Format payload within 62 byte limit: e.g. "I:Code Generation|S:Neutral|L:1.20|C:0.95"
        payload = (
            f"I:{intent[:15]}|S:{sentiment[:8]}|L:{latency_ms:.2f}|C:{confidence:.2f}"
        )
        res = self.bridge.push_event(payload)
        return res

    def close(self):
        self.bridge.close_shm_bridge()


def run_benchmark(messages_count=100000):
    logging.info(
        f"🚀 Running Python -> SHM -> Go-Core Latency Benchmark ({messages_count} msgs)..."
    )
    client = PredictiveEngineSHMClient()
    start_time = time.time()

    for i in range(messages_count):
        client.emit_tensor_metric("Code Gen", "Neutral", 1.25, 0.98)

    elapsed = time.time() - start_time
    ns_per_op = (elapsed * 1e9) / messages_count
    logging.info(f"⏱️ Total Time: {elapsed:.4f}s | Latency: {ns_per_op:.2f} ns/msg")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI-BS Predictive Engine SHM Daemon Client"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run IPC throughput benchmark"
    )
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
    else:
        client = PredictiveEngineSHMClient()
        logging.info("Streaming sample tensor metric event into SHM...")
        client.emit_tensor_metric("Bug Fix", "High-Stress", 2.10, 0.94)
        client.close()
