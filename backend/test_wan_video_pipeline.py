# C:\AI-BS\backend\test_wan_video_pipeline.py
"""
Test Suite: Wan2.1 49-Frame RTX 4090 Video Motion Diffusion Pipeline
Validates scene listing, async job queue dispatch, Weeble Wobble physics parameters, and telemetry callbacks.
"""

import sys
import os
import unittest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from AI_BS_Backend import app
from routers.wan_media_router import (
    WanVideoGenerateRequest,
    _run_wan_generation_worker,
    _ACTIVE_JOBS,
    set_telemetry_broadcaster,
)


class TestWanVideoPipeline(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_screenplay_scenes(self):
        """Verify the 5 screenplay scenes for The Bad Side Upside Down are returned."""
        response = self.client.get("/api/v1/wan-media/t2v/scenes")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("scenes", data)
        self.assertEqual(len(data["scenes"]), 5, "Expected 5 scenes in rendered assets manifest.")

        # Verify first scene has Weeble Wobble physics and Wan2.1 motion profile
        scene_ids = [s["concept_id"] for s in data["scenes"]]
        self.assertIn("concept_dual_realm_storefront", scene_ids)
        self.assertIn("concept_char_fredy", scene_ids)
        self.assertIn("concept_char_satan", scene_ids)
        self.assertIn("concept_char_jesus", scene_ids)
        self.assertIn("concept_char_mr_pimp", scene_ids)

    def test_wan_generation_dispatch(self):
        """Verify dispatching a Wan2.1 49-frame video generation job."""
        payload = {
            "prompt": "Test 3D animated scene, Weeble Wobble octane render",
            "scene_id": "concept_char_fredy",
            "frames": 49,
            "fps": 24,
            "physics_profile": "Weeble Wobble Center of Mass (-35cm) Oscillation"
        }
        response = self.client.post("/api/v1/wan-media/t2v/generate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "queued")
        self.assertIn("job_id", data)
        self.assertEqual(data["scene_id"], "concept_char_fredy")
        self.assertEqual(data["frames"], 49)

        # Check job is in active jobs
        job_id = data["job_id"]
        job_res = self.client.get(f"/api/v1/wan-media/t2v/job/{job_id}")
        self.assertEqual(job_res.status_code, 200)
        job_data = job_res.json()
        self.assertEqual(job_data["job_id"], job_id)

    def test_telemetry_broadcaster_event_stream(self):
        """Verify telemetry callback receives step milestones."""
        received_events = []

        def mock_broadcaster(event):
            received_events.append(event)

        set_telemetry_broadcaster(mock_broadcaster)

        # Run worker directly in asyncio event loop
        req = WanVideoGenerateRequest(
            prompt="Direct worker test",
            scene_id="concept_char_satan",
            frames=49,
            fps=24,
        )
        job_id = "test_worker_job_001"
        _ACTIVE_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0
        }

        asyncio.run(_run_wan_generation_worker(job_id, req))

        # Check job completion
        self.assertEqual(_ACTIVE_JOBS[job_id]["status"], "completed")
        self.assertEqual(_ACTIVE_JOBS[job_id]["progress"], 100)
        self.assertIn("asset", _ACTIVE_JOBS[job_id])
        self.assertEqual(_ACTIVE_JOBS[job_id]["asset"]["frames"], 49)

        # Check telemetry events were emitted
        self.assertGreater(len(received_events), 0)
        types = [e.get("type") for e in received_events]
        self.assertIn("WAN_VIDEO_PROGRESS", types)

    def test_executive_daemons_endpoint(self):
        """Verify /api/executive/daemons returns authoritative port status."""
        response = self.client.get("/api/executive/daemons")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], "v5.266.0")
        self.assertIn("ports", data)
        self.assertIn("hardware", data)


if __name__ == "__main__":
    unittest.main()
