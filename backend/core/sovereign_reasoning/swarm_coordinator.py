#!/usr/bin/env python3
"""
Sovereign Swarm Handoff Coordinator Subsystem
AI-BS Antigravity Sovereign Unison Architecture
Orchestrates collaborative multi-agent execution pipelines across the 14-tool sovereign suite.
Supports 1-click sovereign presets, dynamic MoE auto-routing, and sequential inter-agent context passing.
"""

import os
import sys
import json
import time
import uuid
import asyncio
import sqlite3
import logging
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("swarm_coordinator")

_backend_dir = Path(__file__).resolve().parent.parent.parent
_root_dir = _backend_dir.parent
DB_PATH = _root_dir / "saved_data" / "agent_harness_sessions.db"

# 1-Click Sovereign Swarm Pipelines Catalog
SWARM_PRESETS: Dict[str, Dict[str, Any]] = {
    "full_feature_sprint": {
        "id": "full_feature_sprint",
        "name": "Full Feature Sprint",
        "tagline": "Architect -> Coder -> Verifier -> Release Sentinel",
        "description": "End-to-end 4-stage pipeline: Hermes drafts specs, Claude Code writes code, OpenCode runs pytest verifications, and Hermes Desktop audits parity.",
        "steps": [
            {
                "step_index": 1,
                "role": "Architect & Spec Author",
                "app_id": "hermes_agent",
                "domain": "function_calling",
                "system_prompt": "You are the Lead Systems Architect. Break down the user's objective into technical implementation specifications, component boundaries, and verification criteria."
            },
            {
                "step_index": 2,
                "role": "Lead Code Synthesizer",
                "app_id": "claude_code",
                "domain": "code",
                "system_prompt": "You are the Senior Systems Coder. Using the architectural spec provided, write clean, robust, production-grade implementation code and diffs."
            },
            {
                "step_index": 3,
                "role": "Test & Execution Verifier",
                "app_id": "opencode",
                "domain": "code",
                "system_prompt": "You are the Verification Engineer. Formulate pytest test assertions, verify edge cases, and inspect execution boundaries."
            },
            {
                "step_index": 4,
                "role": "Release Sentinel & Auditor",
                "app_id": "hermes_desktop",
                "domain": "function_calling",
                "system_prompt": "You are the Sovereign Release Sentinel. Audit workspace integrity, confirm multi-mirror parity requirements, and finalize the release handoff."
            }
        ]
    },
    "rapid_bug_fix": {
        "id": "rapid_bug_fix",
        "name": "Rapid Bug Fix & Verification",
        "tagline": "Qwen Coder -> Pytest Verifier",
        "description": "Fast 2-stage cycle: Qwen Coder diagnoses root causes and generates targeted patches, followed by immediate pytest execution.",
        "steps": [
            {
                "step_index": 1,
                "role": "Diagnostic & Patch Coder",
                "app_id": "codex_cli",
                "domain": "code",
                "system_prompt": "You are the Patch Engineer. Analyze the failure or bug description, locate the flaw, and write a precise, surgical patch."
            },
            {
                "step_index": 2,
                "role": "Regression Tester",
                "app_id": "opencode",
                "domain": "code",
                "system_prompt": "You are the Regression Tester. Verify the fix against known edge cases and define automated test assertions."
            }
        ]
    },
    "repo_audit_parity": {
        "id": "repo_audit_parity",
        "name": "Repo Audit & Parity Sync",
        "tagline": "Hermes Desktop -> Terminal Sentinel",
        "description": "2-stage workspace audit: Inspects filesystem state, active daemons, and 4-mirror frontend SHA-256 byte parity.",
        "steps": [
            {
                "step_index": 1,
                "role": "Filesystem Inspector",
                "app_id": "hermes_desktop",
                "domain": "function_calling",
                "system_prompt": "You are the Workspace Inspector. Review active ports, database tables, and modified frontend components across mirrors."
            },
            {
                "step_index": 2,
                "role": "Parity Verifier",
                "app_id": "terminal",
                "domain": "code",
                "system_prompt": "You are the Terminal Sentinel. Summarize verification results, check parity integrity, and formulate remediation commands."
            }
        ]
    }
}


class SwarmHandoffCoordinator:
    """
    Coordinates collaborative multi-agent handoffs with context chaining,
    step-by-step progress tracking, and SQLite state persistence.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_sqlite_schema()

    def _init_sqlite_schema(self):
        """Initializes tables for swarm pipeline execution tracking."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS swarm_pipeline_runs (
                        job_id TEXT PRIMARY KEY,
                        preset_id TEXT,
                        status TEXT NOT NULL,
                        current_step INTEGER DEFAULT 0,
                        total_steps INTEGER NOT NULL,
                        input_prompt TEXT NOT NULL,
                        results_json TEXT,
                        error_message TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS swarm_step_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        step_index INTEGER NOT NULL,
                        role TEXT NOT NULL,
                        app_id TEXT NOT NULL,
                        model_used TEXT,
                        input_context TEXT,
                        output_content TEXT,
                        elapsed_ms REAL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES swarm_pipeline_runs(job_id)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing swarm coordinator database schema: {e}")

    def list_presets(self) -> List[Dict[str, Any]]:
        """Returns all available 1-click swarm pipeline presets."""
        return list(SWARM_PRESETS.values())

    def get_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific preset definition by ID."""
        return SWARM_PRESETS.get(preset_id)

    def create_job(self, input_prompt: str, preset_id: Optional[str] = "full_feature_sprint", custom_steps: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Creates and records a new swarm execution run."""
        job_id = f"swarm_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        if custom_steps:
            steps = custom_steps
            preset_name = "custom_dynamic"
        elif preset_id and preset_id in SWARM_PRESETS:
            steps = SWARM_PRESETS[preset_id]["steps"]
            preset_name = preset_id
        else:
            # Fallback to full feature sprint
            steps = SWARM_PRESETS["full_feature_sprint"]["steps"]
            preset_name = "full_feature_sprint"

        total_steps = len(steps)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO swarm_pipeline_runs
                (job_id, preset_id, status, current_step, total_steps, input_prompt, results_json, created_at, updated_at)
                VALUES (?, ?, 'pending', 0, ?, ?, '[]', ?, ?)
            """, (job_id, preset_name, total_steps, input_prompt, now, now))
            conn.commit()

        return {
            "job_id": job_id,
            "preset_id": preset_name,
            "status": "pending",
            "current_step": 0,
            "total_steps": total_steps,
            "input_prompt": input_prompt,
            "created_at": now
        }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Queries the current status and step history of a swarm job."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM swarm_pipeline_runs WHERE job_id = ?", (job_id,))
            run_row = cursor.fetchone()
            if not run_row:
                return None

            cursor.execute("SELECT * FROM swarm_step_logs WHERE job_id = ? ORDER BY step_index ASC", (job_id,))
            step_rows = cursor.fetchall()

            data = dict(run_row)
            data["steps"] = [dict(s) for s in step_rows]
            if data.get("results_json"):
                try:
                    data["results"] = json.loads(data["results_json"])
                except Exception:
                    data["results"] = []
            return data

    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Lists recent swarm execution runs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM swarm_pipeline_runs ORDER BY updated_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    async def execute_job_stream(
        self,
        job_id: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Executes a swarm pipeline step-by-step, streaming real-time events for each agent stage
        and context handoff. Yields structured status and chunk dictionaries.
        """
        job = self.get_job_status(job_id)
        if not job:
            yield {"type": "error", "message": f"Job {job_id} not found"}
            return

        preset_id = job.get("preset_id")
        steps = []
        if preset_id and preset_id in SWARM_PRESETS:
            steps = SWARM_PRESETS[preset_id]["steps"]
        else:
            steps = SWARM_PRESETS["full_feature_sprint"]["steps"]

        total_steps = len(steps)
        input_prompt = job["input_prompt"]
        context_accumulator: List[Dict[str, Any]] = []

        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE swarm_pipeline_runs SET status = 'running', updated_at = ? WHERE job_id = ?", (now, job_id))
            conn.commit()

        yield {
            "type": "job_start",
            "job_id": job_id,
            "preset_id": preset_id,
            "total_steps": total_steps,
            "input_prompt": input_prompt
        }

        from core.sovereign_reasoning.moe_specialist_router import moe_router

        for step in steps:
            step_idx = step["step_index"]
            role_name = step["role"]
            app_id = step["app_id"]
            domain = step.get("domain", "code")
            system_prompt = step["system_prompt"]

            yield {
                "type": "step_start",
                "job_id": job_id,
                "step_index": step_idx,
                "role": role_name,
                "app_id": app_id,
                "domain": domain
            }

            # Build enriched context from previous steps
            if context_accumulator:
                chain_history = "\n\n---\n".join([
                    f"### Output from Step {item['step_index']} ({item['role']} - {item['app_id']}):\n{item['output']}"
                    for item in context_accumulator
                ])
                effective_prompt = (
                    f"## User Goal:\n{input_prompt}\n\n"
                    f"## Prior Collaborative Agent Work:\n{chain_history}\n\n"
                    f"## Your Task as {role_name} ({app_id}):\n"
                    f"Build directly upon the previous outputs to fulfill your responsibility."
                )
            else:
                effective_prompt = f"## User Goal:\n{input_prompt}\n\n## Your Task as {role_name} ({app_id}):\nExecute your initial phase of the objective."

            # Query MoE router
            start_t = time.perf_counter()
            try:
                dispatch_res = await moe_router.dispatch(
                    prompt=effective_prompt,
                    system_prompt=system_prompt,
                    domain_hint=domain
                )
                elapsed_ms = (time.perf_counter() - start_t) * 1000
                content = dispatch_res.get("response", "")
                model_used = dispatch_res.get("model", "sovereign_local")
                step_status = "completed"
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_t) * 1000
                content = f"Step execution error: {str(e)}"
                model_used = "error"
                step_status = "failed"
                logger.error(f"Error during swarm step {step_idx} ({role_name}): {e}")

            step_record = {
                "step_index": step_idx,
                "role": role_name,
                "app_id": app_id,
                "output": content,
                "model_used": model_used,
                "elapsed_ms": elapsed_ms,
                "status": step_status
            }
            context_accumulator.append(step_record)

            # Record step log in SQLite
            step_now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO swarm_step_logs
                    (job_id, step_index, role, app_id, model_used, input_context, output_content, elapsed_ms, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, step_idx, role_name, app_id, model_used,
                    effective_prompt[:1000], content, elapsed_ms, step_status, step_now
                ))
                conn.execute("""
                    UPDATE swarm_pipeline_runs
                    SET current_step = ?, results_json = ?, updated_at = ?
                    WHERE job_id = ?
                """, (step_idx, json.dumps(context_accumulator), step_now, job_id))
                conn.commit()

            yield {
                "type": "step_complete",
                "job_id": job_id,
                "step_index": step_idx,
                "role": role_name,
                "app_id": app_id,
                "model_used": model_used,
                "elapsed_ms": elapsed_ms,
                "output": content,
                "status": step_status
            }

            if step_status == "failed":
                break

        # Finalize job
        final_now = datetime.now(timezone.utc).isoformat()
        overall_status = "completed" if all(s["status"] == "completed" for s in context_accumulator) else "partial_failure"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE swarm_pipeline_runs
                SET status = ?, results_json = ?, updated_at = ?
                WHERE job_id = ?
            """, (overall_status, json.dumps(context_accumulator), final_now, job_id))
            conn.commit()

        yield {
            "type": "job_complete",
            "job_id": job_id,
            "status": overall_status,
            "total_steps": total_steps,
            "completed_steps": len(context_accumulator),
            "results": context_accumulator
        }


# Global singleton coordinator
swarm_coordinator = SwarmHandoffCoordinator()

if __name__ == "__main__":
    print("Testing Swarm Handoff Coordinator...")
    presets = swarm_coordinator.list_presets()
    print(f"Loaded {len(presets)} swarm presets:")
    for p in presets:
        print(f" - [{p['id']}] {p['name']} ({len(p['steps'])} steps)")
