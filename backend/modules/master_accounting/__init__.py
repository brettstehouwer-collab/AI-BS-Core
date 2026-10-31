from security.host_control_access import AdminHostControlRoute
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


router = APIRouter(route_class=AdminHostControlRoute, prefix="/api/accounting", tags=["Master Accounting & Tax Module"])

class InvoiceDraft(BaseModel):
    client_name: str
    amount: float
    description: str

@router.get("/status")
async def get_accounting_status():
    return {"module": "master_accounting", "currency": "USD", "status": "held", "reason": "Verified invoice ownership and durable decimal draft evidence required"}

@router.post("/invoice/draft")
async def draft_invoice(inv: InvoiceDraft):
    raise HTTPException(503, "Invoice drafting held: verified ownership and durable decimal draft evidence are required before publishing events.")
    invoice_id = f"INV-{int(inv.amount)}-{inv.client_name[:3].upper()}"
    await event_bus.publish(
        "events.accounting.invoice_created",
        {"invoice_id": invoice_id, "client": inv.client_name, "amount": inv.amount},
        source="accounting_module"
    )
    return {"status": "drafted", "invoice_id": invoice_id, "amount": inv.amount}

def init_module(app):
    print("[Module: MasterAccounting] Initialized successfully.")
