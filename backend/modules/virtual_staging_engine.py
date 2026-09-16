import asyncio
import base64
import os
import random
import requests
from bullshit_memory import global_ssd_ram

COMFY_URL = "http://127.0.0.1:8189"

# --- Model presence checks ---
MODELS_BASE = os.path.join(
    os.path.dirname(__file__), "..", "..", "ComfyUI", "ComfyUI", "models"
)


def _model_exists(*path_parts) -> bool:
    return os.path.isfile(os.path.join(MODELS_BASE, *path_parts))


def _detect_pipeline() -> str:
    """
    Auto-detects which pipeline to use based on available models.
    Priority: FLUX.1 > SDXL
    """
    flux_ready = all(
        [
            _model_exists("unet", "z_image_turbo_bf16.safetensors"),
            _model_exists("clip", "clip_l.safetensors"),  # FLUX requires clip_l
            _model_exists("vae", "ae.safetensors"),
        ]
    )
    if flux_ready:
        return "flux"
    return "sdxl"


def _has_upscaler() -> bool:
    return _model_exists("upscale_models", "4x-UltraSharp.pth")


def _has_flux_depth_controlnet() -> bool:
    return _model_exists("controlnet", "flux_depth_controlnet.safetensors")


def _has_canny_controlnet() -> bool:
    return _model_exists(
        "controlnet", "control-lora-canny-rank256.safetensors"
    ) or _model_exists("controlnet", "canny.safetensors")


def _build_sdxl_payload(comfy_filename: str, prompt: str, negative: str) -> dict:
    """
    Current working SDXL + ControlNet-Depth pipeline.
    Appends 4x-UltraSharp upscaler if model is present.
    """
    seed = random.randint(1, 100_000_000_000_000)
    use_upscaler = _has_upscaler()
    use_canny = _has_canny_controlnet()

    nodes = {
        # Checkpoint
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        },
        # Positive prompt
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": prompt},
        },
        # Negative prompt
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["1", 1], "text": negative},
        },
        # Load input image
        "4": {"class_type": "LoadImage", "inputs": {"image": comfy_filename}},
        # ControlNet loader (Depth)
        "5": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "control-lora-depth-rank256.safetensors"},
        },
        # SDXL ZSNRm (ModelSamplingDiscrete)
        "6": {
            "class_type": "ModelSamplingDiscrete",
            "inputs": {"model": ["1", 0], "sampling": "eps", "zsnr": False},
        },
        # ControlNet apply (Depth)
        "7": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["2", 0],
                "negative": ["3", 0],
                "control_net": ["5", 0],
                "image": ["4", 0],
                "strength": 0.80,
                "start_percent": 0.0,
                "end_percent": 0.85,
            },
        },
        # Empty latent
        "8": {
            "class_type": "EmptyLatentImage",
            "inputs": {"batch_size": 1, "height": 1024, "width": 1024},
        },
        # KSampler — SDXL optimal params
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["6", 0],
                "positive": ["7", 0],
                "negative": ["7", 1],
                "latent_image": ["8", 0],
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "steps": 30,
                "cfg": 7.0,
                "denoise": 1.0,
                "seed": seed,
            },
        },
        # VAE Decode
        "10": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["9", 0], "vae": ["1", 2]},
        },
    }

    if use_canny:
        # ControlNet loader (Canny) - Dual CN chaining
        nodes["7_1"] = {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": (
                    "control-lora-canny-rank256.safetensors"
                    if _model_exists(
                        "controlnet", "control-lora-canny-rank256.safetensors"
                    )
                    else "canny.safetensors"
                )
            },
        }
        # ControlNet apply (Canny)
        nodes["7_2"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["7", 0],
                "negative": ["7", 1],
                "control_net": ["7_1", 0],
                "image": ["4", 0],
                "strength": 0.45,
                "start_percent": 0.0,
                "end_percent": 0.70,
            },
        }
        # Connect KSampler to the chained Canny output
        nodes["9"]["inputs"]["positive"] = ["7_2", 0]
        nodes["9"]["inputs"]["negative"] = ["7_2", 1]

    if use_upscaler:
        print("[PIPELINE] SDXL + ControlNet-Depth + 4x-UltraSharp Upscaler")
        nodes["11"] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "4x-UltraSharp.pth"},
        }
        nodes["12"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["11", 0], "image": ["10", 0]},
        }
        nodes["13"] = {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "VirtualStaged_SDXL_4x", "images": ["12", 0]},
        }
    else:
        print("[PIPELINE] SDXL + ControlNet-Depth (no upscaler)")
        nodes["11"] = {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "VirtualStaged_SDXL", "images": ["10", 0]},
        }

    return {"prompt": nodes}


def _build_flux_payload(comfy_filename: str, prompt: str) -> dict:
    """
    FLUX.1 [dev] FP8 pipeline with optional Depth ControlNet and 4x-UltraSharp upscaler.
    Phase 1-4 from the FLUX optimization spec.
    """
    seed = random.randint(1, 100_000_000_000_000)
    use_upscaler = _has_upscaler()
    use_depth_cn = _has_flux_depth_controlnet()

    print(
        f"[PIPELINE] Z-Image FLUX Turbo | DepthCN={use_depth_cn} | Upscaler={use_upscaler}"
    )

    nodes = {
        # PHASE 1: Load UNET
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "z_image_turbo_bf16.safetensors",
                "weight_dtype": "default",
            },
        },
        # PHASE 1: Load CLIP (Qwen)
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux"},
        },
        # PHASE 1: Load VAE
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        # Positive CLIP encode
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["2", 0], "text": prompt},
        },
        # Empty latent (FLUX native res)
        "5": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        # Load input room image for ControlNet
        "6": {"class_type": "LoadImage", "inputs": {"image": comfy_filename}},
    }

    # PHASE 2: ControlNets (Dual Depth + Canny)
    positive_conditioning = ["4", 0]
    if use_depth_cn:
        nodes["7"] = {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "flux_depth_controlnet.safetensors"},
        }
        nodes["8"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": positive_conditioning,
                "negative": ["4", 0],
                "control_net": ["7", 0],
                "image": ["6", 0],
                "strength": 0.75,
                "start_percent": 0.0,
                "end_percent": 0.85,
                "vae": ["3", 0],
            },
        }
        positive_conditioning = ["8", 0]

    use_canny = _has_canny_controlnet()
    if use_canny:
        nodes["8_1"] = {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "control-lora-canny-rank256.safetensors"},
        }
        nodes["8_2"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": positive_conditioning,
                "negative": ["4", 0],
                "control_net": ["8_1", 0],
                "image": ["6", 0],
                "strength": 0.50,
                "start_percent": 0.0,
                "end_percent": 0.75,
                "vae": ["3", 0],
            },
        }
        positive_conditioning = ["8_2", 0]

    # PHASE 3: KSampler — AuraFlow Turbo optimal params
    # AuraFlow requires shift=5.0 to remove granular noise
    nodes["8_5"] = {
        "class_type": "ModelSamplingAuraFlow",
        "inputs": {"model": ["1", 0], "shift": 5.0},
    }

    nodes["9"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["8_5", 0],
            "positive": positive_conditioning,
            "negative": ["4", 0],  # Negative prompt via Qwen
            "latent_image": ["5", 0],
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "steps": 10,
            "cfg": 1.5,
            "denoise": 1.0,
            "seed": seed,
        },
    }

    # VAE Decode
    nodes["10"] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["9", 0], "vae": ["3", 0]},
    }

    # PHASE 4: Upscaler
    if use_upscaler:
        nodes["11"] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "4x-UltraSharp.pth"},
        }
        nodes["12"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["11", 0], "image": ["10", 0]},
        }
        # Phase 4: Hi-res fix pass (denoising 0.25-0.35 to add micro-detail without macro changes)
        nodes["13"] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["12", 0], "vae": ["3", 0]},
        }
        nodes["14"] = {
            "class_type": "KSampler",
            "inputs": {
                "model": ["8_5", 0],
                "positive": positive_conditioning,
                "negative": ["4", 0],
                "latent_image": ["13", 0],
                "sampler_name": "euler",
                "scheduler": "sgm_uniform",
                "steps": 8,
                "cfg": 1.5,
                "denoise": 0.30,
                "seed": seed + 1,
            },
        }
        nodes["15"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["14", 0], "vae": ["3", 0]},
        }
        nodes["16"] = {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "VirtualStaged_FLUX_4x", "images": ["15", 0]},
        }
    else:
        nodes["11"] = {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "VirtualStaged_FLUX", "images": ["10", 0]},
        }

    return {"prompt": nodes}


async def generate_virtual_staging(
    image_base64: str, style: str, room_type: str, custom_prompt: str = ""
):
    """
    Routes to FLUX.1 FP8 or SDXL pipeline based on available models.
    Automatically appends 4x-UltraSharp upscaler when model is present.
    """
    pipeline = _detect_pipeline()
    print(
        f"[Virtual Staging] Detected pipeline: {pipeline.upper()} | Room: {room_type} | Style: {style}"
    )

    try:
        # [SSD Paging] Immediately drop the massive payload from live RAM
        payload_id = f"vstaging_img_{id(image_base64)}"
        global_ssd_ram.page_out(payload_id, {"b64": image_base64})
        del image_base64  # Evict

        # 1. Decode and save input image (JIT retrieval from SSD)
        paged_data = global_ssd_ram.page_in(payload_id)
        raw_b64 = paged_data.get("b64", "")
        if "," in raw_b64:
            _, encoded = raw_b64.split(",", 1)
        else:
            encoded = raw_b64

        temp_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "scratch", "temp_upload.png"
        )
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(encoded))

        # 2. Upload image to ComfyUI input folder
        with open(temp_path, "rb") as f:
            res = requests.post(
                f"{COMFY_URL}/upload/image",
                files={"image": ("temp_upload.png", f)},
                timeout=30,
            )
            res.raise_for_status()
            comfy_filename = res.json().get("name")

        if not comfy_filename:
            raise ValueError(
                "ComfyUI did not return a filename for the uploaded image."
            )

        # 3. Build prompt
        prompt = (
            f"A stunning {style} {room_type}, beautifully furnished, highly detailed, "
            f"photorealistic, 8k architectural photography, beautiful natural lighting, cinematic composition"
        )
        if custom_prompt.strip():
            prompt += f", {custom_prompt.strip()}"

        negative = "blurry, low quality, distorted furniture, bad architecture, empty room, watermark, text, oversaturated"

        # 4. Select and build payload
        if pipeline == "flux":
            comfy_payload = _build_flux_payload(comfy_filename, prompt)
        else:
            comfy_payload = _build_sdxl_payload(comfy_filename, prompt, negative)

        # 5. Submit job
        job_res = requests.post(f"{COMFY_URL}/prompt", json=comfy_payload, timeout=30)
        job_res.raise_for_status()
        prompt_id = job_res.json()["prompt_id"]
        print(f"[ComfyUI] Job submitted. ID: {prompt_id}")

        # 6. Poll for completion (max 5 minutes for upscaled generations)
        output_filename = None
        for i in range(300):
            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
            history_data = history_res.json()

            if prompt_id in history_data:
                job_data = history_data[prompt_id]
                # Check for errors first
                if job_data.get("status", {}).get("status_str") == "error":
                    msgs = job_data.get("status", {}).get("messages", [])
                    raise Exception(f"ComfyUI job errored: {msgs}")

                outputs = job_data.get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        output_filename = node_output["images"][0]["filename"]
                        break
                if output_filename:
                    break

            await asyncio.sleep(1)

        if not output_filename:
            raise Exception("ComfyUI job timed out after 5 minutes.")

        # 7. Retrieve generated image as base64
        img_res = requests.get(
            f"{COMFY_URL}/view?filename={output_filename}&subfolder=&type=output",
            timeout=60,
        )
        img_res.raise_for_status()
        final_b64 = base64.b64encode(img_res.content).decode("utf-8")
        staged_image_url = f"data:image/png;base64,{final_b64}"

        print(f"[ComfyUI] Generation complete! Pipeline: {pipeline.upper()}")

        return {
            "success": True,
            "pipeline_used": pipeline,
            "original_room_type": room_type,
            "applied_style": style,
            "staged_image_url": staged_image_url,
        }

    except Exception as e:
        print(f"[ComfyUI] Failed ({pipeline}): {e}. Returning placeholder.")
        return {
            "success": False,
            "pipeline_used": pipeline,
            "original_room_type": room_type,
            "applied_style": style,
            "error": str(e),
            "staged_image_url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80",
        }


def _build_wan2_video_payload(comfy_filename: str, prompt: str) -> dict:
    """
    Wan2.2 14B Image-to-Video Pipeline using ComfyUI.
    Uses LightX2V 4-step LoRA for rapid generation.
    """
    seed = random.randint(1, 100_000_000_000_000)

    nodes = {
        # 1. Load Wan2.2 UNET
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                "weight_dtype": "fp8_e4m3fn",
            },
        },
        # 2. Load LightX2V LoRA
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "lora_name": "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
                "strength_model": 1.0,
                "model": ["1", 0],
            },
        },
        # 3. Load Text Encoder
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "wan",
            },
        },
        # 4. Load VAE
        "4": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "wan_2.1_vae.safetensors"},
        },
        # 5. Load Input Image
        "5": {"class_type": "LoadImage", "inputs": {"image": comfy_filename}},
        # 6. CLIP Text Encode Positive
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["3", 0], "text": prompt},
        },
        # 6_neg. CLIP Text Encode Negative
        "6_neg": {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": ["3", 0], "text": ""},
        },
        # 7. Wan Video Setup
        "7": {
            "class_type": "WanImageToVideo",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["6_neg", 0],
                "vae": ["4", 0],
                "width": 832,
                "height": 480,
                "length": 33,
                "batch_size": 1,
                "start_image": ["5", 0],
            },
        },
        # 8. KSampler
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["2", 0],
                "positive": ["7", 0],
                "negative": ["7", 1],
                "latent_image": ["7", 2],
                "sampler_name": "euler",
                "scheduler": "sgm_uniform",
                "steps": 4,
                "cfg": 1.5,
                "denoise": 1.0,
                "seed": seed,
            },
        },
        # 9. VAE Decode
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["8", 0], "vae": ["4", 0]},
        },
        # 9.5 Convert to Video format
        "95": {"class_type": "CreateVideo", "inputs": {"images": ["9", 0], "fps": 16}},
        # 10. Save Video
        "10": {
            "class_type": "SaveVideo",
            "inputs": {
                "filename_prefix": "Wan2_Tour",
                "format": "mp4",
                "codec": "h264",
                "video": ["95", 0],
            },
        },
    }
    return {"prompt": nodes}


async def generate_video_tour(image_base64: str, custom_prompt: str = ""):
    """
    Generates a photorealistic video tour pan using Wan2.2 14B.
    """
    print(f"[Virtual Staging] Generating Video Tour with Wan2.2 14B")
    try:
        # [SSD Paging] Immediately drop the massive payload from live RAM
        payload_id = f"vtour_img_{id(image_base64)}"
        global_ssd_ram.page_out(payload_id, {"b64": image_base64})
        del image_base64  # Evict

        # JIT retrieval from SSD
        paged_data = global_ssd_ram.page_in(payload_id)
        raw_b64 = paged_data.get("b64", "")
        if "," in raw_b64:
            _, encoded = raw_b64.split(",", 1)
        else:
            encoded = raw_b64

        temp_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "scratch", "temp_video_input.png"
        )
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(encoded))

        with open(temp_path, "rb") as f:
            res = requests.post(
                f"{COMFY_URL}/upload/image",
                files={"image": ("temp_video_input.png", f)},
                timeout=30,
            )
            res.raise_for_status()
            comfy_filename = res.json().get("name")

        if not comfy_filename:
            raise ValueError(
                "ComfyUI did not return a filename for the uploaded image."
            )

        prompt = (
            f"A slow, smooth, cinematic camera pan across a beautifully furnished room, "
            f"highly detailed, photorealistic, 4k architectural photography, beautiful natural lighting. "
        )
        if custom_prompt.strip():
            prompt += f" {custom_prompt.strip()}"

        comfy_payload = _build_wan2_video_payload(comfy_filename, prompt)
        job_res = requests.post(f"{COMFY_URL}/prompt", json=comfy_payload, timeout=120)
        job_res.raise_for_status()
        prompt_id = job_res.json()["prompt_id"]
        print(f"[ComfyUI] Video Job submitted. ID: {prompt_id}")

        output_filename = None
        for i in range(600):  # Allow 10 mins for video
            history_res = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10)
            history_data = history_res.json()

            if prompt_id in history_data:
                job_data = history_data[prompt_id]
                if job_data.get("status", {}).get("status_str") == "error":
                    msgs = job_data.get("status", {}).get("messages", [])
                    raise Exception(f"ComfyUI video job errored: {msgs}")

                outputs = job_data.get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "videos" in node_output or "images" in node_output:
                        file_list = node_output.get("videos") or node_output.get(
                            "images"
                        )
                        output_filename = file_list[0]["filename"]
                        break
                if output_filename:
                    break
            await asyncio.sleep(1)

        if not output_filename:
            raise Exception("ComfyUI video job timed out after 10 minutes.")

        # Base64 the video for the API response.
        vid_res = requests.get(
            f"{COMFY_URL}/view?filename={output_filename}&subfolder=&type=output",
            timeout=120,
        )
        vid_res.raise_for_status()
        final_b64 = base64.b64encode(vid_res.content).decode("utf-8")
        staged_video_url = f"data:video/mp4;base64,{final_b64}"

        print(f"[ComfyUI] Video Generation complete!")
        return {
            "success": True,
            "pipeline_used": "wan2.2",
            "staged_video_url": staged_video_url,
        }

    except Exception as e:
        print(f"[ComfyUI] Video Failed: {e}.")
        return {"success": False, "error": str(e), "staged_video_url": None}
