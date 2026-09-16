from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from core.social_optimizer_engine import generate_social_payload, detect_topic

logger = logging.getLogger("SocialOutreachRouter")
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/social", tags=["Facebook & Social Outreach Optimizer"])

def get_tenant(request: Request) -> str:
    return request.headers.get("x-client-id") or request.headers.get("X-Client-ID") or "stehouwer_publishing"

class SocialOptimizeRequest(BaseModel):
    text: str
    custom_url: Optional[str] = None
    target_platform: Optional[str] = "facebook"
    fire_writing_mode: Optional[bool] = False

@router.post("/optimize")
async def optimize_social_post(req: SocialOptimizeRequest, client_id: str = Depends(get_tenant)):
    """
    Optimizes raw text into long-form vs short-form posts with auto-detected topics,
    Fire Writing immutable transcription, 3-tier mixed hashtag boxes, and first-comment URL drop.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    
    try:
        payload = generate_social_payload(
            req.text, 
            req.custom_url, 
            target_platform=req.target_platform or "facebook",
            fire_writing_mode=bool(req.fire_writing_mode)
        )
        payload["client_id"] = client_id
        payload["platform"] = req.target_platform
        return payload
    except Exception as e:
        logger.error(f"Social optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/topics")
async def get_available_topics():
    """Returns available topic catalogs and default hashtag definitions."""
    from core.social_optimizer_engine import TOPIC_CATALOG
    return {"status": "success", "catalog": TOPIC_CATALOG}
