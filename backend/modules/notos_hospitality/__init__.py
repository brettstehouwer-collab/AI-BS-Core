from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
import sys
import sqlite3
import datetime

_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.aibs_event_bus import event_bus

DB_PATH = os.path.join(_backend_dir, "backend", "aibs_master.db")
if not os.path.exists(DB_PATH):
    # Fallback to direct path
    DB_PATH = os.path.join(_backend_dir, "aibs_master.db")

router = APIRouter(prefix="/api/notos", tags=["Noto's Enterprise OS Module"])

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

# ─── Pydantic Models ───
class BarStockItem(BaseModel):
    bar_location: str = "GR" # 'GR' or 'GH'
    item_name: str
    current_count: int
    par_level: int

class UpdateItemStockRequest(BaseModel):
    id: str
    field: str # 'upstairs', 'downstairs', 'banquet_a', 'banquet_b', 'patio', 'storeroom', 'status'
    value: str

class NewInventoryItemRequest(BaseModel):
    id: Optional[str] = None
    location: str = "GR"
    name: str
    category: str
    par_level: int = 6
    upstairs: str = "0"
    downstairs: str = "0"
    banquet_a: str = "0"
    banquet_b: str = "0"
    patio: str = "0"
    cellar_bin: str = "N/A"
    storeroom: str = "0"
    distributor: str = ""
    status: str = "FULL"

class NewDispatchRequest(BaseModel):
    target_bar: str
    item: str
    source_loc: str = "Central Storeroom"
    requested_by: str = "Bartender"
    location: str = "GR"

class DispatchStatusRequest(BaseModel):
    id: str
    status: str # 'PENDING', 'EN_ROUTE', 'DELIVERED'

class NewSosRequest(BaseModel):
    bar: str
    type: str
    urgency: str = "NORMAL"
    location: str = "GR"

class New86Request(BaseModel):
    item: str
    station: str
    reason: str
    alt_suggestion: Optional[str] = ""
    location: str = "GR"

# ─── Endpoints ───

@router.get("/status")
async def get_notos_status():
    return {
        "module": "notos_hospitality",
        "locations": ["Grand Rapids", "Grand Haven"],
        "status": "active",
        "db": DB_PATH
    }

@router.get("/inventory")
async def get_inventory(location: str = Query("ALL", description="Filter by GR, GH, or ALL"), category: Optional[str] = None):
    try:
        conn = get_db()
        cur = conn.cursor()
        query = "SELECT * FROM noto_inventory_items WHERE 1=1"
        params = []

        if location and location.upper() != "ALL":
            query += " AND location = ?"
            params.append(location.upper())

        if category and category.upper() != "ALL":
            query += " AND category LIKE ?"
            params.append(f"%{category}%")

        query += " ORDER BY category ASC, name ASC"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]

        # Compute summary stats
        stats = {
            "total": len(rows),
            "low": sum(1 for r in rows if r.get("status") == "LOW"),
            "critical": sum(1 for r in rows if r.get("status") == "CRITICAL"),
            "full": sum(1 for r in rows if r.get("status") == "FULL"),
            "out": sum(1 for r in rows if r.get("status") == "OUT")
        }
        conn.close()
        return {"items": rows, "stats": stats, "location": location}
    except Exception as e:
        return {"error": str(e), "items": [], "stats": {"total": 0, "low": 0, "critical": 0, "full": 0, "out": 0}}

@router.post("/inventory/update")
async def update_inventory_stock(req: UpdateItemStockRequest):
    allowed_fields = {"upstairs", "downstairs", "banquet_a", "banquet_b", "patio", "storeroom", "status", "cellar_bin", "par_level"}
    if req.field not in allowed_fields:
        raise HTTPException(status_code=400, detail=f"Field {req.field} not allowed for update")

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE noto_inventory_items SET {req.field} = ?, last_updated = CURRENT_TIMESTAMP WHERE id = ?", (req.value, req.id))
        conn.commit()
        conn.close()
        return {"success": True, "id": req.id, "field": req.field, "value": req.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/inventory/item")
async def add_inventory_item(req: NewInventoryItemRequest):
    item_id = req.id or f"INV-{req.location}-{datetime.datetime.now().strftime('%M%S')}"
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO noto_inventory_items 
        (id, location, name, category, par_level, upstairs, downstairs, banquet_a, banquet_b, patio, cellar_bin, storeroom, distributor, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, req.location, req.name, req.category, req.par_level, req.upstairs, req.downstairs, 
              req.banquet_a, req.banquet_b, req.patio, req.cellar_bin, req.storeroom, req.distributor, req.status))
        conn.commit()
        conn.close()
        return {"success": True, "id": item_id, "item": req.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/inventory/{item_id}")
async def delete_inventory_item(item_id: str):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM noto_inventory_items WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return {"success": True, "id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Barback Dispatch ───
@router.get("/dispatch")
async def get_dispatch_queue(location: str = Query("ALL")):
    try:
        conn = get_db()
        cur = conn.cursor()
        if location != "ALL":
            cur.execute("SELECT * FROM noto_dispatch_queue WHERE location = ? ORDER BY time DESC", (location,))
        else:
            cur.execute("SELECT * FROM noto_dispatch_queue ORDER BY time DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"queue": rows}
    except Exception as e:
        return {"queue": [], "error": str(e)}

@router.post("/dispatch")
async def create_dispatch(req: NewDispatchRequest):
    disp_id = f"DISP-{datetime.datetime.now().strftime('%f')[:4]}"
    now_time = datetime.datetime.now().strftime("%I:%M %p")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO noto_dispatch_queue (id, location, target_bar, item, source_loc, time, requested_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (disp_id, req.location, req.target_bar, req.item, req.source_loc, now_time, req.requested_by))
        conn.commit()
        conn.close()
        return {"success": True, "id": disp_id, "time": now_time}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dispatch/status")
async def update_dispatch_status(req: DispatchStatusRequest):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE noto_dispatch_queue SET status = ? WHERE id = ?", (req.status, req.id))
        conn.commit()
        conn.close()
        return {"success": True, "id": req.id, "status": req.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── SOS Calls ───
@router.get("/sos")
async def get_sos_calls(location: str = Query("ALL")):
    try:
        conn = get_db()
        cur = conn.cursor()
        if location != "ALL":
            cur.execute("SELECT * FROM noto_sos_calls WHERE location = ? ORDER BY time DESC", (location,))
        else:
            cur.execute("SELECT * FROM noto_sos_calls ORDER BY time DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"calls": rows}
    except Exception as e:
        return {"calls": [], "error": str(e)}

@router.post("/sos")
async def create_sos_call(req: NewSosRequest):
    sos_id = f"SOS-{datetime.datetime.now().strftime('%M%S')}"
    now_time = datetime.datetime.now().strftime("%I:%M %p")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO noto_sos_calls (id, location, bar, type, urgency, time)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (sos_id, req.location, req.bar, req.type, req.urgency, now_time))
        conn.commit()
        conn.close()
        return {"success": True, "id": sos_id, "time": now_time}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sos/{sos_id}")
async def resolve_sos_call(sos_id: str):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM noto_sos_calls WHERE id = ?", (sos_id,))
        conn.commit()
        conn.close()
        return {"success": True, "id": sos_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── 86 Board ───
@router.get("/86")
async def get_86_board(location: str = Query("ALL")):
    try:
        conn = get_db()
        cur = conn.cursor()
        if location != "ALL":
            cur.execute("SELECT * FROM noto_86_board WHERE location = ? ORDER BY time DESC", (location,))
        else:
            cur.execute("SELECT * FROM noto_86_board ORDER BY time DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"items": rows}
    except Exception as e:
        return {"items": [], "error": str(e)}

@router.post("/86")
async def add_86_item(req: New86Request):
    item_id = f"86-{datetime.datetime.now().strftime('%M%S')}"
    now_time = datetime.datetime.now().strftime("%I:%M %p")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO noto_86_board (id, location, item, station, reason, alt_suggestion, time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, req.location, req.item, req.station, req.reason, req.alt_suggestion or "", now_time))
        conn.commit()
        conn.close()
        return {"success": True, "id": item_id, "time": now_time}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/86/{item_id}")
async def remove_86_item(item_id: str):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM noto_86_board WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        return {"success": True, "id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def init_module(app):
    print("[Module: NotosHospitality] Initialized successfully with SQLite persistence.")
