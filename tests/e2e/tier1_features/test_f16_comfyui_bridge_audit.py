"""Tier 1 Feature 16: ComfyUI RTX 4090 Bridge Audit.

Requirement: Dual-port ComfyUI bridge (primary proxy 8188 and highvram 8189)
reporting active RTX 4090 GPU status and zero-VRAM JIT standby operation.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure AI-BS root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from tests.e2e.conftest import HttpClientHelper, PlatformPaths


@pytest.mark.tier1
@pytest.mark.feature(16)
@pytest.mark.feature_16
class TestF16ComfyUIBridgeAudit:
    """Feature 16: ComfyUI RTX 4090 Bridge Audit Test Suite."""

    def test_f16_comfyui_primary_health(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify GET http://localhost:8188/health returns 200 OK with ComfyUI Primary Service."""
        url = f"{platform_paths.comfy_primary_url}/health"
        resp = http_client.get(url, timeout=5.0)
        resp.assert_ok(f"Failed to reach ComfyUI primary gateway at {url}")

        data = resp.json()
        assert data.get("status") == "healthy", f"Expected healthy status, got {data.get('status')}"
        assert data.get("service") == "ComfyUI Primary Service", f"Unexpected service: {data.get('service')}"
        assert data.get("port") == 8188, f"Expected port 8188, got {data.get('port')}"
        assert data.get("target_port") == 8189, f"Expected target_port 8189, got {data.get('target_port')}"

    def test_f16_comfyui_standby_system_stats_rtx_4090(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify GET http://localhost:8189/system_stats returns active NVIDIA RTX 4090 device."""
        url = f"{platform_paths.comfy_worker_url}/system_stats"
        resp = http_client.get(url, timeout=5.0)
        resp.assert_ok(f"Failed to reach ComfyUI standby gateway at {url}")

        data = resp.json()
        assert "devices" in data, f"system_stats missing devices list: {data}"
        devices = data["devices"]
        assert len(devices) > 0, "No GPU devices reported by ComfyUI bridge"

        primary_gpu = devices[0]
        gpu_name = primary_gpu.get("name", "")
        assert "RTX 4090" in gpu_name or "4090" in gpu_name, f"Expected RTX 4090 GPU, got {gpu_name}"
        assert primary_gpu.get("vram_total", 0) > 20_000_000_000, "Expected >=24GB VRAM capacity"

    def test_f16_comfyui_proxy_transparent_forwarding(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify port 8188 transparently proxies /system_stats from port 8189."""
        url = f"{platform_paths.comfy_primary_url}/system_stats"
        resp = http_client.get(url, timeout=5.0)
        resp.assert_ok(f"Failed to proxy system_stats through port 8188: {resp.error}")

        data = resp.json()
        assert "devices" in data, "Proxied system_stats response missing devices"
        assert len(data["devices"]) > 0, "Proxied devices list empty"
        assert "RTX 4090" in data["devices"][0].get("name", "")

    def test_f16_comfyui_queue_and_prompt_endpoints(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Verify the queue is readable and a missing workflow is rejected."""
        queue_url = f"{platform_paths.comfy_primary_url}/queue"
        resp_q = http_client.get(queue_url, timeout=5.0)
        resp_q.assert_ok("Queue endpoint unreachable")
        q_data = resp_q.json()
        assert "queue_running" in q_data and "queue_pending" in q_data

        prompt_url = f"{platform_paths.comfy_primary_url}/prompt"
        resp_p = http_client.post(prompt_url, json_data={"client_id": "e2e_test"}, timeout=5.0)
        resp_p.assert_status(400, "A request without a workflow must be rejected")
        p_data = resp_p.json()
        assert p_data.get("error", {}).get("type") == "no_prompt"
        assert "prompt_id" not in p_data, "Rejected requests must not create a prompt ID"
        queue_after = http_client.get(queue_url, timeout=5.0)
        queue_after.assert_ok("Queue endpoint unreachable after rejection")
        assert queue_after.json() == q_data, "Rejected requests must leave the queue unchanged"

    def test_f16_bridge_source_script_architecture(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify bridge implementation source file and dual-app architecture."""
        script_path = platform_paths.base_dir / "backend" / "comfy_primary_proxy_8188.py"
        assert script_path.exists(), f"Bridge source missing at {script_path}"

        code = script_path.read_text(encoding="utf-8", errors="replace")
        assert "8188" in code and "8189" in code, "Bridge must configure both ports 8188 and 8189"
        assert "TARGET_HOST = \"http://127.0.0.1:8189\"" in code
        assert "RTX 4090" in code, "RTX 4090 hardware profile must be registered"

    def test_f16_m5_audit_comfyui_pass(
        self, platform_paths: PlatformPaths
    ) -> None:
        """Verify ComfyUI subsystem passed in M5 audit report with 0 failures."""
        report_json = platform_paths.base_dir / "tests" / "m5_audit_report.json"
        assert report_json.exists(), f"M5 report missing: {report_json}"

        with open(report_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        comfy_sub = data.get("subsystems", {}).get("comfyui", {})
        assert comfy_sub.get("passed") is True, f"ComfyUI audit failed: {comfy_sub.get('failures')}"
        assert len(comfy_sub.get("failures", [])) == 0, f"Unexpected failures in ComfyUI audit: {comfy_sub.get('failures')}"
