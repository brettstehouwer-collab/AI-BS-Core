#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Sovereign Swarm Coordinator, Host Streaming, and VRAM Failover
AI-BS Antigravity Sovereign Unison Architecture
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

# Ensure root and backend are on sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend = os.path.join(_root, "backend")
if _root not in sys.path:
    sys.path.insert(0, _root)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from core.sovereign_reasoning.swarm_coordinator import (
    swarm_coordinator,
    SWARM_PRESETS
)
from modules.agent_harness_runner import (
    agent_harness_runner,
    AGENT_APPS_CATALOG
)
from core.vram_resource_arbiter import VRAMResourceArbiter


def test_swarm_presets_integrity():
    """Verify standard presets exist and configure valid sovereign agent steps."""
    presets = swarm_coordinator.list_presets()
    preset_ids = [p["id"] for p in presets]
    
    expected_presets = ["full_feature_sprint", "rapid_bug_fix", "repo_audit_parity"]
    for pid in expected_presets:
        assert pid in preset_ids, f"Preset {pid} missing from coordinator"
        
        p_def = swarm_coordinator.get_preset(pid)
        assert p_def is not None
        assert "steps" in p_def
        assert len(p_def["steps"]) >= 2
        
        for step in p_def["steps"]:
            assert "step_index" in step
            assert "role" in step
            assert "app_id" in step
            assert step["app_id"] in AGENT_APPS_CATALOG, f"Unknown app_id {step['app_id']} in preset {pid}"
            assert "system_prompt" in step


def test_swarm_job_creation_and_lifecycle():
    """Verify job record creation, status retrieval, and listing."""
    prompt = "Synthesize and verify an autonomous telemetry monitor."
    job = swarm_coordinator.create_job(prompt, preset_id="rapid_bug_fix")
    
    assert job is not None
    assert "job_id" in job
    job_id = job["job_id"]
    assert job["preset_id"] == "rapid_bug_fix"
    assert job["total_steps"] == 2
    assert job["status"] == "pending"

    # Status check
    status = swarm_coordinator.get_job_status(job_id)
    assert status is not None
    assert status["job_id"] == job_id
    assert status["input_prompt"] == prompt
    assert status["current_step"] == 0

    # Job listing
    recent_jobs = swarm_coordinator.list_jobs(limit=10)
    assert any(j["job_id"] == job_id for j in recent_jobs)


def test_swarm_custom_steps_job():
    """Verify support for custom dynamic step chains."""
    custom_steps = [
        {
            "step_index": 1,
            "role": "Lead Architect",
            "app_id": "hermes_agent",
            "domain": "function_calling",
            "system_prompt": "Plan architecture."
        },
        {
            "step_index": 2,
            "role": "Lead Coder",
            "app_id": "claude_code",
            "domain": "code",
            "system_prompt": "Write code."
        },
        {
            "step_index": 3,
            "role": "QA Sentinel",
            "app_id": "terminal",
            "domain": "code",
            "system_prompt": "Audit repo."
        }
    ]
    job = swarm_coordinator.create_job("Build custom system", custom_steps=custom_steps)
    assert job["preset_id"] == "custom_dynamic"
    assert job["total_steps"] == 3


@pytest.mark.anyio
async def test_host_command_execution_streaming():
    """Verify unrestricted host command streaming and executive action audit recording."""
    test_str = "AI_BS_SOVEREIGN_UNISON_TEST_TOKEN"
    events = []
    
    async for event in agent_harness_runner.execute_host_command(f"Write-Output '{test_str}'"):
        events.append(event)
        
    log_lines = [e.get("line", "") for e in events if e.get("type") in ("stdout", "log")]
    full_output = " ".join(log_lines)
    assert test_str in full_output
    
    # Assert command completion and exit code was emitted
    done_events = [e for e in events if e.get("type") == "command_done"]
    assert len(done_events) == 1
    assert done_events[0]["exit_code"] == 0


def test_compute_target_vram_failover():
    """Verify dynamic compute target resolution and CPU failover when VRAM pressure is exceeded."""
    # Standard check
    normal_target = VRAMResourceArbiter.check_compute_target(min_free_mb=100.0)
    assert "node" in normal_target
    assert "port" in normal_target
    assert "url" in normal_target
    assert isinstance(normal_target["failover_active"], bool)

    # Force failover check by requiring an impossibly high free VRAM threshold (e.g. 100 GB)
    failover_target = VRAMResourceArbiter.check_compute_target(min_free_mb=999999.0)
    assert failover_target["node"] == "cpu"
    assert failover_target["port"] == 11435
    assert failover_target["url"] == "http://127.0.0.1:11435"
    assert failover_target["failover_active"] is True


@pytest.mark.anyio
async def test_swarm_job_stream_mocked():
    """Verify step-by-step swarm event streaming with context handoffs."""
    prompt = "Create a hello world microservice in FastAPI."
    job = swarm_coordinator.create_job(prompt, preset_id="rapid_bug_fix")
    job_id = job["job_id"]

    mock_response = {
        "domain": "code",
        "model": "qwen2.5-coder:latest",
        "response": "FastAPI code synthesized successfully."
    }

    with patch("core.sovereign_reasoning.moe_specialist_router.moe_router.dispatch", new=AsyncMock(return_value=mock_response)):
        events = []
        async for event in swarm_coordinator.execute_job_stream(job_id):
            events.append(event)

        event_types = [e.get("type") for e in events]
        assert "job_start" in event_types
        assert "step_start" in event_types
        assert "step_complete" in event_types
        assert "job_complete" in event_types

        # Verify job status in SQLite after execution
        final_job = swarm_coordinator.get_job_status(job_id)
        assert final_job is not None
        assert final_job["status"] == "completed"
        assert len(final_job["steps"]) == 2
