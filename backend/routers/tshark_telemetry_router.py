import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.tshark_telemetry_engine import TSharkTelemetryEngine

router = APIRouter(prefix="/api/v1/diagnostics/tshark", tags=["TShark Telemetry & Hardware Diagnostics"])


class CaptureRequest(BaseModel):
    ports: Optional[List[int]] = Field([8001, 8080, 8335, 11434, 11435], description="Ports to filter")
    duration_seconds: Optional[int] = Field(3, description="Capture duration in seconds")
    max_packets: Optional[int] = Field(50, description="Max packets to return")
    interface: Optional[str] = Field(None, description="Optional network interface")


@router.post("/capture")
async def capture_packets_endpoint(req: CaptureRequest):
    """
    Executes local packet capture with TShark and socket latency audit.
    """
    return TSharkTelemetryEngine.capture_packets(
        ports=req.ports or [8001, 8080, 8335, 11434, 11435],
        duration_seconds=req.duration_seconds or 3,
        max_packets=req.max_packets or 50,
        interface=req.interface
    )


@router.get("/mining-audit")
async def audit_mining_endpoint(port: int = 8335):
    """
    Audits Pearl Mining Stratum & Wallet daemon connectivity on Port 8335 and hero mining pools.
    """
    return TSharkTelemetryEngine.audit_pearl_mining_telemetry(port=port)


@router.get("/info")
async def get_tshark_info():
    """
    Returns TShark installation path, version, and packet capture capabilities.
    """
    return TSharkTelemetryEngine.get_tshark_info()
