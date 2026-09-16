import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from pydantic import BaseModel, Field
from core.ecosystem_telemetry_engine import EcosystemTelemetryEngine

logger = logging.getLogger("EcosystemTelemetryRouter")

router = APIRouter(prefix="", tags=["Ecosystem Ports & Live Telemetry"])


class TelemetryIngestRequest(BaseModel):
    port: int = Field(..., description="Target port of the sending daemon")
    metrics: Dict[str, Any] = Field(..., description="Arbitrary telemetry metrics payload (CPU, RAM, trade count, buffer state, etc.)")


class PortDiscoverRequest(BaseModel):
    ports: Optional[List[int]] = Field(None, description="List of ports to scan, or None for all active core ports")
    timeout_seconds: Optional[float] = Field(1.5, description="Probe timeout in seconds")


class PortToolDispatchRequest(BaseModel):
    port: int = Field(..., description="Target port number e.g. 8080, 8007, 8189, 11434")
    endpoint: str = Field(..., description="Target API path or RPC route e.g. '/api/health' or '/api/generate'")
    method: Optional[str] = Field("POST", description="HTTP Method: GET, POST, PUT, DELETE")
    payload: Optional[Dict[str, Any]] = Field(None, description="JSON body payload for POST/PUT requests")
    params: Optional[Dict[str, Any]] = Field(None, description="Query string parameters")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers")
    timeout_seconds: Optional[float] = Field(30.0, description="Execution timeout in seconds")


class TelemetryConnectionManager:
    """Manages active WebSocket connections for ecosystem telemetry streaming."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


telemetry_manager = TelemetryConnectionManager()


@router.websocket("/ws/ecosystem/telemetry")
async def websocket_ecosystem_telemetry(websocket: WebSocket):
    """
    Unified Live Telemetry WebSocket streaming listening sockets, CPU%, RAM, VRAM,
    and process status across host and WSL2 every 1.5 seconds.
    """
    await telemetry_manager.connect(websocket)
    try:
        while True:
            data = EcosystemTelemetryEngine.get_full_ecosystem_telemetry()
            await websocket.send_json(data)
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        telemetry_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client error: {e}")
        telemetry_manager.disconnect(websocket)


@router.get("/api/v1/system/ecosystem/telemetry")
async def get_ecosystem_telemetry_snapshot():
    """
    Returns an instant full telemetry snapshot across all listening ports,
    core matrix daemons, dynamic tools, and WSL2 environment.
    """
    return EcosystemTelemetryEngine.get_full_ecosystem_telemetry()


@router.post("/api/v1/system/ecosystem/telemetry/ingest")
async def ingest_port_telemetry(req: TelemetryIngestRequest):
    """
    Allows any internal or external service to report custom telemetry to AI-BS.
    """
    return EcosystemTelemetryEngine.ingest_port_metrics(req.port, req.metrics)


@router.post("/api/v1/system/ecosystem/ports/discover")
async def discover_port_tools_endpoint(req: PortDiscoverRequest = Body(default=PortDiscoverRequest())):
    """
    Probes active ports and auto-discovers OpenAPI schemas, tool signatures, and health endpoints.
    """
    return await EcosystemTelemetryEngine.discover_port_tools(
        ports=req.ports,
        timeout=req.timeout_seconds or 1.5
    )


@router.post("/api/v1/system/ecosystem/ports/dispatch")
async def dispatch_port_tool_endpoint(req: PortToolDispatchRequest):
    """
    Dispatches a dynamic tool call directly to any active port service with circuit-breaking and error containment.
    """
    return await EcosystemTelemetryEngine.dispatch_tool_call(
        port=req.port,
        endpoint=req.endpoint,
        method=req.method or "POST",
        payload=req.payload,
        params=req.params,
        headers=req.headers,
        timeout=req.timeout_seconds or 30.0
    )
