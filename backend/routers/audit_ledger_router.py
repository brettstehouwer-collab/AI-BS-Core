"""
AI-BS CDZ Cryptographic Audit Ledger API Router
Exposes endpoints for querying the CDZ zero-trust audit chain, domain purges,
sensor telemetry history, and active source polling watcher status.
"""

from typing import Optional
from fastapi import APIRouter, Header, Depends, Query
from security.host_control_access import AdminHostControlRoute

from database.cdz_audit_db import get_cdz_summary, get_cdz_blocks
from modules.audit_ledger_watcher import cdz_watcher

router = APIRouter(
    prefix="/api/audit-ledger",
    tags=["CDZ Cryptographic Audit Ledger"],
    route_class=AdminHostControlRoute
)


def get_tenant(x_client_id: Optional[str] = Header(default="stehouwer_publishing")) -> str:
    """Legacy host audit domain; caller labels never establish ownership."""
    return "stehouwer_publishing"


@router.get("/summary")
async def get_summary(tenant: str = Depends(get_tenant)):
    """Returns CDZ audit chain KPIs, head/genesis hashes, and active watcher status."""
    summary = get_cdz_summary(client_id=tenant)
    summary["watcher"] = cdz_watcher.get_status()
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
    tenant: str = Depends(get_tenant)
):
    """Returns paginated and filterable CDZ audit blocks."""
    blocks_data = get_cdz_blocks(
        domain=domain,
        event=event,
        search=search,
        limit=limit,
        offset=offset,
        client_id=tenant
    )
    blocks_data["tenant"] = tenant
    blocks_data["access_scope"] = "host_shared_admin"
    blocks_data["verification_scope"] = "stored_audit_records_only"
    return blocks_data


@router.post("/scan")
async def scan_sources(tenant: str = Depends(get_tenant)):
    """Forces an immediate on-demand scan of watched directories for new ledger exports."""
    result = cdz_watcher.scan_now()
    summary = get_cdz_summary(client_id=tenant)
    return {
        "status": "success",
        "scan_result": result,
        "summary": summary,
        "tenant": tenant
    }
