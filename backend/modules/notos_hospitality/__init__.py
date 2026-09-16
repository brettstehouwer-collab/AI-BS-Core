from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus

router = APIRouter(prefix="/api/notos", tags=["Noto's Enterprise OS Module"])

class BarStockItem(BaseModel):
    bar_location: str # 'Grand Rapids' or 'Grand Haven'
    item_name: str
    current_count: int
    par_level: int

@router.get("/status")
async def get_notos_status():
    return {"module": "notos_hospitality", "locations": ["Grand Rapids", "Grand Haven"], "status": "active"}

@router.post("/inventory/check")
async def check_inventory_level(item: BarStockItem):
    deficit = item.par_level - item.current_count
    needs_reorder = deficit > 0

    if needs_reorder:
        await event_bus.publish(
            "events.notos.inventory_alert",
            {"location": item.bar_location, "item": item.item_name, "deficit": deficit},
            source="notos_module"
        )

    return {
        "item": item.item_name,
        "location": item.bar_location,
        "stock": item.current_count,
        "par": item.par_level,
        "reorder_required": needs_reorder,
        "reorder_units": max(0, deficit)
    }

def init_module(app):
    print("[Module: NotosHospitality] Initialized successfully.")
