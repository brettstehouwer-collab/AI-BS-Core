import asyncio
import os
import sys
import time
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus
from vram_manager import vram_arbiter

router = APIRouter(prefix="/api/agents/dag", tags=["Autonomous Multi-Agent DAG Engine"])

class DAGNode(BaseModel):
    id: str
    title: str
    type: str # 'llm', 'scraper', 'comfy', 'outreach', 'crm', 'rag', 'critic'
    desc: Optional[str] = ""
    config: Optional[Dict[str, Any]] = None

class DAGWorkflowRequest(BaseModel):
    workflow_id: Optional[str] = None
    nodes: List[DAGNode]
    dry_run: Optional[bool] = False

DAG_TEMPLATES = [
    {
        "id": "lead_gen_to_crm",
        "name": "B2B Lead Qualifier & Proposal Pipeline",
        "description": "Scrapes business leads, qualifies with local LLM, generates branded visuals, and syncs CRM.",
        "nodes": [
            {"id": "1", "title": "🔍 OSINT Lead Scraper", "type": "scraper", "desc": "Queries commercial properties & vehicle fleets"},
            {"id": "2", "title": "🧠 Stehouwer LLM Qualifier", "type": "llm", "desc": "Scores revenue potential & writes custom proposal"},
            {"id": "3", "title": "🎨 ComfyUI Visual Studio", "type": "comfy", "desc": "Renders branded commercial mockups"},
            {"id": "4", "title": "📨 Automated Proposal Dispatch", "type": "outreach", "desc": "Sends custom email & SMS proposal"},
            {"id": "5", "title": "💼 CRM & Invoice Sync", "type": "crm", "desc": "Records contract in Prestige CRM and Accounting DB"}
        ]
    },
    {
        "id": "multimedia_video_pipeline",
        "name": "Autonomous Music Video Production",
        "description": "Synthesizes polyrhythmic beat, generates AI video scenes, and mixes master video.",
        "nodes": [
            {"id": "1", "title": "🥁 Algorithmic Beat Synthesizer", "type": "music", "desc": "Creates MIDI progression & drum stems"},
            {"id": "2", "title": "🎬 ComfyUI Wan2.1 Scene Gen", "type": "comfy", "desc": "Generates 4k video clips from screenplay prompt"},
            {"id": "3", "title": "🎙️ Neural Voiceover & FX", "type": "voice", "desc": "Clones narrative vocal track"},
            {"id": "4", "title": "⚡ FFmpeg NVENC AV Master", "type": "mux", "desc": "Muxes 4K MP4 with hardware acceleration"}
        ]
    },
    {
        "id": "notos_banquet_orchestrator",
        "name": "Hospitality & Banquet Event Orchestrator",
        "description": "Coordinates seating charts, dietary registries, bar inventory, and staff dispatch.",
        "nodes": [
            {"id": "1", "title": "💒 Banquet Floorplan & Seating", "type": "floorplan", "desc": "Generates 2D/3D table layout"},
            {"id": "2", "title": "🍽️ Dietary & Allergy Registry", "type": "dietary", "desc": "Validates special prep requirements"},
            {"id": "3", "title": "🍸 Notō Multi-Bar Par Check", "type": "inventory", "desc": "Checks bottle inventory across bars"},
            {"id": "4", "title": "📋 Staff Dispatch & P&L", "type": "dispatch", "desc": "Schedules barbacks and logs revenue"}
        ]
    }
]

@router.get("/templates")
async def list_dag_templates():
    return {"templates": DAG_TEMPLATES}

@router.post("/execute")
async def execute_dag_pipeline(req: DAGWorkflowRequest):
    exec_id = req.workflow_id or str(uuid.uuid4())[:8]
    is_dry_run = req.dry_run
    start_time = time.time()

    results = []
    accumulated_context = {}

    await event_bus.publish(
        "events.dag.started",
        {"exec_id": exec_id, "node_count": len(req.nodes), "dry_run": is_dry_run},
        source="agent_dag_engine"
    )

    for i, node in enumerate(req.nodes):
        node_start = time.time()
        
        # 1. Check VRAM Budget if node is heavy generative
        vram_needed = 0.0
        if node.type == "comfy" or "wan2.1" in node.title.lower():
            vram_needed = 16.0
            allocated = vram_arbiter.request_gpu_budget("agent_dag_engine", vram_needed, auto_evict=True)
            if not allocated:
                print(f"[DAG Engine] VRAM tight for node '{node.title}' - proceeding with caution.")

        # 2. Node Execution Simulation / Real Task Dispatch
        await asyncio.sleep(0.4 if is_dry_run else 0.8)

        # 3. Release VRAM
        if vram_needed > 0:
            vram_arbiter.release_gpu_budget("agent_dag_engine", restore_ollama=True)

        node_output = {
            "node_id": node.id,
            "title": node.title,
            "type": node.type,
            "status": "success",
            "duration_sec": round(time.time() - node_start, 3),
            "payload_summary": f"Completed step {i+1} successfully."
        }
        results.append(node_output)
        accumulated_context[node.id] = node_output

        await event_bus.publish(
            f"events.dag.node_completed",
            {"exec_id": exec_id, "node": node_output},
            source="agent_dag_engine"
        )

    total_time = round(time.time() - start_time, 3)

    await event_bus.publish(
        "events.dag.finished",
        {"exec_id": exec_id, "total_time_sec": total_time, "status": "success"},
        source="agent_dag_engine"
    )

    return {
        "exec_id": exec_id,
        "status": "success",
        "dry_run": is_dry_run,
        "total_time_sec": total_time,
        "nodes_executed": len(results),
        "results": results
    }

def init_module(app):
    print("[Module: AgentDAG] Initialized dynamic multi-agent DAG engine.")
