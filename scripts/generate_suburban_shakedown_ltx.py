"""
Orchestrates LTX-Video Image-to-Video generation for the 5 Suburban Shakedown scenes.
Feeds each anchor frame into ComfyUI LTX-Video workflow with customized motion prompts.
"""

import json
import urllib.request
import urllib.parse
import time
import random

COMFYUI_SERVER = "http://127.0.0.1:8189"

SCENE_PROMPTS = [
    {
        "clip_num": 1,
        "input_image": "SuburbanShakedown_Clip01.png",
        "title": "The SWAT Team Warning",
        "prompt": (
            "Cinematic 4K. The Host in his black suit under harsh stadium floodlights steps forward, "
            "animatedly gesturing with his arms wide, speaking with intense dramatic emotion and disbelief toward off-camera, "
            "suburban front yard at night, lawn shadows moving."
        ),
        "prefix": "SuburbanShakedown_LTX_Clip01"
    },
    {
        "clip_num": 2,
        "input_image": "SuburbanShakedown_Clip02.png",
        "title": "Frictionless Entry",
        "prompt": (
            "Cinematic 4K. Inside the rusty iron jail cell on the front lawn, The Inmate in his orange jumpsuit "
            "tilts his designer sunglasses down his nose and deadpan holds up a large bottle of baby oil with both hands, "
            "the deflating giant lawn nutcracker slowly wheezes on the grass outside the bars."
        ),
        "prefix": "SuburbanShakedown_LTX_Clip02"
    },
    {
        "clip_num": 3,
        "input_image": "SuburbanShakedown_Clip03.png",
        "title": "Fastball Incoming",
        "prompt": (
            "Cinematic 4K low angle camera motion. The Slugger in full vintage baseball uniform aggressively shifts weight, "
            "taps his wooden bat against his cleats sending bits of mulch flying, stepping into a coiled, focused batting stance looking forward."
        ),
        "prefix": "SuburbanShakedown_LTX_Clip03"
    },
    {
        "clip_num": 4,
        "input_image": "SuburbanShakedown_Clip04.png",
        "title": "The Wet Explosion",
        "prompt": (
            "Cinematic slow motion high speed camera. A clear plastic bottle of oil flies in the air, "
            "The Slugger swings his wooden bat connecting squarely, shattering the bottle into a massive backlit burst "
            "and spray of liquid splashing across the night floodlights toward the porch."
        ),
        "prefix": "SuburbanShakedown_LTX_Clip04"
    },
    {
        "clip_num": 5,
        "input_image": "SuburbanShakedown_Clip05.png",
        "title": "Safe at Home",
        "prompt": (
            "Cinematic handheld tracking camera. The Host slips on the wet porch steps against the brick wall, "
            "frantically wiping thick fluid off his suit jacket lapel in frustration and shock, "
            "The Inmate inside the iron cage in the background nods slowly with calm satisfaction."
        ),
        "prefix": "SuburbanShakedown_LTX_Clip05"
    }
]

def build_ltx_workflow(image_name: str, positive_prompt: str, prefix: str, seed: int):
    return {
        "38": {
            "inputs": {
                "clip_name": "umt5_xxl_fp16.safetensors",
                "type": "ltxv"
            },
            "class_type": "CLIPLoader"
        },
        "44": {
            "inputs": {
                "ckpt_name": "ltx-video-2b-v0.9.1.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "6": {
            "inputs": {
                "text": positive_prompt,
                "clip": ["38", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, fused fingers, bad anatomy, weird hand, ugly",
                "clip": ["38", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "69": {
            "inputs": {
                "stg_mode": 25,
                "frame_rate": 24,
                "positive": ["6", 0],
                "negative": ["7", 0]
            },
            "class_type": "LTXVConditioning"
        },
        "78": {
            "inputs": {
                "image": image_name
            },
            "class_type": "LoadImage"
        },
        "77": {
            "inputs": {
                "width": 768,
                "height": 512,
                "length": 97,
                "batch_size": 1,
                "strength": 0.85,
                "positive": ["69", 0],
                "negative": ["69", 1],
                "vae": ["44", 2],
                "image": ["78", 0]
            },
            "class_type": "LTXVImgToVideo"
        },
        "71": {
            "inputs": {
                "steps": 25,
                "max_shift": 2.05,
                "base_shift": 0.95,
                "stretch": True,
                "terminal": 0.1,
                "latent": ["77", 2]
            },
            "class_type": "LTXVScheduler"
        },
        "73": {
            "inputs": {
                "sampler_name": "euler"
            },
            "class_type": "KSamplerSelect"
        },
        "72": {
            "inputs": {
                "add_noise": True,
                "noise_seed": seed,
                "cfg": 3.0,
                "model": ["44", 0],
                "positive": ["77", 0],
                "negative": ["77", 1],
                "sampler": ["73", 0],
                "sigmas": ["71", 0],
                "latent_image": ["77", 2]
            },
            "class_type": "SamplerCustom"
        },
        "8": {
            "inputs": {
                "samples": ["72", 0],
                "vae": ["44", 2]
            },
            "class_type": "VAEDecode"
        },
        "41": {
            "inputs": {
                "frame_rate": 24,
                "loop_count": 0,
                "filename_prefix": prefix,
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
                "images": ["8", 0]
            },
            "class_type": "VHS_VideoCombine"
        }
    }

def queue_prompt(prompt_dict):
    payload = json.dumps({"prompt": prompt_dict, "client_id": "suburban_ltx_orchestrator"}).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_SERVER}/prompt", data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    print("=" * 65)
    print("SUBURBAN SHAKEDOWN - LTX-Video (Image-to-Video) Pipeline")
    print("Target Server: http://127.0.0.1:8189")
    print("Model: ltx-video-2b-v0.9.1.safetensors + umt5_xxl_fp16.safetensors")
    print("Format: H.264 MP4 @ 24fps (768x512, 97 frames)")
    print("=" * 65)

    prompt_ids = []
    for sc in SCENE_PROMPTS:
        seed = random.randint(100000000000, 999999999999)
        wf = build_ltx_workflow(sc["input_image"], sc["prompt"], sc["prefix"], seed)
        res = queue_prompt(wf)
        pid = res.get("prompt_id")
        prompt_ids.append((sc["clip_num"], sc["title"], pid))
        print(f"Queued Video Clip {sc['clip_num']}: '{sc['title']}' [Anchor: {sc['input_image']}] -> Prompt ID: {pid}")
        time.sleep(0.3)

    print("\nAll 5 video scenes successfully queued into LTX-Video!")

if __name__ == "__main__":
    main()
