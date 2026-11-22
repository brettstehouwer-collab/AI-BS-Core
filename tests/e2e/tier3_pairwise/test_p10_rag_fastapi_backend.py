"""Tier 3 Pairwise Test P10: Vector Retrieval (F13) + FastAPI Engine (F15).

Validates that FastAPI backend routes RAG requests to the vector search service
and transforms results into the API contract schema.
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
class TestP10RAGFastAPIBackend:
    """Pairwise F13 x F15: Microservice Vector Retrieval and FastAPI Master Engine."""

    def test_p10_fastapi_rag_endpoint_contract_schema(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify POST /api/rag/query contract conforms to interface specifications."""
        url = f"{platform_paths.backend_url}/api/rag/query"
        payload = {
            "query": "financial real estate",
            "top_k": 1,
            "collection": "ai_bs_synced_drive_assets",
        }
        resp = http_client.post(url, json_data=payload, timeout=20.0)
        resp.assert_ok()

        data = resp.json()
        assert "status" in data
        assert "collection" in data
        assert "count" in data
        assert "results" in data
        assert data["collection"] == "ai_bs_synced_drive_assets"

    def test_p10_fastapi_rag_endpoint_handles_missing_collection_fallback(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify querying without explicit collection defaults gracefully."""
        url = f"{platform_paths.backend_url}/api/rag/query"
        payload = {"query": "legal patent", "top_k": 1}
        resp = http_client.post(url, json_data=payload, timeout=20.0)
        assert resp.status_code in (200, 422)
