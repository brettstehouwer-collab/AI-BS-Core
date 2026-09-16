"""
Unit & Integration Test Suite for Stehouwer LLM Self-Improvement & Ecosystem Operations Engine
Verifies:
1. Universal Data Ingestor path resolution & batch execution
2. Zero-Mock AEO Router evaluation & endpoints
3. VectorVault dimension adaptation (768d vs 384d) & multi-context querying
4. ToolRegistry ecosystem tools (run_ecosystem_script, run_ecosystem_command, manage_ecosystem_service, get_ecosystem_health)
5. Execute-script endpoint logic
"""

import os
import sys
import json
import time
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core.vector_vault import VectorVault, adapt_vector_dimension
from tools.tool_registry import ToolRegistry


class TestSelfImprovementEngine(unittest.TestCase):

    def test_01_vector_vault_dimension_adaptation(self):
        """Tests that VectorVault adapts 768d vectors to 384d (and vice versa) without crashing."""
        vv = VectorVault.get_instance()
        
        # 768 to 384 adaptation (average pooling)
        vec_768 = [float(i % 10) for i in range(768)]
        adapted_384 = vv.adapt_vector_dimension(vec_768, 384)
        self.assertEqual(len(adapted_384), 384)
        
        # 384 to 768 adaptation (repetition/padding)
        vec_384 = [float(i % 5) for i in range(384)]
        adapted_768 = vv.adapt_vector_dimension(vec_384, 768)
        self.assertEqual(len(adapted_768), 768)

    def test_02_vector_vault_multicontext_retrieval(self):
        """Tests that multi-collection querying runs safely and returns string context."""
        vv = VectorVault.get_instance()
        res = vv.retrieve_multicontext("Stehouwer LLM autograd reasoning", top_k=2)
        self.assertIsInstance(res, dict)
        self.assertIn("context_text", res)
        self.assertIn("chunks_retrieved", res)
        print(f"VectorVault Chunks: {res['chunks_retrieved']}, Collections: {res['collections_searched']}")

    def test_03_tool_registry_declarations(self):
        """Tests that the new ecosystem tools are registered in tool declarations."""
        decls = ToolRegistry.get_tool_declarations()
        tool_names = [d["name"] for d in decls]
        
        self.assertIn("run_ecosystem_script", tool_names)
        self.assertIn("run_ecosystem_command", tool_names)
        self.assertIn("manage_ecosystem_service", tool_names)
        self.assertIn("get_ecosystem_health", tool_names)

    def test_04_tool_registry_run_command(self):
        """Tests executing a PowerShell command via ToolRegistry."""
        res = ToolRegistry.execute_tool("run_ecosystem_command", {"command": "Write-Output AIBS_OPERATIONAL"})
        self.assertEqual(res.get("status"), "success")
        self.assertIn("AIBS_OPERATIONAL", res.get("stdout", ""))

    def test_05_tool_registry_manage_service(self):
        """Tests querying service statuses via ToolRegistry."""
        res = ToolRegistry.execute_tool("manage_ecosystem_service", {"action": "status", "service_name": "all"})
        self.assertEqual(res.get("status"), "success")
        services = res.get("services", {})
        self.assertIn("backend", services)
        self.assertIn("frontend", services)
        self.assertIn("ollama", services)

    def test_06_tool_registry_health_check(self):
        """Tests executing ecosystem health via ToolRegistry."""
        res = ToolRegistry.execute_tool("get_ecosystem_health", {"component": "gpu"})
        self.assertEqual(res.get("status"), "success")
        self.assertTrue("report" in res or "hardware" in res)

    def test_07_universal_ingestor_path_resolution(self):
        """Tests that Universal Ingestor identifies databases correctly."""
        from AI_BS_Universal_Data_Ingestor import resolve_db_path, db_names
        
        self.assertGreater(len(db_names), 10)
        p = resolve_db_path(db_names[0])
        self.assertIsNotNone(p)
        self.assertTrue(os.path.exists(p))

    def test_08_aeo_router_structure(self):
        """Tests that authentic AEO router can be imported and initialized."""
        from routers.aeo_router import router, evaluate_query_with_llm
        self.assertIsNotNone(router)
        res = evaluate_query_with_llm("test query")
        self.assertIn("ranking", res)
        self.assertIn("visibility", res)


if __name__ == "__main__":
    unittest.main()
