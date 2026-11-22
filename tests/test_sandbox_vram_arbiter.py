import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))
from vram_manager import VRAMOrchestrator

class TestSandboxVRAMArbiter(unittest.TestCase):
    def setUp(self):
        self.arbiter = VRAMOrchestrator(total_vram_gb=24.0)

    def test_initial_state(self):
        self.assertEqual(self.arbiter.total_vram_gb, 24.0)
        self.assertEqual(self.arbiter.free_vram_gb, 24.0)
        self.assertEqual(self.arbiter.used_vram_gb, 0.0)

    def test_standard_allocation(self):
        granted = self.arbiter.request_gpu_budget("ollama", 8.0)
        self.assertTrue(granted)
        self.assertEqual(self.arbiter.used_vram_gb, 8.0)
        self.assertEqual(self.arbiter.free_vram_gb, 16.0)

    @patch("requests.post")
    def test_auto_eviction_on_heavy_comfyui_load(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Allocate 8GB to Ollama
        self.arbiter.request_gpu_budget("ollama", 8.0)
        self.assertEqual(self.arbiter.free_vram_gb, 16.0)

        # ComfyUI requests 20GB (which exceeds 16GB free)
        # Arbiter should auto-evict Ollama (freeing 8GB -> 24GB free) and grant ComfyUI 20GB
        granted = self.arbiter.request_gpu_budget("comfyui_flux", 20.0, auto_evict=True)
        self.assertTrue(granted)
        self.assertNotIn("ollama", self.arbiter.allocations)
        self.assertEqual(self.arbiter.allocations["comfyui_flux"], 20.0)
        self.assertEqual(self.arbiter.free_vram_gb, 4.0)

        # Release ComfyUI budget and verify Ollama warm-up call
        freed = self.arbiter.release_gpu_budget("comfyui_flux", restore_ollama=True)
        self.assertEqual(freed, 20.0)

    def test_oversized_allocation_rejected(self):
        granted = self.arbiter.request_gpu_budget("huge_model", 32.0, auto_evict=True)
        self.assertFalse(granted)
        self.assertEqual(self.arbiter.used_vram_gb, 0.0)

if __name__ == "__main__":
    unittest.main()
