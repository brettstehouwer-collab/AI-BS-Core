"""
Binary Analysis, Firmware Flashing & Bench Diagnostics Router
Exposes endpoints for:
- POST /api/v1/hardware/disassemble
- POST /api/v1/hardware/flashrom
- POST /api/v1/hardware/bench/diagnostics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from core.binary_hardware_workbench_engine import BinaryHardwareWorkbenchEngine

router = APIRouter(prefix="/api/v1/hardware", tags=["Binary & Hardware Workbench"])


class DisassembleRequest(BaseModel):
    hex_bytes_or_path: str = Field(..., description="Raw hex string or path to binary executable on host")
    arch: str = Field(default="x64", description="'x64', 'x86', or 'arm64'")
    base_address: int = Field(default=0x140000000, description="Virtual base address for instructions")
    max_instructions: int = Field(default=50, description="Max instructions to disassemble")


class FlashromRequest(BaseModel):
    action: str = Field(default="read", description="'probe', 'read', 'write', or 'verify'")
    chip_type: str = Field(default="W25Q128FV", description="SPI Flash IC identifier")
    programmer: str = Field(default="ch341a_spi", description="Programmer hardware identifier")
    image_path: Optional[str] = Field(default=None, description="Optional path to binary firmware image")


class BenchDiagnosticsRequest(BaseModel):
    device_model: str = Field(..., description="Device model e.g. 'iPhone 14 Pro', 'MacBook M2'")
    symptom_or_rail: str = Field(..., description="Voltage rail, error code, or symptom")
    limit: int = Field(default=5, description="Max diagnostic matches to return")


@router.post("/disassemble")
async def disassemble_endpoint(req: DisassembleRequest):
    try:
        res = BinaryHardwareWorkbenchEngine.disassemble_binary_or_bytes(
            hex_bytes_or_path=req.hex_bytes_or_path,
            arch=req.arch,
            base_address=req.base_address,
            max_instructions=req.max_instructions
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flashrom")
async def flashrom_endpoint(req: FlashromRequest):
    try:
        res = BinaryHardwareWorkbenchEngine.flash_chip_firmware(
            action=req.action,
            chip_type=req.chip_type,
            programmer=req.programmer,
            image_path=req.image_path
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bench/diagnostics")
async def bench_diagnostics_endpoint(req: BenchDiagnosticsRequest):
    try:
        res = BinaryHardwareWorkbenchEngine.query_bench_diagnostics(
            device_model=req.device_model,
            symptom_or_rail=req.symptom_or_rail,
            limit=req.limit
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
