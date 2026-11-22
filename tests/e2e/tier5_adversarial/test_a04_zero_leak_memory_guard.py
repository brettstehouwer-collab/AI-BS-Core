"""Tier 5 Adversarial Test A04: Zero-Leak Memory Guard Across Long-Running Sessions.

Monitors process Resident Set Size (RSS) using psutil across long-running batch sessions:
1. 50 sequential RAG queries against FastAPI backend (port 8080).
2. 100 snapshot encoding and validation iterations in Python.
3. Interleaved batch sessions.
Asserts RSS delta is bounded (<25 MB) and asymptotically stable with zero runaway leaks.
"""

from __future__ import annotations

import gc
import json
import os
import time
import urllib.request
import uuid
import psutil
import pytest

from tests.e2e.conftest import PlatformPaths, HttpClientHelper
from native_studio.game_engine.creator_payload import Scope, Create
from native_studio.game_engine.creator_viewport import encode_snapshot


@pytest.mark.tier5
@pytest.mark.feature_4
@pytest.mark.feature_13
@pytest.mark.feature_15
@pytest.mark.feature_18
class TestA04ZeroLeakMemoryGuard:
    """Zero-leak memory guard verifying asymptotic stability under batch workloads."""

    def test_a04_fastapi_backend_batch_rag_zero_memory_leak(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Measure FastAPI backend RSS before and after 50 sequential RAG queries; assert delta < 25MB."""
        health = http_client.get(f"{platform_paths.backend_url}/health", timeout=5.0)
        health.assert_ok("FastAPI backend must be alive")
        backend_pid = health.json().get("process_id")
        assert backend_pid is not None, "Missing process_id in health response"

        proc = psutil.Process(backend_pid)

        endpoint = f"{platform_paths.backend_url}/api/rag/query"

        # Warm-up queries (3 queries) to ensure ChromaDB clients/caches initialize
        for w in range(3):
            http_client.post(
                endpoint,
                json_data={"query": f"warmup query {w}", "top_k": 1, "collection": "ai_bs_synced_drive_assets"},
                timeout=10.0
            )

        time.sleep(0.5)
        initial_rss_mb = proc.memory_info().rss / (1024 * 1024)

        # Execute 50 sequential queries
        num_queries = 50
        for i in range(num_queries):
            res = http_client.post(
                endpoint,
                json_data={
                    "query": f"memory guard iteration {i} semantic probe",
                    "top_k": 1,
                    "collection": "ai_bs_synced_drive_assets"
                },
                timeout=10.0
            )
            res.assert_ok()

        time.sleep(0.5)
        final_rss_mb = proc.memory_info().rss / (1024 * 1024)
        rss_delta_mb = final_rss_mb - initial_rss_mb

        print(
            f"\n[A04 Backend RAG] Start RSS: {initial_rss_mb:.2f} MB, "
            f"End RSS: {final_rss_mb:.2f} MB, Delta: {rss_delta_mb:+.2f} MB "
            f"over {num_queries} queries"
        )

        assert rss_delta_mb < 25.0, (
            f"FastAPI backend RSS grew by {rss_delta_mb:.2f} MB (> 25 MB threshold), indicating memory leak."
        )

    def test_a04_viewport_snapshot_encoder_zero_leak(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Execute 100 snapshot encoding cycles; assert client process RSS delta < 15MB."""
        current_proc = psutil.Process(os.getpid())

        # Construct dummy entities
        entities = []
        for i in range(12):
            uid = str(uuid.uuid4())
            fields = (("x", float(i)), ("y", 0.0), ("z", float(-i)), ("half_x", 1.0), ("half_y", 1.0), ("half_z", 1.0))
            entities.append(Create(f"entity_{i}", f"Entity {i}", uid, fields))

        scope = Scope("AI-BS Chapter 1", "main", str(uuid.uuid4()), str(uuid.uuid4()))

        # Warm up
        for _ in range(5):
            encode_snapshot(
                snapshot_id=str(uuid.uuid4()),
                scope=scope,
                revision=10,
                checkpoint_id=str(uuid.uuid4()),
                rows=entities,
                first_boot=False
            )

        gc.collect()
        time.sleep(0.2)
        initial_rss_mb = current_proc.memory_info().rss / (1024 * 1024)

        # 100 encoding cycles
        iterations = 100
        for rev in range(iterations):
            snap_bytes = encode_snapshot(
                snapshot_id=str(uuid.uuid4()),
                scope=scope,
                revision=rev,
                checkpoint_id=str(uuid.uuid4()),
                rows=entities,
                first_boot=False
            )
            assert len(snap_bytes) > 0

        gc.collect()
        time.sleep(0.2)
        final_rss_mb = current_proc.memory_info().rss / (1024 * 1024)
        delta_mb = final_rss_mb - initial_rss_mb

        print(
            f"\n[A04 Snapshot Encoder] Start RSS: {initial_rss_mb:.2f} MB, "
            f"End RSS: {final_rss_mb:.2f} MB, Delta: {delta_mb:+.2f} MB "
            f"over {iterations} cycles"
        )

        assert delta_mb < 15.0, (
            f"Snapshot encoder process RSS grew by {delta_mb:.2f} MB (> 15 MB threshold)."
        )

    def test_a04_interleaved_session_memory_stability(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Execute 20 interleaved encoding and RAG query cycles asserting asymptotic stability."""
        endpoint = f"{platform_paths.backend_url}/api/rag/query"
        proc = psutil.Process(os.getpid())

        entities = [
            Create("desk", "Writing Desk", str(uuid.uuid4()), (("x", -38.0), ("y", 0.75), ("z", 18.0)))
        ]
        scope = Scope("AI-BS Chapter 1", "main", str(uuid.uuid4()), str(uuid.uuid4()))

        gc.collect()
        rss_start = proc.memory_info().rss / (1024 * 1024)

        for i in range(20):
            # Encode
            data = encode_snapshot(
                snapshot_id=str(uuid.uuid4()),
                scope=scope,
                revision=i,
                checkpoint_id=str(uuid.uuid4()),
                rows=entities,
                first_boot=False
            )
            assert len(data) > 0

            # Query
            resp = http_client.post(
                endpoint,
                json_data={"query": f"stability cycle {i}", "top_k": 1, "collection": "ai_bs_synced_drive_assets"},
                timeout=10.0
            )
            resp.assert_ok()

        gc.collect()
        rss_end = proc.memory_info().rss / (1024 * 1024)
        rss_diff = rss_end - rss_start

        print(f"\n[A04 Interleaved] Delta: {rss_diff:+.2f} MB across 20 interleaved cycles")
        assert rss_diff < 20.0, f"Interleaved session leaked {rss_diff:.2f} MB"
