#!/usr/bin/env python3
"""
Sovereign GPU Telemetry FastAPI Router
AI-BS Port 8080 Endpoint Matrix for Hardware Telemetry & Thermal Control
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from modules.gpu_hardware_telemetry import gpu_telemetry_engine

router = APIRouter(prefix="/api/v1/hardware/gpu", tags=["GPU Hardware Telemetry"])
logger = logging.getLogger("gpu_telemetry_router")


class FanControlPayload(BaseModel):
    speed: int = 100
    auto: bool = False


@router.get("/telemetry")
async def get_gpu_telemetry():
    """Returns current real-time GPU telemetry snapshot and recent SQLite thermal logs."""
    try:
        telemetry = gpu_telemetry_engine.query_nvml_telemetry()
        history = gpu_telemetry_engine.get_recent_logs(limit=30)
        return {
            "status": "success",
            "telemetry": telemetry,
            "history": history
        }
    except Exception as e:
        logger.error(f"Error serving GPU telemetry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_gpu_history(limit: int = Query(default=50, ge=1, le=500)):
    """Returns historical thermal log entries from SQLite vault."""
    try:
        history = gpu_telemetry_engine.get_recent_logs(limit=limit)
        return {
            "status": "success",
            "count": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fan-control")
async def control_gpu_fan(payload: FanControlPayload):
    """Sets GPU fan speed or toggles automatic driver curve mode."""
    try:
        result = gpu_telemetry_engine.set_fan_speed(speed=payload.speed, auto=payload.auto)
        return {
            "status": "success" if result.get("success") else "warning",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compute-target")
async def get_compute_target():
    """Returns current active compute node target (GPU Port 11434 vs CPU Port 11435 failover)."""
    try:
        from core.vram_resource_arbiter import VRAMResourceArbiter
        target = VRAMResourceArbiter.check_compute_target()
        return {
            "status": "success",
            "target": target
        }
    except Exception as e:
        logger.error(f"Error checking compute target: {e}")
        raise HTTPException(status_code=500, detail=str(e))

