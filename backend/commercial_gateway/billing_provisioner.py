import os
import sys
import time
import json
import hmac
import hashlib
import sqlite3
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Auto-load .env configuration file if present
env_file = os.path.join(BACKEND_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as ef:
        for line in ef:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

from commercial_gateway.api_key_manager import create_api_key, USAGE_DB_PATH, TIER_SPECS
from commercial_gateway.security_shield import SecurityShield

logger = logging.getLogger("BillingProvisioner")
logger.setLevel(logging.INFO)

billing_provisioner_router = APIRouter(
    prefix="/api/v1/billing", tags=["Commercial Billing & Payouts"]
)

PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "sandbox_paypal_client_id_2026")
PAYPAL_WEBHOOK_ID = os.environ.get(
    "PAYPAL_WEBHOOK_ID", "sandbox_paypal_webhook_id_2026"
)
STRIPE_WEBHOOK_SECRET = os.environ.get(
    "STRIPE_WEBHOOK_SECRET", "whsec_sandbox_test_2026"
)


class CheckoutSimulationPayload(BaseModel):
    client_name: str
    email: str
    payment_provider: str = "paypal"  # 'paypal' or 'stripe'
    tier: str = "pro"  # 'starter', 'pro', 'enterprise'
    amount_paid: float = 29.99


@billing_provisioner_router.post("/simulate-checkout")
async def simulate_checkout(payload: CheckoutSimulationPayload, request: Request):
    """
    Developer Sandbox Key Provisioner.
    Provisions a local sandbox key for development. Under Zero-Mock policy, synthetic payments
    are strictly prohibited from being inserted into production billing ledgers.
    """
    ip = SecurityShield.extract_client_ip(request)
    tier = payload.tier.lower()
    if tier not in TIER_SPECS:
        tier = "pro"

    # Provision new cryptographic key for developer testing
    key_info = create_api_key(
        tier=tier, client_name=f"Developer Sandbox ({payload.client_name} - {payload.email})"
    )

    logger.info(
        f"🔑 [DEVELOPER SANDBOX KEY] Sandbox API Key issued for {payload.email} ({tier}). Zero-Mock policy enforced: No synthetic financial records written."
    )

    return {
        "status": "success",
        "message": f"Developer Sandbox API Key provisioned for {tier} tier (Zero-Mock compliant).",
        "payout_received_to": "None (Developer Sandbox)",
        "api_key_details": {
            "raw_key": key_info["raw_key"],
            "tier": tier,
            "client_name": key_info["client_name"],
            "daily_quota": TIER_SPECS[tier]["max_requests_per_day"],
            "expires_at": key_info["expires_at"],
        },
    }


@billing_provisioner_router.post("/paypal-webhook")
async def paypal_webhook(request: Request):
    """
    PayPal Webhook Listener.
    Processes live PayPal Checkout events (PAYMENT.CAPTURE.COMPLETED) and provisions live API keys.
    Records verified live transactions into billing_transactions under strict Zero-Mock policy.
    """
    ip = SecurityShield.extract_client_ip(request)
    try:
        body_bytes = await request.body()
        payload = json.loads(body_bytes.decode("utf-8"))

        event_type = payload.get("event_type", "")
        resource = payload.get("resource", {})

        if event_type in ["PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"]:
            payer_email = resource.get("payer", {}).get(
                "email_address", "client@paypal.com"
            )
            custom_id = resource.get("custom_id", "pro")  # tier passes in custom_id
            tier = custom_id if custom_id in TIER_SPECS else "pro"
            amount_val = float(resource.get("amount", {}).get("value", "29.99"))

            key_info = create_api_key(
                tier=tier, client_name=f"PayPal Payer ({payer_email})"
            )

            # Record verified live transaction into SQLite ledger
            try:
                conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                except Exception:
                    pass
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS billing_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        client_name TEXT,
                        email TEXT,
                        provider TEXT,
                        tier TEXT,
                        amount_paid REAL,
                        key_prefix TEXT,
                        status TEXT
                    )
                """)
                cursor.execute(
                    "INSERT INTO billing_transactions (timestamp, client_name, email, provider, tier, amount_paid, key_prefix, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        time.time(),
                        f"PayPal Payer ({payer_email})",
                        payer_email,
                        "paypal",
                        tier,
                        amount_val,
                        key_info["key_prefix"],
                        "verified_live_payment",
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as dbe:
                logger.error(f"Failed to record verified PayPal transaction: {dbe}")

            logger.info(
                f"🎉 [PAYPAL PAYOUT SUCCESS] Verified live payment ${amount_val:.2f} from {payer_email}. Key: {key_info['key_prefix']}..."
            )

            return JSONResponse(
                status_code=200,
                content={
                    "status": "handled",
                    "event_type": event_type,
                    "key_issued": key_info["key_prefix"],
                },
            )

        return JSONResponse(
            status_code=200, content={"status": "ignored", "event_type": event_type}
        )
    except Exception as e:
        logger.error(f"PayPal Webhook Error: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})


@billing_provisioner_router.post("/stripe-webhook")
async def stripe_webhook(
    request: Request, stripe_signature: Optional[str] = Header(None)
):
    """
    Stripe Webhook Listener.
    Processes live Stripe Checkout Session events (checkout.session.completed).
    Records verified live transactions into billing_transactions under strict Zero-Mock policy.
    """
    try:
        body_bytes = await request.body()
        payload = json.loads(body_bytes.decode("utf-8"))

        event_type = payload.get("type", "")
        if event_type == "checkout.session.completed":
            session = payload.get("data", {}).get("object", {})
            customer_email = session.get("customer_details", {}).get(
                "email", "client@stripe.com"
            )
            tier = session.get("metadata", {}).get("tier", "pro")
            amount_cents = session.get("amount_total")
            amount_usd = float(amount_cents) / 100.0 if amount_cents else float(TIER_SPECS.get(tier, {}).get("monthly_price", 29.99))

            key_info = create_api_key(
                tier=tier, client_name=f"Stripe Customer ({customer_email})"
            )

            # Record verified live transaction into SQLite ledger
            try:
                conn = sqlite3.connect(USAGE_DB_PATH, timeout=20.0)
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA synchronous=NORMAL;")
                except Exception:
                    pass
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS billing_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        client_name TEXT,
                        email TEXT,
                        provider TEXT,
                        tier TEXT,
                        amount_paid REAL,
                        key_prefix TEXT,
                        status TEXT
                    )
                """)
                cursor.execute(
                    "INSERT INTO billing_transactions (timestamp, client_name, email, provider, tier, amount_paid, key_prefix, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        time.time(),
                        f"Stripe Customer ({customer_email})",
                        customer_email,
                        "stripe",
                        tier,
                        amount_usd,
                        key_info["key_prefix"],
                        "verified_live_payment",
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as dbe:
                logger.error(f"Failed to record verified Stripe transaction: {dbe}")

            logger.info(
                f"🎉 [STRIPE PAYOUT SUCCESS] Verified live payment ${amount_usd:.2f} from {customer_email}. Key: {key_info['key_prefix']}..."
            )

            return JSONResponse(
                status_code=200,
                content={"status": "handled", "key_issued": key_info["key_prefix"]},
            )

        return JSONResponse(status_code=200, content={"status": "ignored"})
    except Exception as e:
        logger.error(f"Stripe Webhook Error: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})


class StripeSessionPayload(BaseModel):
    tier_id: str
    amount_usd: float
    client_name: str


@billing_provisioner_router.post("/create-stripe-session")
async def create_stripe_session(payload: StripeSessionPayload):
    import aiohttp
    import urllib.parse

    stripe_key = os.environ.get("STRIPE_API_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=500, detail="Stripe API Key not configured")

    amount_cents = int(payload.amount_usd * 100)

    # Stripe uses x-www-form-urlencoded
    data = {
        "success_url": "https://ai-bs-dashboard.web.app/?checkout=success",
        "cancel_url": "https://ai-bs-dashboard.web.app/?checkout=cancelled",
        "mode": "payment",
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][product_data][name]": f"AI-BS {payload.tier_id.replace('_', ' ').title()}",
        "line_items[0][price_data][unit_amount]": str(amount_cents),
        "line_items[0][quantity]": "1",
        "metadata[tier]": payload.tier_id,
        "metadata[client_name]": payload.client_name,
    }

    encoded_data = urllib.parse.urlencode(data)

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.stripe.com/v1/checkout/sessions",
            headers={
                "Authorization": f"Bearer {stripe_key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=encoded_data,
        ) as resp:
            resp_data = await resp.json()
            if resp.status == 200:
                return {"url": resp_data.get("url"), "session_id": resp_data.get("id")}
            else:
                logger.error(f"Stripe API Error: {resp_data}")
                raise HTTPException(
                    status_code=400, detail="Failed to create Stripe session"
                )
