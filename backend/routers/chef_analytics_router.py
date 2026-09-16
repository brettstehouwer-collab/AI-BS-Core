"""
The Simple Chef - Analytics & Sovereign Hosting Retainer Router
Mounted at /api/v1/chef/analytics on Port 8080
"""

from fastapi import APIRouter, Request, Query, HTTPException
from typing import Optional, Dict, Any
from backend.core.thesimplechef_analytics_daemon import analytics_daemon

router = APIRouter(prefix="/api/v1/chef/analytics", tags=["The Simple Chef Analytics"])

@router.get("/overview")
def get_analytics_overview():
    """Returns real-time privacy-first visitor metrics and top meals/rubs from ChromaDB"""
    return {
        "success": True,
        "data": analytics_daemon.get_analytics_summary()
    }

@router.get("/semantic-insights")
def get_semantic_insights(query: str = Query("popular dinners and seasonings", description="Semantic query text")):
    """Performs cosine similarity search against visitor journey embeddings in ChromaDB"""
    results = analytics_daemon.query_semantic_insights(query, n_results=5)
    return {
        "success": True,
        "query": query,
        "insights": results
    }

@router.post("/ingest-event")
async def ingest_visitor_event(payload: Dict[str, Any], request: Request):
    """Ingests client storefront interaction and vectorizes into thesimplechef_analytics_bin"""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Mozilla/5.0")
    
    event_data = {
        "ip": payload.get("ip") or client_ip,
        "user_agent": payload.get("user_agent") or user_agent,
        "path": payload.get("path", "/"),
        "event_type": payload.get("event_type", "page_view"),
        "item_name": payload.get("item_name", "General Storefront"),
        "referrer": payload.get("referrer", "direct"),
        "session_id": payload.get("session_id")
    }
    
    event_id = analytics_daemon.ingest_event(event_data)
    return {
        "success": bool(event_id),
        "event_id": event_id,
        "anonymized_ip": analytics_daemon.anonymize_ip(event_data["ip"])
    }

@router.get("/monthly-report")
def get_monthly_client_report():
    """Returns executive monthly traffic & infrastructure briefing for John Barr's retainer"""
    return {
        "success": True,
        "report": analytics_daemon.generate_monthly_client_report()
    }
