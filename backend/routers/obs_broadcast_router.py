"""
OBS Broadcast & Studio Auto-Director Router
Exposes endpoints for:
- GET /api/v1/broadcast/obs/state
- POST /api/v1/broadcast/obs/scene
- POST /api/v1/broadcast/obs/clip-marker
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.obs_broadcast_controller import ObsBroadcastController

router = APIRouter(prefix="/api/v1/broadcast/obs", tags=["OBS Broadcast Studio"])


class SceneSwitchRequest(BaseModel):
    scene_name: str = Field(..., description="Target OBS Scene name")
    transition: str = Field(default="Fade", description="Transition effect ('Fade', 'Cut', 'Stinger')")
    transition_duration_ms: int = Field(default=300, description="Transition length in ms")


class ClipMarkerRequest(BaseModel):
    marker_name: str = Field(default="Highlight Reel", description="Label for the marker")
    description: str = Field(default="Automated AI-BS clip trigger", description="Contextual note")


@router.get("/state")
async def get_obs_state_endpoint():
    try:
        return ObsBroadcastController.get_broadcast_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scene")
async def switch_scene_endpoint(req: SceneSwitchRequest):
    try:
        return ObsBroadcastController.trigger_scene_switch(
            scene_name=req.scene_name,
            transition=req.transition,
            transition_duration_ms=req.transition_duration_ms
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clip-marker")
async def clip_marker_endpoint(req: ClipMarkerRequest):
    try:
        return ObsBroadcastController.log_clip_marker(
            marker_name=req.marker_name,
            description=req.description
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
