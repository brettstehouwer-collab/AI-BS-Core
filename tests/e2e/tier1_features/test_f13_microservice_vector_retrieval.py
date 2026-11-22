"""Tier 1 Feature Coverage Tests: Feature 13 - Microservice Vector Retrieval.

Tests backend microservice retrieval endpoints and service bridges:
- POST /api/rag/query (query_rag via routers.rag_bridge)
- POST /api/omnidrive/search (hybrid_search via omnidrive_service)
Querying indexed asset collections across all 7 categories.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure tests/e2e root is on sys.path
E2E_ROOT = Path(__file__).resolve().parent.parent
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

import pytest
from conftest import PlatformPaths, SubprocessRunner, HttpClientHelper


TEST_QUERIES = {
    "01_Engineering_Backups": "DirectX 12 native viewport studio runtime",
    "02_Memoirs_Manuscripts": "Stehouwer screenplay memoir",
    "03_Finance_Trading": "trading options risk management",
    "04_Real_Estate": "West Michigan market leads property",
    "05_Music_Audio": "Suno AI guides prompts audio",
    "06_Health_Recovery": "TBI recovery psilocybin journal",
    "07_Legal_Credentials": "Pharmacy credentials license",
}


@pytest.mark.tier1
@pytest.mark.feature_13
@pytest.mark.feature(13)
class TestF13MicroserviceVectorRetrieval:
    """Test suite for Feature 13: Microservice Vector Retrieval."""

    @pytest.fixture(scope="class")
    def rag_retrieval_all_categories(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> dict:
        """Execute RAG queries across all 7 categories via the backend RAG bridge."""
        test_script = f"""
import asyncio, json, sys, os
base_dir = r'{platform_paths.base_dir}'
backend_dir = r'{platform_paths.base_dir / "backend"}'
sys.path.insert(0, base_dir)
sys.path.insert(0, backend_dir)

from routers.rag_bridge import query_rag, RagQuery

queries = {TEST_QUERIES!r}

async def run_all():
    out = {{}}
    for cat, q_text in queries.items():
        req = RagQuery(query=q_text, category=cat, top_k=2, collection='ai_bs_synced_drive_assets', synthesize=False)
        res = await query_rag(req)
        out[cat] = res
    print("OUTPUT_JSON:" + json.dumps(out))

asyncio.run(run_all())
"""
        runner = SubprocessRunner(default_cwd=platform_paths.base_dir, default_timeout=60.0)
        res = runner.run([python_exe, "-c", test_script])
        res.assert_success(f"RAG query execution failed: {res.stderr}")

        # Extract JSON from stdout
        for line in res.stdout.splitlines():
            if line.startswith("OUTPUT_JSON:"):
                return json.loads(line[len("OUTPUT_JSON:"):])

        raise AssertionError(f"Could not find OUTPUT_JSON in stdout: {res.stdout}")

    def test_f13_rag_service_bridge_import_and_schema(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify RagQuery schema accepts query, category, top_k, and collection."""
        script = f"""
import sys
sys.path.insert(0, r'{platform_paths.base_dir}')
sys.path.insert(0, r'{platform_paths.base_dir / "backend"}')
from routers.rag_bridge import RagQuery
q = RagQuery(query="test", category="01_Engineering_Backups", top_k=5, collection="ai_bs_synced_drive_assets")
assert q.query == "test"
assert q.category == "01_Engineering_Backups"
assert q.top_k == 5
assert q.collection == "ai_bs_synced_drive_assets"
print("RAG_SCHEMA_OK")
"""
        runner = SubprocessRunner(default_cwd=platform_paths.base_dir, default_timeout=15.0)
        res = runner.run([python_exe, "-c", script])
        res.assert_success()
        res.assert_stdout_contains("RAG_SCHEMA_OK")

    def test_f13_rag_query_retrieval_across_seven_categories(
        self, rag_retrieval_all_categories: dict
    ) -> None:
        """Verify RAG query returns status 'success' and hits > 0 for all 7 categories."""
        for cat in TEST_QUERIES:
            assert cat in rag_retrieval_all_categories, f"Category '{cat}' missing from retrieval output"
            res = rag_retrieval_all_categories[cat]
            assert res.get("status") == "success", f"Query status not success for '{cat}': {res}"
            results = res.get("results", [])
            assert len(results) > 0, f"Query returned 0 results for category '{cat}'"

    def test_f13_retrieved_results_metadata_payload(
        self, rag_retrieval_all_categories: dict
    ) -> None:
        """Verify retrieved records contain metadata with category, file_name, file_path."""
        for cat in TEST_QUERIES:
            results = rag_retrieval_all_categories[cat].get("results", [])
            for hit in results:
                assert "metadata" in hit, f"Hit missing metadata: {hit}"
                meta = hit["metadata"]
                assert "file_name" in meta
                assert "file_path" in meta
                assert "category" in meta

    def test_f13_category_filter_isolation(self, rag_retrieval_all_categories: dict) -> None:
        """Verify results filtered by category only return documents from that category."""
        for cat in TEST_QUERIES:
            results = rag_retrieval_all_categories[cat].get("results", [])
            for hit in results:
                doc_cat = hit["metadata"].get("category")
                assert doc_cat == cat, f"Category isolation failed: expected '{cat}', got '{doc_cat}'"

    def test_f13_omnidrive_hybrid_search_response_contract(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify OmniDriveService.hybrid_search returns query, latency_us, and results list."""
        script = f"""
import asyncio, json, sys
sys.path.insert(0, r'{platform_paths.base_dir}')
sys.path.insert(0, r'{platform_paths.base_dir / "backend"}')
from omnidrive_service import OmniDriveService
s = OmniDriveService()
res = asyncio.run(s.hybrid_search('options', limit=5))
print("OMNI_JSON:" + json.dumps(res))
"""
        runner = SubprocessRunner(default_cwd=platform_paths.base_dir, default_timeout=20.0)
        res = runner.run([python_exe, "-c", script])
        res.assert_success()
        for line in res.stdout.splitlines():
            if line.startswith("OMNI_JSON:"):
                data = json.loads(line[len("OMNI_JSON:"):])
                assert data["query"] == "options"
                assert "latency_us" in data
                assert isinstance(data["results"], list)
                assert len(data["results"]) > 0

    def test_f13_omnidrive_search_result_items_structure(
        self, platform_paths: PlatformPaths, python_exe: str
    ) -> None:
        """Verify items in omnidrive search results contain filepath, filename, match_type."""
        script = f"""
import asyncio, json, sys
sys.path.insert(0, r'{platform_paths.base_dir}')
sys.path.insert(0, r'{platform_paths.base_dir / "backend"}')
from omnidrive_service import OmniDriveService
s = OmniDriveService()
res = asyncio.run(s.hybrid_search('viewport', limit=3))
print("OMNI_JSON:" + json.dumps(res))
"""
        runner = SubprocessRunner(default_cwd=platform_paths.base_dir, default_timeout=20.0)
        res = runner.run([python_exe, "-c", script])
        res.assert_success()
        for line in res.stdout.splitlines():
            if line.startswith("OMNI_JSON:"):
                data = json.loads(line[len("OMNI_JSON:"):])
                results = data["results"]
                assert len(results) > 0
                for item in results:
                    assert "filepath" in item
                    assert "filename" in item
                    assert "match_type" in item
