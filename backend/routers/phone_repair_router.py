"""
AI-BS Phone & Tablet Repair Knowledge Subsystem API Router
Provides REST endpoints for device teardown guides, diagnostic troubleshooting trees,
micro-soldering IC pinouts, chemical/tooling references, and repair tickets.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.phone_repair_knowledge import phone_repair_engine
from core.personal_intelligence_memory import personal_memory

router = APIRouter(prefix="/api/repair", tags=["Phone & Tablet Repair"])


def get_tenant(x_client_id: Optional[str] = Header("stehouwer_publishing")) -> str:
    return x_client_id if x_client_id else "stehouwer_publishing"


class CreateTicketRequest(BaseModel):
    customer_name: str = Field(..., description="Customer full name")
    customer_phone: Optional[str] = ""
    device_category: str = Field("apple_iphone", description="apple_iphone, apple_ipad, android_phone, android_tablet")
    device_model: str = Field(..., description="e.g. iPhone 15 Pro, Galaxy S24 Ultra, iPad 10th Gen")
    serial_imei: Optional[str] = ""
    reported_issue: str = Field(..., description="e.g. Broken screen, battery drain, no power")
    diagnosis_notes: Optional[str] = ""
    part_grade_used: Optional[str] = "Premium OLED"
    parts_cost_usd: Optional[float] = 0.0
    labor_charge_usd: Optional[float] = 0.0
    total_price_usd: Optional[float] = 0.0
    status: Optional[str] = "Checked-In"


class UpdateTicketStatusRequest(BaseModel):
    status: str = Field(..., description="Checked-In, Diagnosing, Awaiting Parts, In Repair, Testing QA, Completed, Picked Up")
    qa_passed: Optional[int] = 0


@router.get("/categories")
async def list_repair_categories():
    """Lists categorized groups with iconography and counts."""
    return {
        "status": "success",
        "categories": [
            {
                "id": "apple_iphone",
                "name": "Apple iPhone",
                "icon": "🍏",
                "description": "OLED / Screen replacement, TrueTone & EEPROM serialization, BMS battery welding, Face ID dot projectors, and logic board sandwich VDD_MAIN micro-soldering."
            },
            {
                "id": "apple_ipad",
                "name": "Apple iPad",
                "icon": "📱",
                "description": "Air-gap digitizer vs laminated LCD separation, Touch ID transfer, 36-pin dock port micro-soldering, battery adhesive dissolution, and aluminum chassis de-warping."
            },
            {
                "id": "android_phone",
                "name": "Android Phones (Samsung / Pixel / Moto)",
                "icon": "🤖",
                "description": "Curved Dynamic AMOLED & Service Pack swaps, ultrasonic under-display fingerprint calibration (*#0*# test mode), sub-board dock flexes, and Odin/Fastboot unbricking."
            },
            {
                "id": "android_tablet",
                "name": "Android Tablets",
                "icon": "📟",
                "description": "Galaxy Tab, Lenovo & Amazon Fire screen digitizers, battery replacements, and USB-C surface-mount port trace repair."
            }
        ]
    }


@router.get("/guides")
async def list_repair_guides(
    category: Optional[str] = None,
    repair_type: Optional[str] = None,
    difficulty: Optional[str] = None
):
    """Fetches repair guides filtered by category, repair type, or difficulty."""
    try:
        guides = phone_repair_engine.get_all_guides(
            category=category,
            repair_type=repair_type,
            difficulty=difficulty
        )
        return {
            "status": "success",
            "count": len(guides),
            "guides": guides
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch guides: {e}")


@router.get("/guide/{guide_id}")
async def get_single_guide(guide_id: str):
    """Fetches full step-by-step repair guide details."""
    guide = phone_repair_engine.get_guide_by_id(guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Repair guide not found.")
    return {"status": "success", "guide": guide}


@router.get("/diagnostics")
async def get_diagnostic_trees():
    """Fetches hardware troubleshooting decision trees and DC bench power supply curves."""
    try:
        trees = phone_repair_engine.get_diagnostic_trees()
        return {
            "status": "success",
            "count": len(trees),
            "diagnostic_trees": trees
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch diagnostics: {e}")


@router.get("/ic_reference")
async def get_ic_references():
    """Fetches micro-soldering IC reference tables, symptom cross-references, and diode mode readings."""
    try:
        ics = phone_repair_engine.get_ic_references()
        return {
            "status": "success",
            "count": len(ics),
            "ic_references": ics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch IC reference: {e}")


@router.get("/tools_reference")
async def get_tools_and_chemical_reference():
    """Returns screwdriver matrices, thermal presets, and chemical bonding guidelines."""
    return {
        "status": "success",
        "screwdrivers": [
            {"type": "Pentalobe P2 (0.8mm)", "use_cases": "Apple iPhone lower chassis perimeter screws (iPhone 4 to 16 Pro Max)"},
            {"type": "Pentalobe P5 (1.2mm)", "use_cases": "MacBook Air & Pro lower case screws"},
            {"type": "Tri-Point Y000 (0.6mm)", "use_cases": "iPhone 7 to 16 display brackets, battery EMI shields, and Taptic engine screws"},
            {"type": "Phillips PH000 (1.5mm)", "use_cases": "Internal frame screws on Samsung, Google Pixel, iPad LCD mounts, and tablets"},
            {"type": "Torx T3 / T4 / T5", "use_cases": "Google Pixel brackets, Motorola housings, and iPad Pro Face ID brackets"},
            {"type": "Standoff Bit (2.5mm)", "use_cases": "iPhone logic board grounded standoff screws"}
        ],
        "thermal_presets": [
            {"substrate": "iPhone OLED Screen Opening", "temp_c": 75, "time_min": 2.5, "warning": "Do not exceed 80°C on soft OLEDs"},
            {"substrate": "iPad Digitizer Separation", "temp_c": 90, "time_min": 5.0, "warning": "Keep frame flat; monitor LCD temp with IR thermometer"},
            {"substrate": "Samsung Rear Glass De-Gluing", "temp_c": 80, "time_min": 3.0, "warning": "Avoid direct heat on camera lenses to prevent sensor haze"},
            {"substrate": "Logic Board Sandwich Separation", "temp_c": 190, "time_min": 2.0, "warning": "Use low-melt 138°C alloy or 183°C leaded solder"}
        ],
        "chemicals_and_adhesives": [
            {"chemical": "99.9% Isopropyl Alcohol (IPA)", "usage": "Dissolves battery stretch adhesive and frame glue instantly without shorting active circuits."},
            {"chemical": "B-7000 Adhesive", "usage": "Clear slow-cure elastomeric glue (24h full cure). Ideal for phone rear glass and plastic frames."},
            {"chemical": "T-7000 Adhesive", "usage": "Black high-strength rubber adhesive. Superior for iPad digitizers and plastic bezel bonding."},
            {"chemical": "Amtech NC-559-V2-TF Flux", "usage": "No-clean rosin flux for micro-BGA reballing and connector drag-soldering."},
            {"chemical": "3M Primer 94", "usage": "Adhesion promoter applied to aluminum chamfers before seating glass."}
        ]
    }


@router.get("/tickets")
async def get_repair_tickets(client_id: str = Depends(get_tenant)):
    """Fetches customer repair ticket logs."""
    try:
        tickets = phone_repair_engine.get_repair_tickets(client_id=client_id)
        return {
            "status": "success",
            "client_id": client_id,
            "count": len(tickets),
            "tickets": tickets
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repair tickets: {e}")


@router.post("/tickets/create")
async def create_repair_ticket(req: CreateTicketRequest, client_id: str = Depends(get_tenant)):
    """Creates a new customer repair ticket and logs into episodic lore."""
    try:
        ticket = phone_repair_engine.create_repair_ticket({
            "client_id": client_id,
            **req.dict()
        })
        
        # Auto-record in AI-BS Episodic Memory Vault
        try:
            personal_memory.record_ecosystem_event(
                event_type="phone_repair_ticket",
                summary=f"Created Repair Ticket #{ticket['ticket_id']}: {req.device_model} ({req.reported_issue}) for {req.customer_name}",
                metadata={"ticket_id": ticket["ticket_id"], "model": req.device_model, "price": req.total_price_usd}
            )
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"Repair ticket #{ticket['ticket_id']} successfully registered.",
            "ticket": ticket
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repair ticket: {e}")


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: int, req: UpdateTicketStatusRequest):
    """Updates ticket lifecycle status."""
    try:
        updated = phone_repair_engine.update_ticket_status(
            ticket_id=ticket_id,
            new_status=req.status,
            qa_passed=req.qa_passed
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return {"status": "success", "ticket": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ticket status: {e}")
