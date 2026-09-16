from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.aibs_event_bus import event_bus
from vram_manager import vram_orchestrator

router = APIRouter(prefix="/api/system", tags=["System Upgrades & VRAM"])

class VRAMRequest(BaseModel):
    requester: str
    required_vram_gb: float
    auto_evict: bool = True

class VRAMRelease(BaseModel):
    requester: str
    restore_ollama: bool = True

class EventPublishRequest(BaseModel):
    topic: str
    payload: Dict[str, Any]
    source: str = "frontend"

@router.get("/vram/status")
async def get_vram_status():
    """Returns live GPU VRAM usage and allocation status."""
    return {
        "total_vram_gb": vram_orchestrator.total_vram_gb,
        "used_vram_gb": vram_orchestrator.used_vram_gb,
        "free_vram_gb": vram_orchestrator.free_vram_gb,
        "allocations": vram_orchestrator.allocations,
        "primary_model": vram_orchestrator.active_primary_model
    }

@router.post("/vram/allocate")
async def allocate_vram(req: VRAMRequest):
    """Requests VRAM budget for heavy GPU task (e.g. ComfyUI render)."""
    granted = vram_orchestrator.request_gpu_budget(
        requester=req.requester,
        required_vram_gb=req.required_vram_gb,
        auto_evict=req.auto_evict
    )
    if not granted:
        raise HTTPException(
            status_code=429,
            detail=f"Insufficient VRAM: Requested {req.required_vram_gb} GB, Available {vram_orchestrator.free_vram_gb:.1f} GB"
        )
    return {
        "status": "granted",
        "requester": req.requester,
        "allocated_gb": req.required_vram_gb,
        "free_vram_gb": vram_orchestrator.free_vram_gb
    }

@router.post("/vram/release")
async def release_vram(req: VRAMRelease):
    """Releases VRAM budget and restores primary LLM."""
    freed = vram_orchestrator.release_gpu_budget(
        requester=req.requester,
        restore_ollama=req.restore_ollama
    )
    return {
        "status": "released",
        "freed_gb": freed,
        "free_vram_gb": vram_orchestrator.free_vram_gb
    }

@router.post("/events/publish")
async def publish_event(req: EventPublishRequest):
    """Publishes a real-time event across all vertical subsystems."""
    await event_bus.publish(
        topic=req.topic,
        payload=req.payload,
        source=req.source
    )
    return {"status": "published", "topic": req.topic}

@router.get("/events/recent")
async def get_recent_events(limit: int = 50, topic_filter: Optional[str] = None):
    """Retrieves recent event ledger from the in-memory ring buffer."""
    events = event_bus.get_recent_events(limit=limit, topic_filter=topic_filter)
    return {"count": len(events), "events": events}
