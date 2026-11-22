"""Held legacy GPU network paths; no provider, credential or financial store access.

Unowned historic credits and caller budgets are not payment/compute evidence.
The original implementation is retained in the scoped hardening checkpoint.
"""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from security.financial_auth import require_financial_owner

NETWORK_HOLD_REASON = "Verified owned compute receipts and treasury records are unavailable."
NETWORK_DISPATCH_HOLD = "Network payouts, registration and code dispatch are held pending verified ownership and reconciliation."
PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization, X-Admin-Key, X-Api-Key"}

gpu_network_router = APIRouter(
    prefix="/v1/network", tags=["GPU Compute Network API"],
    dependencies=[Depends(require_financial_owner)],
)

# Compatibility containers only. No route admits, reads or consumes their data.
NODES_REGISTRY: Dict[str, Dict[str, Any]] = {}
JOB_QUEUE: List[Dict[str, Any]] = []
EARNINGS_LEDGER: Dict[str, Dict[str, Any]] = {}


def network_unavailable():
    return {
        "schema_version": 1, "status": "unavailable", "reason": NETWORK_HOLD_REASON,
        "payouts_enabled": False, "job_dispatch_enabled": False,
        "registration_enabled": False,
        "ledger": {"total_earned_usd": None, "pending_usd": None,
                   "redeemed_usd": None, "total_compute_hours": None},
        "hardware": None, "treasury": None,
        "idle_policy": {"status": "unavailable", "enforced": False},
    }


def require_verified_network_execution():
    """No credentials, feature flags or caller budgets release this hold."""
    raise RuntimeError(NETWORK_DISPATCH_HOLD)


def load_real_compute_ledger():
    """Retired unowned/synthetic financial reader; never touch legacy files."""
    require_verified_network_execution()


def save_real_compute_ledger(ledger):
    """Retired optimistic credit writer; preserve historic files unchanged."""
    require_verified_network_execution()


def decrypt_vault_key(value):
    """Compatibility entry point cannot release credentials to held dispatch."""
    require_verified_network_execution()


def held_network_action():
    raise HTTPException(503, NETWORK_DISPATCH_HOLD, headers=PRIVATE_HEADERS)


@gpu_network_router.get("/nodes")
async def list_nodes_endpoint():
    return dict(network_unavailable(), nodes=[], total_active_nodes=None)


@gpu_network_router.get("/earnings/{node_id}")
async def get_node_earnings_endpoint(node_id: str):
    # A requested identifier is not verified ownership and never initializes state.
    return network_unavailable()


@gpu_network_router.get("/treasury-status")
async def get_treasury_status():
    return network_unavailable()


@gpu_network_router.post("/register-node")
async def register_node_endpoint(request: Request):
    held_network_action()


@gpu_network_router.post("/heartbeat")
async def heartbeat_endpoint(request: Request):
    held_network_action()


@gpu_network_router.post("/submit-job")
async def submit_job_endpoint(request: Request):
    held_network_action()


@gpu_network_router.post("/redeem-payout")
async def redeem_payout_endpoint(request: Request):
    # Request body is deliberately not parsed before the unconditional hold.
    held_network_action()
