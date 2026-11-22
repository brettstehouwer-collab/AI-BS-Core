"""Tier 4 Real-World Application Scenario 07: Multi-Modal Drive Assets Ingestion to Viewport Asset Browser.

Exercises: F01 (Stations), F04 (Native Viewport), F11 (Synced Drive Assets),
F12 (ChromaDB Ingestion), F13 (Microservice Retrieval).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import HttpClientHelper, PlatformPaths, SubprocessRunner


@pytest.mark.tier4
class TestS07MultimodalDriveAssetsViewport:
    """Scenario 07: Multi-Modal Drive Assets Ingestion to Viewport Asset Browser."""

    def test_s07_drive_assets_vector_retrieval_and_viewport_entity_mapping(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper, subprocess_runner: SubprocessRunner
    ) -> None:
        """Query asset catalog via vector search and render scene entities in DX12 viewport."""
        # 1. Search for asset documentation
        rag_url = f"{platform_paths.backend_url}/api/rag/query"
        payload = {"query": "engineering spec architectural concept", "top_k": 2, "collection": "ai_bs_synced_drive_assets"}
        resp = http_client.post(rag_url, json_data=payload, timeout=20.0)
        resp.assert_ok()

        data = resp.json()
        assert len(data.get("results", [])) > 0

        # 2. Verify native DX12 creator viewport executes offscreen with scene entities
        verify_script = platform_paths.native_studio_dir / "verify_sheltered_hub_viewport_session.py"
        python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(platform_paths.base_dir)
        env["QT_QPA_PLATFORM"] = "offscreen"

        res = subprocess_runner.run([python_exe, str(verify_script)], cwd=platform_paths.base_dir, env=env, timeout=120)
        res.assert_success()

        # 3. Verify telemetry JSON confirms entity rendering
        telemetry_file = platform_paths.base_dir / "docs" / "viewport_telemetry" / "probe_run" / "viewport.json"
        assert telemetry_file.exists()
        with open(telemetry_file, "r", encoding="utf-8") as f:
            t = json.load(f)
        assert t.get("debug_errors") == 0
        assert t.get("nonbackground_pixels", 0) > 0
