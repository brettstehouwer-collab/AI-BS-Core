import os
import sys
import time
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from commercial_gateway.api_key_manager import USAGE_DB_PATH
from commercial_gateway.security_shield import (
    AUDIT_DB_PATH,
    ban_ip,
    load_banned_ips,
    SecurityShield,
    COMMERCIAL_DIR,
)

logger = logging.getLogger("AdminTelemetryRouter")
logger.setLevel(logging.INFO)

admin_telemetry_router = APIRouter(
    prefix="/api/admin", tags=["Admin Security Telemetry"]
)

AUTHORIZED_ADMIN_EMAILS = {
    "footballstar0325@gmail.com",
    "footballsyat0325@gmail.com",
    "brettstehouwer@gmail.com",
    "stehouwer@gmail.com",
    "theseandaley@gmail.com",
    "rottierannajoy@gmail.com",
    "keith@evolution6media.com",
}


def verify_admin_access(
    request: Request, x_admin_email: Optional[str] = Header(None)
) -> str:
    """Verify inbound header against authorized admin email whitelist."""
    if (
        not x_admin_email
        or x_admin_email.strip().lower() not in AUTHORIZED_ADMIN_EMAILS
    ):
        ip = SecurityShield.extract_client_ip(request)
        logger.warning(
            f"Unauthorized admin telemetry attempt from IP: {ip}, Email: '{x_admin_email}'"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "access_restricted",
                    "message": "Access prohibited. Authorized admin credentials required.",
                }
            },
        )
    return x_admin_email.strip().lower()


@admin_telemetry_router.get("/security-telemetry")
async def get_security_telemetry(
    request: Request, x_admin_email: Optional[str] = Header(None)
):
    """Fetch live security audit events, active IP bans, and usage metrics for admin view."""
    verify_admin_access(request, x_admin_email)

    # 1. Fetch Security Audit Events
    events = []
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, ip_address, event_type, severity, details FROM security_events ORDER BY id DESC LIMIT 50"
        )
        rows = cursor.fetchall()
        for r in rows:
            events.append(
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "ip_address": r[2],
                    "event_type": r[3],
                    "severity": r[4],
                    "details": r[5],
                }
            )

        cursor.execute(
            "SELECT ip_address, banned_at, reason FROM ip_blacklist ORDER BY banned_at DESC LIMIT 50"
        )
        bans = [
            {"ip_address": r[0], "banned_at": r[1], "reason": r[2]}
            for r in cursor.fetchall()
        ]
        conn.close()
    except Exception as e:
        logger.error(f"Failed to query audit db: {e}")
        events = []
        bans = []

    # 2. Fetch Commercial Gateway Live Request Stream
    live_stream = []
    try:
        conn = sqlite3.connect(USAGE_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, key_hash, ip_address, endpoint, status_code, response_time_ms, units_consumed FROM usage_logs ORDER BY id DESC LIMIT 50"
        )
        rows = cursor.fetchall()
        for r in rows:
            live_stream.append(
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "key_prefix": r[2][:8] + "...",
                    "ip_address": r[3],
                    "endpoint": r[4],
                    "status_code": r[5],
                    "response_time_ms": r[6],
                    "units_consumed": r[7],
                }
            )
        conn.close()
    except Exception as e:
        logger.error(f"Failed to query usage logs db: {e}")
        live_stream = []

    return {
        "status": "success",
        "timestamp": time.time(),
        "total_security_events": len(events),
        "total_banned_ips": len(bans),
        "security_events": events,
        "active_ip_bans": bans,
        "live_stream": live_stream,
    }


@admin_telemetry_router.post("/ip-ban")
async def manual_ip_ban(
    payload: Dict[str, str],
    request: Request,
    x_admin_email: Optional[str] = Header(None),
):
    """Allow admins to manually ban an IP address."""
    verify_admin_access(request, x_admin_email)
    target_ip = payload.get("ip_address")
    reason = payload.get("reason", "Manual Admin Ban")

    if not target_ip:
        raise HTTPException(status_code=400, detail="Missing ip_address")

    ban_ip(target_ip, reason)
    load_banned_ips()
    return {"status": "success", "message": f"IP {target_ip} has been banned."}


@admin_telemetry_router.post("/tester-passkey/create")
async def create_tester_passkey_endpoint(
    payload: Dict[str, Any],
    request: Request,
    x_admin_email: Optional[str] = Header(None),
):
    """Allow admins to generate a new Authorized Tester Passkey and secret header rules."""
    verify_admin_access(request, x_admin_email)
    tester_email = payload.get("tester_email")
    allowed_ips = payload.get("allowed_ips", ["127.0.0.1"])
    duration_days = int(payload.get("duration_days", 30))

    if not tester_email:
        raise HTTPException(status_code=400, detail="Missing tester_email")

    from commercial_gateway.create_tester_passkey import generate_tester_passkey

    result = generate_tester_passkey(
        tester_email, allowed_ips=allowed_ips, duration_days=duration_days
    )
    return {
        "status": "success",
        "message": "Tester Passkey generated successfully",
        "tester_profile": result,
    }


@admin_telemetry_router.get("/scope-manifest")
async def get_scope_manifest(request: Request):
    """Publicly expose authorized testing scope manifest for auditors."""
    manifest_path = os.path.join(COMMERCIAL_DIR, "SCOPE_MANIFEST.json")
    if os.path.exists(manifest_path):
        import json

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e)}
    return {"status": "Manifest missing"}
