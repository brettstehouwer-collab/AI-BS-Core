"""
AI-BS Sovereign Personal Intelligence & Long-Term Memory API Router
Provides endpoints for viewing, managing, querying, and extracting personal intelligence memories.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import sys

# Ensure backend root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.personal_intelligence_memory import personal_memory

router = APIRouter(prefix="/api/memory/personal", tags=["Personal Intelligence Memory"])


def get_tenant(x_client_id: Optional[str] = Header("stehouwer_publishing")) -> str:
    return x_client_id if x_client_id else "stehouwer_publishing"


class AddMemoryRequest(BaseModel):
    category: str = Field("preferences", description="Memory category: directives, preferences, hardware, businesses, coding_patterns, episodic")
    fact_key: str = Field(..., description="Unique alphanumeric identifier for this fact")
    fact_text: str = Field(..., description="The verified statement or rule")
    importance_score: int = Field(5, ge=1, le=10, description="Priority score from 1 to 10")
    is_pinned: bool = Field(False, description="Whether this fact is permanently pinned into system prompts")
    user_id: Optional[str] = "brett"


class QueryMemoryRequest(BaseModel):
    query: str = Field(..., description="Search query or chat prompt")
    limit: Optional[int] = 6


class ExtractMemoryRequest(BaseModel):
    text: str = Field(..., description="Conversation or text snippet to extract facts from")
    user_id: Optional[str] = "brett"


@router.get("")
async def list_personal_memories(client_id: str = Depends(get_tenant), user_id: str = "brett"):
    """Lists all stored personal intelligence memories for the tenant."""
    try:
        memories = personal_memory.get_all_memories(client_id=client_id, user_id=user_id)
        categories = {}
        for m in memories:
            cat = m["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(m)

        return {
            "status": "success",
            "client_id": client_id,
            "user_id": user_id,
            "total_count": len(memories),
            "pinned_count": sum(1 for m in memories if m["is_pinned"]),
            "categories": categories,
            "memories": memories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch memories: {e}")


@router.post("/add")
async def add_personal_memory(req: AddMemoryRequest, client_id: str = Depends(get_tenant)):
    """Adds or updates a personal intelligence memory fact."""
    try:
        mem = personal_memory.add_memory(
            category=req.category,
            fact_key=req.fact_key,
            fact_text=req.fact_text,
            importance_score=req.importance_score,
            is_pinned=req.is_pinned,
            client_id=client_id,
            user_id=req.user_id or "brett",
            source="user_manual"
        )
        return {
            "status": "success",
            "message": f"Memory fact '{req.fact_key}' saved to NVMe intelligence vault.",
            "memory": mem
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save memory fact: {e}")


@router.delete("/delete/{fact_id}")
async def delete_personal_memory(fact_id: int, client_id: str = Depends(get_tenant)):
    """Deletes a memory fact from the intelligence bank."""
    try:
        success = personal_memory.delete_memory(fact_id=fact_id, client_id=client_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory fact not found or already deleted.")
        return {
            "status": "success",
            "message": f"Memory fact #{fact_id} permanently erased from intelligence vault."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {e}")


@router.post("/query")
async def query_personal_memory(req: QueryMemoryRequest, client_id: str = Depends(get_tenant)):
    """Performs semantic BM25 + Pinned retrieval for a prompt."""
    try:
        results = personal_memory.get_relevant_memories(
            query_text=req.query,
            client_id=client_id,
            limit=req.limit or 6
        )
        prompt_block = personal_memory.format_system_prompt_block(
            query_text=req.query,
            client_id=client_id
        )
        return {
            "status": "success",
            "query": req.query,
            "matched_count": len(results),
            "memories": results,
            "system_prompt_block": prompt_block
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query memories: {e}")


@router.get("/activity")
async def get_activity_timeline(limit: int = 50, client_id: str = Depends(get_tenant), user_id: str = "brett"):
    """Fetches the chronological activity feed and episodic lore across all AI-BS interactions."""
    try:
        events = personal_memory.get_activity_timeline(client_id=client_id, user_id=user_id, limit=limit)
        return {
            "status": "success",
            "client_id": client_id,
            "count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activity timeline: {e}")


class LogEventRequest(BaseModel):
    event_type: str = Field(..., description="Type of event: chat_interaction, tool_run, program_built, code_edit, trade_action")
    summary: str = Field(..., description="Human-readable event summary")
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "brett"


@router.post("/log_event")
async def log_ecosystem_event(req: LogEventRequest, client_id: str = Depends(get_tenant)):
    """Logs an ecosystem event directly into the episodic lore vault."""
    try:
        ev = personal_memory.record_ecosystem_event(
            event_type=req.event_type,
            summary=req.summary,
            metadata=req.metadata,
            client_id=client_id,
            user_id=req.user_id or "brett"
        )
        return {
            "status": "success",
            "event": ev
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log event: {e}")
