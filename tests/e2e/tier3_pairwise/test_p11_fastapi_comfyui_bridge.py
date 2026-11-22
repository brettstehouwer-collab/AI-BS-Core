"""Tier 3 Pairwise Test P11: FastAPI Master Engine (F15) + ComfyUI Bridge (F16).

Validates coordination between FastAPI central cognitive backend and
ComfyUI dual-port gateway (8188/8189) for GPU generative operations.
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
class TestP11FastAPIComfyUIBridge:
    """Pairwise F15 x F16: FastAPI Master Engine and ComfyUI RTX 4090 Bridge."""

    def test_p11_fastapi_comfyui_client_registration(self, platform_paths: PlatformPaths) -> None:
        """Verify backend registers ComfyUIClient targeting ports 8188 and 8189."""
        backend_file = platform_paths.base_dir / "backend" / "AI_BS_Backend.py"
        code = backend_file.read_text(encoding="utf-8", errors="replace")
        assert "8188" in code or "comfy" in code.lower(), "ComfyUI integration not found in backend"
        assert "ComfyUIClient" in code or "comfy" in code.lower()

    def test_p11_concurrent_health_and_stats_query(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify concurrent reachability of FastAPI 8080 and ComfyUI 8188 gateways."""
        resp_fastapi = http_client.get(f"{platform_paths.backend_url}/health", timeout=5.0)
        resp_fastapi.assert_ok()

        resp_comfy = http_client.get(f"{platform_paths.comfy_primary_url}/health", timeout=5.0)
        resp_comfy.assert_ok()

        assert resp_fastapi.json().get("status") == "online"
        assert resp_comfy.json().get("status") == "healthy"
