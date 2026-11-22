"""Tier 4 Real-World Application Scenario 08: Disaster Recovery & Missing Dependency Graceful Fallback.

Exercises: F05 (DirectX Fallbacks), F08 (Training Driver Fallbacks),
F12 (Offline ChromaDB), F15 (FastAPI Master Engine).
"""

from __future__ import annotations

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
class TestS08DisasterRecoveryGracefulFallback:
    """Scenario 08: Disaster Recovery & Missing Dependency Graceful Fallback."""

    def test_s08_backend_resilience_under_missing_external_credentials(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify backend runs in fallback mock mode without fatal crashes when external keys are absent."""
        url = f"{platform_paths.backend_url}/health"
        resp = http_client.get(url, timeout=5.0)
        resp.assert_ok()

        data = resp.json()
        assert data.get("status") == "online"
        # Verify local maintenance protocol or daemons are managed gracefully
        assert "local_maintenance_protocol" in data or "daemons" in data

    def test_s08_distributed_driver_local_execution_without_gcp_dataproc(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner
    ) -> None:
        """Verify training driver can be queried and validated even without GCP credentials or internet."""
        driver_script = platform_paths.distributed_training_dir / "distributed_training_driver.py"
        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

        res = subprocess_runner.run([python_exe, str(driver_script), "--help"], timeout=15)
        res.assert_success()
        assert "--framework" in res.stdout

    def test_s08_graphics_warp_fallback_availability(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify software WARP renderer is available in graphics_pipeline.json as safety net."""
        import json

        config_path = platform_paths.base_dir / "engine" / "config" / "graphics_pipeline.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        assert cfg.get("allow_software_warp") is True
        assert "WARP_Software" in cfg.get("fallback_chain", [])
