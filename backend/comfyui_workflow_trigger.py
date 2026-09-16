import os
import sys
import time
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
    level=logging.INFO, format="%(asctime)s - [ComfyUIWorkflowTrigger] - %(message)s"
)

app = FastAPI(title="AI-BS ComfyUI Workflow Trigger", version="1.0.0")
bridge = ShmBridge()
bridge.init_shm_bridge()


class WorkflowTriggerRequest(BaseModel):
    workflow_type: str = "SDXL"  # "SDXL" or "Wan2.1"
    prompt: str
    steps: int = 30
    cfg: float = 7.0
    seed: int = 42


@app.post("/api/v1/comfyui/trigger")
def trigger_comfyui_workflow(req: WorkflowTriggerRequest):
    logging.info(
        f"🎨 Triggering ComfyUI Workflow [{req.workflow_type}]: '{req.prompt}' ({req.steps} steps)"
    )

    # Simulate render progression telemetry over SHM Topic 0x0006
    vram_load = 18432 if req.workflow_type == "SDXL" else 21504
    payload = f"TRIGGER|MODEL:{req.workflow_type[:6]}|STEPS:{req.steps}|VRAM:{vram_load}M|PROMPT:{req.prompt[:15]}"
    bridge.push_topic_event(TOPIC_COMFYUI_GPU_RENDER, FLAG_HIGH_PRIORITY, payload)

    return {
        "status": "QUEUED",
        "workflow": req.workflow_type,
        "prompt": req.prompt,
        "steps": req.steps,
        "cfg": req.cfg,
        "seed": req.seed,
        "vram_allocation_mb": vram_load,
        "estimated_duration_sec": 3.5 if req.workflow_type == "SDXL" else 12.0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
