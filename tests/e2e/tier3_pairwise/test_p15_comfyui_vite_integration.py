"""Tier 3 Pairwise Test P15: ComfyUI Bridge (F16) + Vite Frontend (F17).

Validates that Vite frontend can query ComfyUI bridge on port 8188/8189,
receive GPU hardware telemetry, and display active generation states.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import HttpClientHelper, PlatformPaths


@pytest.mark.tier3
class TestP15ComfyUIViteIntegration:
    """Pairwise F16 x F17: ComfyUI RTX 4090 Bridge and Vite Frontend Dashboard."""

    def test_p15_comfyui_cors_for_vite_dashboard(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify ComfyUI bridge permits cross-origin requests from Vite development server."""
        headers = {"Origin": "http://localhost:5173"}
        resp = http_client.get(f"{platform_paths.comfy_primary_url}/health", headers=headers, timeout=5.0)
        resp.assert_ok()

        cors = resp.headers.get("access-control-allow-origin") or resp.headers.get("Access-Control-Allow-Origin")
        assert cors in ("*", "http://localhost:5173")

    def test_p15_system_stats_for_dashboard_display(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify system stats return JSON consumable by frontend dashboard (GPU name, VRAM free)."""
        resp = http_client.get(f"{platform_paths.comfy_primary_url}/system_stats", timeout=5.0)
        resp.assert_ok()

        data = resp.json()
        assert "devices" in data and len(data["devices"]) > 0
        device = data["devices"][0]
        assert "vram_total" in device and "vram_free" in device
        assert device["vram_total"] > device["vram_free"] > 0
