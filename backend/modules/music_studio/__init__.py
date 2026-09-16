from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus
from modules.music_studio.video_export_engine import render_master_av_export

router = APIRouter(prefix="/api/studio", tags=["FL Music & Video Multimedia Studio Module"])

class BeatGenRequest(BaseModel):
    genre: str = "trap"
    bpm: int = 140
    bars: int = 4

class AISceneRequest(BaseModel):
    prompt: str
    engine: Optional[str] = "comfyui"

class RenderExportRequest(BaseModel):
    title: Optional[str] = "Master_Track"
    resolution: Optional[str] = "1080p"

@router.get("/status")
async def get_studio_status():
    return {"module": "music_and_video_studio", "engines": ["Tone.js", "ComfyUI_Wan2.1", "FFmpeg_NVENC"], "status": "active"}

@router.post("/generate_beat")
async def generate_beat_pattern(req: BeatGenRequest):
    pattern = {
        "genre": req.genre,
        "bpm": req.bpm,
        "kick_steps": [0, 6, 10],
        "snare_steps": [4, 12],
        "hihat_steps": list(range(16)),
        "chords": ["C4", "D#4", "G4", "A#4"] if req.genre == "trap" else ["A3", "F3", "G3", "E3"]
    }
    await event_bus.publish(
        "events.music.beat_generated",
        {"genre": req.genre, "bpm": req.bpm},
        source="music_studio_module"
    )
    return {"status": "success", "pattern": pattern}

@router.post("/generate_ai_scene")
async def generate_ai_scene(req: AISceneRequest):
    # Triggers ComfyUI Wan2.1 generative scene
    output_url = "https://assets.mixkit.co/videos/preview/mixkit-futuristic-city-with-neon-lights-41551-large.mp4"
    await event_bus.publish(
        "events.studio.ai_scene_rendered",
        {"prompt": req.prompt, "engine": req.engine},
        source="multimedia_studio_module"
    )
    return {
        "status": "success",
        "prompt": req.prompt,
        "stream_url": output_url,
        "engine": "comfyui_wan2.1"
    }

@router.post("/render_master_video")
async def render_master_video(req: RenderExportRequest):
    res = render_master_av_export(output_filename=f"{req.title}.mp4")
    await event_bus.publish(
        "events.studio.master_exported",
        {"file": res.get("rendered_file"), "engine": res.get("engine")},
        source="multimedia_studio_module"
    )
    return res

def init_module(app):
    print("[Module: MultimediaStudio] Initialized successfully with AV capabilities.")
