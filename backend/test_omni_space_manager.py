import os
import sys
import unittest
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.omni_space_manager import omni_space_manager
from core.oversight_parent_engine import master_oversight_engine


class TestOmniSpaceAndOversight(unittest.TestCase):

    def test_all_11_spaces_presence_and_integrity(self):
        """Validates that all 11 database spaces are recognized and pass quick_check."""
        overview = omni_space_manager.get_spaces_overview()
        self.assertEqual(len(overview), 11, f"Expected 11 spaces, found {len(overview)}")
        
        for space_id, info in overview.items():
            self.assertTrue(info["exists"], f"Space {space_id} file does not exist: {info['path']}")
            self.assertEqual(info["integrity"], "ok", f"Space {space_id} integrity failed: {info['integrity']}")
            self.assertGreater(info["tables_count"], 0, f"Space {space_id} has 0 tables")

    def test_universal_space_retrieval(self):
        """Validates cross-database search returns structured matches with execution telemetry."""
        res = omni_space_manager.search_all_spaces("Grand Rapids", limit_per_space=3)
        self.assertEqual(res["query"], "Grand Rapids")
        self.assertGreater(res["spaces_searched"], 0)
        self.assertIn("matches_by_space", res)
        self.assertIn("execution_time_ms", res)
        card = omni_space_manager.format_retrieval_card(res)
        self.assertIn("Universal Space Retrieval Report", card)

    def test_on_demand_ingest_vault(self):
        """Validates that on-demand ingestion successfully persists and commits to stehouwer_vault."""
        test_content = "UnitTest Note: Sovereign cognitive ingestion verification"
        res = omni_space_manager.ingest_on_demand(
            content=test_content,
            target_space="stehouwer_vault",
            target_table="vault_items",
            metadata={"source": "test_suite", "category": "unit_test"}
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["target_space"], "stehouwer_vault")
        self.assertEqual(res["target_table"], "vault_items")
        self.assertIsNotNone(res["record_id"])
        self.assertEqual(res["integrity_check"], "verified")

    def test_on_demand_ingest_leads(self):
        """Validates auto-routing of commercial lead content into growth_leads."""
        lead_content = "Commercial B2B Lead: West Michigan Manufacturing Corp | precision CNC milling | contact: info@wm-mfg.example.com"
        res = omni_space_manager.ingest_on_demand(content=lead_content)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["target_table"], "growth_leads")
        self.assertIsNotNone(res["record_id"])

    def test_43_modules_oversight_inspection(self):
        """Validates that all 43 Master Hub modules are cataloged and mapped across 6 operational domains."""
        res = master_oversight_engine.inspect_all_modules()
        self.assertEqual(res["total_modules"], 43, f"Expected 43 modules, found {res['total_modules']}")
        self.assertEqual(len(res["modules"]), 43)
        self.assertEqual(len(res["domains"]), 6)
        
        domain_names = list(res["domains"].keys())
        self.assertIn("Business Operations", domain_names)
        self.assertIn("Hollywood & Creative", domain_names)
        self.assertIn("Hospitality OS", domain_names)
        self.assertIn("Creator Studio", domain_names)
        self.assertIn("Neural & Dev IDE", domain_names)
        self.assertIn("Hardware & Satellites", domain_names)

    def test_oversight_dashboard_formatting(self):
        """Validates markdown formatting of the executive oversight dashboard."""
        dash = master_oversight_engine.format_oversight_dashboard()
        self.assertIn("AI-BS Sovereign Parent Oversight Console", dash)
        self.assertIn("Business Operations", dash)
        self.assertIn("Hollywood & Creative", dash)
        self.assertIn("Hospitality OS", dash)

    def test_oversight_action_dispatch(self):
        """Validates action dispatcher for query_space and satellite mappings."""
        res_search = master_oversight_engine.execute_action("search_spaces", "Grand Rapids", {"limit": 2})
        self.assertEqual(res_search["status"], "success")

        res_sat = master_oversight_engine.execute_action("launch_satellite", "broadcast_studio")
        self.assertEqual(res_sat["status"], "success")
        self.assertIn("BroadcastStudioApp", res_sat["path"])


if __name__ == "__main__":
    unittest.main()
