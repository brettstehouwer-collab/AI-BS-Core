"""
Multi-Agent Specialist Crews Router (Phase 3)
Exposes endpoints for:
- GET /api/v1/agents/crews
- POST /api/v1/agents/route
- POST /api/v1/agents/security/validate
"""

from fastapi import APIRouter, HTTPException, Request
import asyncio
import queue
import threading
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


class HierarchicalRouteRequest(BaseModel):
    prompt: str = Field(..., description="User query or task prompt")
    active_nav_tab: Optional[str] = Field(
        None,
        description="Active mobile bottom nav tab id (chat, project_noco, video_streaming, executive_cockpit, menu)",
    )


class ImmutableScribeVerifyRequest(BaseModel):
    raw_text: str = Field(..., description="Original raw voice dictation or source text")
    formatted_text: str = Field(..., description="Punctuated/formatted output text to verify for 100% word fidelity")


from core.subagent_coordinator import (
    DOMAIN_TAXONOMY,
    HierarchicalDomainRouter,
    PersistentAgentDatabase,
    seed_all_64_specialists,
    verify_immutable_transcription,
)

_specialist_db: Optional[PersistentAgentDatabase] = None
_specialist_db_lock = threading.Lock()
_specialist_coordinator = None
_specialist_coordinator_lock = threading.Lock()


def _get_specialist_coordinator(db):
    """One admission queue per serving process; runtime also holds an OS lock."""
    global _specialist_coordinator
    from core.subagent_coordinator import BoundedSwarmCoordinator
    with _specialist_coordinator_lock:
        if _specialist_coordinator is None or _specialist_coordinator.db is not db:
            _specialist_coordinator = BoundedSwarmCoordinator(db=db)
        return _specialist_coordinator


def _get_specialist_db() -> PersistentAgentDatabase:
    global _specialist_db
    with _specialist_db_lock:
        if _specialist_db is None:
            database = PersistentAgentDatabase()
            existing = database.list_specialists(active_only=False)
            if len(existing) < 64:
                seed_all_64_specialists(database)
            # Concurrent pool callers must never observe an unseeded instance.
            _specialist_db = database
        return _specialist_db


@router.get("/domains")
def list_specialist_domains_endpoint():
    """Returns the 7 operational domains and mobile navigation tab mappings for the 64-specialist catalog."""
    try:
        db = _get_specialist_db()
        all_specs = db.list_specialists(active_only=False)
        tab_counts = {}
        for s in all_specs:
            tab = (s.metadata or {}).get("nav_tab", "chat")
            tab_counts[tab] = tab_counts.get(tab, 0) + 1
        return {
            "status": "success",
            "total_specialists": len(all_specs),
            "domain_count": len(DOMAIN_TAXONOMY),
            "domains": DOMAIN_TAXONOMY,
            "nav_tab_counts": tab_counts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specialists")
def list_64_specialists_endpoint(
    domain_id: Optional[str] = None,
    nav_tab: Optional[str] = None,
    active_only: bool = True,
):
    """Returns the SQLite-backed 64 specialist subagent profiles filtered by domain or mobile nav tab."""
    try:
        db = _get_specialist_db()
        specs = db.list_specialists(active_only=active_only, domain_id=domain_id, nav_tab=nav_tab)
        from core.specialist_execution import check_readiness
        return {
            "status": "success",
            "count": len(specs),
            "filters": {"domain_id": domain_id, "nav_tab": nav_tab, "active_only": active_only},
            "specialists": [
                {
                    "role_index": s.role_index,
                    "agent_id": s.agent_id,
                    "name": s.name,
                    "responsibility": s.responsibility,
                    "concrete_deliverable": s.concrete_deliverable,
                    "engine_target": s.engine_target.value,
                    "model_name": s.model_name,
                    "allowed_tools": s.allowed_tools,
                    "workspace_scope": s.workspace_scope,
                    "completion_check_cmd": s.completion_check_cmd,
                    "check_status": check_readiness(s)[0],
                    "active": s.active,
                    "metadata": s.metadata,
                }
                for s in specs
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/route-hierarchical")
def route_hierarchical_endpoint(req: HierarchicalRouteRequest):
    """Two-tier hierarchical routing across the 7 domains and 64 SQLite-persisted specialists."""
    try:
        db = _get_specialist_db()
        routing = HierarchicalDomainRouter.route(
            db=db,
            prompt=req.prompt,
            active_nav_tab=req.active_nav_tab,
        )
        return {"status": "success", **routing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/immutable-scribe/verify")
async def verify_immutable_scribe_endpoint(req: ImmutableScribeVerifyRequest):
    """Verifies Role 49 (immutable_fire_scribe) verbatim lexical word-token equality."""
    try:
        result = verify_immutable_transcription(req.raw_text, req.formatted_text)
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SealChapterRequest(BaseModel):
    chapter_id: str = Field(..., description="Unique slug or chapter identifier")
    title: str = Field(..., description="Human-readable chapter title")
    raw_text: str = Field(..., description="Exact raw voice dictation text")
    formatted_text: str = Field(..., description="Punctuated chapter text to be verified and sealed")
    author: Optional[str] = Field("Brett Adam Stehouwer", description="Author attribution")


@router.get("/immutable-scribe/chapters")
async def list_sealed_chapters_endpoint():
    """List stored sealing metadata; current artifact bytes are not reverified."""
    from core.immutable_publishing_engine import ImmutablePublishingEngine, PublishingStorageError
    try:
        chapters = await asyncio.to_thread(ImmutablePublishingEngine.list_chapters)
        return {"status": "success", "count": len(chapters), "chapters": chapters,
                "current_integrity": "not_checked"}
    except PublishingStorageError:
        raise HTTPException(status_code=503, detail="Chapter storage is unavailable or needs review; existing files were preserved.")


@router.post("/immutable-scribe/seal")
async def seal_immutable_chapter_endpoint(req: SealChapterRequest):
    """Verifies verbatim fidelity and seals the manuscript chapter to disk."""
    from core.immutable_publishing_engine import (ImmutablePublishingEngine, LexicalIntegrityError,
                                                ChapterConflictError, PublishingStorageError)
    try:
        res = await asyncio.to_thread(ImmutablePublishingEngine.save_verified_chapter,
            chapter_id=req.chapter_id,
            title=req.title,
            raw_text=req.raw_text,
            formatted_text=req.formatted_text,
            author=req.author,
        )
        return res
    except LexicalIntegrityError as le:
        raise HTTPException(status_code=422, detail={"error": str(le), "details": le.details})
    except ChapterConflictError:
        raise HTTPException(status_code=409, detail="The chapter identifier is already sealed or conflicts with another identifier. Use a new identifier for a revision.")
    except PublishingStorageError:
        raise HTTPException(status_code=503, detail="Chapter storage is unavailable or needs review; existing files were preserved.")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


class SpecialistRunGateRequest(BaseModel):
    timeout_sec: Optional[int] = Field(None, ge=1, le=1800, description="Total queue and execution timeout in seconds")
    priority: int = Field(1, ge=1, le=5, description="Execution priority (1-5)")


class _GateCancellation:
    """Remember cancellation even while the worker is still admitting a job."""
    def __init__(self):
        self._lock = threading.Lock()
        self._cancelled = False
        self._coordinator = None
        self._job_id = None

    def bind(self, coordinator, job_id):
        with self._lock:
            self._coordinator, self._job_id = coordinator, job_id
            if self._cancelled:
                coordinator.cancel_job(job_id)

    def cancel(self):
        with self._lock:
            self._cancelled = True
            if self._coordinator is not None:
                self._coordinator.cancel_job(self._job_id)


def _execute_specialist_gate_request(agent_id, req, cancellation):
    """Own blocking registry access, reservation and execution in one worker."""
    db = _get_specialist_db()
    spec = db.get_specialist(agent_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Specialist '{agent_id}' not found in SQLite registry")
    coordinator = _get_specialist_coordinator(db)
    timeout = (req.timeout_sec if req and req.timeout_sec else None) or (
        900 if (spec.metadata or {}).get("domain_id") == "game_development_core" else 60
    )
    priority = req.priority if req and req.priority else 1
    # enqueue_job performs another registry lookup; keep it in this worker too.
    job_id = coordinator.enqueue_job(spec.agent_id, f"UI Gate Run: {spec.name}", priority=priority)
    cancellation.bind(coordinator, job_id)
    return coordinator.execute_verified_check(job_id=job_id, contract=spec, timeout_sec=timeout)


@router.post("/specialists/{agent_id}/run-gate")
async def run_specialist_gate_endpoint(agent_id: str, request: Request, req: Optional[SpecialistRunGateRequest] = None):
    """Executes deterministic verification gate for a registered specialist under bounded semaphore."""
    try:
        cancellation = _GateCancellation()
        task = asyncio.create_task(asyncio.to_thread(_execute_specialist_gate_request, agent_id, req, cancellation))
        try:
            while not task.done():
                if await request.is_disconnected():
                    cancellation.cancel()
                await asyncio.wait({task}, timeout=.1)
            result = await task
        finally:
            # The bounded runner owns child cleanup; cancelling an await does
            # not itself terminate an OS process or its admission reservation.
            if not task.done():
                cancellation.cancel()
                await asyncio.shield(asyncio.gather(task, return_exceptions=True))
        return {"status": "success", "result": result}
    except queue.Full:
        raise HTTPException(status_code=429, detail="The specialist verification queue is full. Try again later.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specialists/{agent_id}/evidence")
def get_specialist_evidence_endpoint(agent_id: str, limit: int = 10):
    """Retrieves historical job evidence records from SQLite for a specialist."""
    try:
        if not 1 <= limit <= 100:
            raise HTTPException(status_code=422, detail="Evidence limit must be between 1 and 100.")
        import sqlite3
        from contextlib import closing
        db = _get_specialist_db()
        with closing(sqlite3.connect(str(db.db_path))) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT job_id, agent_id, engine_target, source_revision,
                       command_executed, returncode, passed, stdout_log,
                       stderr_log, duration_sec, created_at
                FROM agent_job_evidence
                WHERE agent_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            )
            rows = cursor.fetchall()
        evidence = [
            {
                "job_id": r[0],
                "agent_id": r[1],
                "engine_target": r[2],
                "source_revision": r[3],
                "command": r[4],
                "exit_code": r[5],
                "verified_pass": bool(r[6]),
                "stdout_snippet": (r[7] or "")[-500:],
                "error_snippet": (r[8] or "")[-500:],
                "duration_sec": r[9],
                "recorded_at": r[10],
            }
            for r in rows
        ]
        return {"status": "success", "agent_id": agent_id, "count": len(evidence), "evidence": evidence}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



