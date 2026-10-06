#!/usr/bin/env python3
"""
Sovereign Agent Harness FastAPI Router
AI-BS Port 8080 Endpoint Matrix for Sovereign Agent Applications
Exposes session management, app catalog, and multi-turn execution for the 14 agent tools.
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Query, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

try:
    from modules.agent_harness_runner import agent_harness_runner
    from core.sovereign_reasoning.swarm_coordinator import swarm_coordinator
except ImportError:
    import sys
    import os
    _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)
    from modules.agent_harness_runner import agent_harness_runner
    from core.sovereign_reasoning.swarm_coordinator import swarm_coordinator

router = APIRouter(prefix="/api/v1/agent-harness", tags=["Sovereign Agent Harness"])
logger = logging.getLogger("agent_harness_router")


class CreateSessionRequest(BaseModel):
    app_id: str
    workspace_path: Optional[str] = None


class TurnRequest(BaseModel):
    prompt: str
    system_override: Optional[str] = None


@router.get("/apps")
async def list_agent_apps():
    """Returns the catalog of 14 sovereign agent applications with capabilities and status."""
    try:
        apps = agent_harness_runner.list_apps()
        return {
            "status": "success",
            "count": len(apps),
            "apps": apps
        }
    except Exception as e:
        logger.error(f"Error listing agent apps: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_agent_sessions(
    app_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Lists recent agent sessions, optionally filtered by application ID."""
    try:
        sessions = agent_harness_runner.list_sessions(app_id=app_id, limit=limit)
        return {
            "status": "success",
            "count": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error listing agent sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/create")
async def create_agent_session(payload: CreateSessionRequest):
    """Initializes a new active agent session."""
    try:
        session = agent_harness_runner.create_session(
            app_id=payload.app_id,
            workspace_path=payload.workspace_path
        )
        return {
            "status": "success",
            "session": session
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating agent session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_agent_session(session_id: str):
    """Retrieves session metadata and full message history."""
    try:
        session = agent_harness_runner.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {
            "status": "success",
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/turn")
async def execute_turn_in_session(session_id: str, payload: TurnRequest):
    """Submits a user prompt to an active agent session and returns the specialist response."""
    try:
        result = await agent_harness_runner.execute_turn(
            session_id=session_id,
            prompt=payload.prompt,
            system_override=payload.system_override
        )
        return {
            "status": "success",
            "turn": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing turn in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def terminate_agent_session(session_id: str):
    """Archives/terminates an active session."""
    try:
        success = agent_harness_runner.terminate_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return {
            "status": "success",
            "message": f"Session {session_id} terminated."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating agent session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# TRIPLE-TIER HYBRID STREAMING (WEBSOCKET + SSE FALLBACK)
# =============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_agent_session(websocket: WebSocket, session_id: str):
    """
    Tier 1 Streaming: High-speed bidirectional WebSocket connection for live agent sessions.
    Streams token-by-token LLM output and line-by-line subprocess logs directly to the UI.
    """
    await websocket.accept()
    logger.info(f"[AgentWS] Client connected to session {session_id}")
    try:
        session = agent_harness_runner.get_session(session_id)
        if not session:
            await websocket.send_json({"type": "error", "message": f"Session {session_id} not found."})
            await websocket.close()
            return

        # Send connection ACK with current turn count and app info
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "app_id": session["app_id"],
            "turn_count": session["turn_count"]
        })

        while True:
            data = await websocket.receive_json()
            action = data.get("action", "turn")

            if action == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if action == "turn":
                prompt = data.get("prompt", "")
                system_override = data.get("system_override")
                if not prompt.strip():
                    await websocket.send_json({"type": "error", "message": "Empty prompt provided."})
                    continue

                # Stream token-by-token and log-by-log
                async for event in agent_harness_runner.stream_turn(
                    session_id=session_id,
                    prompt=prompt,
                    system_override=system_override
                ):
                    await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info(f"[AgentWS] Client disconnected gracefully from session {session_id}")
    except Exception as e:
        logger.error(f"[AgentWS] Error in session {session_id} WebSocket: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.get("/session/{session_id}/stream")
async def sse_agent_session_stream(
    session_id: str,
    prompt: str = Query(..., description="User prompt to execute"),
    system_override: Optional[str] = Query(default=None)
):
    """
    Tier 2 Streaming: Server-Sent Events (SSE) fallback stream.
    Used when WebSocket connections cannot be established.
    """
    session = agent_harness_runner.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    async def event_generator():
        try:
            async for event in agent_harness_runner.stream_turn(
                session_id=session_id,
                prompt=prompt,
                system_override=system_override
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# =============================================================================
# MULTI-AGENT SWARM HANDOFF COORDINATION ENDPOINTS
# =============================================================================

class SwarmExecuteRequest(BaseModel):
    prompt: str
    preset_id: Optional[str] = "full_feature_sprint"
    custom_steps: Optional[List[Dict[str, Any]]] = None


@router.get("/swarm/presets")
async def list_swarm_presets():
    """Returns available 1-click sovereign swarm pipeline presets."""
    try:
        presets = swarm_coordinator.list_presets()
        return {
            "status": "success",
            "count": len(presets),
            "presets": presets
        }
    except Exception as e:
        logger.error(f"Error listing swarm presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/swarm/execute")
async def execute_swarm_pipeline(payload: SwarmExecuteRequest):
    """Initiates a new multi-agent swarm collaborative execution run."""
    try:
        job = swarm_coordinator.create_job(
            input_prompt=payload.prompt,
            preset_id=payload.preset_id,
            custom_steps=payload.custom_steps
        )
        return {
            "status": "success",
            "job": job
        }
    except Exception as e:
        logger.error(f"Error creating swarm pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/swarm/jobs")
async def list_swarm_jobs(limit: int = Query(default=20, ge=1, le=100)):
    """Lists recorded multi-agent swarm runs."""
    try:
        jobs = swarm_coordinator.list_jobs(limit=limit)
        return {
            "status": "success",
            "count": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        logger.error(f"Error listing swarm jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/swarm/jobs/{job_id}")
async def get_swarm_job(job_id: str):
    """Retrieves current execution status, logs, and step outputs for a swarm job."""
    try:
        job = swarm_coordinator.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        return {
            "status": "success",
            "job": job
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving swarm job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/swarm/jobs/{job_id}/stream")
async def stream_swarm_job(job_id: str):
    """Streams step-by-step agent handoff events for a swarm job via SSE."""
    job = swarm_coordinator.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    async def sse_gen():
        try:
            async for event in swarm_coordinator.execute_job_stream(job_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(sse_gen(), media_type="text/event-stream")


@router.websocket("/swarm/ws/{job_id}")
async def websocket_swarm_job(websocket: WebSocket, job_id: str):
    """WebSocket stream for real-time multi-agent swarm execution."""
    await websocket.accept()
    try:
        job = swarm_coordinator.get_job_status(job_id)
        if not job:
            await websocket.send_json({"type": "error", "message": f"Job {job_id} not found"})
            await websocket.close()
            return

        async for event in swarm_coordinator.execute_job_stream(job_id):
            await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info(f"[SwarmWS] Client disconnected from job {job_id}")
    except Exception as e:
        logger.error(f"[SwarmWS] Error streaming job {job_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

