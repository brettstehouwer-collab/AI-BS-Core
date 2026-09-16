"""
Comprehensive Automated Test Suite for AI-BS Ecosystem Additions (v5.286.0+)
Tests:
1. Media Render Engine (Manim script & Canvas overlay)
2. Ebook Factoring Engine (PDF/EPUB & PDF stream optimization)
3. Audio DSP & Prosody Engine (DSP filters & Lyric Prosody mapper)
4. Binary & Hardware Workbench Engine (Capstone disassembly & Bench diagnostics)
5. Quantitative & Spatial Analytics Engine (DuckDB queries & TA Indicators & Project NOCO spatial metrics)
6. OBS Broadcast Controller (Process scanning & Highlight marker logging)
7. Multi-Agent Specialist Crews (Dynamic supervisor intent routing & Security policy validation)
8. Autonomous Swarm & Graph Engine (Sandbox refinement & Episodic graph relations)
9. ToolRegistry Execution Integration across all new tools
"""

import os
import sys
import unittest
import time
import json

# Ensure AI-BS root is on sys.path
AIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if AIBS_ROOT not in sys.path:
    sys.path.insert(0, AIBS_ROOT)
if os.path.join(AIBS_ROOT, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(AIBS_ROOT, "backend"))

from backend.core.media_render_engine import MediaRenderEngine
from backend.core.ebook_factoring_engine import EbookFactoringEngine
from backend.core.audio_dsp_prosody_engine import AudioDspProsodyEngine
from backend.core.binary_hardware_workbench_engine import BinaryHardwareWorkbenchEngine
from backend.core.quantitative_spatial_analytics_engine import QuantitativeSpatialAnalyticsEngine
from backend.core.obs_broadcast_controller import ObsBroadcastController
from backend.core.agent_specialist_crew import AgentSpecialistCrewEngine
from backend.core.autonomous_swarm_graph_engine import AutonomousSwarmGraphEngine
from backend.tools.tool_registry import ToolRegistry


class TestAllEcosystemAdditions(unittest.TestCase):

    def test_01_media_render_engine(self):
        """Test Manim animation script compilation and Canvas HUD overlay rendering."""
        # 1. Manim
        scene_code = """
class TestScene(Scene):
    def construct(self):
        c = Circle(color=BLUE)
        self.play(Create(c))
"""
        res_manim = MediaRenderEngine.render_manim_animation(scene_code=scene_code, scene_name="TestScene")
        self.assertIn(res_manim["status"], ["success", "partial"])
        self.assertIn("script_path", res_manim)

        # 2. Canvas Overlay
        metrics = {"FPS": "60.0", "GPU_VRAM": "4.2/24.0 GB", "RTX_TEMP": "48°C", "CRO_PRICE": "$0.0574"}
        res_canvas = MediaRenderEngine.render_canvas_overlay(title="Live Broadcast HUD", metrics=metrics)
        self.assertEqual(res_canvas["status"], "success")
        self.assertTrue(os.path.exists(res_canvas["overlay_html_path"]))
        print("[PASS] 01. Media Render Engine verified.")

    def test_02_ebook_factoring_engine(self):
        """Test eBook compilation and PDF stream optimization."""
        sample_text = "This is the sovereign manuscript for Stehouwer Publishing LLC.\n\nChapter 1: The Zero-Cost Mandate."
        res_ebook = EbookFactoringEngine.convert_ebook(
            input_text_or_path=sample_text,
            to_format="pdf",
            title="Stehouwer Publishing Test Book",
            author="Brett Stehouwer"
        )
        self.assertEqual(res_ebook["status"], "success")
        pdf_path = res_ebook["output_path"]
        self.assertTrue(os.path.exists(pdf_path))

        # Test PDF optimization
        res_opt = EbookFactoringEngine.optimize_pdf_stream(pdf_path=pdf_path, watermark_text="CONFIDENTIAL AI-BS")
        self.assertEqual(res_opt["status"], "success")
        self.assertTrue(os.path.exists(res_opt["output_path"]))
        print("[PASS] 02. Ebook Factoring & PDF Stream Optimization verified.")

    def test_03_audio_prosody_engine(self):
        """Test Lyric prosody mapping and DAW 4/4 grid alignment."""
        sample_lyrics = """
I got the master plan running on the local host
RTX forty ninety making records coast to coast
Never pay a fee when we execute the code
Zero cost engine on the sovereign road
"""
        res_prosody = AudioDspProsodyEngine.map_lyrics_prosody(raw_lyrics=sample_lyrics, bpm=130)
        self.assertEqual(res_prosody["status"], "success")
        self.assertEqual(res_prosody["total_bars"], 4)
        self.assertGreater(res_prosody["total_syllables"], 20)
        self.assertIn("mapped_bars", res_prosody)
        print(f"[PASS] 03. Lyric Prosody Mapper verified ({res_prosody['total_bars']} bars, {res_prosody['avg_syllables_per_bar']} avg syl/bar).")

    def test_04_binary_hardware_workbench_engine(self):
        """Test Capstone binary disassembly, AOB extraction, and Bench diagnostics."""
        # 1. Disassembly of x64 prologue: push rbp; mov rbp, rsp; sub rsp, 0x20
        hex_prologue = "55 48 89 E5 48 83 EC 20"
        res_disasm = BinaryHardwareWorkbenchEngine.disassemble_binary_or_bytes(hex_bytes_or_path=hex_prologue, arch="x64")
        self.assertEqual(res_disasm["status"], "success")
        self.assertGreater(res_disasm["instruction_count"], 0)
        self.assertTrue(len(res_disasm["aob_signature"]) > 0)

        # 2. Bench diagnostics
        res_bench = BinaryHardwareWorkbenchEngine.query_bench_diagnostics(device_model="iPhone 14 Pro", symptom_or_rail="VDD_MAIN")
        self.assertEqual(res_bench["status"], "success")
        self.assertGreater(res_bench["matches_found"], 0)
        print("[PASS] 04. Binary Disassembler & Bench Diagnostics verified.")

    def test_05_quantitative_spatial_analytics_engine(self):
        """Test DuckDB cross-database SQL querying, TA Indicators, and Project NOCO spatial math."""
        # 1. DuckDB Query
        res_duck = QuantitativeSpatialAnalyticsEngine.execute_duckdb_query("SELECT 42 AS answer, 'AI-BS' AS ecosystem;")
        self.assertEqual(res_duck["status"], "success")
        self.assertEqual(res_duck["results"][0]["answer"], 42)

        # 2. Technical Indicators (RSI, MACD, Bollinger Bands)
        test_prices = [0.055, 0.056, 0.0555, 0.057, 0.058, 0.0575, 0.059, 0.060, 0.0595, 0.061, 0.062, 0.0615, 0.063, 0.064, 0.0635, 0.065, 0.066, 0.0655, 0.067, 0.068, 0.0675]
        res_ta = QuantitativeSpatialAnalyticsEngine.calculate_technical_indicators(prices=test_prices)
        self.assertEqual(res_ta["status"], "success")
        self.assertIn("rsi", res_ta)
        self.assertIn("bollinger_bands", res_ta)

        # 3. Project NOCO Spatial Calculator
        res_noco = QuantitativeSpatialAnalyticsEngine.calculate_noco_spatial_parameters(facility_sq_ft=2400.0, growing_tiers=4)
        self.assertEqual(res_noco["status"], "success")
        self.assertGreater(res_noco["agricultural_metrics"]["total_plant_sites"], 1000)
        print("[PASS] 05. DuckDB Analytics, TA Indicators & Project NOCO Spatial verified.")

    def test_06_obs_broadcast_controller(self):
        """Test OBS broadcast state inspection and highlight clip marker logging."""
        res_obs = ObsBroadcastController.get_broadcast_state()
        self.assertEqual(res_obs["status"], "success")
        self.assertIn("suggested_scene", res_obs)

        res_marker = ObsBroadcastController.log_clip_marker(marker_name="Epic Moment", description="Test stream highlight")
        self.assertEqual(res_marker["status"], "success")
        print("[PASS] 06. OBS Broadcast Controller & Auto-Director verified.")

    def test_07_agent_specialist_crew(self):
        """Test Multi-Agent supervisor routing and security policy validation."""
        # 1. Routing to Audio Specialist
        res_route_audio = AgentSpecialistCrewEngine.route_to_specialist("Please strip the vocals and master this wav track to -14 LUFS")
        self.assertEqual(res_route_audio["assigned_crew_id"], "audio_producer")

        # 2. Routing to Workbench Specialist
        res_route_bench = AgentSpecialistCrewEngine.route_to_specialist("Check the diode mode readings on the iPhone VDD_MAIN rail")
        self.assertEqual(res_route_bench["assigned_crew_id"], "workbench_diagnostician")

        # 3. Security gatekeeper validation
        res_sec_safe = AgentSpecialistCrewEngine.validate_command_security("powershell -ExecutionPolicy Bypass -Command 'Get-Process'")
        self.assertTrue(res_sec_safe["safe"])

        res_sec_danger = AgentSpecialistCrewEngine.validate_command_security("format C:")
        self.assertFalse(res_sec_danger["safe"])
        print("[PASS] 07. Multi-Agent Specialist Crews & Security Gatekeeper verified.")

    def test_08_autonomous_swarm_graph_engine(self):
        """Test Sandbox code refinement, episodic graph relation storage, and digital twin sync."""
        # 1. Sandbox execution
        safe_code = "print('AI-BS Autonomous Refinement Test Passed')\nassert 2 + 2 == 4"
        res_refine = AutonomousSwarmGraphEngine.refine_and_test_code(code=safe_code, script_name="test_autonomous_pass.py")
        self.assertEqual(res_refine["status"], "success")

        # 2. Episodic graph persistence
        res_graph = AutonomousSwarmGraphEngine.record_graph_relation(
            source_name="RTX 4090",
            source_type="hardware_gpu",
            relation="powers_inference_for",
            target_name="Demucs Audio Separator",
            target_type="dsp_engine"
        )
        self.assertEqual(res_graph["status"], "success")

        # 3. Digital twin sync
        res_twin = AutonomousSwarmGraphEngine.sync_digital_twin_telemetry({"soil_moisture": 42.5, "light_par": 850, "stage_rt60": 0.95})
        self.assertEqual(res_twin["status"], "success")
        print("[PASS] 08. Autonomous Swarm & Episodic Graph Engine verified.")

    def test_09_tool_registry_dispatches(self):
        """Test that ToolRegistry dispatches newly registered tools properly."""
        r1 = ToolRegistry.execute_tool("map_lyrics_prosody", {"raw_lyrics": "Line one rhyme\nLine two time", "bpm": 120})
        self.assertEqual(r1["status"], "success")

        r2 = ToolRegistry.execute_tool("execute_duckdb_query", {"sql_query": "SELECT 'Sovereign' as mode;"})
        self.assertEqual(r2["status"], "success")

        r3 = ToolRegistry.execute_tool("query_bench_diagnostics", {"device_model": "iPhone 13", "symptom_or_rail": "PPBUS"})
        self.assertEqual(r3["status"], "success")

        r4 = ToolRegistry.execute_tool("route_to_specialist", {"prompt": "Calculate RSI and MACD for CRO"})
        self.assertEqual(r4["assigned_crew_id"], "crypto_scalper")
        print("[PASS] 09. Tool Registry integration verified across all new tools.")


if __name__ == "__main__":
    unittest.main()
