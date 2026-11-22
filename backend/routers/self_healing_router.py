"""Held administrator routes preserving the unintegrated self-healing API contract.

No verified sentinel factory is available; these endpoints perform no repair,
filesystem mutation, model inference, or circuit-breaker changes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from security.host_control_access import AdminHostControlRoute, HOST_CONTROL_PRIVATE_HEADERS

logger = logging.getLogger("AIBS_SelfHealingRouter")
router = APIRouter(prefix="/api/sentinel", tags=["Self-Healing Sentinel"], route_class=AdminHostControlRoute)


class HealRequest(BaseModel):
    error_trace: str = Field(..., description="Python traceback or pytest failure output to diagnose and repair.")
    target_file: Optional[str] = Field(None, description="Optional explicit file path if known.")
    test_target: Optional[str] = Field(None, description="Optional pytest target to run for verification.")


class ResetCircuitBreakerRequest(BaseModel):
    error_signature: Optional[str] = Field(None, description="Signature to reset, or omit to reset all.")


@router.get("/status")
async def get_sentinel_status() -> Dict[str, Any]:
    """Unavailable: no verified sentinel factory or safe autonomous repair implementation."""
    raise HTTPException(status_code=503, detail="Self-healing is unavailable and held; no verified sentinel integration is configured.", headers=dict(HOST_CONTROL_PRIVATE_HEADERS))


@router.get("/incidents")
async def list_incidents(
    limit: int = Query(default=20, ge=1, le=100)
) -> List[Dict[str, Any]]:
    """Unavailable: no verified sentinel factory or safe autonomous repair implementation."""
    raise HTTPException(status_code=503, detail="Self-healing is unavailable and held; no verified sentinel integration is configured.", headers=dict(HOST_CONTROL_PRIVATE_HEADERS))


@router.post("/heal")
async def trigger_self_healing(request: HealRequest) -> Dict[str, Any]:
    """Unavailable: no verified sentinel factory or safe autonomous repair implementation."""
    raise HTTPException(status_code=503, detail="Self-healing is unavailable and held; no verified sentinel integration is configured.", headers=dict(HOST_CONTROL_PRIVATE_HEADERS))


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(request: ResetCircuitBreakerRequest) -> Dict[str, Any]:
    """Unavailable: no verified sentinel factory or safe autonomous repair implementation."""
    raise HTTPException(status_code=503, detail="Self-healing is unavailable and held; no verified sentinel integration is configured.", headers=dict(HOST_CONTROL_PRIVATE_HEADERS))
