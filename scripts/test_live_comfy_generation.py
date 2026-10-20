import urllib.request
import json
import time

prompt_workflow = {
    "1": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"}
    },
    "2": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 512, "height": 512, "batch_size": 1}
    },
    "3": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "A futuristic glowing crystal cybernetic sphere hovering over neon metallic grid, 8k resolution, cinematic lighting", "clip": ["1", 1]}
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": "blurry, low quality, artifacts, watermark", "clip": ["1", 1]}
    },
    "5": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 42,
            "steps": 15,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["1", 0],
            "positive": ["3", 0],
            "negative": ["4", 0],
            "latent_image": ["2", 0]
        }
    },
    "6": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
    },
    "7": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "AI_BS_Live_Test", "images": ["6", 0]}
    }
}

payload = json.dumps({"prompt": prompt_workflow, "client_id": "aibs_live_test"}).encode('utf-8')
req = urllib.request.Request("http://127.0.0.1:8189/prompt", data=payload, headers={'Content-Type': 'application/json'})

print("[Test] Dispatching workflow prompt to ComfyUI on Port 8189...")
t0 = time.time()
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    prompt_id = res.get("prompt_id")
    print(f"[Test] Workflow queued successfully! Prompt ID: {prompt_id}")

print("[Test] Awaiting generation result from NVIDIA RTX 4090 and D: drive model...")
while True:
    time.sleep(1.0)
    with urllib.request.urlopen(f"http://127.0.0.1:8189/history/{prompt_id}") as h_resp:
        history = json.loads(h_resp.read().decode('utf-8'))
        if prompt_id in history:
            duration = round(time.time() - t0, 2)
            out = history[prompt_id].get("outputs", {}).get("7", {}).get("images", [])
            print(f"[SUCCESS] Image generated in {duration}s!")
            print(f"[Output] Image files: {out}")
            break
