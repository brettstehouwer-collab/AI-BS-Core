from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus

router = APIRouter(prefix="/api/crypto", tags=["Crypto Swarm & Mining Module"])

class TwapOrder(BaseModel):
    pair: str # e.g. 'ETH/USDT'
    total_amount: float
    intervals: int
    duration_minutes: int

@router.get("/status")
async def get_crypto_status():
    return {"module": "crypto_swarm", "network": "Polygon / EVM", "status": "active"}

@router.post("/twap/queue")
async def queue_twap_order(order: TwapOrder):
    slice_amount = round(order.total_amount / order.intervals, 4)
    await event_bus.publish(
        "events.crypto.twap_queued",
        {"pair": order.pair, "total": order.total_amount, "slice": slice_amount},
        source="crypto_swarm_module"
    )
    return {
        "status": "queued",
        "pair": order.pair,
        "total_amount": order.total_amount,
        "slice_amount": slice_amount,
        "intervals": order.intervals
    }

def init_module(app):
    print("[Module: CryptoSwarm] Initialized successfully.")
