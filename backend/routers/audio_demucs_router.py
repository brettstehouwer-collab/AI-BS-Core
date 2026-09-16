import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.demucs_audio_engine import DemucsAudioEngine, STEMS_DIR

router = APIRouter(prefix="/api/v1/audio/demucs", tags=["Demucs Audio Stem Separator"])


class SeparateRequest(BaseModel):
    audio_file_path: str = Field(..., description="Absolute path to the input audio file (.mp3, .wav, .flac)")
    output_dir: Optional[str] = Field(None, description="Optional custom DAW project target folder")
    model_name: Optional[str] = Field("htdemucs", description="Demucs model: 'htdemucs', 'htdemucs_ft', 'mdx_extra_q'")
    two_stems: Optional[str] = Field(None, description="Set to 'vocals' for fast 2-stem vocal/accompaniment split")


@router.post("/separate")
async def separate_audio_endpoint(req: SeparateRequest):
    """
    Triggers local PyTorch/CUDA stem separation on RTX 4090, exporting discrete stems to DAW directory.
    """
    try:
        res = DemucsAudioEngine.separate_stems(
            audio_file_path=req.audio_file_path,
            output_dir=req.output_dir,
            model_name=req.model_name or "htdemucs",
            two_stems=req.two_stems
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hardware")
async def get_audio_hardware_status():
    """
    Returns GPU/CUDA availability, device model name, and VRAM for Demucs audio separation.
    """
    return DemucsAudioEngine.get_hardware_status()


@router.get("/sessions")
async def get_stem_sessions():
    """
    Returns recent audio separation sessions and stems catalog.
    """
    return {
        "sessions": DemucsAudioEngine.list_recent_sessions()
    }


@router.get("/file/{session_id}/{filename}")
async def get_stem_audio_file(session_id: str, filename: str):
    """
    Streams or downloads a generated audio stem WAV file.
    """
    session_dir = os.path.join(STEMS_DIR, session_id)
    stem_path = os.path.join(session_dir, filename)
    if not os.path.exists(stem_path):
        raise HTTPException(status_code=404, detail="Stem file not found.")
    return FileResponse(stem_path, media_type="audio/wav", filename=filename)
