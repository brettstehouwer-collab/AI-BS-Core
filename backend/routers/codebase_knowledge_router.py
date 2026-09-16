"""
backend/routers/codebase_knowledge_router.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Codebase Knowledge & Multi-Tiered Semantic Search REST Router (v5.290.0)
- Exposes endpoints to query the 3,230-file master codebase knowledge base.
- Sub-5ms SQLite FTS5 full-text keyword retrieval.
- ChromaDB vector memory semantic similarity.
- Exact file inspection and architectural breakdown.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from core.sovereign_reasoning.sourcecode_knowledge_engine import sourcecode_knowledge_engine

router = APIRouter(prefix="/api/v1/knowledge/codebase", tags=["Codebase Knowledge & Master Source Code"])


class CodebaseSearchRequest(BaseModel):
    query: str
    subsystem: Optional[str] = None
    language: Optional[str] = None
    limit: Optional[int] = 10


@router.post("/search")
async def search_codebase_knowledge(req: CodebaseSearchRequest):
    """
    Searches across all 3,230 files using hybrid FTS5 and ChromaDB vector retrieval.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query parameter cannot be empty.")
    
    results = sourcecode_knowledge_engine.search_codebase(
        query=req.query,
        subsystem=req.subsystem,
        language=req.language,
        limit=req.limit or 10
    )
    return {
        "status": "success",
        "query": req.query,
        "total_matches": len(results),
        "matches": results
    }


@router.get("/file")
async def get_sourcecode_file(path: str = Query(..., description="Target file path or filename")):
    """
    Retrieves the complete content, line counts, and metadata for a specific file.
    """
    file_record = sourcecode_knowledge_engine.get_file_by_path(path)
    if not file_record:
        raise HTTPException(status_code=404, detail=f"File not found in codebase knowledge base: {path}")
    
    return {
        "status": "success",
        "file": file_record
    }


@router.get("/summary")
async def get_codebase_summary(subsystem: Optional[str] = Query(None, description="Optional subsystem filter")):
    """
    Returns an aggregated breakdown of all subsystems, file counts, and lines of code.
    """
    breakdown = sourcecode_knowledge_engine.get_subsystem_breakdown()
    if subsystem:
        filtered = [s for s in breakdown.get("subsystems", []) if s["subsystem"] == subsystem]
        return {
            "status": "success",
            "subsystem": subsystem,
            "details": filtered[0] if filtered else None
        }
    return {
        "status": "success",
        "data": breakdown
    }
