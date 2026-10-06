#!/usr/bin/env python3
"""
AI-BS Sovereign Intelligence Ecosystem - Unreal Engine 5.8+ Native MCP Router
Bridges the local Unreal Editor Model Context Protocol (Port 8000) and On-Demand Launcher
into the AI-BS Executive Studio and Media Production Suite.
"""

import os
import sys
import json
import logging
import subprocess
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, BackgroundTasks

logger = logging.getLogger("UnrealMcpRouter")

router = APIRouter(prefix="/api/v1/unreal", tags=["unreal_mcp"])

_root_dir = Path(__file__).resolve().parent.parent.parent
UNREAL_LAUNCHER_BAT = _root_dir / "Launch_Unreal_OnDemand.bat"
UNREAL_ASSETS_FILE = _root_dir / "all_unreal_assets.txt"
DEFAULT_MCP_URL = "http://127.0.0.1:8000/mcp"


class McpRpcRequest(BaseModel):
    method: str = Field(..., description="MCP tool or JSON-RPC method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")


class SpawnCameraRequest(BaseModel):
    camera_name: str = Field(default="CineCameraActor_AIBS_Master", description="Name of the spawned camera actor")
    location: List[float] = Field(default=[0.0, 0.0, 150.0], description="[X, Y, Z] world location")
    rotation: List[float] = Field(default=[0.0, 0.0, 0.0], description="[Pitch, Yaw, Roll] rotation")
    focal_length: float = Field(default=35.0, description="Focal length in mm")


class SequencerTriggerRequest(BaseModel):
    sequence_path: Optional[str] = Field(default=None, description="Path to LevelSequence asset in Unreal")
    action: str = Field(default="play", description="play | pause | stop | record")


def _is_unreal_editor_running() -> bool:
    """Checks if UnrealEditor.exe process is currently active."""
    try:
        import psutil
        for p in psutil.process_iter(['name']):
            if p.info['name'] and 'UnrealEditor' in p.info['name']:
                return True
    except Exception:
        pass
    return False


def _check_mcp_server_alive(url: str = DEFAULT_MCP_URL) -> bool:
    """Sends a ping/health request to Unreal Engine's native MCP server."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AI-BS-Core/5.311.0", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as response:
            return response.status in (200, 204)
    except urllib.error.HTTPError as e:
        # A 400, 404, or 405 still confirms the HTTP server is bound and listening
        return e.code in (200, 400, 404, 405)
    except Exception:
        return False


@router.get("/status")
async def get_unreal_status() -> Dict[str, Any]:
    """Returns the live connection status of Unreal Engine 5.8 and its native MCP server."""
    is_proc_running = _is_unreal_editor_running()
    is_mcp_alive = _check_mcp_server_alive()

    return {
        "unreal_editor_running": is_proc_running,
        "mcp_server_online": is_mcp_alive,
        "mcp_url": DEFAULT_MCP_URL,
        "engine_version": "Unreal Engine 5.8",
        "project_path": "C:\\AI-BS\\UnrealHub\\AI_BS_Hub.uproject",
        "recommended_action": "ready" if is_mcp_alive else ("waiting_for_mcp" if is_proc_running else "launch_required")
    }


@router.post("/launch")
async def launch_unreal_on_demand(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Triggers Launch_Unreal_OnDemand.bat to start Unreal Engine 5.8 in the background."""
    if _is_unreal_editor_running():
        return {
            "status": "already_running",
            "message": "UnrealEditor.exe is already active on the system."
        }

    if not UNREAL_LAUNCHER_BAT.exists():
        raise HTTPException(status_code=404, detail="Launch_Unreal_OnDemand.bat not found in AI-BS root.")

    def run_launcher():
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", str(UNREAL_LAUNCHER_BAT)],
                cwd=str(_root_dir),
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            logger.error(f"Failed to launch Unreal on demand: {e}")

    background_tasks.add_task(run_launcher)

    return {
        "status": "launching",
        "message": "Unreal Engine 5.8 on-demand launch initiated.",
        "script": str(UNREAL_LAUNCHER_BAT)
    }


@router.get("/assets")
async def list_unreal_assets(
    query: str = "",
    category: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Searches the indexed local Unreal Engine assets catalog (5,200+ items).
    Supports filtering by query and category (Blueprints, Animation, ArtTools, Materials).
    """
    if not UNREAL_ASSETS_FILE.exists():
        return {"total": 0, "results": [], "categories": []}

    results = []
    matched_count = 0
    categories_set = set()

    q_lower = query.strip().lower()
    cat_lower = (category or "").strip().lower()

    try:
        with open(UNREAL_ASSETS_FILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                path = line.strip()
                if not path or path.startswith("FullName") or path.startswith("---"):
                    continue

                # Deduce category from directory hierarchy
                parts = path.replace("\\", "/").split("/")
                cat = "General"
                for idx, p in enumerate(parts):
                    if p.lower() in ("animation", "arttools", "blueprints", "materials", "engine", "editor"):
                        cat = p.capitalize()
                        break
                categories_set.add(cat)

                if cat_lower and cat.lower() != cat_lower:
                    continue

                if q_lower and q_lower not in path.lower():
                    continue

                matched_count += 1
                if len(results) < limit:
                    asset_name = os.path.splitext(os.path.basename(path))[0]
                    results.append({
                        "asset_name": asset_name,
                        "category": cat,
                        "full_path": path
                    })
    except Exception as e:
        logger.error(f"Error reading unreal assets: {e}")

    return {
        "total_matched": matched_count,
        "returned": len(results),
        "categories": sorted(list(categories_set)),
        "results": results
    }


@router.post("/rpc")
async def execute_mcp_rpc(payload: McpRpcRequest) -> Dict[str, Any]:
    """Forwards a raw JSON-RPC tool invocation to Unreal Engine's native MCP server."""
    if not _check_mcp_server_alive():
        return {
            "success": False,
            "error": "Unreal Engine native MCP server (Port 8000) is unreachable.",
            "fallback_available": True
        }

    rpc_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": payload.method,
        "params": payload.params
    }

    try:
        req = urllib.request.Request(
            DEFAULT_MCP_URL,
            data=json.dumps(rpc_data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"success": True, "response": data}
    except Exception as e:
        return {"success": False, "error": str(e), "fallback_available": True}


@router.post("/camera/spawn")
async def spawn_cinematic_camera(req: SpawnCameraRequest) -> Dict[str, Any]:
    """High-level helper to spawn and orient a Cine Camera Actor for virtual production."""
    rpc_payload = McpRpcRequest(
        method="spawn_actor",
        params={
            "class": "CineCameraActor",
            "name": req.camera_name,
            "location": req.location,
            "rotation": req.rotation,
            "properties": {
                "CurrentFocalLength": req.focal_length
            }
        }
    )
    return await execute_mcp_rpc(rpc_payload)


@router.post("/sequencer/trigger")
async def trigger_sequencer(req: SequencerTriggerRequest) -> Dict[str, Any]:
    """High-level helper to command Unreal Sequencer playback or Take Recorder capture."""
    rpc_payload = McpRpcRequest(
        method="sequencer_action",
        params={
            "sequence_path": req.sequence_path,
            "action": req.action
        }
    )
    return await execute_mcp_rpc(rpc_payload)
