from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus
from db_manager import get_sqlite_connection

router = APIRouter(prefix="/api/prestige", tags=["Prestige Mobile Wash Module"])
DB_PATH = os.path.join(_backend_dir, "prestige_powerwash.db")

class EstimateRequest(BaseModel):
    client_name: str
    property_type: str # 'residential' or 'commercial'
    sq_ft: float
    chemical_package: Optional[str] = "standard_bleach_surfactant"

@router.get("/status")
async def get_prestige_status():
    return {"module": "prestige_wash", "status": "active", "db": DB_PATH}

@router.post("/estimate")
async def calculate_estimate(req: EstimateRequest):
    rate_per_sqft = 0.35 if req.property_type == "commercial" else 0.28
    base_cost = req.sq_ft * rate_per_sqft
    chem_multiplier = 1.15 if "hot_degrease" in req.chemical_package else 1.05
    final_quote = round(base_cost * chem_multiplier, 2)

    # Dispatch to Event Bus
    await event_bus.publish(
        "events.prestige.new_estimate",
        {"client": req.client_name, "sq_ft": req.sq_ft, "quote": final_quote},
        source="prestige_module"
    )

    return {
        "client_name": req.client_name,
        "sq_ft": req.sq_ft,
        "rate_per_sqft": rate_per_sqft,
        "estimated_quote": final_quote,
        "status": "quoted"
    }

def init_module(app):
    print("[Module: PrestigeWash] Initialized successfully.")
