"""Tier 4 Real-World Application Scenario 06: Full Stack Subsystem Integration & Health Audit.

Exercises: F14 (Chapter Creator & Native Studio Audit), F15 (FastAPI Master Engine Audit),
F16 (ComfyUI RTX 4090 Bridge Audit), F17 (Vite Frontend Build & Dev Audit).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import HttpClientHelper, PlatformPaths, SubprocessRunner


@pytest.mark.tier4
class TestS06FullStackSubsystemAudit:
    """Scenario 06: Full Stack Subsystem Integration & Health Audit."""

    def test_s06_execute_m5_master_audit_script(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Run tests/run_m5_subsystem_health_audit.py and assert overall PASS across all 4 pillars."""
        audit_script = platform_paths.base_dir / "tests" / "run_m5_subsystem_health_audit.py"
        assert audit_script.exists()

        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)

        res = subprocess_runner.run([python_exe, str(audit_script)], cwd=platform_paths.base_dir, env=env, timeout=120)
        res.assert_success("M5 master subsystem health audit script exited with failure")

        # Parse written report
        report_path = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert report.get("overall_passed") is True, f"M5 report did not pass: {report}"

        subsystems = report.get("subsystems", {})
        assert subsystems["native_studio"]["passed"] is True
        assert subsystems["fastapi"]["passed"] is True
        assert subsystems["comfyui"]["passed"] is True
        assert subsystems["vite"]["passed"] is True

    def test_s06_direct_endpoint_matrix_verification(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Independently probe each core subsystem URL to guarantee live responsiveness."""
        # 1. FastAPI Master Engine (8080)
        resp_fastapi = http_client.get(f"{platform_paths.backend_url}/health", timeout=5.0)
        resp_fastapi.assert_ok("FastAPI 8080 health check failed")
        assert resp_fastapi.json().get("status") == "online"

        # 2. ComfyUI Primary Proxy (8188)
        resp_comfy8188 = http_client.get(f"{platform_paths.comfy_primary_url}/health", timeout=5.0)
        resp_comfy8188.assert_ok("ComfyUI 8188 proxy failed")

        # 3. ComfyUI HighVRAM Worker (8189)
        resp_comfy8189 = http_client.get(f"{platform_paths.comfy_worker_url}/system_stats", timeout=5.0)
        resp_comfy8189.assert_ok("ComfyUI 8189 worker failed")
        assert "RTX 4090" in resp_comfy8189.json()["devices"][0]["name"]

        # 4. Vite Frontend Dashboard (5173)
        resp_vite = http_client.get(platform_paths.frontend_url, timeout=5.0)
        resp_vite.assert_ok("Vite 5173 dev server failed")
        assert "<!doctype html" in resp_vite.text.lower()
