#!/usr/bin/env python3
"""
Sovereign GPU Telemetry FastAPI Router
AI-BS Port 8080 Endpoint Matrix for Hardware Telemetry & Thermal Control
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
import logging
import json
import asyncio
from sse_starlette.sse import EventSourceResponse

from modules.gpu_hardware_telemetry import gpu_telemetry_engine
from security.financial_auth import require_financial_owner

router = APIRouter(prefix="/api/v1/hardware/gpu", tags=["GPU Hardware Telemetry"])
logger = logging.getLogger("gpu_telemetry_router")


@router.get("/controller")
async def get_adaptive_gpu_controller_status():
    """Measured admission state; reads never load models or change GPU settings."""
    from gpu.compute_scheduler import get_controller
    from orchestrator.gpu_task_dispatcher import get_dispatcher
    from starlette.responses import JSONResponse
    snapshot = await get_controller().snapshot()
    snapshot["rollout"] = {
        "enabled": get_dispatcher().enabled,
        "setting": "AIBS_ADAPTIVE_GPU_ENABLED=true",
        "scope": "Cooperative chat, agent-router and chat embedding adapter calls in this process.",
        "acceptance": "Application performance and real-time acceptance required before production enablement.",
    }
    return JSONResponse(snapshot, headers={"Cache-Control": "no-store"})


class FanControlPayload(BaseModel):
    model_config = {"extra": "forbid"}
    speed: int = Field(default=100, ge=0, le=100, strict=True)
    auto: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_manual_speed(self):
        if not self.auto and self.speed < 30:
            raise ValueError("Manual fan speed must be between 30 and 100 percent")
        return self


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


@router.post("/fan-control", dependencies=[Depends(require_financial_owner)])
async def control_gpu_fan(payload: FanControlPayload):
    """Sets GPU fan speed or toggles automatic driver curve mode."""
    try:
        result = gpu_telemetry_engine.set_fan_speed(speed=payload.speed, auto=payload.auto)
        return {
            "status": "success" if result.get("success") else "warning",
            "result": result
        }
    except Exception:
        logger.error("GPU fan control failed")
        raise HTTPException(status_code=500, detail="GPU fan control is unavailable. Refresh telemetry before retrying.",
                            headers={"Cache-Control": "private, no-store"}) from None


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


@router.get("/stream")
async def stream_gpu_telemetry():
    """Streams real-time GPU telemetry snapshots via Server-Sent Events (SSE)."""
    async def event_generator():
        while True:
            try:
                telemetry = gpu_telemetry_engine.query_nvml_telemetry()
                yield {
                    "event": "telemetry",
                    "data": json.dumps(telemetry, allow_nan=False, separators=(",", ":"))
                }
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
            await asyncio.sleep(2.0)

    return EventSourceResponse(event_generator())


