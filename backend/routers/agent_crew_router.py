"""
Multi-Agent Specialist Crews Router (Phase 3)
Exposes endpoints for:
- GET /api/v1/agents/crews
- POST /api/v1/agents/route
- POST /api/v1/agents/security/validate
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.agent_specialist_crew import AgentSpecialistCrewEngine

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Specialist Crews"])


class RouteSpecialistRequest(BaseModel):
    prompt: str = Field(..., description="User query or task prompt")


class ValidateSecurityRequest(BaseModel):
    command: str = Field(..., description="Command to validate against system policy")


from fastapi.responses import StreamingResponse
from core.sovereign_reasoning.model_domain_matrix import ModelDomainMatrix, MODEL_FLEET_TAXONOMY
from core.sovereign_reasoning.cross_model_bus import CrossModelCognitiveBus

@router.get("/crews")
async def list_crews_endpoint():
    try:
        return AgentSpecialistCrewEngine.get_all_crews()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-matrix")
async def get_model_matrix_endpoint():
    """Returns the full 17-model taxonomy, keyword dictionaries, and domain specializations."""
    try:
        return {
            "status": "success",
            "model_count": len(MODEL_FLEET_TAXONOMY),
            "fleet": MODEL_FLEET_TAXONOMY
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-model")
async def classify_model_endpoint(req: RouteSpecialistRequest):
    """Classifies a prompt across all 17 models, ranking domain affinity and returning cross-model allocation."""
    try:
        crew = ModelDomainMatrix.get_optimal_cross_communication_crew(req.prompt)
        ranked = ModelDomainMatrix.score_prompt_against_fleet(req.prompt)
        return {
            "status": "success",
            "prompt": req.prompt,
            "optimal_crew": crew,
            "ranked_models": ranked
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cross-model/stream")
async def stream_cross_model_endpoint(req: RouteSpecialistRequest):
    """Streams live multi-model cross-communication reasoning (Lead -> Auditor -> Synthesizer)."""
    try:
        return StreamingResponse(
            CrossModelCognitiveBus.stream_cross_model_reasoning(req.prompt),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route")
async def route_specialist_endpoint(req: RouteSpecialistRequest):
    try:
        return AgentSpecialistCrewEngine.route_to_specialist(prompt=req.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/validate")
async def validate_security_endpoint(req: ValidateSecurityRequest):
    try:
        return AgentSpecialistCrewEngine.validate_command_security(command=req.command)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

