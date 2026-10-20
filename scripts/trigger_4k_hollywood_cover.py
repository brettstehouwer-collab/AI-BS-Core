import sys
import json
import urllib.request
import urllib.error
import time

sys.path.insert(0, r"C:\AI-BS")
from backend.core.comfy_workflow_builders import build_sdxl_txt2img_graph

prompt_body = (
    "In the ever-evolving landscape of technology and human interaction, the convergence "
    "of artificial intelligence and human creativity stands as a monumental pillar, "
    "shaping the trajectory of our collective future. A cinematic monumental cybernetic monolith "
    "pulsing with neural energy overlooking an epic futuristic metropolis at twilight, "
    "dramatic volumetric rim lighting, photorealistic cinematic masterpiece."
)
full_prompt = (
    "cinematic movie still, 8k resolution, dramatic film lighting, 35mm lens, sharp focus, "
    + prompt_body +
    ", Panavision, highly detailed film grain, color graded, masterpiece, ultra-hd"
)
negative_prompt = (
    "blurry, low quality, cartoon, 3d render, plastic, oversaturated, deformed, bad anatomy, "
    "disfigured, text, watermark, bad hands, low resolution"
)

graph = build_sdxl_txt2img_graph(
    prompt=full_prompt,
    negative_prompt=negative_prompt,
    target_tier="4K",
    aspect_ratio="16:9",
    steps=28,
    cfg=7.5,
    sampler_name="euler_ancestral",
    scheduler="karras",
    seed=int(time.time()),
    prefix="AIBS_SDXL_Hollywood_4K_Cover"
)

client_id = f"aibs_cover_{int(time.time())}"
payload = {
    "prompt": graph,
    "client_id": client_id
}

print(f"[ComfyUI 4K Trigger] Connecting to Port 8189 on RTX 4090...")
req = urllib.request.Request(
    "http://127.0.0.1:8189/prompt",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode("utf-8"))
    prompt_id = data.get("prompt_id")
    print(f"✅ [SUCCESS] Workflow Queued on Port 8189! Prompt ID: {prompt_id}")
    print(f"Pipeline: SDXL Base (1280x720 Latent) -> 28 Steps Euler Ancestral / Karras (CFG 7.5) -> VAE Decode -> 4x-UltraSharp Detail Pass -> Lanczos 3840x2160 Output")
except urllib.error.URLError as e:
    print(f"❌ [ERROR] Could not connect to ComfyUI on Port 8189: {e}")
    sys.exit(1)
