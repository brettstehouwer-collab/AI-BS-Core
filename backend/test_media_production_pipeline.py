"""
Test Suite for Autonomous Headless Media Production Studio (v5.294.0)
Validates all 13 media production domains, 40 new tools (121 total),
Zero-Copy IPC memory buffers, VRAM arbitration, atomic SQLite checkpoints,
and mandatory VFR-to-CFR pre-normalization gate.
"""

import os
import sys
import json
import time
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.vram_resource_arbiter import vram_arbiter, VRAMResourceArbiter
from core.media_render_engine import MediaRenderEngine
from tools.tool_registry import ToolRegistry


class TestMediaProductionPipeline(unittest.TestCase):
    def setUp(self):
        self.test_job_id = f"test_studio_{int(time.time() * 1000)}"

    # =========================================================================
    # 1. HARDWARE GOVERNANCE & VRAM ARBITRATION
    # =========================================================================
    def test_01_vram_telemetry_and_eviction(self):
        """Validates live RTX 4090 telemetry and cache flush."""
        telemetry = vram_arbiter.get_vram_telemetry()
        self.assertIn("device_name", telemetry)
        self.assertIn("total_mb", telemetry)
        self.assertGreaterEqual(telemetry["total_mb"], 24000)

        flush_res = vram_arbiter.flush_vram_cache()
        self.assertEqual(flush_res["status"], "success")

    def test_02_zero_copy_shared_memory_ipc(self):
        """Validates zero-copy shared memory buffer allocation and teardown."""
        buf_name = f"test_shm_{int(time.time())}"
        shape = (1080, 1920, 3)
        shm_buf = vram_arbiter.create_shared_frame_buffer(buf_name, shape, "uint8")
        self.assertIsNotNone(shm_buf)
        self.assertIn(buf_name, vram_arbiter._allocated_shared_buffers)

        # Release buffer
        vram_arbiter.release_shared_buffer(buf_name)
        self.assertNotIn(buf_name, vram_arbiter._allocated_shared_buffers)

    def test_03_atomic_sqlite_checkpoints(self):
        """Validates atomic persistence and resumption from media_pipeline_checkpoints."""
        job_id = self.test_job_id
        chk_id = vram_arbiter.save_checkpoint(
            job_id=job_id,
            domain_id=1,
            stage_name="vram_initialization",
            status="COMPLETED",
            input_payload={"stage": "start"},
            output_payload={"vram_available": True},
            vram_used_mb=256.0,
            execution_time_ms=12.5
        )
        self.assertTrue(chk_id.startswith("chk_"))

        # Retrieve checkpoint
        last_cp = vram_arbiter.get_last_successful_checkpoint(job_id)
        self.assertIsNotNone(last_cp)
        self.assertEqual(last_cp["job_id"], job_id)
        self.assertEqual(last_cp["status"], "COMPLETED")
        self.assertEqual(last_cp["stage_name"], "vram_initialization")

    # =========================================================================
    # 2. INGESTION & MANDATORY CFR PRE-NORMALIZATION GATE
    # =========================================================================
    def test_04_mandatory_cfr_normalization_gate(self):
        """Validates mandatory CFR lock before timeline cuts."""
        test_file = r"C:\AI-BS\sandbox\test_ingest.mp4"
        res = MediaRenderEngine.normalize_vfr_to_cfr(test_file, target_fps=30)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["domain"], 12)
        self.assertTrue(res["cfr_locked"])
        self.assertEqual(res["target_fps"], 30)

    # =========================================================================
    # 3. SEMANTIC COMPUTER VISION & AUDIO ENGINEERING
    # =========================================================================
    def test_05_shot_boundary_and_smart_reframe(self):
        """Validates shot boundary detection and 9:16 vertical reframing."""
        test_video = r"C:\AI-BS\sandbox\demo.mp4"
        shot_res = MediaRenderEngine.detect_shot_boundaries(test_video, threshold=27.0)
        self.assertEqual(shot_res["status"], "success")
        self.assertIn("scenes", shot_res)

        reframe_res = MediaRenderEngine.smart_reframe_vertical(test_video, target_aspect="9:16")
        self.assertEqual(reframe_res["status"], "success")
        self.assertEqual(reframe_res["target_aspect"], "9:16")

    def test_06_audio_engineering_and_ducking(self):
        """Validates audio sidechain ducking and EBU R128 loudness normalization."""
        speech = r"C:\AI-BS\sandbox\speech.wav"
        music = r"C:\AI-BS\sandbox\music.wav"
        duck_res = MediaRenderEngine.duck_background_music(speech, music, duck_db=-12.0)
        self.assertEqual(duck_res["status"], "success")
        self.assertEqual(duck_res["duck_db"], -12.0)

        lufs_res = MediaRenderEngine.normalize_ebu_loudness(speech, target_lufs=-14.0)
        self.assertEqual(lufs_res["status"], "success")
        self.assertEqual(lufs_res["target_lufs"], -14.0)

    # =========================================================================
    # 4. RASTER GRAPHICS & RECIPE ORCHESTRATION
    # =========================================================================
    def test_07_pyvips_and_psd_composition(self):
        """Validates high-res Pyvips streaming and PSD layer composition."""
        img_path = r"C:\AI-BS\sandbox\cover.png"
        ops = [{"type": "resize", "width": 1920}, {"type": "cmyk"}]
        raster_res = MediaRenderEngine.pyvips_raster_transform(img_path, ops, output_format="png")
        self.assertEqual(raster_res["status"], "success")
        self.assertTrue(raster_res["zero_copy_stream"])

    def test_08_end_to_end_recipe_execution(self):
        """Validates multi-domain recipe execution with atomic checkpoints."""
        recipe = {
            "title": "Automated Book Promo",
            "stages": [
                {"domain": 12, "action": "normalize_cfr", "input": "raw_footage.mp4"},
                {"domain": 2, "action": "smart_reframe", "aspect": "9:16"},
                {"domain": 4, "action": "vse_timeline", "resolution": "1080x1920"},
                {"domain": 8, "action": "verify_qc", "min_vmaf": 93.0}
            ]
        }
        res = MediaRenderEngine.execute_media_pipeline_recipe(recipe, job_id=self.test_job_id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["stages_completed"], 5)
        self.assertTrue(res["checkpoints_saved"])

    # =========================================================================
    # 5. TOOL REGISTRY PARITY (121 TOTAL TOOLS)
    # =========================================================================
    def test_09_tool_registry_count_and_dispatch(self):
        """Validates that exactly 123 tools are registered and callable."""
        tools = ToolRegistry.get_tool_declarations()
        tool_names = [t["name"] for t in tools]
        self.assertEqual(len(tools), 123, f"Expected 123 tools, got {len(tools)}")

        # Verify key new media studio tools exist
        media_tools = [
            "vram_telemetry_status", "vram_evict_cache", "vram_manage_shared_buffer",
            "save_pipeline_checkpoint", "resume_pipeline_checkpoint",
            "detect_shot_boundaries", "smart_reframe_vertical", "stabilize_camera_motion",
            "inpaint_temporal_artifacts", "compose_psd_layers", "pyvips_raster_transform",
            "comfy_outpaint_expand", "extract_alpha_matting", "assemble_vse_timeline",
            "strip_audio_silences", "beat_sync_timeline_cuts", "apply_3d_lut_grade",
            "render_natron_vfx_graph", "clone_neural_voice_tts", "deepfilter_audio_clean",
            "duck_background_music", "normalize_ebu_loudness", "vectorize_raster_to_svg",
            "shape_typography_harfbuzz", "generate_karaoke_captions",
            "synthesize_3d_mesh_trellis", "render_gaussian_splat_sweep",
            "verify_vmaf_quality", "score_aesthetic_thumbnails", "inject_rich_metadata",
            "package_hls_stream", "execute_media_pipeline_recipe", "query_media_workflow_vault",
            "synthesize_wan_video_broll", "retarget_neural_character",
            "synthesize_prosody_tts", "match_dialogue_duration",
            "normalize_vfr_to_cfr", "ingest_media_stream_ytdlp",
            "render_web_overlay_pyppeteer", "convert_script_to_production_recipe",
            "generate_script_storyboard_prompts"
        ]
        for tool_name in media_tools:
            self.assertIn(tool_name, tool_names, f"Missing media studio tool: {tool_name}")

        # Test execution dispatch for a representative tool
        call_res = ToolRegistry.execute_tool("vram_telemetry_status", {})
        self.assertIn("device_name", call_res)
        self.assertEqual(call_res["device_name"], "NVIDIA GeForce RTX 4090")


if __name__ == "__main__":
    unittest.main()
