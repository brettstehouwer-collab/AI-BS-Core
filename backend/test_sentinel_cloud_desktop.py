"""
AI-BS Automated Test Suite: v5.299.0
Verifies:
1. Autonomous Sentinel Engine Lifecycle & Proactive Alerts
2. Sovereign GPU Local Execution ($0.00 Spend Governance)
3. Directorial Voice HUD Guardrails (Zero-Overhead Hybrid Fallback)
4. 4-Mirror SHA-256 Byte Parity across ExecutiveCockpitTab.jsx
5. Executive Cockpit REST API Router Endpoints
"""

import os
import sys
import json
import hashlib
import asyncio
import pytest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend and root paths are on sys.path
backend_dir = str(Path(__file__).resolve().parent)
root_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from core.autonomous_sentinel_engine import sentinel_engine
from core.cloud_gpu_burst_engine import cloud_burst_engine
from routers.executive_cockpit_router import router as executive_cockpit_router


class TestSentinelCloudDesktopV5299:
    """Master validation suite for AI-BS Ecosystem v5.299.0."""

    @classmethod
    def setup_class(cls):
        cls.app = FastAPI(title="AI-BS Test App")
        cls.app.include_router(executive_cockpit_router)
        cls.client = TestClient(cls.app)

    def test_01_sentinel_engine_lifecycle(self):
        """Verifies Sentinel scan, cataloging, and alert generation."""
        status = sentinel_engine.get_status()
        assert "poll_interval_sec" in status
        assert status["poll_interval_sec"] > 0

        # Trigger complete scan
        scan_res = asyncio.run(sentinel_engine.scan_all())
        assert "hardware" in scan_res
        assert "crypto" in scan_res
        assert "media" in scan_res

        alerts = sentinel_engine.get_alerts(limit=20)
        assert isinstance(alerts, list)
        assert len(alerts) > 0
        # Check alert schema
        first_alert = alerts[0]
        assert "alert_id" in first_alert
        assert "category" in first_alert
        assert "severity" in first_alert
        assert "title" in first_alert

    def test_02_cloud_burst_sovereignty_and_spend_lock(self):
        """Verifies strict local RTX 4090 sovereign mode and zero spend lock."""
        status = cloud_burst_engine.get_status()
        assert status["sovereign_local_exclusive"] is True
        assert status["cloud_burst_enabled"] is False
        assert status["current_daily_spend_usd"] == 0.0
        assert status["daily_spend_limit_usd"] == 5.0
        assert "RTX 4090" in status["execution_target"]

        # Queue a local render job
        job_res = asyncio.run(cloud_burst_engine.queue_job("test_reframe_short", {"duration": 15}))
        assert job_res["status"] == "success"
        assert "job_id" in job_res
        queue = cloud_burst_engine.get_queue()
        assert len(queue) >= 1

    def test_03_voice_guardrail_thresholds(self):
        """Verifies voice readiness and hybrid fallback logic."""
        response = self.client.get("/api/v1/executive/voice/status")
        assert response.status_code == 200
        data = response.json()
        assert data["web_speech_api_available"] is True
        assert "f5_tts_eligible" in data
        assert "active_mode" in data
        assert data["governor_policy"] == "HYBRID_ZERO_OVERHEAD_FALLBACK"

    def test_04_four_mirror_parity_cockpit_upgrade(self):
        """Asserts 100% SHA-256 byte parity across all 4 mirrors of ExecutiveCockpitTab.jsx."""
        mirrors = [
            Path("C:/AI-BS/frontend/src/components/ExecutiveCockpitTab.jsx"),
            Path("C:/AI-BS/frontend/components/ExecutiveCockpitTab.jsx"),
            Path("C:/AI-BS/frontend/src/components/components/ExecutiveCockpitTab.jsx"),
            Path("C:/AI-BS/frontend/components/components/ExecutiveCockpitTab.jsx")
        ]

        hashes = []
        for path in mirrors:
            assert path.exists(), f"Mirror file missing: {path}"
            with open(path, "rb") as f:
                hashes.append(hashlib.sha256(f.read()).hexdigest())

        # All 4 hashes must be identical
        assert len(set(hashes)) == 1, f"Mirror hash divergence detected: {hashes}"

    def test_05_sentinel_rest_endpoints(self):
        """Verifies all new REST endpoints on Executive Cockpit router."""
        # 1. GET /sentinel/alerts
        r_alerts = self.client.get("/api/v1/executive/sentinel/alerts?limit=5")
        assert r_alerts.status_code == 200
        assert "alerts" in r_alerts.json()

        # 2. GET /sentinel/status
        r_status = self.client.get("/api/v1/executive/sentinel/status")
        assert r_status.status_code == 200
        assert "engine" in r_status.json()

        # 3. POST /sentinel/scan
        r_scan = self.client.post("/api/v1/executive/sentinel/scan")
        assert r_scan.status_code == 200
        assert r_scan.json()["status"] == "success"

        # 4. GET /cloud/status
        r_cloud = self.client.get("/api/v1/executive/cloud/status")
        assert r_cloud.status_code == 200
        assert r_cloud.json()["gpu_sovereignty"]["current_daily_spend_usd"] == 0.0

        # 5. POST /cloud/config
        r_cfg = self.client.post("/api/v1/executive/cloud/config", json={
            "sovereign_exclusive": True,
            "cloud_burst_enabled": False,
            "daily_spend_cap": 5.0
        })
        assert r_cfg.status_code == 200
        assert r_cfg.json()["config"]["sovereign_local_exclusive"] is True
