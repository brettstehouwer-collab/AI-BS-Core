"""Tier 1 Feature 15: FastAPI Master Engine Audit.

Requirement: Central cognitive backend listening on port 8080 responding 200 OK
on health endpoints, RAG retrieval endpoints, and Omnidrive search endpoints.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import HttpClientHelper, PlatformPaths, SubprocessRunner


@pytest.mark.tier1
@pytest.mark.feature(15)
@pytest.mark.feature_15
class TestF15FastAPIEngineAudit:
    """Feature 15: FastAPI Master Engine Audit Test Suite."""

    def test_f15_backend_health_status_online(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify GET /health returns 200 OK with online status and GPU acceleration."""
        url = f"{platform_paths.backend_url}/health"
        resp = http_client.get(url, timeout=10.0)
        resp.assert_ok(f"Failed to query backend health at {url}")

        data = resp.json()
        assert isinstance(data, dict), f"Expected JSON object, got {type(data)}"
        assert data.get("status") == "online", f"Expected status 'online', got {data.get('status')}"
        assert data.get("gpu_accelerated") is True, f"Expected gpu_accelerated True, got {data.get('gpu_accelerated')}"
        assert "process_id" in data and isinstance(data["process_id"], int), "process_id integer required"
        assert data["process_id"] > 0, "process_id must be positive"

    def test_f15_backend_openapi_schema_discovery(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify GET /openapi.json returns a valid OpenAPI spec with extensive routes."""
        url = f"{platform_paths.backend_url}/openapi.json"
        resp = http_client.get(url, timeout=10.0)
        resp.assert_ok("Failed to retrieve openapi.json")

        spec = resp.json()
        assert "openapi" in spec or "swagger" in spec, "Response is not a valid OpenAPI document"
        assert "paths" in spec, "Missing 'paths' in OpenAPI document"
        paths = spec["paths"]
        assert len(paths) >= 50, f"Expected comprehensive API routes (>=50), found {len(paths)}"

        # Verify key endpoints are defined in OpenAPI
        assert "/health" in paths, "Route /health not registered"
        assert "/api/rag/query" in paths, "Route /api/rag/query not registered"
        assert "/api/omnidrive/search" in paths, "Route /api/omnidrive/search not registered"

    def test_f15_rag_query_endpoint(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify POST /api/rag/query performs vector search and returns document hits."""
        url = f"{platform_paths.backend_url}/api/rag/query"
        payload = {
            "query": "engineering",
            "top_k": 3,
            "collection": "ai_bs_synced_drive_assets",
        }
        resp = http_client.post(url, json_data=payload, timeout=30.0)
        resp.assert_ok(f"RAG query endpoint failed with status {resp.status_code}")

        data = resp.json()
        assert data.get("status") == "success", f"RAG query status not success: {data}"
        assert "results" in data, "Missing 'results' key in RAG query response"
        assert isinstance(data["results"], list), "'results' must be a list"
        assert len(data["results"]) > 0, "Expected at least 1 document match in RAG search"

        first_hit = data["results"][0]
        assert "id" in first_hit or "metadata" in first_hit, "Result item missing id/metadata"

    def test_f15_omnidrive_hybrid_search_endpoint(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify POST /api/omnidrive/search performs hybrid vector/keyword asset lookup."""
        url = f"{platform_paths.backend_url}/api/omnidrive/search"
        payload = {"query": "engineering", "limit": 3}
        resp = http_client.post(url, json_data=payload, timeout=30.0)
        resp.assert_ok(f"Omnidrive search endpoint failed with status {resp.status_code}")

        data = resp.json()
        assert "results" in data, "Omnidrive response missing 'results' field"
        assert isinstance(data["results"], list), "'results' should be a list"
        assert "latency_us" in data, "Omnidrive response missing 'latency_us' telemetry"
        assert data["latency_us"] >= 0, "latency_us must be non-negative"

    def test_f15_backend_source_and_daemons_contract(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify backend source file presence and daemon subsystem registry."""
        backend_file = platform_paths.base_dir / "backend" / "AI_BS_Backend.py"
        assert backend_file.exists(), f"Backend source file missing at {backend_file}"
        assert backend_file.stat().st_size > 100_000, "Backend source file unexpectedly small"

        # Check health response daemons mapping
        url = f"{platform_paths.backend_url}/health"
        resp = http_client.get(url, timeout=10.0)
        resp.assert_ok()

        data = resp.json()
        assert "daemons" in data, "Health response missing 'daemons' map"
        daemons = data["daemons"]
        assert isinstance(daemons, dict), "'daemons' must be a dictionary"
        expected_daemons = ["chroma_daemon", "crypto_trader_bot", "broadcast_daemon"]
        for d in expected_daemons:
            assert d in daemons, f"Expected daemon '{d}' missing from health status"

    def test_f15_m5_audit_fastapi_pass(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify that the FastAPI subsystem audit passes with 0 failures in the report."""
        report_json = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_json.exists(), f"M5 report missing: {report_json}"

        with open(report_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        fastapi_sub = data.get("subsystems", {}).get("fastapi", {})
        assert fastapi_sub.get("passed") is True, f"FastAPI audit failed: {fastapi_sub.get('failures')}"
        assert len(fastapi_sub.get("failures", [])) == 0, f"Unexpected failures in FastAPI audit: {fastapi_sub.get('failures')}"
