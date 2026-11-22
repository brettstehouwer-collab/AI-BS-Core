"""
ComfyUI Workflow Graph Builders for AI-BS Creative Workspace.
Generates fully-specified ComfyUI API-compatible node execution graphs
with exact node classes, exact inputs, and zero ambiguous title matching.
"""

from typing import Dict, Any, Optional, Tuple

RESOLUTION_MAP = {
    "4K": {
        "16:9": (3840, 2160, 1280, 720),
        "1:1": (4096, 4096, 1024, 1024),
        "9:16": (2160, 3840, 720, 1280),
        "21:9": (5120, 2160, 1344, 576),
        "4:3": (3840, 2880, 1152, 864),
        "3:4": (2880, 3840, 864, 1152),
    },
    "8K": {
        "16:9": (7680, 4320, 1280, 720),
        "1:1": (8192, 8192, 1024, 1024),
        "9:16": (4320, 7680, 720, 1280),
        "21:9": (10240, 4320, 1344, 576),
        "4:3": (7680, 5760, 1152, 864),
        "3:4": (5760, 7680, 864, 1152),
    },
    "16K": {
        "16:9": (15360, 8640, 1280, 720),
        "1:1": (16384, 16384, 1024, 1024),
        "9:16": (8640, 15360, 720, 1280),
        "21:9": (16384, 6880, 1344, 576),
        "4:3": (15360, 11520, 1152, 864),
        "3:4": (11520, 15360, 864, 1152),
    }
}

def get_resolution_specs(tier: str = "4K", aspect_ratio: str = "16:9") -> Tuple[int, int, int, int]:
    """
    Returns (target_w, target_h, latent_w, latent_h) for given tier and aspect ratio.
    Latent sizes are strictly budgeted to optimal base buckets (1024x1024 budget) to prevent
    CUDA OOM and compositional repetition, while final outputs guarantee 4K, 8K, or 16K.
    """
    tier_upper = tier.upper() if tier else "4K"
    aspect = aspect_ratio if aspect_ratio else "16:9"
    tier_data = RESOLUTION_MAP.get(tier_upper, RESOLUTION_MAP["4K"])
    return tier_data.get(aspect, tier_data["16:9"])


def build_sdxl_txt2img_graph(
    prompt: str,
    negative_prompt: str = "blurry, low quality, distorted, bad anatomy, deformed, disfigured",
    width: Optional[int] = None,
    height: Optional[int] = None,
    target_tier: str = "4K",
    aspect_ratio: str = "16:9",
    steps: int = 25,
    cfg: float = 7.5,
    sampler_name: str = "euler_ancestral",
    scheduler: str = "karras",
    seed: int = 42,
    batch_size: int = 1,
    prefix: str = "AIBS_SDXL"
) -> Dict[str, Any]:
    """Generates SDXL base text-to-image workflow graph scaled directly to 4K/8K/16K Ultra-HD."""
    target_w, target_h, latent_w, latent_h = get_resolution_specs(target_tier, aspect_ratio)
    if width and height and max(width, height) <= 1536:
        latent_w, latent_h = width, height

    graph = {
        "4": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": latent_w,
                "height": latent_h,
                "batch_size": batch_size
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        }
    }

    # Ultra-Resolution 4K/8K/16K Chain (4x-UltraSharp spatial model pass + Lanczos resize)
    if target_tier in ["4K", "8K", "16K"]:
        graph["20"] = {
            "inputs": {
                "model_name": "4x-UltraSharp.pth"
            },
            "class_type": "UpscaleModelLoader"
        }
        graph["21"] = {
            "inputs": {
                "upscale_model": ["20", 0],
                "image": ["8", 0]
            },
            "class_type": "ImageUpscaleWithModel"
        }
        graph["22"] = {
            "inputs": {
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "disabled",
                "image": ["21", 0]
            },
            "class_type": "ImageScale"
        }
        save_source = ["22", 0]
        final_prefix = f"{prefix}_{target_tier}"
    else:
        save_source = ["8", 0]
        final_prefix = prefix

    graph["9"] = {
        "inputs": {
            "filename_prefix": final_prefix,
            "images": save_source
        },
        "class_type": "SaveImage"
    }

    return graph


def build_sd15_txt2img_graph(
    prompt: str,
    negative_prompt: str = "blurry, low quality, bad anatomy, deformed",
    width: Optional[int] = None,
    height: Optional[int] = None,
    target_tier: str = "4K",
    aspect_ratio: str = "16:9",
    steps: int = 20,
    cfg: float = 7.0,
    sampler_name: str = "euler",
    scheduler: str = "normal",
    seed: int = 42,
    batch_size: int = 1,
    prefix: str = "AIBS_SD15"
) -> Dict[str, Any]:
    """Generates standard SD 1.5 text-to-image workflow scaled directly to 4K/8K/16K Ultra-HD."""
    target_w, target_h, latent_w, latent_h = get_resolution_specs(target_tier, aspect_ratio)
    # SD 1.5 operates natively on 512-class latents
    latent_w = max(512, (latent_w // 2) // 64 * 64)
    latent_h = max(512, (latent_h // 2) // 64 * 64)
    if width and height and max(width, height) <= 768:
        latent_w, latent_h = width, height

    graph = {
        "4": {
            "inputs": {
                "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": latent_w,
                "height": latent_h,
                "batch_size": batch_size
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        }
    }

    if target_tier in ["4K", "8K", "16K"]:
        graph["20"] = {
            "inputs": {
                "model_name": "4x-UltraSharp.pth"
            },
            "class_type": "UpscaleModelLoader"
        }
        graph["21"] = {
            "inputs": {
                "upscale_model": ["20", 0],
                "image": ["8", 0]
            },
            "class_type": "ImageUpscaleWithModel"
        }
        graph["22"] = {
            "inputs": {
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "disabled",
                "image": ["21", 0]
            },
            "class_type": "ImageScale"
        }
        save_source = ["22", 0]
        final_prefix = f"{prefix}_{target_tier}"
    else:
        save_source = ["8", 0]
        final_prefix = prefix

    graph["9"] = {
        "inputs": {
            "filename_prefix": final_prefix,
            "images": save_source
        },
        "class_type": "SaveImage"
    }

    return graph


def build_two_stage_upscale_graph(
    image_filename: str,
    prompt: str = "masterpiece, sharp focus, ultra-detailed textures, photorealistic, 4k",
    negative_prompt: str = "blurry, low quality, artifacts, smooth plastic skin, noise",
    upscale_model_name: str = "4x-UltraSharp.pth",
    target_tier: str = "4K",
    aspect_ratio: str = "16:9",
    denoise: float = 0.15,
    steps: int = 25,
    cfg: float = 6.0,
    seed: int = 42,
    prefix: str = "AIBS_Upscale"
) -> Dict[str, Any]:
    """
    Module 2 Refinery:
    Stage 1: Spatial model upscale (4x-UltraSharp)
    Stage 2: Ultimate SD Upscale tiled diffusion texture injection pass
    Stage 3: Precision lanczos scale to target ultra-resolution (4K / 8K / 16K)
    """
    target_w, target_h, _, _ = get_resolution_specs(target_tier, aspect_ratio)

    return {
        "1": {
            "inputs": {
                "image": image_filename
            },
            "class_type": "LoadImage"
        },
        "2": {
            "inputs": {
                "model_name": upscale_model_name
            },
            "class_type": "UpscaleModelLoader"
        },
        "4": {
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "6": {
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "10": {
            "inputs": {
                "image": ["1", 0],
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "vae": ["4", 2],
                "upscale_by": 2.0,
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": denoise,
                "upscale_model": ["2", 0],
                "mode_type": "Linear",
                "tile_width": 1024,
                "tile_height": 1024,
                "mask_blur": 16,
                "tile_padding": 32,
                "seam_fix_mode": "None",
                "seam_fix_denoise": 0.05,
                "seam_fix_width": 64,
                "seam_fix_mask_blur": 8,
                "seam_fix_padding": 16,
                "force_uniform_tiles": True,
                "tiled_decode": True,
                "batch_size": 1
            },
            "class_type": "UltimateSDUpscale"
        },
        "22": {
            "inputs": {
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "disabled",
                "image": ["10", 0]
            },
            "class_type": "ImageScale"
        },
        "12": {
            "inputs": {
                "filename_prefix": f"{prefix}_{target_tier}",
                "images": ["22", 0]
            },
            "class_type": "SaveImage"
        }
    }


def build_ltx_img2video_graph(
    image_filename: str,
    prompt: str,
    negative_prompt: str = "low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, bad anatomy, ugly",
    width: int = 768,
    height: int = 512,
    target_tier: str = "4K",
    aspect_ratio: str = "16:9",
    length: int = 97,
    fps: int = 24,
    steps: int = 25,
    cfg: float = 3.0,
    strength: float = 0.85,
    seed: int = 42,
    prefix: str = "AIBS_LTX_Video"
) -> Dict[str, Any]:
    """Generates LTX-Video 2B Image-to-Video generation graph with 4K/8K/16K Ultra-HD video output."""
    graph = {
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
                "text": prompt,
                "clip": ["38", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["38", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "69": {
            "inputs": {
                "stg_mode": 25,
                "frame_rate": fps,
                "positive": ["6", 0],
                "negative": ["7", 0]
            },
            "class_type": "LTXVConditioning"
        },
        "78": {
            "inputs": {
                "image": image_filename
            },
            "class_type": "LoadImage"
        },
        "77": {
            "inputs": {
                "width": width,
                "height": height,
                "length": length,
                "batch_size": 1,
                "strength": strength,
                "positive": ["69", 0],
                "negative": ["69", 1],
                "vae": ["44", 2],
                "image": ["78", 0]
            },
            "class_type": "LTXVImgToVideo"
        },
        "71": {
            "inputs": {
                "steps": steps,
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
                "cfg": cfg,
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
        }
    }

    video_source = ["8", 0]
    final_prefix = prefix
    if target_tier in ["4K", "8K", "16K"]:
        target_w, target_h, _, _ = get_resolution_specs(target_tier, aspect_ratio)
        # Stage 1: Neural Spatial Detail Pass (4x-UltraSharp)
        graph["81"] = {
            "inputs": {
                "model_name": "4x-UltraSharp.pth"
            },
            "class_type": "UpscaleModelLoader"
        }
        graph["82"] = {
            "inputs": {
                "upscale_model": ["81", 0],
                "image": ["8", 0]
            },
            "class_type": "ImageUpscaleWithModel"
        }
        # Stage 2: Precision Lanczos Clamping
        graph["80"] = {
            "inputs": {
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "disabled",
                "image": ["82", 0]
            },
            "class_type": "ImageScale"
        }
        video_source = ["80", 0]
        final_prefix = f"{prefix}_{target_tier}"

        if target_tier == "16K":
            # 16K Master PNG Sequence
            graph["85"] = {
                "inputs": {
                    "filename_prefix": f"{prefix}_16K_Master/frame",
                    "images": ["80", 0]
                },
                "class_type": "SaveImage"
            }
            # Companion 4K Proxy
            proxy_w, proxy_h, _, _ = get_resolution_specs("4K", aspect_ratio)
            graph["86"] = {
                "inputs": {
                    "upscale_method": "lanczos",
                    "width": proxy_w,
                    "height": proxy_h,
                    "crop": "disabled",
                    "image": ["80", 0]
                },
                "class_type": "ImageScale"
            }
            graph["41"] = {
                "inputs": {
                    "frame_rate": fps,
                    "loop_count": 0,
                    "filename_prefix": f"{prefix}_16K_Proxy_4K",
                    "format": "video/h264-mp4",
                    "pingpong": False,
                    "save_output": True,
                    "images": ["86", 0]
                },
                "class_type": "VHS_VideoCombine"
            }
            return graph

    graph["41"] = {
        "inputs": {
            "frame_rate": fps,
            "loop_count": 0,
            "filename_prefix": final_prefix,
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True,
            "images": video_source
        },
        "class_type": "VHS_VideoCombine"
    }

    return graph


def build_wan_video_graph(
    prompt: str,
    negative_prompt: str = "low quality, worst quality, deformed, distorted, disfigured, motion smear, motion artifacts, bad anatomy, ugly",
    image_filename: Optional[str] = None,
    target_tier: str = "4K",
    aspect_ratio: str = "16:9",
    length: int = 81,
    fps: int = 16,
    steps: int = 25,
    cfg: float = 6.0,
    seed: int = 42,
    prefix: str = "AIBS_Wan_Video"
) -> Dict[str, Any]:
    """
    Generates Wan2.1 Video generation graph with 4K/8K/16K Ultra-HD video output.
    Dual Unified Modality:
    - If image_filename is provided -> Image-to-Video via Wan 14B FP8 (wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors)
    - If image_filename is None -> Text-to-Video via Wan 1.3B (wan2.1-t2v-1.3B.safetensors)
    - 4x-UltraSharp neural spatial micro-texture pass + precision Lanczos clamping.
    - Dual-tier 16K output: 16K Master PNG sequence + 4K MP4 preview proxy.
    """
    aspect = aspect_ratio if aspect_ratio else "16:9"
    wan_base_map = {
        "16:9": (832, 480),
        "9:16": (480, 832),
        "1:1": (640, 640),
        "21:9": (960, 416),
        "4:3": (768, 576),
        "3:4": (576, 768)
    }
    base_w, base_h = wan_base_map.get(aspect, (832, 480))

    graph: Dict[str, Any] = {
        "11": {
            "inputs": {
                "model_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "precision": "bf16",
                "load_device": "offload_device",
                "quantization": "disabled"
            },
            "class_type": "LoadWanVideoT5TextEncoder"
        },
        "16": {
            "inputs": {
                "t5": ["11", 0],
                "positive_prompt": prompt,
                "negative_prompt": negative_prompt,
                "force_offload": True,
                "use_disk_cache": False,
                "device": "gpu"
            },
            "class_type": "WanVideoTextEncode"
        },
        "38": {
            "inputs": {
                "model_name": "Wan2_1_VAE_bf16.safetensors",
                "precision": "bf16"
            },
            "class_type": "WanVideoVAELoader"
        }
    }

    is_i2v = bool(image_filename and image_filename.strip())
    if is_i2v:
        graph["22"] = {
            "inputs": {
                "model": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device",
                "attention_mode": "sdpa"
            },
            "class_type": "WanVideoModelLoader"
        }
        graph["40"] = {
            "inputs": {
                "image": image_filename.strip()
            },
            "class_type": "LoadImage"
        }
        graph["37"] = {
            "inputs": {
                "image": ["40", 0],
                "width": base_w,
                "height": base_h,
                "num_frames": length,
                "vae": ["38", 0]
            },
            "class_type": "WanVideoImageToVideo"
        }
        latent_source = ["37", 0]
    else:
        graph["22"] = {
            "inputs": {
                "model": "wan2.1-t2v-1.3B.safetensors",
                "base_precision": "bf16",
                "quantization": "disabled",
                "load_device": "offload_device",
                "attention_mode": "sdpa"
            },
            "class_type": "WanVideoModelLoader"
        }
        graph["37"] = {
            "inputs": {
                "width": base_w,
                "height": base_h,
                "num_frames": length
            },
            "class_type": "WanVideoEmptyEmbeds"
        }
        latent_source = ["37", 0]

    graph["27"] = {
        "inputs": {
            "model": ["22", 0],
            "image_embeds": latent_source,
            "text_embeds": ["16", 0],
            "steps": steps,
            "cfg": cfg,
            "shift": 5.0,
            "seed": seed,
            "force_offload": "fixed",
            "scheduler": True,
            "riflex_freq_index": "dpm++_sde",
            "denoise_strength": 1.0,
            "batched_cfg": 1,
            "rope_function": False,
            "start_step": "comfy",
            "end_step": 0,
            "add_noise_to_samples": -1
        },
        "class_type": "WanVideoSampler"
    }

    graph["28"] = {
        "inputs": {
            "vae": ["38", 0],
            "samples": ["27", 0],
            "enable_vae_tiling": True,
            "tile_x": 272,
            "tile_y": 272,
            "tile_stride_x": 144,
            "tile_stride_y": 128,
            "normalization": "default"
        },
        "class_type": "WanVideoDecode"
    }

    video_source = ["28", 0]
    final_prefix = prefix
    if target_tier in ["4K", "8K", "16K"]:
        target_w, target_h, _, _ = get_resolution_specs(target_tier, aspect_ratio)
        # Stage 1: Neural Detail Pass (4x-UltraSharp)
        graph["81"] = {
            "inputs": {
                "model_name": "4x-UltraSharp.pth"
            },
            "class_type": "UpscaleModelLoader"
        }
        graph["82"] = {
            "inputs": {
                "upscale_model": ["81", 0],
                "image": ["28", 0]
            },
            "class_type": "ImageUpscaleWithModel"
        }
        # Stage 2: Precision Lanczos Clamping
        graph["80"] = {
            "inputs": {
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "disabled",
                "image": ["82", 0]
            },
            "class_type": "ImageScale"
        }
        video_source = ["80", 0]
        final_prefix = f"{prefix}_{target_tier}"

        if target_tier == "16K":
            # 16K Master PNG Sequence
            graph["85"] = {
                "inputs": {
                    "filename_prefix": f"{prefix}_16K_Master/frame",
                    "images": ["80", 0]
                },
                "class_type": "SaveImage"
            }
            # Companion 4K Proxy
            proxy_w, proxy_h, _, _ = get_resolution_specs("4K", aspect_ratio)
            graph["86"] = {
                "inputs": {
                    "upscale_method": "lanczos",
                    "width": proxy_w,
                    "height": proxy_h,
                    "crop": "disabled",
                    "image": ["80", 0]
                },
                "class_type": "ImageScale"
            }
            graph["30"] = {
                "inputs": {
                    "frame_rate": fps,
                    "loop_count": 0,
                    "filename_prefix": f"{prefix}_16K_Proxy_4K",
                    "format": "video/h264-mp4",
                    "pingpong": False,
                    "save_output": True,
                    "images": ["86", 0]
                },
                "class_type": "VHS_VideoCombine"
            }
            return graph

    graph["30"] = {
        "inputs": {
            "frame_rate": fps,
            "loop_count": 0,
            "filename_prefix": final_prefix,
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True,
            "images": video_source
        },
        "class_type": "VHS_VideoCombine"
    }

    return graph



def build_lumina2_zimage_graph(
    prompt: str,
    negative_prompt: str = "blurry, low quality, deformed, artifacts, cartoon",
    width: Optional[int] = None,
    height: Optional[int] = None,
    target_tier: str = "4K",
    aspect_ratio: str = "16:9",
    steps: int = 20,
    cfg: float = 4.0,
    sampler_name: str = "euler",
    scheduler: str = "normal",
    seed: int = 42,
    batch_size: int = 1,
    prefix: str = "AIBS_Lumina2"
) -> Dict[str, Any]:
    """
    Generates Lumina 2 NextDiT quantized (INT8) text-to-image workflow graph
    scaled directly to 4K/8K/16K Ultra-HD.
    Uses UNETLoader with z_image_int8_convrot.safetensors, CLIPLoader with qwen_3_4b (type lumina2),
    VAELoader with ae.safetensors, and 4x-UltraSharp spatial pass + Lanczos resize.
    """
    target_w, target_h, latent_w, latent_h = get_resolution_specs(target_tier, aspect_ratio)
    if width and height and max(width, height) <= 1536:
        latent_w, latent_h = width, height

    graph = {
        "1": {
            "inputs": {
                "unet_name": "z_image_int8_convrot.safetensors",
                "weight_dtype": "default"
            },
            "class_type": "UNETLoader"
        },
        "2": {
            "inputs": {
                "clip_name": "qwen_3_4b.safetensors",
                "type": "lumina2"
            },
            "class_type": "CLIPLoader"
        },
        "3": {
            "inputs": {
                "vae_name": "ae.safetensors"
            },
            "class_type": "VAELoader"
        },
        "4": {
            "inputs": {
                "width": latent_w,
                "height": latent_h,
                "batch_size": batch_size
            },
            "class_type": "EmptyLatentImage"
        },
        "5": {
            "inputs": {
                "text": prompt,
                "clip": ["2", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "6": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["2", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["4", 0]
            },
            "class_type": "KSampler"
        },
        "8": {
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 0]
            },
            "class_type": "VAEDecode"
        }
    }

    if target_tier in ["4K", "8K", "16K"]:
        graph["20"] = {
            "inputs": {
                "model_name": "4x-UltraSharp.pth"
            },
            "class_type": "UpscaleModelLoader"
        }
        graph["21"] = {
            "inputs": {
                "upscale_model": ["20", 0],
                "image": ["8", 0]
            },
            "class_type": "ImageUpscaleWithModel"
        }
        graph["22"] = {
            "inputs": {
                "upscale_method": "lanczos",
                "width": target_w,
                "height": target_h,
                "crop": "disabled",
                "image": ["21", 0]
            },
            "class_type": "ImageScale"
        }
        save_source = ["22", 0]
        final_prefix = f"{prefix}_{target_tier}"
    else:
        save_source = ["8", 0]
        final_prefix = prefix

    graph["9"] = {
        "inputs": {
            "filename_prefix": final_prefix,
            "images": save_source
        },
        "class_type": "SaveImage"
    }

    return graph


def build_image_grid_stitch_graph(
    image_filenames: list,
    columns: int = 2,
    cell_width: int = 512,
    cell_height: int = 512,
    padding: int = 4,
    prefix: str = "AIBS_Grid2x2"
) -> Dict[str, Any]:
    """
    Generates a 2x2 image grid stitch workflow combining up to 4 input images.
    """
    graph: Dict[str, Any] = {}
    total_imgs = min(len(image_filenames), 4)
    if total_imgs < 1:
        raise ValueError("At least 1 image filename is required for grid stitching")

    # Load images
    for i, fn in enumerate(image_filenames[:total_imgs]):
        node_id = f"load_{i+1}"
        graph[node_id] = {
            "inputs": {"image": fn},
            "class_type": "LoadImage"
        }

    # Batch them
    if total_imgs == 1:
        batch_source = ["load_1", 0]
    elif total_imgs == 2:
        graph["batch_1"] = {
            "inputs": {"image1": ["load_1", 0], "image2": ["load_2", 0]},
            "class_type": "ImageBatch"
        }
        batch_source = ["batch_1", 0]
    elif total_imgs == 3:
        graph["batch_1"] = {
            "inputs": {"image1": ["load_1", 0], "image2": ["load_2", 0]},
            "class_type": "ImageBatch"
        }
        graph["batch_2"] = {
            "inputs": {"image1": ["batch_1", 0], "image2": ["load_3", 0]},
            "class_type": "ImageBatch"
        }
        batch_source = ["batch_2", 0]
    else:  # 4 images
        graph["batch_1"] = {
            "inputs": {"image1": ["load_1", 0], "image2": ["load_2", 0]},
            "class_type": "ImageBatch"
        }
        graph["batch_2"] = {
            "inputs": {"image1": ["load_3", 0], "image2": ["load_4", 0]},
            "class_type": "ImageBatch"
        }
        graph["batch_final"] = {
            "inputs": {"image1": ["batch_1", 0], "image2": ["batch_2", 0]},
            "class_type": "ImageBatch"
        }
        batch_source = ["batch_final", 0]

    # Grid layout
    graph["grid_node"] = {
        "inputs": {
            "images": batch_source,
            "columns": columns,
            "cell_width": cell_width,
            "cell_height": cell_height,
            "padding": padding
        },
        "class_type": "ImageGrid"
    }

    # Save
    graph["save_node"] = {
        "inputs": {
            "filename_prefix": prefix,
            "images": ["grid_node", 0]
        },
        "class_type": "SaveImage"
    }

    return graph


def build_feather_mask_graph(
    image_filename: str,
    feather_radius: int = 12,
    prefix: str = "AIBS_MaskFeather"
) -> Dict[str, Any]:
    """
    Generates a mask feathering and boundary refinement workflow.
    """
    return {
        "load_img": {
            "inputs": {"image": image_filename},
            "class_type": "LoadImage"
        },
        "img_to_mask": {
            "inputs": {
                "image": ["load_img", 0],
                "channel": "red"
            },
            "class_type": "ImageToMask"
        },
        "feather": {
            "inputs": {
                "mask": ["img_to_mask", 0],
                "left": feather_radius,
                "top": feather_radius,
                "right": feather_radius,
                "bottom": feather_radius
            },
            "class_type": "FeatherMask"
        },
        "mask_to_img": {
            "inputs": {"mask": ["feather", 0]},
            "class_type": "MaskToImage"
        },
        "save_mask": {
            "inputs": {
                "filename_prefix": prefix,
                "images": ["mask_to_img", 0]
            },
            "class_type": "SaveImage"
        }
    }
