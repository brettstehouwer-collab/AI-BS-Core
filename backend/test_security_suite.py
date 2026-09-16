#!/usr/bin/env python3
"""
Comprehensive 5-Tier Security Suite Automated Test (v5.129.0)
Tests OWASP Headers, CORS Whitelisting, In-Memory Rate Limiting,
SQLite Backups, X-Admin-Key Guard, and Anti-Tamper Watchdog.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from AI_BS_Backend import app
from scripts.backup_databases import run_database_backups
from aibs_security_watchdog import FileIntegrityWatchdog

class TestSecurityHardeningSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_1_owasp_security_headers(self):
        """Tier 1: Verify OWASP defensive HTTP security headers are injected."""
        resp = self.client.get("/api/security/health")
        self.assertEqual(resp.status_code, 200)
        headers = resp.headers
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers.get("x-frame-options"), "SAMEORIGIN")
        self.assertEqual(headers.get("referrer-policy"), "strict-origin-when-cross-origin")
        self.assertEqual(headers.get("x-xss-protection"), "1; mode=block")
        self.assertIn("geolocation=()", headers.get("permissions-policy", ""))
        print("\n[TEST PASS] Tier 1: OWASP defensive security headers verified.")

    def test_2_security_health_telemetry(self):
        """Tier 1: Verify /api/security/health endpoint status."""
        resp = self.client.get("/api/security/health")
        data = resp.json()
        self.assertEqual(data["status"], "SECURE")
        self.assertEqual(data["ecosystem_version"], "5.129.0")
        print("[TEST PASS] Tier 1: Security health endpoint operational.")

    def test_3_rate_limiter_throttling(self):
        """Tier 2: Verify in-memory sliding-window rate limiter throttles excessive bursts."""
        from security.rate_limiter import InMemoryRateLimiter
        test_limiter = InMemoryRateLimiter(default_limit=5, burst_limit=3, window_seconds=10)
        
        # Non-whitelisted simulated external IP
        ext_ip = "198.51.100.42"
        for i in range(3):
            is_limited, _ = test_limiter.is_rate_limited(ext_ip, is_burst_route=True)
            self.assertFalse(is_limited, f"Request {i+1} should be allowed")
            
        # 4th request must be rate-limited
        is_limited, retry_after = test_limiter.is_rate_limited(ext_ip, is_burst_route=True)
        self.assertTrue(is_limited, "4th burst request should be rate-limited")
        self.assertGreater(retry_after, 0)
        print("[TEST PASS] Tier 2: In-memory sliding-window rate limiter triggered on excessive burst.")

    def test_4_sqlite_database_backups(self):
        """Tier 3: Verify automated online database backup & SHA-256 manifest."""
        summary = run_database_backups(retention_days=7)
        self.assertEqual(summary["status"], "success")
        self.assertGreaterEqual(summary["total_databases_backed_up"], 1)
        self.assertTrue(os.path.exists(summary["manifest_path"]))
        print(f"[TEST PASS] Tier 3: SQLite online backup created at {summary['backup_directory']} ({summary['total_databases_backed_up']} DBs verified).")

    def test_5_admin_key_protection(self):
        """Tier 4: Verify X-Admin-Key authorization dependency."""
        from security.auth_guard import DEFAULT_ADMIN_KEY
        
        # Test valid key
        resp_valid = self.client.post("/api/security/backups/run", headers={"X-Admin-Key": DEFAULT_ADMIN_KEY})
        self.assertEqual(resp_valid.status_code, 200)
        
        print("[TEST PASS] Tier 4: Cryptographic X-Admin-Key authorization verified.")

    def test_6_anti_tamper_watchdog(self):
        """Tier 5: Verify anti-tamper file integrity watchdog SHA-256 hash checks."""
        watchdog = FileIntegrityWatchdog()
        self.assertGreater(len(watchdog.baselines), 0)
        alerts = watchdog.run_check()
        self.assertEqual(len(alerts), 0, "No alerts expected on unmodified baseline")
        print(f"[TEST PASS] Tier 5: Anti-tamper file integrity watchdog verified {len(watchdog.baselines)} core files.")

if __name__ == "__main__":
    unittest.main()
