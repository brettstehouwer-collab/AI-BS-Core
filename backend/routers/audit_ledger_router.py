"""
AI-BS CDZ Cryptographic Audit Ledger API Router
Exposes endpoints for querying the CDZ zero-trust audit chain, domain purges,
sensor telemetry history, and active source polling watcher status.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import APIRouter, Header, Depends, Query, Request, HTTPException
from security.host_control_access import AdminHostControlRoute

from database.cdz_audit_db import get_cdz_summary, get_cdz_blocks
from modules.audit_ledger_watcher import cdz_watcher, CDZScanDraining
from modules.cdz_host_lifecycle import CDZHostLifecycle


@asynccontextmanager
async def cdz_router_lifespan(app):
    """Normal include_router path; explicit typed opt-in only.

    No lifecycle attribute means pass-through, including legacy background
    settings. An opt-in host must disable its separate legacy watcher startup.
    Refuse an already active legacy scanner rather than stop somebody else's
    worker or run two selected database paths concurrently.
    """
    lifecycle = getattr(app.state, "cdz_host_lifecycle", None)
    if lifecycle is None:
        yield
        return
    if not isinstance(lifecycle, CDZHostLifecycle):
        raise RuntimeError("Explicit typed CDZHostLifecycle required")
    legacy = cdz_watcher.get_status()
    if lifecycle.watcher is not cdz_watcher and (legacy["running"] or legacy.get("active_scans", 0)):
        raise RuntimeError("Separate legacy CDZ scanning is active; opt-in startup refused")
    async with lifecycle.lifespan(app):
        yield

router = APIRouter(
    prefix="/api/audit-ledger",
    tags=["CDZ Cryptographic Audit Ledger"],
    route_class=AdminHostControlRoute,
    lifespan=cdz_router_lifespan,
)


def get_tenant(x_client_id: Optional[str] = Header(default="stehouwer_publishing")) -> str:
    """Legacy host audit domain; caller labels never establish ownership."""
    return "stehouwer_publishing"


def get_cdz_store(request: Request):
    """Use an explicitly host-bound runtime; omission preserves legacy access.

    Hosts may instead override this dependency with their already-activated
    audit store. A configured but malformed/closed runtime fails without fallback.
    This dependency never constructs or activates a runtime.
    """
    runtime = getattr(request.app.state, "swarm_runtime", None)
    if runtime is None:
        return None
    store = runtime.stores["cdz_audit"]
    if store is None or getattr(store, "name", None) != "cdz_audit":
        raise RuntimeError("Configured audit store is unavailable")
    return store


def _watcher_for_store(request: Request, store):
    if store is None:
        return cdz_watcher
    watcher = getattr(request.app.state, "cdz_watcher", None)
    if getattr(watcher, "store", None) is store:
        return watcher
    return None


@router.get("/summary")
async def get_summary(request: Request, tenant: str = Depends(get_tenant), store=Depends(get_cdz_store)):
    """Returns CDZ audit chain KPIs, head/genesis hashes, and active watcher status."""
    summary = await asyncio.to_thread(get_cdz_summary, client_id=tenant, store=store)
    watcher = _watcher_for_store(request, store)
    summary["watcher"] = watcher.get_status() if watcher is not None else {"configured": False, "running": False}
    summary["tenant"] = tenant
    summary["access_scope"] = "host_shared_admin"
    summary["verification_scope"] = "stored_audit_records_only"
    return summary


@router.get("/blocks")
async def get_blocks(
    domain: Optional[str] = Query(default="ALL"),
    event: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant: str = Depends(get_tenant),
    store=Depends(get_cdz_store)
):
    """Returns paginated and filterable CDZ audit blocks."""
    blocks_data = await asyncio.to_thread(get_cdz_blocks,
        domain=domain,
        event=event,
        search=search,
        limit=limit,
        offset=offset,
        client_id=tenant,
        store=store
    )
    blocks_data["tenant"] = tenant
    blocks_data["access_scope"] = "host_shared_admin"
    blocks_data["verification_scope"] = "stored_audit_records_only"
    return blocks_data


@router.post("/scan")
async def scan_sources(request: Request, tenant: str = Depends(get_tenant), store=Depends(get_cdz_store)):
    """Forces an immediate on-demand scan of watched directories for new ledger exports."""
    watcher = _watcher_for_store(request, store)
    if watcher is None:
        raise HTTPException(409, "Shared-store source scanning is not configured.")
    if store is None:
        # Preserve ordinary unbound host behavior.
        result = await asyncio.to_thread(watcher.scan_now)
        summary = await asyncio.to_thread(get_cdz_summary, client_id=tenant, store=store)
    else:
        try:
            result, summary = await asyncio.to_thread(watcher.scan_and_summarize, client_id=tenant)
        except CDZScanDraining:
            raise HTTPException(409, "CDZ source scanning is draining.") from None
    return {
        "status": "success",
        "scan_result": result,
        "summary": summary,
        "tenant": tenant
    }
