"""Tier 5 Adversarial Test A01: High-Concurrency Stress on RAG & Vector Retrieval.

Executes 50+ (55) simultaneous RAG and vector queries against http://localhost:8080/api/rag/query.
Verifies 100% success rate, 0 unhandled exceptions, 0 server crashes, and bounded latencies.
"""

from __future__ import annotations

import concurrent.futures
import json
import time
import urllib.error
import urllib.request
import pytest
from tests.e2e.conftest import PlatformPaths, HttpClientHelper


@pytest.mark.tier5
@pytest.mark.feature_12
@pytest.mark.feature_13
@pytest.mark.feature_15
class TestA01ConcurrencyStressRag:
    """Adversarial stress and concurrency verification for RAG cognitive endpoint."""

    def test_a01_high_concurrency_rag_55_simultaneous_workers(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Execute 55 concurrent queries against /api/rag/query asserting 100% success."""
        endpoint = f"{platform_paths.backend_url}/api/rag/query"
        health_url = f"{platform_paths.backend_url}/health"

        # Verify backend online before test
        health_resp = http_client.get(health_url, timeout=5.0)
        health_resp.assert_ok("FastAPI backend must be online before stress test")
        initial_pid = health_resp.json().get("process_id")

        num_workers = 55

        def send_query(idx: int) -> dict:
            payload = json.dumps({
                "query": f"stress test query vector lookup index {idx} memory validation",
                "top_k": 2,
                "collection": "ai_bs_synced_drive_assets"
            }).encode("utf-8")

            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=25.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    dur = time.perf_counter() - t0
                    return {
                        "index": idx,
                        "status_code": resp.status,
                        "status": data.get("status"),
                        "count": data.get("count", 0),
                        "duration": dur,
                        "error": None
                    }
            except Exception as exc:
                dur = time.perf_counter() - t0
                return {
                    "index": idx,
                    "status_code": getattr(exc, "code", 500),
                    "status": "exception",
                    "count": 0,
                    "duration": dur,
                    "error": str(exc)
                }

        start_wall = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as pool:
            futures = [pool.submit(send_query, i) for i in range(num_workers)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        wall_time = time.perf_counter() - start_wall

        # Assertions
        assert len(results) == num_workers
        failed = [r for r in results if r["status_code"] != 200 or r["status"] != "success"]
        assert len(failed) == 0, f"{len(failed)} requests failed under concurrency: {failed[:3]}"

        durations = [r["duration"] for r in results]
        avg_dur = sum(durations) / len(durations)
        max_dur = max(durations)
        print(f"\n[A01] 55 Simultaneous Queries: Wall {wall_time:.2f}s, Avg {avg_dur:.2f}s, Max {max_dur:.2f}s")
        assert max_dur < 20.0, f"Max query latency {max_dur:.2f}s exceeded 20s bound"

        # Verify backend survived with exact same PID (zero crash)
        final_health = http_client.get(health_url, timeout=5.0)
        final_health.assert_ok()
        assert final_health.json().get("process_id") == initial_pid, "Server crashed and restarted during concurrency"

    def test_a01_concurrency_multi_category_stress(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Execute 50 simultaneous queries targeting diverse categories across cloud assets."""
        endpoint = f"{platform_paths.backend_url}/api/rag/query"
        categories = [
            "01_Engineering_Backups",
            "02_Memoirs_Manuscripts",
            "03_Finance_Trading",
            "04_Real_Estate",
            "05_Music_Audio",
            "06_Health_Recovery",
            "07_Legal_Credentials"
        ]

        queries = [
            (i, categories[i % len(categories)], f"query term {i} category specific token")
            for i in range(50)
        ]

        def query_cat(item: tuple) -> dict:
            idx, cat, q_text = item
            payload = json.dumps({
                "query": q_text,
                "top_k": 1,
                "collection": "ai_bs_synced_drive_assets",
                "category": cat
            }).encode("utf-8")

            req = urllib.request.Request(
                endpoint,
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=20.0) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return {"idx": idx, "code": resp.status, "status": body.get("status")}
            except Exception as e:
                return {"idx": idx, "code": 500, "error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
            res = list(pool.map(query_cat, queries))

        assert all(r["code"] == 200 and r.get("status") == "success" for r in res), "Category stress failures"

    def test_a01_rapid_burst_stability(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Execute rapid sequential burst of queries in a tight loop and verify server stability."""
        endpoint = f"{platform_paths.backend_url}/api/rag/query"
        for i in range(15):
            res = http_client.post(
                endpoint,
                json_data={"query": f"burst token {i}", "top_k": 1, "collection": "ai_bs_synced_drive_assets"},
                timeout=5.0
            )
            res.assert_ok()
            assert res.json().get("status") == "success"
