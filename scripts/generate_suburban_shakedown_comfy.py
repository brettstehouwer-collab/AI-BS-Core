"""
Script to queue the 5 Suburban Shakedown scenes into ComfyUI (Port 8189)
Uses SDXL base checkpoint with 1024x576 (16:9 cinematic widescreen aspect ratio)
"""

import json
import urllib.request
import urllib.parse
import time
import random

COMFYUI_SERVER = "http://127.0.0.1:8189"

SCENE_DNA = (
    "Cinematic movie still, realistic 4K, dramatic movie lighting. "
    "Setting: manicured suburban front yard at night with house number 246 on the brick porch, "
    "blinding stadium floodlights casting harsh shadows across grass. "
)

SCENES = [
    {
        "clip_num": 1,
        "title": "The SWAT Team Warning",
        "prompt": (
            SCENE_DNA +
            "Wide cinematic shot from front yard looking at brick porch. "
            "The Host, a man with long hair, neat trimmed beard, tailored black suit, "
            "steps forward under harsh stadium floodlights, throwing arms wide in dramatic exasperated welcoming gesture, "
            "talking intensely with shocked expression."
        ),
        "prefix": "SuburbanShakedown_Clip01"
    },
    {
        "clip_num": 2,
        "title": "Frictionless Entry",
        "prompt": (
            SCENE_DNA +
            "Medium shot of a giant 6-foot freestanding rusty iron jail cell sitting on lawn grass. "
            "A giant inflatable nutcracker lawn ornament lies face down deflating slowly wedged between cage bars. "
            "Inside the iron cell, The Inmate in an orange prison jumpsuit and dark designer sunglasses "
            "grips the bars, tilting sunglasses down nose, deadpan holding up a large bottle of baby oil with both hands."
        ),
        "prefix": "SuburbanShakedown_Clip02"
    },
    {
        "clip_num": 3,
        "title": "Fastball Incoming",
        "prompt": (
            SCENE_DNA +
            "Low angle dynamic shot following The Slugger on concrete walkway. "
            "A man in full classic baseball uniform and helmet aggressively digging cleats into landscaping mulch, "
            "tapping wooden baseball bat against cleats, stepping into intense wound-up batting stance looking toward porch."
        ),
        "prefix": "SuburbanShakedown_Clip03"
    },
    {
        "clip_num": 4,
        "title": "The Wet Explosion",
        "prompt": (
            SCENE_DNA +
            "Slow-motion high action cinematic shot. "
            "The Inmate tosses clear plastic bottle into the air from between iron bars. "
            "The Slugger executes explosive full swing with wooden bat connecting perfectly, "
            "shattering bottle into dramatic backlit spray of clear liquid exploding through night floodlights towards porch."
        ),
        "prefix": "SuburbanShakedown_Clip04"
    },
    {
        "clip_num": 5,
        "title": "Safe at Home",
        "prompt": (
            SCENE_DNA +
            "Handheld camera style shot. "
            "The Host scrambled against brick wall of porch, slipping on steps, frantically wiping thick fluid off black suit lapel in anger. "
            "In background, The Inmate inside the iron cell nodding calmly holding bottle tight. Dramatic cinematic atmosphere."
        ),
        "prefix": "SuburbanShakedown_Clip05"
    }
]

def build_workflow(positive_prompt: str, prefix: str, seed: int):
    return {
        "3": {
            "inputs": {
                "seed": seed,
                "steps": 25,
                "cfg": 7.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": 1024,
                "height": 576,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": positive_prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": "blurry, low quality, cartoon, anime, 3d render, watermark, text, signature, distorted, ugly, bad anatomy",
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": prefix,
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

def queue_prompt(prompt_dict):
    payload = json.dumps({"prompt": prompt_dict, "client_id": "suburban_shakedown_builder"}).encode('utf-8')
    req = urllib.request.Request(f"{COMFYUI_SERVER}/prompt", data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def main():
    print("=" * 60)
    print("SUBURBAN SHAKEDOWN - ComfyUI Cinematic Scene Generator")
    print("Target Server: http://127.0.0.1:8189")
    print("Model: sd_xl_base_1.0.safetensors | Resolution: 1024x576 (16:9)")
    print("=" * 60)

    prompt_ids = []
    for sc in SCENES:
        seed = random.randint(100000000000, 999999999999)
        wf = build_workflow(sc["prompt"], sc["prefix"], seed)
        res = queue_prompt(wf)
        pid = res.get("prompt_id")
        prompt_ids.append((sc["clip_num"], sc["title"], pid))
        print(f"Queued Clip {sc['clip_num']}: {sc['title']} -> Prompt ID: {pid}")
        time.sleep(0.3)

    print("\nAll 5 scenes successfully queued in ComfyUI!")
    return prompt_ids

if __name__ == "__main__":
    main()
