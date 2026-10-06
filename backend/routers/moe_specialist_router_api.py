#!/usr/bin/env python3
"""
Sovereign MoE Specialist Router FastAPI Router
AI-BS Port 8080 Endpoint Matrix for Mixture-of-Specialists Dynamic Routing
Routes agent and operator prompts to the optimal local specialist LLM (Ports 11434/11435).
"""

from fastapi import APIRouter, HTTPException, Query, Body, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
import logging
import asyncio

try:
    from core.sovereign_reasoning.moe_specialist_router import (
        moe_router,
        SPECIALIST_MATRIX,
        SpecialistDomain,
        RoutingDecision
    )
except ImportError:
    # Direct path fallback
    import sys
    import os
    _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
    from core.sovereign_reasoning.moe_specialist_router import (
        moe_router,
        SPECIALIST_MATRIX,
        SpecialistDomain,
        RoutingDecision
    )

router = APIRouter(prefix="/api/v1/moe", tags=["Sovereign MoE Specialist Router"])
logger = logging.getLogger("moe_specialist_router_api")


class ClassifyRequest(BaseModel):
    prompt: str
    domain_hint: Optional[str] = None


class RouteRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    domain_hint: Optional[str] = None
    stream: bool = False
    temperature: float = 0.2
    max_tokens: int = 4096


@router.get("/matrix")
async def get_specialist_matrix():
    """Returns the static Mixture-of-Specialists domain mapping matrix and model specs."""
    return {
        "status": "success",
        "specialists": SPECIALIST_MATRIX,
        "domains": list(SPECIALIST_MATRIX.keys())
    }


@router.get("/fleet")
async def get_ollama_fleet_status():
    """Checks the health and discovered model inventory of local Ollama ports 11434/11435."""
    try:
        fleet = await moe_router.discover_fleet()
        return {
            "status": "success",
            "fleet": fleet
        }
    except Exception as e:
        logger.error(f"Error querying Ollama fleet: {e}")
        return {
            "status": "warning",
            "error": str(e),
            "fleet": {
                "online": False,
                "port": 11434,
                "model_count": 0,
                "models": []
            }
        }


@router.post("/classify")
async def classify_prompt_specialist(payload: ClassifyRequest):
    """Classifies an incoming prompt and determines the optimal local specialist model."""
    try:
        decision = moe_router.classify_intent(payload.prompt, domain_hint=payload.domain_hint)
        return {
            "status": "success",
            "decision": decision.to_dict()
        }
    except Exception as e:
        logger.error(f"Error classifying prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route")
async def route_and_execute(payload: RouteRequest):
    """Classifies prompt intent, routes to local specialist Ollama model, and returns response."""
    try:
        decision = moe_router.classify_intent(payload.prompt, domain_hint=payload.domain_hint)
        response = await moe_router.dispatch(
            prompt=payload.prompt,
            system_prompt=payload.system_prompt,
            domain_hint=payload.domain_hint,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens
        )
        return {
            "status": "success",
            "decision": decision.to_dict(),
            "response": response
        }
    except Exception as e:
        logger.error(f"Error routing specialist prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def stream_specialist_execution(payload: RouteRequest):
    """Streams token-by-token response from the classified specialist model."""
    try:
        decision = moe_router.classify_intent(payload.prompt, domain_hint=payload.domain_hint)
        
        async def event_generator():
            # Initial decision event
            yield f"data: {json.dumps({'type': 'decision', 'data': decision.to_dict()})}\n\n"
            
            async for chunk in moe_router.stream_dispatch(
                prompt=payload.prompt,
                system_prompt=payload.system_prompt,
                domain_hint=payload.domain_hint,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens
            ):
                yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"
                
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        logger.error(f"Error streaming specialist prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))
