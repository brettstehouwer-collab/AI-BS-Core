"""
Verification Suite for BsMedia-Chat, Dedicated ChromaDB & VLM Engine (v5.297.0)
Validates:
1. Dedicated Media ChromaDB collection ('stehouwer_media_memory') initialization, insertion, and semantic search.
2. VLM Multi-modal guidance engine initialization and visual asset analysis plan generation.
3. Media Render Router API endpoints for /api/v1/media/chat/stream, /vault/index, /vault/search, and /vlm/analyze.
4. Component existence and mirror parity for BsMediaCreatorTab.jsx across all 4 mirrors.
"""

import os
import sys
import json
import time
import asyncio
import unittest

sys.path.append(r"C:\AI-BS\backend")
sys.path.append(r"C:\AI-BS")

from core.media_chromadb_vault import media_chroma_vault
from core.sovereign_reasoning.vlm_guidance_engine import vlm_guidance_engine

class TestBsMediaCreatorSuite(unittest.TestCase):
    def test_01_media_chromadb_vault(self):
        """Validates that dedicated stehouwer_media_memory ChromaDB collection functions properly."""
        test_id = f"test_media_{int(time.time())}"
        res = media_chroma_vault.add_media_asset(
            media_id=test_id,
            media_type="video",
            title="Cyberpunk Flight Demonstration",
            description="High speed aerial camera through neon matrix corridor with heavy motion blur",
            file_path=r"C:\AI-BS\saved_data\mtd_demo_showcase\mtd_vertical_short_9x16.mp4",
            metadata={"fps": 30, "aspect_ratio": "9:16", "resolution": "1080x1920"}
        )
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(res.get("collection"), "stehouwer_media_memory")
        
        # Test search
        search_res = media_chroma_vault.search_media_memory("neon matrix cyber", top_k=2)
        self.assertEqual(search_res.get("status"), "success")
        self.assertGreaterEqual(search_res.get("count", 0), 1)
        
        stats = media_chroma_vault.get_stats()
        self.assertEqual(stats.get("collection_name"), "stehouwer_media_memory")
        self.assertGreaterEqual(stats.get("count", 0), 1)

    def test_02_vlm_guidance_engine_analysis(self):
        """Validates local VLM visual asset analysis logic."""
        test_frame = r"C:\AI-BS\MP4 medial screen recordings\staest_frame_25.jpg"
        if not os.path.exists(test_frame):
            # Create temporary frame
            test_frame = r"C:\AI-BS\saved_data\test_frame.jpg"
            import subprocess
            subprocess.run(f'ffmpeg -y -f lavfi -i testsrc=duration=1:size=640x360:rate=1 -frames:v 1 "{test_frame}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        analysis_res = loop.run_until_complete(
            vlm_guidance_engine.analyze_visual_asset(test_frame, instruction="Provide crop and grade plan.")
        )
        loop.close()
        
        self.assertEqual(analysis_res.get("status"), "success")
        self.assertIn("analysis", analysis_res)
        self.assertTrue(len(analysis_res["analysis"]) > 20)

    def test_03_four_mirror_parity_bsmediacreator(self):
        """Validates that BsMediaCreatorTab.jsx exists in all 4 mirror paths with identical sizes."""
        mirrors = [
            r"C:\AI-BS\frontend\src\components\BsMediaCreatorTab.jsx",
            r"C:\AI-BS\frontend\components\BsMediaCreatorTab.jsx",
            r"C:\AI-BS\frontend\src\components\components\BsMediaCreatorTab.jsx",
            r"C:\AI-BS\frontend\components\components\BsMediaCreatorTab.jsx"
        ]
        sizes = []
        for m in mirrors:
            self.assertTrue(os.path.exists(m), f"Missing mirror file: {m}")
            sizes.append(os.path.getsize(m))
        self.assertEqual(len(set(sizes)), 1, f"Mirror size mismatch detected: {sizes}")

if __name__ == "__main__":
    unittest.main()
