"""
Unreal Engine Pixel Streaming Lifecycle Daemon
================================================
Manages the execution of the Unreal Engine headless instance
and the WebRTC Signaling Server. Exposes FastAPI endpoints
for controlling the lifecycle from the React frontend.
"""

import asyncio
import os
import subprocess
import logging
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)

unreal_router = APIRouter(prefix="/api/unreal", tags=["Unreal Lifecycle"])

class UnrealDaemon:
    def __init__(self):
        self.unreal_process: Optional[subprocess.Popen] = None
        self.signaling_process: Optional[subprocess.Popen] = None
        self.uproject_path = r"C:\AI-BS\UnrealHub\AI_BS_Hub.uproject"
        self.unreal_editor_cmd = r"C:\Program Files\Epic Games\UE_5.4\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
        # Using Epic's default cirrus server path or custom node script
        self.signaling_script = r"C:\AI-BS\backend\core\unreal_signaling_server\cirrus.js"
        
    async def start(self) -> Dict[str, str]:
        if self.is_running():
            return {"status": "already_running"}
            
        try:
            # 1. Start Signaling Server (Node.js)
            # Assuming cirrus.js is set up
            if os.path.exists(self.signaling_script):
                self.signaling_process = subprocess.Popen(
                    ["node", self.signaling_script],
                    cwd=os.path.dirname(self.signaling_script),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info("WebRTC Signaling Server started.")
            
            # 2. Start Unreal Headless
            if os.path.exists(self.uproject_path) and os.path.exists(self.unreal_editor_cmd):
                cmd = [
                    self.unreal_editor_cmd,
                    self.uproject_path,
                    "-game",
                    "-ResX=1920", "-ResY=1080",
                    "-PixelStreamingIP=127.0.0.1",
                    "-PixelStreamingPort=8888",
                    "-AudioMixer",
                    "-RenderOffScreen"
                ]
                self.unreal_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info("Unreal Headless Instance started.")
            else:
                logger.warning("Unreal Engine or project path not found. Proceeding in mock mode.")
                
            return {"status": "started"}
        except Exception as e:
            logger.error(f"Failed to start Unreal lifecycle: {e}")
            self.stop()
            raise HTTPException(status_code=500, detail=str(e))

    def stop(self) -> Dict[str, str]:
        if self.unreal_process:
            self.unreal_process.terminate()
            self.unreal_process = None
        if self.signaling_process:
            self.signaling_process.terminate()
            self.signaling_process = None
        logger.info("Unreal lifecycle stopped.")
        return {"status": "stopped"}

    def is_running(self) -> bool:
        return self.unreal_process is not None and self.unreal_process.poll() is None

daemon = UnrealDaemon()

@unreal_router.get("/status")
async def get_status():
    return {"running": daemon.is_running()}

@unreal_router.post("/start")
async def start_unreal():
    return await daemon.start()

@unreal_router.post("/stop")
async def stop_unreal():
    return daemon.stop()

@unreal_router.post("/remote-control")
async def proxy_remote_control(request: Request):
    """
    Proxy camera and actor manipulation commands to Unreal Engine's 
    Web Remote Control endpoint on port 30010. Enforces validation.
    """
    try:
        body = await request.json()
        
        # Simple schema validation to ensure it's a valid remote control command
        if "objectPath" not in body and "functionName" not in body:
            raise HTTPException(status_code=400, detail="Invalid Remote Control Schema")
            
        async with httpx.AsyncClient() as client:
            # Proxy to the headless Unreal Engine on port 30010
            resp = await client.post("http://127.0.0.1:30010/remote/object/call", json=body, timeout=5.0)
            
            # Unreal Remote Control returns 200 on success
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
                
            return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Unreal Remote Control unreachable: {e}")
        raise HTTPException(status_code=503, detail="Unreal Engine Web Remote Control is unreachable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================================
# Theatrical Virtual Production Staging & DMX Lighting Bridge
# ==========================================================

UNREAL_THEATRICAL_PROFILES = {
    "aggressive": {
        "theme": "AGGRESSIVE",
        "dmx_color_hex": "#FF0033",
        "dmx_rgb": [255, 0, 51],
        "post_process_lut": "LUT_HighContrast_Crimson",
        "camera_rig": "CineCam_Tight_Tracking_01",
        "fog_density": 0.08,
        "light_intensity_lux": 8500.0,
        "bloom_intensity": 1.75
    },
    "calm": {
        "theme": "CALM",
        "dmx_color_hex": "#00E5FF",
        "dmx_rgb": [0, 229, 255],
        "post_process_lut": "LUT_Soft_Warm_Teal",
        "camera_rig": "CineCam_Wide_Orbit_02",
        "fog_density": 0.02,
        "light_intensity_lux": 2200.0,
        "bloom_intensity": 0.40
    },
    "hype": {
        "theme": "HYPE",
        "dmx_color_hex": "#FFB700",
        "dmx_rgb": [255, 183, 0],
        "post_process_lut": "LUT_Cyberpunk_Vibrant",
        "camera_rig": "CineCam_Dynamic_Jib_03",
        "fog_density": 0.05,
        "light_intensity_lux": 9500.0,
        "bloom_intensity": 2.20
    },
    "analytical": {
        "theme": "ANALYTICAL",
        "dmx_color_hex": "#A855F7",
        "dmx_rgb": [168, 85, 247],
        "post_process_lut": "LUT_Clean_Studio_Rec709",
        "camera_rig": "CineCam_Grid_Orthographic_04",
        "fog_density": 0.00,
        "light_intensity_lux": 4500.0,
        "bloom_intensity": 0.10
    }
}

current_stage_state = {
    "active_theme": "neutral",
    "dmx_color_hex": "#00FFFF",
    "camera_rig": "CineCam_Master_00",
    "profile": {}
}

class TheatricalStageTriggerRequest(BaseModel):
    theme: str

@unreal_router.get("/theatrical/stage-state")
async def get_theatrical_stage_state():
    return current_stage_state

@unreal_router.post("/theatrical/stage-trigger")
async def trigger_theatrical_stage(req: TheatricalStageTriggerRequest):
    theme_key = req.theme.lower().strip()
    profile = UNREAL_THEATRICAL_PROFILES.get(theme_key)
    
    if not profile:
        profile = {
            "theme": "NEUTRAL",
            "dmx_color_hex": "#94A3B8",
            "dmx_rgb": [148, 163, 184],
            "post_process_lut": "LUT_Default_Linear",
            "camera_rig": "CineCam_Master_00",
            "fog_density": 0.01,
            "light_intensity_lux": 3000.0,
            "bloom_intensity": 0.50
        }

    current_stage_state["active_theme"] = theme_key
    current_stage_state["dmx_color_hex"] = profile["dmx_color_hex"]
    current_stage_state["camera_rig"] = profile["camera_rig"]
    current_stage_state["profile"] = profile

    # If Unreal Web Remote Control is running on port 30010, attempt to forward actor properties
    try:
        async with httpx.AsyncClient() as client:
            rc_payload = {
                "objectPath": "/Game/TheatricalStage/Lighting/BP_DMX_Master.BP_DMX_Master_C",
                "functionName": "SetTheatricalThemeColor",
                "parameters": {
                    "NewColor": profile["dmx_rgb"],
                    "Intensity": profile["light_intensity_lux"],
                    "CameraRig": profile["camera_rig"]
                }
            }
            await client.post("http://127.0.0.1:30010/remote/object/call", json=rc_payload, timeout=0.8)
            logger.info(f"Forwarded Theatrical Stage DMX command to Unreal Engine 5 on Port 30010: {theme_key}")
    except Exception:
        # Non-blocking fallback if UE5 instance is operating standalone or pixel streaming
        pass

    logger.info(f"Theatrical Staging updated to theme '{theme_key}': DMX={profile['dmx_color_hex']}, Cam={profile['camera_rig']}")
    return {
        "status": "success",
        "theme": theme_key,
        "stage_profile": profile
    }

