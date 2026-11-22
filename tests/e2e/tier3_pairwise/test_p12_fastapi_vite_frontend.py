"""Tier 3 Pairwise Test P12: FastAPI Master Engine (F15) + Vite Frontend (F17).

Validates proxy routing, CORS origins, and API integration between
Vite React frontend on port 5173 and FastAPI backend on port 8080.
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
class TestP12FastAPIViteFrontend:
    """Pairwise F15 x F17: FastAPI Master Engine and Vite Frontend Dashboard."""

    def test_p12_backend_cors_allows_vite_origin(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify FastAPI /health returns CORS headers accommodating Vite origin http://localhost:5173."""
        headers = {"Origin": "http://localhost:5173"}
        resp = http_client.get(f"{platform_paths.backend_url}/health", headers=headers, timeout=5.0)
        resp.assert_ok()

        cors_origin = resp.headers.get("access-control-allow-origin") or resp.headers.get("Access-Control-Allow-Origin")
        assert cors_origin in ("*", "http://localhost:5173"), f"CORS not accommodating Vite: {cors_origin}"

    def test_p12_concurrent_frontend_and_backend_availability(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify both Vite frontend (5173) and FastAPI backend (8080) respond concurrently."""
        resp_front = http_client.get(platform_paths.frontend_url, timeout=5.0)
        resp_front.assert_ok("Frontend 5173 offline")

        resp_back = http_client.get(f"{platform_paths.backend_url}/health", timeout=5.0)
        resp_back.assert_ok("Backend 8080 offline")
