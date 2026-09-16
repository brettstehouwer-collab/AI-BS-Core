import os
import sys
import time
import logging

sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sandbox_scratch", "ipc_benchmark"
    )
)

try:
    from shm_bridge import ShmBridge, TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY
except ImportError:
    TOPIC_ZERO_COPY_VECTOR_TENSORS = 0x0005
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [VectorTensorPublisher] - %(message)s"
)


class VectorTensorPublisher:
    def __init__(self):
        self.bridge = ShmBridge()
        self.bridge.init_shm_bridge()
        logging.info("🚀 VectorTensorPublisher initialized on Topic 0x0005")

    def publish_vector_embedding(
        self, source: str, dimensions: int, latency_us: float, token_chunk: str
    ):
        payload = f"TENSOR|SRC:{source[:8]}|DIM:{dimensions}|LAT:{latency_us:.1f}u|TOK:{token_chunk[:20]}"
        return self.bridge.push_topic_event(
            TOPIC_ZERO_COPY_VECTOR_TENSORS, FLAG_HIGH_PRIORITY, payload
        )

    def close(self):
        self.bridge.close_shm_bridge()


if __name__ == "__main__":
    pub = VectorTensorPublisher()
    pub.publish_vector_embedding("ChromaDB", 1536, 1.4, "stehouwer_vector_mem")
    pub.publish_vector_embedding("Ollama", 4096, 2.8, "autonomous_agent_step")
    pub.close()
