#!/usr/bin/env python3
"""
Unit tests for Sovereign MoE Specialist Router & Agent Harness Runner
AI-BS Antigravity Sovereign Unison Architecture
"""

import sys
import os
import pytest

# Ensure backend is on sys.path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend = os.path.join(_root, "backend")
if _root not in sys.path:
    sys.path.insert(0, _root)
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from core.sovereign_reasoning.moe_specialist_router import (
    moe_router,
    SPECIALIST_MATRIX,
    SpecialistDomain,
    RoutingDecision
)
from modules.agent_harness_runner import (
    agent_harness_runner,
    AGENT_APPS_CATALOG
)


def test_specialist_matrix_integrity():
    """Verify all 6 core specialist domains are properly defined with models and context windows."""
    required_domains = ["code", "creative", "function_calling", "vision", "reasoning", "embedding"]
    for d in required_domains:
        assert d in SPECIALIST_MATRIX, f"Domain {d} missing from matrix"
        spec = SPECIALIST_MATRIX[d]
        assert "primary" in spec
        assert "fallback" in spec
        assert "params" in spec
        assert spec["context_window"] >= 2048


def test_moe_intent_classification():
    """Test intent classification across distinct domain prompts."""
    # Code prompt
    code_prompt = "def calculate_matrix_determinant(matrix: list[list[float]]) -> float:"
    decision = moe_router.classify_intent(code_prompt)
    assert decision.domain == SpecialistDomain.CODE
    assert "qwen" in decision.selected_model.lower() or "coder" in decision.selected_model.lower()
    assert decision.confidence >= 0.7

    # Creative prompt
    creative_prompt = "Write a cinematic screenplay dialogue between two rogue cyberpunks in Neo Tokyo."
    decision = moe_router.classify_intent(creative_prompt)
    assert decision.domain == SpecialistDomain.CREATIVE
    assert "dolphin" in decision.selected_model.lower() or "stehouwer" in decision.selected_model.lower()

    # Reasoning prompt
    math_prompt = "Prove that the square root of 2 is irrational using formal contradiction."
    decision = moe_router.classify_intent(math_prompt)
    assert decision.domain == SpecialistDomain.REASONING
    assert "llama" in decision.selected_model.lower() or "70b" in decision.selected_model.lower()


def test_agent_apps_catalog_completeness():
    """Verify all 14 sovereign agent applications are present in the catalog."""
    expected_apps = [
        "claude_code", "codex_cli", "openclaw", "opencode",
        "hermes_agent", "hermes_desktop", "droid", "pi",
        "cline", "copilot_cli", "oh_my_pi", "deepseek_harness",
        "qwen_code", "terminal"
    ]
    apps = agent_harness_runner.list_apps()
    app_ids = [a["id"] for a in apps]
    assert len(apps) == 14
    for app_id in expected_apps:
        assert app_id in app_ids, f"App {app_id} missing from catalog"


def test_agent_session_lifecycle():
    """Verify session creation, metadata retrieval, and termination."""
    session = agent_harness_runner.create_session("claude_code")
    assert session["app_id"] == "claude_code"
    assert session["status"] == "active"
    session_id = session["session_id"]

    # Verify retrieval
    retrieved = agent_harness_runner.get_session(session_id)
    assert retrieved is not None
    assert retrieved["session_id"] == session_id
    assert retrieved["app_name"] == "Claude Code"

    # Verify termination
    terminated = agent_harness_runner.terminate_session(session_id)
    assert terminated is True

    # Check updated status
    updated = agent_harness_runner.get_session(session_id)
    assert updated["status"] == "archived"
