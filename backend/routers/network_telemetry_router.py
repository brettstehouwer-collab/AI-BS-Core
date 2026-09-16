"""
AI-BS Network Telemetry & Over-The-Air Wave Sensor API Router
Exposes application-level ASGI wire packet metrics, Npcap L2/L3 promiscuous capture engine,
capture mode selectors (ASGI, NPCAP, HYBRID), BPF filter settings, cryptographic packet hashes,
stehouwer-publishing.com traffic filters, and ambient RF wave hardware sensor telemetry.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, Depends, Query
from fastapi.responses import StreamingResponse
from modules.network_telemetry import network_telemetry_engine, telemetry_manager
from modules.ambient_sensor_telemetry import air_sensor_engine

router = APIRouter(
    prefix="/api/network-telemetry",
    tags=["Network Telemetry & Over-The-Air Wave Sensors"]
)

def get_tenant(x_client_id: Optional[str] = Header(default="stehouwer_publishing")) -> str:
    return x_client_id if x_client_id else "stehouwer_publishing"


@router.get("/summary")
async def get_network_summary(tenant: str = Depends(get_tenant)):
    """
    Returns decoupled, technically defensible telemetry summaries for L7 Transactions,
    L2/L3 Wire Frames, L4 Flows, and Stehouwer Publishing.
    """
    summary = network_telemetry_engine.get_summary()
    summary["tenant"] = tenant
    return summary


@router.get("/capture-mode")
async def get_engine_mode(tenant: str = Depends(get_tenant)):
    """
    Returns current capture engine configuration.
    """
    summary = network_telemetry_engine.get_summary()
    return {
        "status": "success",
        "tenant": tenant,
        "capture_engine": summary.get("capture_engine", {})
    }


@router.post("/capture-mode")
async def set_engine_mode(
    mode: str = Query(default="ASGI", pattern="^(ASGI|NPCAP|HYBRID)$"),
    interface: Optional[str] = Query(default=None),
    bpf: str = Query(default="tcp or udp"),
    tenant: str = Depends(get_tenant)
):
    """
    Toggles between pure ASGI, Npcap raw wire promiscuous capture, or parallel Hybrid telemetry.
    """
    try:
        res = network_telemetry_engine.set_mode(mode=mode, interface=interface, bpf_filter=bpf)
        res["tenant"] = tenant
        return res
    except RuntimeError as e:
        return {
            "status": "error",
            "message": str(e),
            "npcap_available": False,
            "active_mode": network_telemetry_engine.capture_mode,
            "tenant": tenant
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "tenant": tenant
        }


@router.get("/interfaces")
async def get_network_interfaces(tenant: str = Depends(get_tenant)):
    """
    Returns list of discovered host network adapters with name, description, MAC, and IP addresses.
    """
    interfaces = network_telemetry_engine.get_interfaces()
    return {
        "status": "success",
        "tenant": tenant,
        "count": len(interfaces),
        "interfaces": interfaces
    }


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
    return {
        "status": "success",
        "tenant": tenant,
        "record_type": record_type,
        "count": len(records),
        "traffic": records
    }


@router.get("/flows")
async def get_network_flows(tenant: str = Depends(get_tenant)):
    """
    Returns active L4 conversational 5-tuple flows.
    """
    summary = network_telemetry_engine.get_summary()
    return {
        "status": "success",
        "tenant": tenant,
        "flows": summary.get("flows", {})
    }


@router.get("/routes")
async def get_route_distribution(tenant: str = Depends(get_tenant)):
    """
    Returns endpoint route frequency counts.
    """
    summary = network_telemetry_engine.get_summary()
    return {
        "status": "success",
        "tenant": tenant,
        "top_routes": summary.get("transactions", {}).get("top_routes", summary.get("top_routes", []))
    }


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
        return {
            "status": "not_found",
            "tenant": tenant,
            "message": "No correlated flow found for provided flow_id or transaction_id."
        }
    res["status"] = "success"
    res["tenant"] = tenant
    return res


@router.get("/air/scan")
async def scan_ambient_air(tenant: str = Depends(get_tenant)):
    """
    Triggers an active on-demand over-the-air RF wave sweep across host PC hardware sensors
    (Wi-Fi 2.4/5/6 GHz beacon frames and Bluetooth BLE advertisements), generates deterministic
    SHA-256 beacon hashes, persists them to SQLite, and returns live discovered signals.
    """
    scan_result = air_sensor_engine.scan_air()
    scan_result["tenant"] = tenant
    return scan_result


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
    records = air_sensor_engine.get_records(
        limit=limit,
        offset=offset,
        sensor_type=sensor_type,
        band=band,
        hash_query=hash_query
    )
    return {
        "status": "success",
        "tenant": tenant,
        "count": len(records),
        "records": records
    }


@router.get("/air/summary")
async def get_air_summary(tenant: str = Depends(get_tenant)):
    """
    Returns aggregated air wave telemetry statistics.
    """
    summary = air_sensor_engine.get_summary()
    summary["tenant"] = tenant
    return summary


@router.post("/clear")
@router.post("/air/clear")
async def clear_traffic(tenant: str = Depends(get_tenant)):
    """
    Clears in-memory ring buffers and resets telemetry counters.
    """
    network_telemetry_engine.clear()
    return {
        "status": "success",
        "tenant": tenant,
        "message": "Network telemetry transaction and frame buffers cleared."
    }


@router.get("/stream")
async def stream_live_telemetry(tenant: str = Depends(get_tenant)):
    """
    Real-time Server-Sent Events (SSE) stream emitting live L7 transactions and L2/L3 frames.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    with network_telemetry_engine.lock:
        network_telemetry_engine.subscribers.append(queue)

    async def event_generator():
        try:
            # Yield initial connection confirmation
            init_payload = {
                "event": "connected",
                "timestamp": network_telemetry_engine.get_summary()["transactions"],
                "capture_engine": network_telemetry_engine.capture_mode
            }
            yield f"event: ping\ndata: {json.dumps(init_payload)}\n\n"

            while True:
                try:
                    record = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: packet\ndata: {json.dumps(record)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
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
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
