"""
Autonomous Optimization, Graph Memory & Digital Twin Router (Phases 4 & 5)
Exposes endpoints for:
- POST /api/v1/swarm/code/refine
- POST /api/v1/swarm/graph/record
- GET /api/v1/swarm/graph/query
- POST /api/v1/swarm/digital-twin/sync
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from core.autonomous_swarm_graph_engine import AutonomousSwarmGraphEngine

router = APIRouter(prefix="/api/v1/swarm", tags=["Autonomous Swarm & Graph Memory"])


class CodeRefineRequest(BaseModel):
    code: str = Field(..., description="Python code to test and auto-refine in sandbox")
    script_name: str = Field(default="sandbox_task.py", description="Target script filename")


class GraphRecordRequest(BaseModel):
    source_name: str = Field(..., description="Source entity name")
    source_type: str = Field(..., description="Source entity category")
    relation: str = Field(..., description="Relationship label")
    target_name: str = Field(..., description="Target entity name")
    target_type: str = Field(..., description="Target entity category")
    attributes: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class DigitalTwinSyncRequest(BaseModel):
    telemetry_payload: Dict[str, Any] = Field(..., description="Dictionary of live edge/sensor telemetry")
    target_ue5_port: int = Field(default=8888, description="Unreal Engine Signaling port")


@router.post("/code/refine")
async def refine_code_endpoint(req: CodeRefineRequest):
    try:
        return AutonomousSwarmGraphEngine.refine_and_test_code(
            code=req.code,
            script_name=req.script_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/record")
async def record_graph_endpoint(req: GraphRecordRequest):
    try:
        return AutonomousSwarmGraphEngine.record_graph_relation(
            source_name=req.source_name,
            source_type=req.source_type,
            relation=req.relation,
            target_name=req.target_name,
            target_type=req.target_type,
            attributes=req.attributes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/query")
async def query_graph_endpoint(query: str):
    try:
        return AutonomousSwarmGraphEngine.query_graph_relations(query_name=query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/digital-twin/sync")
async def digital_twin_sync_endpoint(req: DigitalTwinSyncRequest):
    try:
        return AutonomousSwarmGraphEngine.sync_digital_twin_telemetry(
            telemetry_payload=req.telemetry_payload,
            target_ue5_port=req.target_ue5_port
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
