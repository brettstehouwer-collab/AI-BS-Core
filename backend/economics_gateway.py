"""Read-only availability contract; no inspected source establishes reconciled finances.

Manual entries, unsigned billing events and draft invoices are not verified
revenue. Source adapters must establish ownership, currency, settlement, fees
and coverage before replacing these null values with canonical decimal strings.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from security.firebase_auth import get_admin_principal

router = APIRouter(prefix="/api/v1/economics", tags=["System Economics"])
NO_STORE = {"Cache-Control": "private, no-store"}


async def require_economics_owner(request: Request) -> str:
    key = request.headers.get("x-admin-key", "") or request.headers.get("x-api-key", "")
    owner = await asyncio.to_thread(
        get_admin_principal, key, request.headers.get("authorization", "")
    )
    if owner is None:
        raise HTTPException(403, "Authenticated administrator required", headers=NO_STORE)
    return owner


# Availability descriptors, not imported accounting records.
METRICS = {
    "revenue.monthly_recurring_revenue": "USD",
    "revenue.active_subscriptions": "count",
    "revenue.recent_invoices_paid": "count",
    "revenue.total_volume_30d": "USD",
    "llm_costs.openai_gpt4_cost": "USD",
    "llm_costs.anthropic_claude_cost": "USD",
    "llm_costs.local_ollama_vram_kwh": "kWh",
    "llm_costs.total_compute_30d": "USD",
    "security_telemetry.total_api_requests_30d": "count",
    "security_telemetry.unauthorized_access_attempts": "count",
    "security_telemetry.rate_limit_hits": "count",
    "security_telemetry.avg_latency_ms": "ms",
    "margins.net_profit_30d": "USD",
    "margins.profit_margin_pct": "percent",
}
REASONS = {
    "revenue": ("NO_RECONCILED_REVENUE_SOURCE", "Revenue records have not been verified and reconciled for this reporting window."),
    "llm_costs": ("NO_RECONCILED_COST_SOURCE", "Provider costs and local energy use have not been verified for this reporting window."),
    "security_telemetry": ("NO_VERIFIED_TELEMETRY_SOURCE", "No verified telemetry source establishes coverage for this reporting window."),
    "margins": ("DEPENDENCIES_UNAVAILABLE", "Verified revenue and costs are required before profit or margin can be reported."),
}


@router.get("/summary")
async def get_economics_summary(_owner: str = Depends(require_economics_owner)):
    end = datetime.now(timezone.utc)
    metrics = {}
    for name, unit in METRICS.items():
        code, reason = REASONS[name.split(".")[0]]
        metrics[name] = {
            "value": None, "unit": unit, "status": "unavailable",
            "verification": "not_verified", "source": None,
            "observed_at": None, "fresh_until": None,
            "reason_code": code, "reason": reason,
        }
    return JSONResponse({
        "schema": "aibs.economics.summary.v1", "status": "unavailable",
        "currency": "USD", "timestamp": end.isoformat(),
        "window": {
            "start": (end - timedelta(days=30)).isoformat(), "end": end.isoformat(),
            "coverage": "unconfirmed",
        },
        "metrics": metrics,
    }, headers=NO_STORE)
