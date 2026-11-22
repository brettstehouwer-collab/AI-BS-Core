"""
AI-BS Network Telemetry & Over-The-Air Wave Sensor API Router
Exposes application-level ASGI wire packet metrics, Npcap L2/L3 promiscuous capture engine,
capture mode selectors (ASGI, NPCAP, HYBRID), BPF filter settings, cryptographic packet hashes,
stehouwer-publishing.com traffic filters, and ambient RF wave hardware sensor telemetry.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from fastapi.responses import StreamingResponse
from modules.network_telemetry import network_telemetry_engine, sanitize_telemetry_record
from security.firebase_auth import get_admin_principal

PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization, X-Admin-Key, X-Api-Key",
}


def get_air_sensor_engine():
    # The legacy sensor singleton initializes its SQLite schema. Do not import
    # it at application startup or before the administrator boundary succeeds.
    from modules.ambient_sensor_telemetry import air_sensor_engine
    return air_sensor_engine


async def get_tenant(request: Request) -> str:
    """Verified administrator for global host telemetry, never a client tenant claim."""
    principal = await asyncio.to_thread(
        get_admin_principal,
        request.headers.get("x-admin-key") or request.headers.get("x-api-key", ""),
        request.headers.get("authorization", ""),
    )
    if not principal:
        raise HTTPException(403, "Administrator authorization is required for host telemetry.",
                            headers=PRIVATE_HEADERS)
    return principal


class PrivateTelemetryRoute(APIRoute):
    """Apply private cache/error boundaries to JSON, validation and SSE responses."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private_handler(request: Request):
            try:
                response = await handler(request)
            except HTTPException as exc:
                raise HTTPException(exc.status_code, exc.detail,
                                    headers={**(exc.headers or {}), **PRIVATE_HEADERS}) from None
            except RequestValidationError:
                raise HTTPException(422, "Invalid telemetry request.", headers=PRIVATE_HEADERS) from None
            except Exception:
                raise HTTPException(503, "Host telemetry is unavailable.", headers=PRIVATE_HEADERS) from None
            response.headers.update(PRIVATE_HEADERS)
            return response

        return private_handler


def host_response(payload):
    """All admitted administrators inspect one host; records are not tenant-owned."""
    return dict(sanitize_telemetry_record(payload), scope="global_host_admin_only")


router = APIRouter(
    prefix="/api/network-telemetry",
    tags=["Network Telemetry & Over-The-Air Wave Sensors"],
    dependencies=[Depends(get_tenant)],
    route_class=PrivateTelemetryRoute,
)


@router.get("/summary")
async def get_network_summary(tenant: str = Depends(get_tenant)):
    """
    Returns decoupled, technically defensible telemetry summaries for L7 Transactions,
    L2/L3 Wire Frames, L4 Flows, and Stehouwer Publishing.
    """
    summary = network_telemetry_engine.get_summary()
    summary["tenant"] = tenant
    return host_response(summary)


@router.get("/capture-mode")
async def get_engine_mode(tenant: str = Depends(get_tenant)):
    """
    Returns current capture engine configuration.
    """
    summary = network_telemetry_engine.get_summary()
    return host_response({
        "status": "success",
        "tenant": tenant,
        "capture_engine": summary.get("capture_engine", {})
    })


@router.post("/capture-mode")
async def set_engine_mode(
    mode: str = Query(default="ASGI", pattern="^(ASGI|NPCAP|HYBRID)$"),
    interface: Optional[str] = Query(default=None),
    bpf: str = Query(default="tcp or udp"),
    tenant: str = Depends(get_tenant)
):
    """Held until capture/runtime ownership and a safe lifecycle are verified."""
    raise HTTPException(503, "Capture control is held pending verified runtime and ownership migration.",
                        headers=PRIVATE_HEADERS)


@router.get("/interfaces")
async def get_network_interfaces(tenant: str = Depends(get_tenant)):
    """
    Returns list of discovered host network adapters with name, description, MAC, and IP addresses.
    """
    interfaces = network_telemetry_engine.get_interfaces()
    return host_response({
        "status": "success",
        "tenant": tenant,
        "count": len(interfaces),
        "interfaces": interfaces
    })


@router.get("/traffic")
async def get_traffic_records(
    record_type: str = Query(default="ALL", pattern="^(ALL|TRANSACTION|FRAME|TX|FRM)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    domain: Optional[str] = Query(default=None),
    is_stehouwer: Optional[bool] = Query(default=None),
    has_hash: Optional[bool] = Query(default=None),
    method: Optional[str] = Query(default=None),
    status: Optional[int] = Query(default=None),
    engine: Optional[str] = Query(default=None),
    trusted_only: Optional[bool] = Query(default=None),
    tenant: str = Depends(get_tenant)
):
    """
    Retrieves filterable list of captured HTTP/WebSocket transactions and/or Npcap physical wire frames
    with SHA-256 payload digests, TCP flags, and L2 MACs.
    """
    records = network_telemetry_engine.get_traffic(
        record_type=record_type,
        limit=limit,
        offset=offset,
        domain=domain,
        is_stehouwer=is_stehouwer,
        has_hash=has_hash,
        method=method,
        status=status,
        engine=engine,
        trusted_only=trusted_only
    )
    return host_response({
        "status": "success",
        "tenant": tenant,
        "record_type": record_type,
        "count": len(records),
        "traffic": records
    })


@router.get("/flows")
async def get_network_flows(tenant: str = Depends(get_tenant)):
    """
    Returns active L4 conversational 5-tuple flows.
    """
    summary = network_telemetry_engine.get_summary()
    return host_response({
        "status": "success",
        "tenant": tenant,
        "flows": summary.get("flows", {})
    })


@router.get("/routes")
async def get_route_distribution(tenant: str = Depends(get_tenant)):
    """
    Returns endpoint route frequency counts.
    """
    summary = network_telemetry_engine.get_summary()
    return host_response({
        "status": "success",
        "tenant": tenant,
        "top_routes": summary.get("transactions", {}).get("top_routes", summary.get("top_routes", []))
    })


@router.get("/correlation")
async def get_flow_correlation(
    flow_id: Optional[str] = Query(default=None),
    transaction_id: Optional[str] = Query(default=None),
    tenant: str = Depends(get_tenant)
):
    """
    Answers: 'Which physical wire frames carried this particular HTTP transaction?'
    Returns correlated flow metadata, linked L7 transactions, and all L2/L3 physical wire frames.
    """
    res = network_telemetry_engine.get_flow_correlation(flow_id=flow_id, transaction_id=transaction_id)
    if not res:
        return host_response({
            "status": "not_found",
            "tenant": tenant,
            "message": "No correlated flow found for provided flow_id or transaction_id."
        })
    res["status"] = "success"
    res["tenant"] = tenant
    return host_response(res)


@router.get("/air/scan")
async def scan_ambient_air(tenant: str = Depends(get_tenant)):
    """GET must not trigger hardware scans or write new radio observations."""
    raise HTTPException(503, "Active radio scans are held pending verified capture controls.",
                        headers=PRIVATE_HEADERS)


@router.get("/air/records")
async def get_air_records(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sensor_type: Optional[str] = Query(default=None),
    band: Optional[str] = Query(default=None),
    hash_query: Optional[str] = Query(default=None),
    tenant: str = Depends(get_tenant)
):
    """
    Queries historical over-the-air radio wave beacon records from SQLite.
    """
    records = get_air_sensor_engine().get_records(
        limit=limit,
        offset=offset,
        sensor_type=sensor_type,
        band=band,
        hash_query=hash_query
    )
    return host_response({
        "status": "success",
        "tenant": tenant,
        "count": len(records),
        "records": records
    })


@router.get("/air/summary")
async def get_air_summary(tenant: str = Depends(get_tenant)):
    """
    Returns aggregated air wave telemetry statistics.
    """
    summary = get_air_sensor_engine().get_summary()
    summary["tenant"] = tenant
    return host_response(summary)


@router.post("/clear")
async def clear_traffic(tenant: str = Depends(get_tenant)):
    """
    Clears in-memory ring buffers and resets telemetry counters.
    """
    network_telemetry_engine.clear()
    return host_response({
        "status": "success",
        "tenant": tenant,
        "message": "Network telemetry transaction and frame buffers cleared."
    })


@router.post("/air/clear")
async def clear_air_records(tenant: str = Depends(get_tenant)):
    """Retain sensor history until a reviewed retention/reset contract exists."""
    raise HTTPException(503, "Radio history reset is held pending verified retention controls.",
                        headers=PRIVATE_HEADERS)


@router.get("/stream")
async def stream_live_telemetry(request: Request, tenant: str = Depends(get_tenant)):
    """
    Real-time Server-Sent Events (SSE) stream emitting live L7 transactions and L2/L3 frames.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    async def event_generator():
        # Register only when consumption begins, so an unconsumed/cancelled
        # response does not leave an orphan subscriber.
        with network_telemetry_engine.lock:
            network_telemetry_engine.subscribers.append(queue)
        try:
            # Yield initial connection confirmation
            init_payload = host_response({
                "event": "connected",
                "timestamp": network_telemetry_engine.get_summary()["transactions"],
                "capture_engine": network_telemetry_engine.capture_mode,
                "tenant": tenant,
            })
            yield f"event: ping\ndata: {json.dumps(init_payload)}\n\n"

            while True:
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    record = None
                # Revalidate before every data publication, and on idle
                # heartbeats. Expired/revoked/changed identities end the stream.
                try:
                    if await get_tenant(request) != tenant:
                        return
                except HTTPException:
                    return
                if record is None:
                    yield ": keepalive\n\n"
                else:
                    yield f"event: packet\ndata: {json.dumps(sanitize_telemetry_record(record))}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            with network_telemetry_engine.lock:
                if queue in network_telemetry_engine.subscribers:
                    network_telemetry_engine.subscribers.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            **PRIVATE_HEADERS,
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
