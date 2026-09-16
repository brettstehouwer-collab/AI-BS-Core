from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus

router = APIRouter(prefix="/api/noco", tags=["Project NoCo & Living Stage Module"])

class SensorReading(BaseModel):
    zone: str # 'living_stage', 'greenhouse', 'compound'
    ambient_db: float
    soil_moisture: float
    solar_generation_kw: float

@router.get("/status")
async def get_noco_status():
    return {"module": "noco_stage", "enclave_acres": 23.0, "status": "active"}

@router.post("/telemetry")
async def record_sensor_telemetry(data: SensorReading):
    await event_bus.publish(
        "events.noco.sensor_update",
        {"zone": data.zone, "ambient_db": data.ambient_db, "solar_kw": data.solar_generation_kw},
        source="noco_module"
    )
    return {"status": "recorded", "zone": data.zone, "acoustic_db": data.ambient_db}

def init_module(app):
    print("[Module: NoCoStage] Initialized successfully.")
