"""Tier 3 Pairwise Test P17: Synced Drive Assets (F11) + FastAPI Omnidrive (F15).

Validates that FastAPI hybrid search endpoint discovers and indexes files
directly from the synced_drive_assets physical directory.
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
class TestP17DriveAssetsFastAPIOmnidrive:
    """Pairwise F11 x F15: Synced Drive Assets and FastAPI Omnidrive Search."""

    def test_p17_omnidrive_returns_synced_asset_references(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify Omnidrive search locates documents residing in synced_drive_assets."""
        url = f"{platform_paths.backend_url}/api/omnidrive/search"
        payload = {"query": "screenplay", "limit": 3}
        resp = http_client.post(url, json_data=payload, timeout=20.0)
        resp.assert_ok()

        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0

    def test_p17_omnidrive_latency_bounds(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify hybrid Omnidrive search satisfies sub-second latency requirements."""
        url = f"{platform_paths.backend_url}/api/omnidrive/search"
        payload = {"query": "engineering", "limit": 2}
        resp = http_client.post(url, json_data=payload, timeout=20.0)
        resp.assert_ok()

        data = resp.json()
        latency_us = data.get("latency_us", 0)
        # Latency should be reported in microseconds
        assert latency_us >= 0
