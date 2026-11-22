"""
AI-BS CDZ Audit Ledger & Poller Test Suite
Validates SQLite schema, SHA-256 chain verification, idempotent ingestion,
active watcher polling, and FastAPI router endpoints.
"""

import sys
import unittest
sys.path.insert(0, r"C:\AI-BSackend")

from fastapi import FastAPI
from starlette.testclient import TestClient
from database.cdz_audit_db import ingest_ledger_file, get_cdz_summary, get_cdz_blocks, DB_PATH
from modules.audit_ledger_watcher import cdz_watcher
from routers.audit_ledger_router import router as audit_ledger_router


class TestCDZAuditLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger_file = r"C:\AI-BS\penitscradle_audit_ledger_1789023393998.json"
        cls.app = FastAPI()
        cls.app.include_router(audit_ledger_router)
        cls.client = TestClient(cls.app)

    def test_01_ingest_and_verify(self):
        new_b, total_b, valid = ingest_ledger_file(self.ledger_file)
        self.assertTrue(valid)
        self.assertGreaterEqual(total_b, 15)
        print(f"[PASS] Ingested ledger: total_blocks={total_b}, valid={valid}")

    def test_02_idempotency(self):
        new_b, total_b, valid = ingest_ledger_file(self.ledger_file)
        self.assertEqual(new_b, 0, "Repeated ingestion should insert 0 duplicates")
        self.assertGreaterEqual(total_b, 15)
        print(f"[PASS] Idempotency verified: new_blocks={new_b}, total={total_b}")

    def test_03_summary_kpis(self):
        summary = get_cdz_summary()
        self.assertEqual(summary["status"], "success")
        self.assertTrue(summary["is_valid"])
        self.assertEqual(summary["head_hash"], "d674929ea53399a3")
        self.assertEqual(summary["genesis_hash"], "0000000000000000")
        self.assertIn("TACTICAL", summary["domain_breakdown"])
        self.assertIn("ADULT", summary["domain_breakdown"])
        print(f"[PASS] Summary KPIs verified: head_hash={summary['head_hash']}, domains={summary['domain_breakdown']}")

    def test_04_blocks_filtering(self):
        all_blocks = get_cdz_blocks(domain="ALL", limit=50)
        self.assertGreaterEqual(all_blocks["total"], 15)

        tactical = get_cdz_blocks(domain="TACTICAL", limit=50)
        self.assertEqual(tactical["total"], 11)

        adult = get_cdz_blocks(domain="ADULT", limit=50)
        self.assertEqual(adult["total"], 4)

        purges = get_cdz_blocks(event="domain_purge", limit=50)
        self.assertEqual(purges["total"], 4)

        print(f"[PASS] Filtering verified: Tactical={tactical['total']}, Adult={adult['total']}, Purges={purges['total']}")

    def test_05_watcher_scan(self):
        scan_res = cdz_watcher.scan_now()
        self.assertEqual(scan_res["status"], "success")
        self.assertGreaterEqual(scan_res["scanned_files_count"], 1)
        status = cdz_watcher.get_status()
        self.assertIn("watch_dirs", status)
        print(f"[PASS] Watcher scan verified: files_scanned={scan_res['scanned_files_count']}")

    def test_06_fastapi_endpoints(self):
        # GET /summary
        r = self.client.get("/api/audit-ledger/summary", headers={"x-client-id": "stehouwer_publishing"})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["total_blocks"], 15)
        self.assertEqual(d["head_hash"], "d674929ea53399a3")

        # GET /blocks
        r = self.client.get("/api/audit-ledger/blocks?domain=TACTICAL&limit=5")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(len(d["blocks"]), 5)

        # POST /scan
        r = self.client.post("/api/audit-ledger/scan")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["status"], "success")
        print("[PASS] All FastAPI audit ledger endpoints returned HTTP 200")


if __name__ == "__main__":
    unittest.main()
