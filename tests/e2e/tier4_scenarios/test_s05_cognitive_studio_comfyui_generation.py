"""Tier 4 Real-World Application Scenario 05: Cognitive Studio Authoring to ComfyUI RTX 4090 Generation.

Exercises: F01 (Sheltered Hub Stations), F13 (Vector Retrieval),
F15 (FastAPI Master Engine), F16 (ComfyUI RTX 4090 Bridge).
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
class TestS05CognitiveStudioComfyUIGeneration:
    """Scenario 05: Cognitive Studio Authoring to ComfyUI RTX 4090 Generation."""

    def test_s05_studio_notes_to_generative_prompt_dispatch(
        self, platform_paths: PlatformPaths, http_client: HttpClientHelper
    ) -> None:
        """Execute full flow: retrieve story context -> check RTX 4090 capacity -> submit prompt."""
        # 1. Retrieve story context via RAG
        rag_url = f"{platform_paths.backend_url}/api/rag/query"
        rag_payload = {"query": "screenplay opening", "top_k": 1, "collection": "ai_bs_synced_drive_assets"}
        resp_rag = http_client.post(rag_url, json_data=rag_payload, timeout=20.0)
        resp_rag.assert_ok()

        # 2. Check ComfyUI hardware telemetry (RTX 4090 device)
        stats_url = f"{platform_paths.comfy_primary_url}/system_stats"
        resp_stats = http_client.get(stats_url, timeout=5.0)
        resp_stats.assert_ok()

        stats = resp_stats.json()
        assert "devices" in stats and len(stats["devices"]) > 0
        device = stats["devices"][0]
        assert "RTX 4090" in device.get("name", "")
        assert device.get("vram_free", 0) > 10_000_000_000

        # 3. Submit generation job to ComfyUI Primary Gateway
        prompt_url = f"{platform_paths.comfy_primary_url}/prompt"
        job_payload = {
            "client_id": "cognitive_studio_authoring",
            "prompt": {"6": {"inputs": {"text": "Sheltered Hub dimly lit cinematic opening"}}},
        }
        resp_prompt = http_client.post(prompt_url, json_data=job_payload, timeout=5.0)
        resp_prompt.assert_ok()

        prompt_data = resp_prompt.json()
        assert "prompt_id" in prompt_data
        assert prompt_data.get("number", 0) >= 1

        # 4. Check Queue status
        queue_url = f"{platform_paths.comfy_primary_url}/queue"
        resp_queue = http_client.get(queue_url, timeout=5.0)
        resp_queue.assert_ok()
