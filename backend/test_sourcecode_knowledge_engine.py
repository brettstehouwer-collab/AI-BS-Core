"""
backend/test_sourcecode_knowledge_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Authoritative Verification Test Suite for Master Codebase Knowledge Engine (v5.290.0)
- Verifies SQLite FTS5 full-text keyword indexing across 3,230 files.
- Verifies exact file lookup and metadata extraction.
- Verifies dynamic context grounding for Stehouwer LLM.
- Verifies Master Tool Registry execution (81 tools).
- Verifies FastAPI REST endpoints on Port 8080.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
backend_dir = os.path.join(BASE_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from core.sovereign_reasoning.sourcecode_knowledge_engine import sourcecode_knowledge_engine
from tools.tool_registry import ToolRegistry
from AI_BS_Backend import app

client = TestClient(app)


def test_01_subsystem_breakdown_and_total_counts():
    """Verifies that all 3,230 files and 820k+ lines are properly indexed."""
    stats = sourcecode_knowledge_engine.get_subsystem_breakdown()
    assert stats["total_files"] == 3230, f"Expected 3230 files, got {stats['total_files']}"
    assert stats["total_lines"] > 800000, f"Expected >800k lines, got {stats['total_lines']}"
    assert len(stats["subsystems"]) >= 10, "Expected at least 10 categorized subsystems."


def test_02_fts5_fulltext_search():
    """Verifies SQLite FTS5 search queries across multiple technical domains."""
    # 1. Search for live telemetry
    res1 = sourcecode_knowledge_engine.search_codebase("ecosystem telemetry websocket", limit=5)
    assert len(res1) > 0, "Expected matches for 'ecosystem telemetry websocket'"
    assert any("telemetry" in r["file_path"].lower() or "telemetry" in r["summary"].lower() for r in res1)

    # 2. Search for tools
    res2 = sourcecode_knowledge_engine.search_codebase("tool_registry", subsystem="backend_tools", limit=3)
    assert len(res2) > 0, "Expected matches for tool_registry"
    assert any("tool_registry" in r["file_path"] for r in res2)

    # 3. Search for frontend components
    res3 = sourcecode_knowledge_engine.search_codebase("ChatTab", subsystem="frontend_components", limit=3)
    assert len(res3) > 0, "Expected matches for ChatTab"
    assert any("ChatTab.jsx" in r["file_path"] for r in res3)


def test_03_exact_file_lookup():
    """Verifies retrieval of exact file contents and metadata."""
    file_record = sourcecode_knowledge_engine.get_file_by_path("backend/AI_BS_Backend.py")
    assert file_record is not None, "Failed to retrieve backend/AI_BS_Backend.py"
    assert file_record["subsystem"] == "backend_services"
    assert file_record["lines_count"] > 1000
    assert "FastAPI" in file_record["content"]


def test_04_context_injection_grounding():
    """Verifies dynamic prompt grounding block generation."""
    prompt = "Can you check how the audio stem DAW engine is wired in backend?"
    grounding = sourcecode_knowledge_engine.inject_codebase_context(prompt)
    assert len(grounding) > 0, "Expected non-empty grounding block"
    assert "SOVEREIGN CODEBASE MASTER GROUNDING" in grounding
    assert any(term in grounding.lower() for term in ["audio", "backend", "file", "summary"])


def test_05_tool_registry_codebase_tools():
    """Verifies execution of the 3 new tools in ToolRegistry."""
    # Tool 1: search_codebase_knowledge
    r1 = ToolRegistry.execute_tool("search_codebase_knowledge", {
        "query": "quant indicators MACD RSI",
        "limit": 3
    })
    assert r1["status"] == "success"
    assert r1["total_matches"] > 0

    # Tool 2: get_sourcecode_file
    r2 = ToolRegistry.execute_tool("get_sourcecode_file", {
        "file_path": ".agents/AGENTS.md"
    })
    assert r2["status"] == "success"
    assert "Operational Directive" in r2["content"]

    # Tool 3: get_codebase_architecture_summary
    r3 = ToolRegistry.execute_tool("get_codebase_architecture_summary", {})
    assert r3["status"] == "success"
    assert r3["total_files"] == 3230


def test_06_fastapi_rest_endpoints():
    """Verifies FastAPI REST endpoints for codebase knowledge."""
    # 1. POST /api/v1/knowledge/codebase/search
    res1 = client.post("/api/v1/knowledge/codebase/search", json={
        "query": "OBS WebSocket NVENC",
        "limit": 3
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "success"
    assert data1["total_matches"] > 0

    # 2. GET /api/v1/knowledge/codebase/file
    res2 = client.get("/api/v1/knowledge/codebase/file?path=.agents/rules/permissions.md")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "success"
    assert "Full-Privilege Machine" in data2["file"]["content"]

    # 3. GET /api/v1/knowledge/codebase/summary
    res3 = client.get("/api/v1/knowledge/codebase/summary")
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["status"] == "success"
    assert data3["data"]["total_files"] == 3230


if __name__ == "__main__":
    pytest.main(["-v", __file__])
