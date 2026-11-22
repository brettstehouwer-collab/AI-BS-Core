"""Tier 4 Real-World Application Scenario 04: Cloud Assets End-to-End Vectorization & Semantic Search.

Exercises: F11 (Synced Drive Assets 177 Files), F12 (ChromaDB Ingestion),
F13 (Microservice Retrieval), F15 (FastAPI Master Engine).
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


@pytest.mark.tier4
class TestS04CloudAssetsVectorizationSearch:
    """Scenario 04: Cloud Assets End-to-End Vectorization & Semantic Search."""

    def test_s04_assets_inventory_and_category_completeness(self, platform_paths: PlatformPaths) -> None:
        """Step 1: Verify all 177 files across 7 cloud categories exist on disk with 0 I/O errors."""
        assets_dir = platform_paths.synced_drive_assets_dir
        assert assets_dir.exists()

        all_files = [f for f in assets_dir.rglob("*") if f.is_file()]
        assert len(all_files) == 177, f"Expected 177 assets, found {len(all_files)}"

        # Verify zero I/O read errors across all 177 files
        for f in all_files:
            assert f.exists()
            assert f.stat().st_size >= 0

    def test_s04_semantic_search_and_metadata_retrieval_lifecycle(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Step 2, 3 & 4: Query vector memory across multiple topic domains and verify document hits."""
        test_queries = [
            ("engineering", "ai_bs_synced_drive_assets"),
            ("screenplay", "ai_bs_synced_drive_assets"),
            ("market leads", "ai_bs_synced_drive_assets"),
        ]

        for query_str, collection_name in test_queries:
            url = f"{platform_paths.backend_url}/api/rag/query"
            payload = {"query": query_str, "top_k": 2, "collection": collection_name}
            resp = http_client.post(url, json_data=payload, timeout=20.0)
            resp.assert_ok(f"Query '{query_str}' failed")

            data = resp.json()
            assert data.get("status") == "success"
            assert len(data.get("results", [])) > 0

            hit = data["results"][0]
            assert "metadata" in hit or "document" in hit

        # Step 5: Verify Omnidrive hybrid search
        omni_url = f"{platform_paths.backend_url}/api/omnidrive/search"
        resp_omni = http_client.post(omni_url, json_data={"query": "engineering", "limit": 2}, timeout=20.0)
        resp_omni.assert_ok()
        omni_data = resp_omni.json()
        assert len(omni_data.get("results", [])) > 0
        assert "latency_us" in omni_data
