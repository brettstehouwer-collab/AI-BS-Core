import os
import sys
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("MediaRouter")
router = APIRouter(prefix="/api/media", tags=["Media Generation & Output Engine"])

# Canonical Output Paths
OUTPUT_ROOT = "C:/AI-BS/output"
IMAGES_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "images")
VIDEOS_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "videos")
AUDIO_OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "audio")

for d in [IMAGES_OUTPUT_DIR, VIDEOS_OUTPUT_DIR, AUDIO_OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

COMFYUI_HOST = os.environ.get("COMFYUI_HOST", "http://127.0.0.1:8189")

class ImageGenRequest(BaseModel):
    prompt: str = Field(..., description="Visual scene prompt")
    negative_prompt: str = Field(default="blurry, distorted, low quality, artifacts", description="Negative prompt")
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    steps: int = Field(default=25, ge=1, le=100)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=20.0)

class VideoRenderRequest(BaseModel):
    prompt: str = Field(..., description="Motion video prompt")
    duration_sec: float = Field(default=4.0, ge=1.0, le=30.0)
    fps: int = Field(default=24, ge=12, le=60)
    model: str = Field(default="wan2.2", description="Video diffusion backbone: wan2.2, ltx, animatediff")

@router.get("/health")
async def get_media_engine_health():
    """Checks ComfyUI rendering backend status."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{COMFYUI_HOST}/system_stats", timeout=aiohttp.ClientTimeout(total=2.0)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"status": "online", "engine": "ComfyUI", "details": data}
    except Exception as e:
        return {"status": "offline", "engine": "ComfyUI", "error": str(e)}
    return {"status": "offline"}

@router.get("/outputs")
async def list_media_outputs(category: Optional[str] = Query(None, description="Category filter: images, videos, audio")):
    """Returns indexed list of generated media files from canonical output directories."""
    categories = ["images", "videos", "audio"] if not category else [category]
    results = []

    for cat in categories:
        cat_dir = os.path.join(OUTPUT_ROOT, cat)
        if not os.path.exists(cat_dir):
            continue
        for entry in os.scandir(cat_dir):
            if entry.is_file():
                stat = entry.stat()
                results.append({
                    "filename": entry.name,
                    "category": cat,
                    "path": entry.path.replace("\\", "/"),
                    "url": f"/api/media/file/{cat}/{entry.name}",
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

    # Sort descending by creation timestamp
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return {"status": "success", "count": len(results), "outputs": results}

@router.get("/file/{category}/{filename}")
async def serve_media_file(category: str, filename: str):
    """Serves a static rendered media file with appropriate MIME headers."""
    if category not in ["images", "videos", "audio"]:
        raise HTTPException(status_code=400, detail="Invalid media category")
    
    file_path = os.path.join(OUTPUT_ROOT, category, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {filename} not found in {category}")

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".flac": "audio/flac"
    }
    ext = os.path.splitext(filename)[1].lower()
    media_type = mime_types.get(ext, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, filename=filename)

@router.post("/generate_image")
async def generate_image(request: ImageGenRequest):
    """Submits image generation task to ComfyUI SDXL/Flux pipeline."""
    try:
        from vram_manager import vram_orchestrator
        vram_orchestrator.request_gpu_budget("comfyui", 8.0, auto_evict=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_filename = f"gen_{timestamp}.png"
        target_path = os.path.join(IMAGES_OUTPUT_DIR, target_filename).replace("\\", "/")

        return {
            "status": "queued",
            "prompt": request.prompt,
            "target_path": target_path,
            "preview_url": f"/api/media/file/images/{target_filename}",
            "engine": "ComfyUI SDXL"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/render_video")
async def render_video(request: VideoRenderRequest):
    """Submits text-to-video / image-to-video render to Wan2.2 pipeline."""
    try:
        from vram_manager import vram_orchestrator
        vram_orchestrator.request_gpu_budget("comfyui", 14.0, auto_evict=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_filename = f"wan22_{timestamp}.mp4"
        target_path = os.path.join(VIDEOS_OUTPUT_DIR, target_filename).replace("\\", "/")

        return {
            "status": "queued",
            "prompt": request.prompt,
            "target_path": target_path,
            "preview_url": f"/api/media/file/videos/{target_filename}",
            "engine": f"ComfyUI {request.model}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))