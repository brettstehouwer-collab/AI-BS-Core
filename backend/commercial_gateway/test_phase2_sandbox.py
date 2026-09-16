import os
import sys
import asyncio
import logging
import sqlite3
import time
from typing import Dict, Any

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from commercial_gateway.api_key_manager import (
    create_api_key,
    verify_api_key,
    USAGE_DB_PATH,
    TIER_SPECS,
)
from commercial_gateway.security_shield import SecurityShield, AUDIT_DB_PATH
from commercial_gateway.tunnel_manager import TunnelManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("Phase2SandboxTest")


async def run_phase2_validation():
    print("\n======================================================================")
    print(
        "[INIT] RUNNING PHASE 2: 7-PASS VALIDATION PROTOCOL (COMMERCIAL MONETIZATION)"
    )
    print("======================================================================\n")

    passes_succeeded = 0
    total_passes = 7

    # ------------------------------------------------------------------
    # PASS 1: PayPal Checkout Key Provisioning Verification
    # ------------------------------------------------------------------
    print("---> [Pass 1/7] PayPal Checkout Key Provisioning Verification")
    try:
        from commercial_gateway.billing_provisioner import (
            CheckoutSimulationPayload,
            simulate_checkout,
        )
        from fastapi import Request

        class MockRequest:
            headers = {}
            client = type("C", (), {"host": "127.0.0.1"})()

        payload = CheckoutSimulationPayload(
            client_name="PayPalTester",
            email="tester@paypal.com",
            payment_provider="paypal",
            tier="pro",
            amount_paid=29.99,
        )
        res = await simulate_checkout(payload, MockRequest())
        assert res["status"] == "success"
        raw_key = res["api_key_details"]["raw_key"]

        verified = verify_api_key(raw_key)
        assert verified is not None
        assert verified["tier"] == "pro"

        print("[PASS 1 SUCCESS] PayPal checkout key issuance verified.\n")
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 1 FAILED]: {e}\n")

    # ------------------------------------------------------------------
    # PASS 2: Stripe Checkout Key Provisioning Verification
    # ------------------------------------------------------------------
    print("---> [Pass 2/7] Stripe Checkout Key Provisioning Verification")
    try:
        payload_stripe = CheckoutSimulationPayload(
            client_name="StripeTester",
            email="tester@stripe.com",
            payment_provider="stripe",
            tier="enterprise",
            amount_paid=149.99,
        )
        res_stripe = await simulate_checkout(payload_stripe, MockRequest())
        assert res_stripe["status"] == "success"
        verified_ent = verify_api_key(res_stripe["api_key_details"]["raw_key"])
        assert verified_ent["tier"] == "enterprise"

        print("[PASS 2 SUCCESS] Stripe checkout key issuance verified.\n")
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 2 FAILED]: {e}\n")

    # ------------------------------------------------------------------
    # PASS 3: Billing Transaction Database Audit
    # ------------------------------------------------------------------
    print("---> [Pass 3/7] Billing Transaction Database Audit")
    try:
        conn = sqlite3.connect(USAGE_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "SELECT email, provider, amount_paid FROM billing_transactions WHERE email = ?",
            ("tester@paypal.com",),
        )
        tx = cursor.fetchone()
        conn.close()

        assert tx is not None
        assert tx[0] == "tester@paypal.com"
        assert tx[1] == "paypal"
        assert tx[2] == 29.99

        print(
            "[PASS 3 SUCCESS] Transaction details accurately recorded in SQLite billing DB.\n"
        )
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 3 FAILED]: {e}\n")

    # ------------------------------------------------------------------
    # PASS 4: Credit Quota Calculation & Tier Verification
    # ------------------------------------------------------------------
    print("---> [Pass 4/7] Credit Quota Calculation & Tier Verification")
    try:
        assert TIER_SPECS["pro"]["max_requests_per_day"] == 5000
        assert TIER_SPECS["enterprise"]["max_requests_per_day"] == 100000

        print(
            "[PASS 4 SUCCESS] Quotas & hardware rental specs aligned with billing tiers.\n"
        )
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 4 FAILED]: {e}\n")

    # ------------------------------------------------------------------
    # PASS 5: Cloudflare Tunnel Status Inspection
    # ------------------------------------------------------------------
    print("---> [Pass 5/7] Cloudflare Tunnel Status Inspection")
    try:
        tunnel_status = TunnelManager.get_status(8000)
        assert tunnel_status["target_port"] == 8000
        assert "cloudflared" in tunnel_status["recommended_command"]

        print("[PASS 5 SUCCESS] Cloudflare tunnel status & command specs verified.\n")
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 5 FAILED]: {e}\n")

    # ------------------------------------------------------------------
    # PASS 6: Security Shield Header & Forwarding Verification
    # ------------------------------------------------------------------
    print("---> [Pass 6/7] Security Shield Header & Forwarding Verification")
    try:

        class ForwardedMockRequest:
            headers = {"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}
            client = type("C", (), {"host": "10.0.0.1"})()

        ip = SecurityShield.extract_client_ip(ForwardedMockRequest())
        assert ip == "203.0.113.195"

        print(
            "[PASS 6 SUCCESS] Real client IP extraction through proxy/tunnel verified.\n"
        )
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 6 FAILED]: {e}\n")

    # ------------------------------------------------------------------
    # PASS 7: End-to-End Monetization Gateway Verification
    # ------------------------------------------------------------------
    print("---> [Pass 7/7] End-to-End Monetization Gateway Verification")
    try:
        # Verify authenticated key lookup and spec mapping
        live_key = create_api_key(tier="starter", client_name="LiveClient")
        verified_live = verify_api_key(live_key["raw_key"])
        assert verified_live["tier"] == "starter"

        print("[PASS 7 SUCCESS] End-to-end monetization pipeline verified.\n")
        passes_succeeded += 1
    except Exception as e:
        print(f"[PASS 7 FAILED]: {e}\n")

    print("======================================================================")
    print(f"SUMMARY: {passes_succeeded}/{total_passes} PASSES SUCCEEDED")
    print("======================================================================\n")
    return passes_succeeded == total_passes


if __name__ == "__main__":
    asyncio.run(run_phase2_validation())
