"""
AI-BS Executive Command Cockpit Automated Test Suite (v5.298.0)
Validates:
1. Dispatcher schema validation across all 4 pillars + LLM reasoning.
2. Tiered Autonomy Governance Queue (Tier 1 instant, Tier 2 gate, Tier 3 approval).
3. Action approval resolution, rejection, and global emergency halt execution.
4. 4-Mirror SHA-256 byte parity for ExecutiveCockpitTab.jsx.
5. Executive Cockpit FastAPI Router endpoints (/matrix/status, /chat, /actions/pending, /settings/autonomy).
"""

import os
import sys
import json
import time
import hashlib
import unittest
import concurrent.futures
from pathlib import Path

# Add backend and root to sys.path
backend_path = r"C:\AI-BS\backend"
root_path = r"C:\AI-BS"
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from core.executive_action_dispatcher import executive_dispatcher, TOOL_MANIFEST, ExecutiveActionDispatcher
from routers.executive_cockpit_router import router, extract_tool_calls_from_llm_response
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestExecutiveCockpitSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatcher = executive_dispatcher
        cls.app = FastAPI()
        cls.app.include_router(router)
        cls.client = TestClient(cls.app)

    def test_01_dispatcher_schema_validation(self):
        """Verifies tool-manifest schemas, tiers, and parameter constraints for all pillars."""
        # 1. Verify all required pillars exist
        required_pillars = ["media_render", "broadcast_control", "crypto_order", "vault_query", "llm_reasoning"]
        for p in required_pillars:
            self.assertIn(p, TOOL_MANIFEST, f"Missing pillar: {p}")

        # 2. Verify tier designations
        self.assertEqual(TOOL_MANIFEST["vault_query"]["get_vault_stats"]["tier"], 1)
        self.assertEqual(TOOL_MANIFEST["vault_query"]["search_vault_sqlite"]["tier"], 1)
        self.assertEqual(TOOL_MANIFEST["broadcast_control"]["get_broadcast_state"]["tier"], 1)
        self.assertEqual(TOOL_MANIFEST["crypto_order"]["get_crypto_status"]["tier"], 1)

        self.assertEqual(TOOL_MANIFEST["media_render"]["cut_and_normalize"]["tier"], 2)
        self.assertEqual(TOOL_MANIFEST["media_render"]["reframe_vertical_9x16"]["tier"], 2)
        self.assertEqual(TOOL_MANIFEST["broadcast_control"]["switch_scene"]["tier"], 2)

        self.assertEqual(TOOL_MANIFEST["crypto_order"]["place_limit_order"]["tier"], 3)
        self.assertEqual(TOOL_MANIFEST["crypto_order"]["set_trailing_stop"]["tier"], 3)

        # 3. Test parameter validation
        # Valid call
        valid, err = self.dispatcher.validate_action(
            "crypto_order",
            "place_limit_order",
            {"symbol": "CRO/USD", "side": "BUY", "amount": 50.0, "price": 0.125}
        )
        self.assertTrue(valid)
        self.assertIsNone(err)

        # Missing required parameter ('price')
        valid, err = self.dispatcher.validate_action(
            "crypto_order",
            "place_limit_order",
            {"symbol": "CRO/USD", "side": "BUY", "amount": 50.0}
        )
        self.assertFalse(valid)
        self.assertIn("price", err)

        # Unknown pillar
        valid, err = self.dispatcher.validate_action("unknown_pillar", "action", {})
        self.assertFalse(valid)

    def test_02_tiered_governance_queue(self):
        """Asserts Tier 1 auto-executes, while Tier 2 in SAFE and Tier 3 crypto orders are held in pending queue."""
        # Set to SAFE mode
        self.dispatcher.set_autonomy_mode("SAFE")
        self.assertEqual(self.dispatcher.get_autonomy_mode(), "SAFE")

        # Tier 1: get_vault_stats should execute immediately
        t1_res = self.dispatcher.dispatch("vault_query", "get_vault_stats", {})
        self.assertEqual(t1_res.get("status"), "EXECUTED")
        self.assertFalse(t1_res.get("requires_approval"))
        self.assertIn("sqlite_vault_records", t1_res.get("result", {}))

        # Tier 2 in SAFE: cut_and_normalize should be queued
        t2_res = self.dispatcher.dispatch("media_render", "cut_and_normalize", {
            "video_path": r"C:\AI-BS\MP4 medial screen recordings\mtd.mp4",
            "start_sec": 0.0,
            "duration_sec": 10.0
        })
        self.assertEqual(t2_res.get("status"), "QUEUED")
        self.assertTrue(t2_res.get("requires_approval"))
        t2_id = t2_res.get("action_id")

        # Tier 3 in SAFE: place_limit_order should be queued
        t3_res = self.dispatcher.dispatch("crypto_order", "place_limit_order", {
            "symbol": "CRO/USD",
            "side": "BUY",
            "amount": 200.0,
            "price": 0.122
        })
        self.assertEqual(t3_res.get("status"), "QUEUED")
        self.assertTrue(t3_res.get("requires_approval"))
        t3_id = t3_res.get("action_id")

        # Verify both are present in pending queue
        pending = self.dispatcher.get_pending_actions()
        pending_ids = [p["action_id"] for p in pending]
        self.assertIn(t2_id, pending_ids)
        self.assertIn(t3_id, pending_ids)

        # Test SEMI_AUTO mode: Tier 2 auto-executes, Tier 3 remains queued
        self.dispatcher.set_autonomy_mode("SEMI_AUTO")
        t2_semi = self.dispatcher.dispatch("media_render", "reframe_vertical_9x16", {
            "video_path": r"C:\AI-BS\MP4 medial screen recordings\mtd.mp4"
        })
        self.assertEqual(t2_semi.get("status"), "EXECUTED")
        self.assertFalse(t2_semi.get("requires_approval"))

        t3_semi = self.dispatcher.dispatch("crypto_order", "set_trailing_stop", {
            "symbol": "CRO/USD",
            "stop_pct": 2.0
        })
        self.assertEqual(t3_semi.get("status"), "QUEUED")

        # Cleanup created actions
        self.dispatcher.resolve_action(t2_id, "REJECT")
        self.dispatcher.resolve_action(t3_id, "REJECT")
        self.dispatcher.resolve_action(t3_semi["action_id"], "REJECT")

    def test_03_action_approval_execution(self):
        """Tests approving a pending action and verifies audit logging in stehouwer_vault.db."""
        self.dispatcher.set_autonomy_mode("SAFE")

        # Queue a Tier 3 order
        t3_order = self.dispatcher.dispatch("crypto_order", "place_limit_order", {
            "symbol": "CRO/USD",
            "side": "BUY",
            "amount": 75.0,
            "price": 0.130
        })
        action_id = t3_order["action_id"]
        self.assertEqual(t3_order["status"], "QUEUED")

        # Approve the queued action
        appr_res = self.dispatcher.resolve_action(action_id, "APPROVE", operator_note="Approved in automated test")
        self.assertEqual(appr_res.get("status"), "APPROVED")
        self.assertEqual(appr_res.get("action_id"), action_id)
        self.assertIn("result", appr_res)

        # Assert removed from pending queue
        pending = self.dispatcher.get_pending_actions()
        self.assertNotIn(action_id, [p["action_id"] for p in pending])

        # Verify audit record in SQLite
        history = self.dispatcher.get_action_history(limit=10)
        found = [h for h in history if h["action_id"] == action_id]
        self.assertTrue(len(found) == 1)
        self.assertEqual(found[0]["status"], "APPROVED")
        self.assertIsNotNone(found[0]["resolved_at"])

        # Test Reject path
        t3_reject = self.dispatcher.dispatch("crypto_order", "place_limit_order", {
            "symbol": "CRO/USD",
            "side": "SELL",
            "amount": 50.0,
            "price": 0.145
        })
        rej_id = t3_reject["action_id"]
        rej_res = self.dispatcher.resolve_action(rej_id, "REJECT")
        self.assertEqual(rej_res.get("status"), "REJECTED")

        # Test Emergency Halt
        # Stage 2 actions
        self.dispatcher.dispatch("crypto_order", "place_limit_order", {"symbol": "CRO/USD", "side": "BUY", "amount": 10.0, "price": 0.12})
        self.dispatcher.dispatch("media_render", "cut_and_normalize", {"video_path": "test.mp4"})
        self.assertGreaterEqual(len(self.dispatcher.get_pending_actions()), 2)

        halt_res = self.dispatcher.emergency_halt()
        self.assertEqual(halt_res.get("status"), "HALTED")
        self.assertEqual(halt_res.get("autonomy_mode"), "SAFE")
        self.assertEqual(len(self.dispatcher.get_pending_actions()), 0)

    def test_04_four_mirror_parity_executive_cockpit(self):
        """Tests SHA-256 byte parity across all 4 frontend locations for ExecutiveCockpitTab.jsx."""
        mirrors = [
            r"C:\AI-BS\frontend\src\components\ExecutiveCockpitTab.jsx",
            r"C:\AI-BS\frontend\components\ExecutiveCockpitTab.jsx",
            r"C:\AI-BS\frontend\src\components\components\ExecutiveCockpitTab.jsx",
            r"C:\AI-BS\frontend\components\components\ExecutiveCockpitTab.jsx"
        ]

        def get_sha256(path_str):
            h = hashlib.sha256()
            with open(path_str, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        hashes = []
        for m in mirrors:
            self.assertTrue(os.path.exists(m), f"Mirror path missing: {m}")
            hashes.append(get_sha256(m))

        self.assertEqual(len(set(hashes)), 1, f"Hash mismatch detected across mirrors: {hashes}")

    def test_05_executive_router_endpoints(self):
        """Tests all REST endpoints on the executive router."""
        # 1. /matrix/status
        res = self.client.get("/api/v1/executive/matrix/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("pillars", data)
        self.assertIn("hardware", data)
        self.assertIn("vault", data)
        self.assertGreaterEqual(data["vault"].get("sqlite_vault_records", 0), 300000)

        # 2. /chat endpoint
        chat_res = self.client.post("/api/v1/executive/chat", json={
            "prompt": "Audit system health and check crypto daemon status"
        })
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        self.assertIn("response", chat_data)
        self.assertIn("tool_calls", chat_data)

        # 3. /settings/autonomy
        set_res = self.client.post("/api/v1/executive/settings/autonomy", json={"mode": "SEMI_AUTO"})
        self.assertEqual(set_res.status_code, 200)
        self.assertEqual(set_res.json().get("autonomy_mode"), "SEMI_AUTO")

        get_res = self.client.get("/api/v1/executive/settings/autonomy")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json().get("autonomy_mode"), "SEMI_AUTO")

        # Reset to SAFE
        self.client.post("/api/v1/executive/settings/autonomy", json={"mode": "SAFE"})

    def test_06_concurrency_and_idempotent_resolution(self):
        """Tests that concurrent approval calls for the same action execute only once and remain idempotent."""
        self.dispatcher.set_autonomy_mode("SAFE")
        # Ensure trading is not paused
        self.dispatcher._trading_paused = False

        # Stage an action
        staged = self.dispatcher.dispatch("media_render", "cut_and_normalize", {
            "video_path": "concurrent_test.mp4",
            "start_sec": 0.0,
            "duration_sec": 5.0
        })
        action_id = staged["action_id"]
        self.assertEqual(staged["status"], "QUEUED")

        # Spawn 5 concurrent threads trying to approve the action simultaneously
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self.dispatcher.resolve_action, action_id, "APPROVE", f"Worker {i}")
                for i in range(5)
            ]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        # Assert all 5 got a valid response without unhandled exceptions
        self.assertEqual(len(results), 5)
        # Exactly one should have executed or approved first, others return status APPROVED or RESOLVING
        statuses = [r.get("status") for r in results]
        self.assertTrue(all(s in ("APPROVED", "RESOLVING") for s in statuses))

        # Check final SQLite state
        history = self.dispatcher.get_action_history(limit=5)
        matched = [h for h in history if h["action_id"] == action_id]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["status"], "APPROVED")

    def test_07_emergency_halt_crypto_guard(self):
        """Tests that emergency_halt actively pauses trading bots and blocks subsequent order placement."""
        # Reset mode to SAFE
        self.dispatcher.set_autonomy_mode("SAFE")

        # Trigger Emergency Halt
        halt_res = self.dispatcher.emergency_halt()
        self.assertEqual(halt_res.get("status"), "HALTED")
        self.assertTrue(halt_res.get("trading_paused"))
        self.assertIn("crypto_halt", halt_res)
        self.assertTrue(halt_res["crypto_halt"].get("trading_paused"))

        # Verify get_crypto_status reports paused
        crypto_status = self.dispatcher._exec_crypto_order("get_crypto_status", {})
        self.assertTrue(crypto_status.get("trading_paused"))

        # Attempt to dispatch or execute a limit order while paused - must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            self.dispatcher._exec_crypto_order("place_limit_order", {
                "symbol": "CRO/USD",
                "side": "BUY",
                "amount": 100.0,
                "price": 0.12
            })
        self.assertIn("HALTED", str(ctx.exception))

        # Test resume_trading
        resume_res = self.dispatcher._exec_crypto_order("resume_trading", {})
        self.assertEqual(resume_res.get("status"), "success")
        self.assertFalse(resume_res.get("trading_paused"))

    def test_08_chat_edge_cases_and_llm_tool_extraction(self):
        """Tests zero-division protection in chat and tool extraction from LLM JSON responses."""
        # 1. Zero price in chat prompt must not raise ZeroDivisionError
        res = self.client.post("/api/v1/executive/chat", json={
            "prompt": "Stage a $50 CRO limit buy order at 0"
        })
        self.assertEqual(res.status_code, 200)

        # 2. Pause trading intent in chat
        pause_chat = self.client.post("/api/v1/executive/chat", json={
            "prompt": "Pause trading immediately"
        })
        self.assertEqual(pause_chat.status_code, 200)
        tool_names = [tc.get("action_name") or tc.get("action") for tc in pause_chat.json().get("tool_calls", [])]
        self.assertIn("emergency_pause_trading", tool_names)

        # 3. LLM tool extraction from markdown JSON block
        llm_response_text = (
            "Based on strategic assessment, I am dispatching a vault search query.\n\n"
            "```json\n"
            "{\n"
            '  "pillar": "vault_query",\n'
            '  "action": "search_vault_sqlite",\n'
            '  "parameters": {"query": "genomics", "limit": 3}\n'
            "}\n"
            "```\n"
            "Awaiting results."
        )
        extracted = extract_tool_calls_from_llm_response(llm_response_text)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["pillar"], "vault_query")
        self.assertEqual(extracted[0]["action"], "search_vault_sqlite")
        self.assertEqual(extracted[0]["parameters"]["query"], "genomics")

        # Cleanup: resume trading
        self.dispatcher._exec_crypto_order("resume_trading", {})


if __name__ == "__main__":
    unittest.main()
