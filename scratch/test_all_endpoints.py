import requests
import urllib.request
import json
import sys

MASTER_KEY = "sk_aibs_dev_master_key_2026"
HEADERS = {
    "Authorization": f"Bearer {MASTER_KEY}",
    "Content-Type": "application/json"
}

def write_out(msg):
    sys.stdout.buffer.write((msg + "\n").encode('utf-8'))
    sys.stdout.flush()

write_out("--- Testing ComfyUI Engine (Port 8189) ---")
try:
    data = {
        "prompt": {
            "3": {"class_type": "KSampler", "inputs": {"seed": 123, "steps": 1, "cfg": 7.0, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "test", "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "test", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "AI_BS_HD_TEST", "images": ["8", 0]}}
        }
    }
    req = urllib.request.Request("http://127.0.0.1:8189/prompt", data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    res = urllib.request.urlopen(req).read().decode()
    write_out(f"✅ ComfyUI Base Model API responded successfully: {res}")
except Exception as e:
    write_out(f"❌ ComfyUI Base Model Error: {e}")

write_out("\n--- Testing Stehouwer LLM Chat (Port 8000) ---")
try:
    res = requests.post("http://127.0.0.1:8000/v1/chat/completions", json={
        "model": "stehouwer_llm",
        "messages": [{"role": "user", "content": "Hello! System check."}],
        "stream": False
    }, headers=HEADERS, timeout=120)
    write_out(f"✅ Chat API Response: {res.status_code}")
except Exception as e:
    write_out(f"❌ Chat API Error: {e}")

write_out("\n--- Testing Commercial Image Pipeline (Port 8000 -> 8188) ---")
try:
    res = requests.post("http://127.0.0.1:8000/v1/images/generations", json={
        "prompt": "A futuristic city skyline at sunset",
        "n": 1,
        "size": "1024x1024"
    }, headers=HEADERS, timeout=120)
    write_out(f"✅ Image API Response: {res.status_code} {res.text[:200]}")
except Exception as e:
    write_out(f"❌ Image API Error: {e}")

write_out("\n--- Testing Commercial Video Pipeline (Port 8000 -> 8188) ---")
try:
    res = requests.post("http://127.0.0.1:8000/v1/videos/generations", json={
        "prompt": "A futuristic city skyline flying car",
        "duration_sec": 4,
        "fps": 12
    }, headers=HEADERS, timeout=300)
    write_out(f"✅ Video API Response: {res.status_code} {res.text[:200]}")
except Exception as e:
    write_out(f"❌ Video API Error: {e}")

write_out("\n--- Testing Commercial Audio Pipeline (Port 8000) ---")
try:
    res = requests.post("http://127.0.0.1:8000/v1/audio/generations", json={
        "prompt": "Synthwave test track",
        "genre": "synthwave",
        "duration_sec": 10,
        "lyrics": "This is a system check, everything is online.",
        "tempo_bpm": 120
    }, headers=HEADERS, timeout=300)
    write_out(f"✅ Audio API Response: {res.status_code} {res.text[:200]}")
except Exception as e:
    write_out(f"❌ Audio API Error: {e}")
