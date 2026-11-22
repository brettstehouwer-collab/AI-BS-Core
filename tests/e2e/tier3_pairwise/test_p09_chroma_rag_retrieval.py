"""Tier 3 Pairwise Test P09: ChromaDB Ingestion (F12) + Vector Retrieval (F13).

Validates vector distance queries against the indexed collection
'ai_bs_synced_drive_assets' returning semantic matches.
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
class TestP09ChromaRAGRetrieval:
    """Pairwise F12 x F13: ChromaDB Vector Ingestion and Microservice Vector Retrieval."""

    def test_p09_vector_retrieval_returns_ranked_results(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify vector retrieval query returns ranked documents with metadata and distance scores."""
        url = f"{platform_paths.backend_url}/api/rag/query"
        payload = {
            "query": "market leads",
            "top_k": 3,
            "collection": "ai_bs_synced_drive_assets",
        }
        resp = http_client.post(url, json_data=payload, timeout=20.0)
        resp.assert_ok("Failed vector retrieval query")

        data = resp.json()
        assert data.get("status") == "success"
        assert len(data.get("results", [])) > 0

        hit = data["results"][0]
        assert "distance" in hit, "Ranked result missing distance metric"
        assert "metadata" in hit, "Ranked result missing metadata payload"

    def test_p09_vector_retrieval_respects_top_k_parameter(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify top_k parameter bounds the number of returned results."""
        url = f"{platform_paths.backend_url}/api/rag/query"
        payload = {
            "query": "creative screenplay",
            "top_k": 2,
            "collection": "ai_bs_synced_drive_assets",
        }
        resp = http_client.post(url, json_data=payload, timeout=20.0)
        resp.assert_ok()

        data = resp.json()
        assert len(data.get("results", [])) <= 2
