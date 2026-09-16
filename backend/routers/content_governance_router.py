from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from aibs_reasoning_engine import AIBSRiskGovernanceEngine

router = APIRouter(prefix="/api/v1/content-governance", tags=["Content Governance & Risk Scoring"])

logger = logging.getLogger("ContentGovernanceRouter")

class RiskAnalysisRequest(BaseModel):
    text: str = Field(..., description="Natural language input text to analyze for latent risk and compliance.")
    context_category: Optional[str] = Field("marketing", description="Department context: hr, legal, marketing, sales, executive")
    target_audience: Optional[str] = Field("external_client", description="Target audience: internal_staff, external_client, public_press_release, executive_board")
    custom_threshold: Optional[float] = Field(45.0, description="Custom risk threshold sensitivity percentage (tau)")

class RefinementItem(BaseModel):
    original: str
    refined: str
    reason: str

class RiskAnalysisResponse(BaseModel):
    quantifiable_risk_score: float
    status: str
    status_color: str
    threshold: float
    exceeds_threshold: bool
    target_audience: str
    context_category: str
    vector_breakdown: Dict[str, float]
    refinements: List[RefinementItem]
    executive_summary: str

@router.post("/analyze", response_model=RiskAnalysisResponse)
async def analyze_content_risk(payload: RiskAnalysisRequest):
    """
    Evaluates Quantifiable Risk Score (Sf) across 6 multidimensional vectors,
    calculates dynamic thresholds (tau), and returns executive terminology optimizations.
    """
    try:
        res = AIBSRiskGovernanceEngine.analyze_content_risk(
            text=payload.text,
            context_category=payload.context_category,
            target_audience=payload.target_audience,
            custom_threshold=payload.custom_threshold
        )
        return res
    except Exception as e:
        logger.error(f"Content governance analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def get_governance_categories():
    """Returns available context categories, audience presets, and vector definitions."""
    return {
        "vectors": [
            {"key": "litigation_legal", "label": "Litigation & Legal Liability", "description": "Strict warranties, contractual guarantees, non-compliant disclaimers."},
            {"key": "harassment_hr", "label": "Harassment & HR Policy Risk", "description": "Hostile workplace comments, harassment triggers, unprofessional conduct."},
            {"key": "pr_polarization", "label": "PR & Sociocultural Polarization", "description": "Controversial public relations risks, brand fallout, boycotts."},
            {"key": "discriminatory_sentiment", "label": "Discriminatory Sentiment & Bias", "description": "Age, gender, racial, ability microaggressions or stereotyping."},
            {"key": "confidentiality_databreach", "label": "Confidentiality & Data Breach Risk", "description": "Unintentionally leaking internal passwords, trade secrets, SSN, API keys."},
            {"key": "aggressive_tone", "label": "Aggressive & High-Conflict Tone", "description": "Hostile imperatives, excessive shouting (ALL-CAPS), argumentative tone."}
        ],
        "audiences": [
            {"key": "internal_staff", "label": "Internal Staff / Team"},
            {"key": "external_client", "label": "External Client / Customer"},
            {"key": "public_press_release", "label": "Public Press Release"},
            {"key": "executive_board", "label": "Executive Board / Investors"}
        ],
        "categories": [
            {"key": "marketing", "label": "Marketing & Campaigns"},
            {"key": "sales", "label": "Sales & Client Outreach"},
            {"key": "hr", "label": "Human Resources & Internal"},
            {"key": "legal", "label": "Legal & Contracts"},
            {"key": "executive", "label": "Executive Correspondence"}
        ]
    }
