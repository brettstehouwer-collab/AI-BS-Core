import os
import sys
import json
import uuid
import time
import shutil
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

core_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core"))
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from comfy_workflow_builders import (
    build_sdxl_txt2img_graph,
    build_sd15_txt2img_graph,
    build_two_stage_upscale_graph,
    build_ltx_img2video_graph,
    build_wan_video_graph,
    build_lumina2_zimage_graph,
    build_image_grid_stitch_graph,
    build_feather_mask_graph
)

router = APIRouter(prefix="/api/comfyui/workspace", tags=["comfyui-workspace"])

COMFY_HOST = "http://127.0.0.1:8189"
STYLES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "comfy_styles.json")
OUTPUT_DIR = r"C:\AI-BS\ComfyUI\ComfyUI\output"
INPUT_DIR = r"C:\AI-BS\ComfyUI\ComfyUI\input"

class GenerateWorkspaceRequest(BaseModel):
    num_frames: int = Field(default=49, ge=9, le=129)
    fps: int = Field(default=16, ge=1, le=60)
    media_type: str  # image, video, upscale
    template_id: str  # sdxl_txt2img, sd15_txt2img, ltx_i2v, two_stage_upscale
    prompt: str
    negative_prompt: Optional[str] = ""
    style_id: Optional[str] = None
    scene_dna: Optional[str] = None
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    target_resolution: Optional[str] = "4K"  # 4K, 8K, 16K
    aspect_ratio: Optional[str] = "16:9"  # 16:9, 1:1, 9:16, 21:9, 4:3, 3:4
    steps: Optional[int] = 25
    cfg: Optional[float] = 7.5
    sampler_name: Optional[str] = "euler_ancestral"
    scheduler: Optional[str] = "karras"
    seed: Optional[int] = -1
    reference_image: Optional[str] = None
    strength: Optional[float] = 0.85
    upscale_denoise: Optional[float] = 0.15

class StyleCreateRequest(BaseModel):
    id: str
    name: str
    category: str
    prompt_prefix: str
    prompt_suffix: str
    negative_prompt: str
    recommended_sampler: str = "euler_ancestral"
    recommended_scheduler: str = "karras"
    cfg: float = 7.5
    steps: int = 25

def call_comfy_api(endpoint: str, data: Optional[dict] = None) -> dict:
    url = f"{COMFY_HOST}{endpoint}"
    req_data = json.dumps(data).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json"} if req_data else {}
    req = urllib.request.Request(url, data=req_data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with ComfyUI: {str(e)}")

@router.get("/capabilities")
async def get_capabilities():
    """Returns real-time hardware status, models, and node availability."""
    try:
        system_stats = call_comfy_api("/system_stats")
        object_info = call_comfy_api("/object_info")
    except Exception as e:
        return {"online": False, "error": str(e)}

    ckpt_loader = object_info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {})
    checkpoints = ckpt_loader.get("ckpt_name", [[]])[0] if "ckpt_name" in ckpt_loader else []

    upscale_loader = object_info.get("UpscaleModelLoader", {}).get("input", {}).get("required", {})
    upscale_entry = upscale_loader.get("model_name", [[]])
    if len(upscale_entry) > 1 and isinstance(upscale_entry[1], dict) and "options" in upscale_entry[1]:
        upscale_models = upscale_entry[1]["options"]
    elif len(upscale_entry) > 0 and isinstance(upscale_entry[0], list):
        upscale_models = upscale_entry[0]
    else:
        upscale_models = []

    has_ultimate_sd = "UltimateSDUpscale" in object_info
    has_face_detailer = "FaceDetailer" in object_info
    has_rtx_vsr = "RTXVideoSuperResolution" in object_info

    from core.video_workflows import video_capabilities
    video_status = video_capabilities(object_info)
    templates = [
        {
            "id": "sdxl_txt2img",
            "name": "SDXL High-Resolution (1024p)",
            "media_type": "image",
            "ready": "sd_xl_base_1.0.safetensors" in checkpoints,
            "description": "Native 1024x1024 base diffusion with rich dynamic range."
        },
        {
            "id": "sd15_txt2img",
            "name": "SD 1.5 Fast Standard (512p)",
            "media_type": "image",
            "ready": "v1-5-pruned-emaonly-fp16.safetensors" in checkpoints,
            "description": "Ultra fast standard resolution image generation."
        },
        {
            "id": "two_stage_upscale",
            "name": "2-Stage 4K Ultra-Refinery",
            "media_type": "upscale",
            "ready": has_ultimate_sd and ("4x-UltraSharp.pth" in upscale_models or "RealESRGAN_x4plus.safetensors" in upscale_models),
            "description": "Spatial 4x model scale followed by low-denoise tiled micro-texture injection."
        },
        {
            "id": "z_image_lumina2",
            "name": "Z-Image Lumina 2 NextDiT (INT8)",
            "media_type": "image",
            "ready": os.path.exists(r"C:\AI-BS\ComfyUI\ComfyUI\models\unet\z_image_int8_convrot.safetensors"),
            "description": "State-of-the-art NextDiT transformer with rotary embeddings and INT8 quantization."
        },
        {
            "id": "ltx_i2v",
            "name": "LTX-Video (Image-to-Video)",
            "media_type": "video",
            "ready": video_status["ltx_i2v"]["ready"],
            "missing": video_status["ltx_i2v"]["missing"],
            "description": "Transforms any visual anchor image into a high frame-rate motion video."
        },
        {
            "id": "wan_video",
            "name": "Wan2.1 Unified Studio (T2V/I2V)",
            "media_type": "video",
            "ready": video_status["wan_t2v"]["ready"],
            "missing": video_status["wan_t2v"]["missing"],
            "description": "Wan2.1 text-to-video at native dimensions using the installed core model. High-resolution upscaling requires a separate accepted workflow."
        }
    ]

    return {
        "online": True,
        "system": system_stats.get("system", {}),
        "devices": system_stats.get("devices", []),
        "checkpoints": checkpoints,
        "upscale_models": upscale_models,
        "features": {
            "ultimate_sd_upscale": has_ultimate_sd,
            "face_detailer": has_face_detailer,
            "rtx_vsr": has_rtx_vsr
        },
        "templates": templates
    }

@router.get("/styles")
async def list_styles():
    if not os.path.exists(STYLES_FILE):
        return []
    with open(STYLES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@router.post("/styles")
async def add_style(style: StyleCreateRequest):
    styles = []
    if os.path.exists(STYLES_FILE):
        with open(STYLES_FILE, "r", encoding="utf-8") as f:
            styles = json.load(f)
    styles = [s for s in styles if s["id"] != style.id]
    styles.append(style.dict())
    with open(STYLES_FILE, "w", encoding="utf-8") as f:
        json.dump(styles, f, indent=2)
    return {"status": "success", "style": style}

@router.delete("/styles/{style_id}")
async def delete_style(style_id: str):
    if not os.path.exists(STYLES_FILE):
        raise HTTPException(status_code=404, detail="Style file not found")
    with open(STYLES_FILE, "r", encoding="utf-8") as f:
        styles = json.load(f)
    styles = [s for s in styles if s["id"] != style_id]
    with open(STYLES_FILE, "w", encoding="utf-8") as f:
        json.dump(styles, f, indent=2)
    return {"status": "deleted"}

@router.post("/run")
async def run_pipeline(req: GenerateWorkspaceRequest):
    expected_type = {'wan_video':'video','ltx_i2v':'video','sdxl_txt2img':'image','sd15_txt2img':'image','z_image_lumina2':'image','two_stage_upscale':'upscale'}.get(req.template_id)
    if expected_type and expected_type != req.media_type:
        raise HTTPException(status_code=422, detail="Media type does not match the selected template.")
    if req.media_type == "video" and (req.target_resolution or '').upper() != 'NATIVE':
        raise HTTPException(status_code=409, detail="High-resolution video upscaling still needs acceptance. Select NATIVE video output.")
    """Assembles exact graph and queues directly into ComfyUI."""
    import random

    effective_seed = req.seed if req.seed and req.seed > 0 else random.randint(100000000000, 999999999999)
    full_prompt = req.prompt.strip()

    if req.scene_dna:
        full_prompt = f"{req.scene_dna.strip()} {full_prompt}"

    if req.style_id:
        if os.path.exists(STYLES_FILE):
            with open(STYLES_FILE, "r", encoding="utf-8") as f:
                styles = json.load(f)
                matched = next((s for s in styles if s["id"] == req.style_id), None)
                if matched:
                    full_prompt = f"{matched.get('prompt_prefix', '')}{full_prompt}{matched.get('prompt_suffix', '')}"

    target_tier = (req.target_resolution or "4K").upper()
    aspect_ratio = req.aspect_ratio or "16:9"

    graph = None
    if req.template_id == "sdxl_txt2img":
        graph = build_sdxl_txt2img_graph(
            prompt=full_prompt,
            negative_prompt=req.negative_prompt or "blurry, low quality, bad anatomy, deformed",
            width=req.width,
            height=req.height,
            target_tier=target_tier,
            aspect_ratio=aspect_ratio,
            steps=req.steps or 25,
            cfg=req.cfg or 7.5,
            sampler_name=req.sampler_name or "euler_ancestral",
            scheduler=req.scheduler or "karras",
            seed=effective_seed
        )
    elif req.template_id == "sd15_txt2img":
        graph = build_sd15_txt2img_graph(
            prompt=full_prompt,
            negative_prompt=req.negative_prompt or "blurry, low quality, bad anatomy",
            width=req.width,
            height=req.height,
            target_tier=target_tier,
            aspect_ratio=aspect_ratio,
            steps=req.steps or 20,
            cfg=req.cfg or 7.0,
            sampler_name=req.sampler_name or "euler",
            scheduler=req.scheduler or "normal",
            seed=effective_seed
        )
    elif req.template_id == "two_stage_upscale":
        target_ref = req.reference_image
        if not target_ref and os.path.exists(OUTPUT_DIR):
            imgs = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.webp'))]
            if imgs:
                imgs.sort(key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)), reverse=True)
                target_ref = imgs[0]
        if not target_ref:
            raise HTTPException(status_code=400, detail="Reference image required for upscaling. Please select or generate an image first.")

        base_name = os.path.basename(target_ref)
        input_target = os.path.join(INPUT_DIR, base_name)
        output_src = os.path.join(OUTPUT_DIR, base_name)
        if not os.path.exists(input_target) and os.path.exists(output_src):
            shutil.copy2(output_src, input_target)
        elif not os.path.exists(input_target) and os.path.exists(target_ref):
            shutil.copy2(target_ref, input_target)

        graph = build_two_stage_upscale_graph(
            image_filename=base_name,
            prompt=full_prompt,
            negative_prompt=req.negative_prompt or "blurry, low quality, artifacts, smooth plastic",
            target_tier=target_tier,
            aspect_ratio=aspect_ratio,
            denoise=req.upscale_denoise or 0.15,
            seed=effective_seed
        )
    elif req.template_id == "z_image_lumina2":
        graph = build_lumina2_zimage_graph(
            prompt=full_prompt,
            negative_prompt=req.negative_prompt or "blurry, low quality, deformed, artifacts, cartoon",
            width=req.width,
            height=req.height,
            target_tier=target_tier,
            aspect_ratio=aspect_ratio,
            steps=req.steps or 20,
            cfg=req.cfg or 4.0,
            sampler_name=req.sampler_name or "euler",
            scheduler=req.scheduler or "normal",
            seed=effective_seed
        )
    elif req.template_id == "ltx_i2v":
        target_ref = req.reference_image
        if not target_ref and os.path.exists(OUTPUT_DIR):
            imgs = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith(('.png', '.jpg', '.webp'))]
            if imgs:
                imgs.sort(key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)), reverse=True)
                target_ref = imgs[0]
        if not target_ref:
            raise HTTPException(status_code=400, detail="Reference image required for LTX video generation. Please select or generate an anchor image first.")

        base_name = os.path.basename(target_ref)
        input_target = os.path.join(INPUT_DIR, base_name)
        output_src = os.path.join(OUTPUT_DIR, base_name)
        if not os.path.exists(input_target) and os.path.exists(output_src):
            shutil.copy2(output_src, input_target)
        elif not os.path.exists(input_target) and os.path.exists(target_ref):
            shutil.copy2(target_ref, input_target)

        graph = build_ltx_img2video_graph(
            image_filename=base_name,
            prompt=full_prompt,
            negative_prompt=req.negative_prompt or "blurry, low quality, deformed, motion artifacts",
            width=req.width or 768,
            height=req.height or 512,
            target_tier=target_tier,
            aspect_ratio=aspect_ratio,
            steps=req.steps or 25,
            strength=req.strength or 0.85,
            seed=effective_seed
        )
    elif req.template_id == "wan_video":
        from core.video_workflows import build_core_wan_graph
        if req.reference_image:
            raise HTTPException(status_code=409, detail="Select LTX image-to-video for a reference image; this Wan route uses a text prompt.")
        if target_tier != "NATIVE":
            raise HTTPException(status_code=409, detail="Native video is available. High-resolution video upscaling is not accepted; select NATIVE.")
        info = call_comfy_api("/object_info")
        try:
            graph = build_core_wan_graph(full_prompt, info, negative_prompt=req.negative_prompt or "blurry, low quality, static", width=req.width or 832, height=req.height or 480, length=req.num_frames, fps=req.fps, steps=req.steps or 8, cfg=req.cfg or 6.0, seed=effective_seed)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported template_id: {req.template_id}")

    if req.media_type == "video":
        from core.video_workflows import core_video_output, validate_graph
        graph = core_video_output(graph)
        if req.template_id == "ltx_i2v":
            graph["38"]["inputs"]["clip_name"] = "t5xxl_fp16.safetensors"
        problems = validate_graph(graph, call_comfy_api("/object_info"))
        if problems:
            raise HTTPException(status_code=409, detail="Video unavailable: " + "; ".join(problems))

    client_id = f"aibs_workspace_{int(time.time())}"
    res = call_comfy_api("/prompt", {"prompt": graph, "client_id": client_id})

    return {
        "status": "queued",
        "prompt_id": res.get("prompt_id"),
        "seed": effective_seed,
        "template_id": req.template_id,
        "client_id": client_id
    }

@router.get("/gallery")
async def get_recent_gallery():
    """Scans the master ComfyUI output directory for recent generated files."""
    if not os.path.exists(OUTPUT_DIR):
        return []

    files = []
    for f in os.listdir(OUTPUT_DIR):
        if f.lower().endswith((".png", ".jpg", ".webp", ".mp4")):
            fp = os.path.join(OUTPUT_DIR, f)
            files.append({
                "filename": f,
                "type": "video" if f.lower().endswith(".mp4") else "image",
                "size_bytes": os.path.getsize(fp),
                "modified": os.path.getmtime(fp)
            })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return files[:40]

@router.post("/free")
async def free_vram():
    """Unloads cached models and clears GPU memory in ComfyUI."""
    res = call_comfy_api("/free", {"unload_models": True, "free_memory": True})
    return {"status": "cleared", "details": res}


class BlueprintGridRequest(BaseModel):
    images: List[str]
    columns: Optional[int] = 2
    cell_width: Optional[int] = 512
    cell_height: Optional[int] = 512
    padding: Optional[int] = 4

@router.post("/blueprints/grid")
async def run_grid_blueprint(req: BlueprintGridRequest):
    """Executes 2x2 image grid stitching subgraph."""
    graph = build_image_grid_stitch_graph(
        image_filenames=req.images,
        columns=req.columns or 2,
        cell_width=req.cell_width or 512,
        cell_height=req.cell_height or 512,
        padding=req.padding or 4
    )
    client_id = f"aibs_grid_{int(time.time())}"
    res = call_comfy_api("/prompt", {"prompt": graph, "client_id": client_id})
    return {"status": "queued", "prompt_id": res.get("prompt_id"), "blueprint": "grid2x2"}


class BlueprintFeatherRequest(BaseModel):
    image: str
    feather_radius: Optional[int] = 12

@router.post("/blueprints/feather")
async def run_feather_blueprint(req: BlueprintFeatherRequest):
    """Executes mask feathering boundary refinement subgraph."""
    graph = build_feather_mask_graph(
        image_filename=req.image,
        feather_radius=req.feather_radius or 12
    )
    client_id = f"aibs_feather_{int(time.time())}"
    res = call_comfy_api("/prompt", {"prompt": graph, "client_id": client_id})
    return {"status": "queued", "prompt_id": res.get("prompt_id"), "blueprint": "feather_mask"}
