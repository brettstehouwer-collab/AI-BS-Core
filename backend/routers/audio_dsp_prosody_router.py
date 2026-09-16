"""
Audio DSP, Pitch Shift & Prosody Router for AI-BS Wave Studio
Exposes endpoints for:
- POST /api/v1/audio/dsp/filter
- POST /api/v1/audio/dsp/stretch
- POST /api/v1/audio/prosody/map
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.audio_dsp_prosody_engine import AudioDspProsodyEngine

router = APIRouter(prefix="/api/v1/audio", tags=["Audio DSP & Prosody"])


class DspFilterRequest(BaseModel):
    audio_path: str = Field(..., description="Absolute path to input audio file")
    filter_type: str = Field(default="loudness_normalize", description="'loudness_normalize', 'vocal_clean', 'bass_boost', 'phase_invert'")
    target_lufs: float = Field(default=-14.0, description="Target integrated loudness LUFS")
    output_filename: Optional[str] = Field(default=None, description="Optional custom output filename")


class PitchStretchRequest(BaseModel):
    audio_path: str = Field(..., description="Absolute path to input audio file")
    tempo_ratio: float = Field(default=1.0, description="Speed multiplier (0.5 to 2.0)")
    semitones: float = Field(default=0.0, description="Pitch shift in semitones (-12 to +12)")
    output_filename: Optional[str] = Field(default=None, description="Optional custom output filename")


class ProsodyMapRequest(BaseModel):
    raw_lyrics: str = Field(..., description="Raw song lyrics text with line breaks per bar")
    bpm: int = Field(default=140, description="Song tempo in BPM")
    time_signature: str = Field(default="4/4", description="Time signature")


@router.post("/dsp/filter")
async def dsp_filter_endpoint(req: DspFilterRequest):
    try:
        res = AudioDspProsodyEngine.process_dsp_filter(
            audio_path=req.audio_path,
            filter_type=req.filter_type,
            target_lufs=req.target_lufs,
            output_filename=req.output_filename
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dsp/stretch")
async def pitch_stretch_endpoint(req: PitchStretchRequest):
    try:
        res = AudioDspProsodyEngine.stretch_pitch_tempo(
            audio_path=req.audio_path,
            tempo_ratio=req.tempo_ratio,
            semitones=req.semitones,
            output_filename=req.output_filename
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prosody/map")
async def prosody_map_endpoint(req: ProsodyMapRequest):
    try:
        res = AudioDspProsodyEngine.map_lyrics_prosody(
            raw_lyrics=req.raw_lyrics,
            bpm=req.bpm,
            time_signature=req.time_signature
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
