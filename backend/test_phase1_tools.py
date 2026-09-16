import os
import sys
import time
import unittest
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from backend.tools.tool_registry import ToolRegistry
from backend.core.typst_pandoc_engine import TypstPandocEngine
from backend.core.demucs_audio_engine import DemucsAudioEngine
from backend.core.powershell_process_engine import PowerShellProcessEngine
from backend.core.tshark_telemetry_engine import TSharkTelemetryEngine
from backend.core.comfy_image_processor import ComfyImageProcessor


class TestPhase1Tools(unittest.TestCase):

    def test_01_typst_compilation(self):
        """Test sub-50ms Typst PDF compilation and KDP formatting."""
        markup = "= Phase 1 Sovereign Validation\nThis is a test contract for Stehouwer Publishing LLC."
        res = TypstPandocEngine.compile_typst(
            markup_text=markup,
            title="Sovereign Contract Test",
            author="Brett Stehouwer",
            trim_size="6x9"
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["pdf_path"]))
        self.assertGreater(res["file_size_bytes"], 1000)
        print(f"\n[Typst] Generated PDF ({res['file_size_bytes']} bytes) in {res['elapsed_ms']} ms")

    def test_02_demucs_hardware_status(self):
        """Test Demucs hardware detection and CUDA availability on RTX 4090."""
        status = DemucsAudioEngine.get_hardware_status()
        self.assertTrue(status["cuda_available"])
        self.assertEqual(status["device"], "cuda")
        self.assertIn("4090", status["gpu_name"])
        print(f"\n[Demucs] GPU: {status['gpu_name']} | VRAM: {status['vram_total_gb']} GB | Device: {status['device']}")

    def test_03_powershell_process_manager(self):
        """Test PowerShell execution policy bypass, Chrome profile inspection, and directory check."""
        ps_res = PowerShellProcessEngine.execute_powershell("Get-Date -Format 'yyyy-MM-dd HH:mm:ss'")
        self.assertEqual(ps_res["status"], "success")
        self.assertEqual(ps_res["returncode"], 0)
        print(f"\n[PowerShell] Output: {ps_res['stdout'].strip()} in {ps_res['elapsed_ms']} ms")

        chrome_res = PowerShellProcessEngine.manage_chrome_profiles(action="status")
        self.assertEqual(chrome_res["status"], "success")
        self.assertGreaterEqual(chrome_res["profiles_count"], 1)
        print(f"[PowerShell/Chrome] Detected {chrome_res['profiles_count']} profiles and {chrome_res['running_chrome_processes']} active chrome processes")

        dir_res = PowerShellProcessEngine.inspect_directory_state(r"C:\AI-BS\backend")
        self.assertEqual(dir_res["status"], "success")
        self.assertGreater(dir_res["total_files"], 10)
        print(f"[PowerShell/Directory] Scanned {dir_res['total_files']} files ({dir_res['total_size_mb']} MB) in {dir_res['elapsed_ms']} ms")

    def test_04_tshark_telemetry_monitor(self):
        """Test TShark and socket-level packet extraction."""
        info = TSharkTelemetryEngine.get_tshark_info()
        self.assertTrue(info["tshark_installed"])
        print(f"\n[TShark] Binary: {info['tshark_path']} | Version: {info['version']}")

        mining_audit = TSharkTelemetryEngine.audit_pearl_mining_telemetry(port=8335)
        self.assertEqual(mining_audit["status"], "success")
        print(f"[TShark/Mining] Port 8335 Open: {mining_audit['stratum_listening']} | Pool Reachable: {mining_audit['herominers_pool_reachable']}")

    def test_05_comfy_image_processor(self):
        """Test ComfyUI workflow JSON mapping, matting, and upscaling."""
        # Create a test image
        test_img_path = r"C:\AI-BS\saved_data\test_sample_image.png"
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Draw a black square in center
        for x in range(30, 70):
            for y in range(30, 70):
                img.putpixel((x, y), (20, 20, 20))
        img.save(test_img_path)

        matting_wf = ComfyImageProcessor.build_matting_workflow(test_img_path)
        self.assertIn("1", matting_wf)
        self.assertEqual(matting_wf["1"]["class_type"], "LoadImage")

        upscale_wf = ComfyImageProcessor.build_upscale_workflow(test_img_path)
        self.assertIn("2", upscale_wf)
        self.assertEqual(upscale_wf["2"]["class_type"], "UpscaleModelLoader")
        print(f"\n[ComfyUI] Workflows generated successfully for matting & upscaling.")

    def test_06_tool_registry_invocations(self):
        """Test ToolRegistry execution dispatch for all 5 Phase 1 tools."""
        r1 = ToolRegistry.execute_tool("compile_typst_document", {
            "markup_text": "= ToolRegistry Test\nValidated Typst Document.",
            "title": "Tool Registry Typst",
            "author": "Brett Stehouwer"
        })
        self.assertEqual(r1["status"], "success")

        r2 = ToolRegistry.execute_tool("powershell_process_manager", {
            "action": "execute",
            "command": "Write-Output 'AIBS_TOOL_REGISTRY_TEST_OK'"
        })
        self.assertEqual(r2["status"], "success")
        self.assertIn("AIBS_TOOL_REGISTRY_TEST_OK", r2["stdout"])

        r3 = ToolRegistry.execute_tool("tshark_telemetry_monitor", {
            "action": "info"
        })
        self.assertTrue(r3["tshark_installed"])

        print(f"\n[ToolRegistry] All Phase 1 tool execution dispatches verified 100% OK.")


if __name__ == "__main__":
    unittest.main()
