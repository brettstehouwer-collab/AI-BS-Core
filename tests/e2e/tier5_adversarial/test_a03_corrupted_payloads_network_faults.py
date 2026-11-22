"""Tier 5 Adversarial Test A03: Corrupted Payloads, Malformed Snapshots & Network Faults.

Injects corrupted binary snapshots to native viewport binary, transmits malformed
and oversized payloads (10MB, binary chunks) to FastAPI backend, and simulates
abrupt client network timeouts (timeout=0.005s).
Asserts clean error handling, HTTP 400/422 status codes, and zero crashes.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
import pytest
from tests.e2e.conftest import PlatformPaths, HttpClientHelper, SubprocessRunner


@pytest.mark.tier5
@pytest.mark.feature_4
@pytest.mark.feature_13
@pytest.mark.feature_15
class TestA03CorruptedPayloadsNetworkFaults:
    """Fault-injection and adversarial payload handling verification."""

    def test_a03_viewport_binary_corrupted_snapshot_rejection(
        self, platform_paths: PlatformPaths, subprocess_runner: SubprocessRunner, tmp_path: Path
    ) -> None:
        """Inject corrupt and truncated AIBV snapshots to viewport; assert clean exit without crash."""
        exe = platform_paths.engine_dir / "out" / "windows-msvc" / "Debug" / "aibs_creator_viewport.exe"
        assert exe.is_file(), f"Viewport binary missing: {exe}"

        corrupt_scenarios = [
            ("invalid_magic", b"JUNK_HEADER_NOT_AIBV_MAGIC_BYTES_1234567890"),
            ("truncated_bytes", b"AIBV\x00\x01"),
            ("random_binary", os.urandom(4096)),
        ]

        for label, payload in corrupt_scenarios:
            scene_file = tmp_path / f"{label}.aibv"
            scene_file.write_bytes(payload)
            stop_file = tmp_path / f"{label}.stop"
            stop_file.touch()
            bmp_file = tmp_path / f"{label}.bmp"
            rpt_file = tmp_path / f"{label}.json"

            args = [
                str(exe),
                "--snapshot", str(scene_file),
                "--stop-file", str(stop_file),
                "--self-test",
                "--capture", str(bmp_file),
                "--report", str(rpt_file),
            ]

            res = subprocess_runner.run(args, cwd=platform_paths.base_dir, timeout=10.0)
            # Binary should detect corrupt snapshot and exit cleanly (non-zero), not hang or crash
            assert res.returncode != 0, f"Viewport did not reject corrupted snapshot '{label}'"
            assert "Unsupported viewport snapshot" in res.stderr or res.returncode == 1

    def test_a03_backend_oversized_and_binary_payload_fuzzing(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Send oversized (10MB) payloads and random binary blobs; assert graceful handling."""
        endpoint = f"{platform_paths.backend_url}/api/rag/query"

        # 1. Random binary data without valid JSON
        bin_payload = os.urandom(32768)
        req_bin = urllib.request.Request(
            endpoint,
            data=bin_payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req_bin, timeout=10.0) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code

        assert status in (400, 422), f"Expected HTTP 400 or 422 for binary junk, got {status}"

        # 2. Malformed unclosed JSON payload
        bad_json = b'{"query": "broken json payload", "top_k": '
        req_bad = urllib.request.Request(
            endpoint,
            data=bad_json,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req_bad, timeout=10.0) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code

        assert status in (400, 422), f"Expected HTTP 400 or 422 for malformed JSON, got {status}"

        # 3. Huge 10MB text query string
        huge_str = "vector query stress test token " * 350000  # ~10 MB
        huge_payload = json.dumps({"query": huge_str, "top_k": 1}).encode("utf-8")
        req_huge = urllib.request.Request(
            endpoint,
            data=huge_payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req_huge, timeout=15.0) as resp:
                status = resp.status
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = {}

        assert status in (200, 400, 413, 422), f"Unexpected status for huge payload: {status}"
        if status == 200:
            assert body.get("status") in ("success", "error")

        # Confirm backend survives
        health = http_client.get(f"{platform_paths.backend_url}/health", timeout=5.0)
        health.assert_ok("FastAPI backend crashed after payload fuzzing")

    def test_a03_network_timeout_and_abrupt_disconnect(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Simulate rapid client-side network timeouts (0.005s) and verify backend recovery."""
        endpoint = f"{platform_paths.backend_url}/api/rag/query"

        # Fire 8 queries with aggressive 0.005s timeout
        for i in range(8):
            payload = json.dumps({"query": f"abrupt timeout test {i}", "top_k": 1}).encode("utf-8")
            req = urllib.request.Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=0.005) as _:
                    pass
            except (urllib.error.URLError, socket.timeout, TimeoutError):
                pass
            except Exception:
                pass

        # Immediate follow-up query must succeed cleanly
        followup = http_client.post(
            endpoint,
            json_data={"query": "recovery verification query", "top_k": 1, "collection": "ai_bs_synced_drive_assets"},
            timeout=10.0
        )
        followup.assert_ok("Subsequent query failed after network timeout simulation")
        assert followup.json().get("status") == "success"

        health = http_client.get(f"{platform_paths.backend_url}/health", timeout=5.0)
        health.assert_ok()
        assert health.json().get("status") == "online"
