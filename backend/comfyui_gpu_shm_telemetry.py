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
    from shm_bridge import ShmBridge, TOPIC_COMFYUI_GPU_RENDER, FLAG_HIGH_PRIORITY
except ImportError:
    TOPIC_COMFYUI_GPU_RENDER = 0x0006
    FLAG_HIGH_PRIORITY = 0x02

    class ShmBridge:
        def init_shm_bridge(self):
            return 0

        def push_topic_event(self, topic, flags, data):
            return 0

        def close_shm_bridge(self):
            pass


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [ComfyUIGPU] - %(message)s"
)


class ComfyUIGPUSHMTelemetry:
    def __init__(self):
        self.bridge = ShmBridge()
        self.bridge.init_shm_bridge()
        logging.info("🎨 ComfyUIGPUSHMTelemetry initialized on Topic 0x0006")

    def publish_gpu_render_stats(
        self,
        model: str,
        step: int,
        total_steps: int,
        vram_used_mb: int,
        vram_total_mb: int,
        fps: float,
    ):
        payload = f"COMFY|M:{model[:6]}|STEP:{step}/{total_steps}|VRAM:{vram_used_mb}/{vram_total_mb}M|FPS:{fps:.1f}"
        return self.bridge.push_topic_event(
            TOPIC_COMFYUI_GPU_RENDER, FLAG_HIGH_PRIORITY, payload
        )

    def close(self):
        self.bridge.close_shm_bridge()


if __name__ == "__main__":
    telemetry = ComfyUIGPUSHMTelemetry()
    telemetry.publish_gpu_render_stats("SDXL", 15, 30, 18432, 24576, 24.5)
    telemetry.publish_gpu_render_stats("WanVid", 42, 50, 21504, 24576, 18.2)
    telemetry.close()
