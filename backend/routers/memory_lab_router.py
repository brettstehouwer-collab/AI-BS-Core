"""
AI-BS Process Instrumentation & Gaming Lab Router
Enables real-time Win32 process discovery, memory inspection, pointer tracking,
and game trainer profile execution from the AI-BS dashboard.
"""

import sys
import os
import psutil
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel

# Add root directory to sys.path for game_trainer imports
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from game_trainer.core.memory import MemoryManager
from game_trainer.profiles.btd6_profile import BTD6Trainer

logger = logging.getLogger("MemoryLabRouter")
router = APIRouter(prefix="/api/memory-lab", tags=["Process Memory & Gaming Lab"])

# Multi-Tenant isolation dependency
def get_tenant(x_client_id: Optional[str] = Header(default="stehouwer_publishing")) -> str:
    return x_client_id or "stehouwer_publishing"


# Singleton instances for persistent web session
active_mem_mgr: Optional[MemoryManager] = None
active_btd6_trainer: Optional[BTD6Trainer] = None


# -----------------------------------------------------------------------------
# Request / Response Models
# -----------------------------------------------------------------------------

class AttachRequest(BaseModel):
    target: str # PID as str or process name (e.g. "BloonsTD6.exe" or "12345")

class ReadMemoryRequest(BaseModel):
    address: str # hex string (e.g. "0x7FF6B0C40000") or decimal string
    data_type: str = "int32" # int32, uint32, int64, float, double, string, hex
    length: int = 4

class WriteMemoryRequest(BaseModel):
    address: str
    data_type: str = "int32"
    value: str # parsed according to data_type

class ProfileActionRequest(BaseModel):
    profile_id: str # "btd6" or "mock_titan"
    feature_name: str
    action: str = "toggle" # "toggle" or "trigger"
    value: Optional[str] = None

class ScanCashRequest(BaseModel):
    current_cash: Optional[float] = None

class FilterCashRequest(BaseModel):
    current_cash: float

class SetCashRequest(BaseModel):
    value: float = 99999.0

class ScanCoinsRequest(BaseModel):
    current_coins: int = 99999

class SetCoinsRequest(BaseModel):
    value: int = 99999



# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/processes")
def list_processes(search: Optional[str] = None, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Returns top active Windows processes with PID, name, and memory footprint."""
    procs = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                name = p.info['name'] or ""
                if search and search.lower() not in name.lower():
                    continue
                mem_mb = round((p.info['memory_info'].rss if p.info['memory_info'] else 0) / (1024 * 1024), 1)
                procs.append({
                    "pid": p.info['pid'],
                    "name": name,
                    "memory_mb": mem_mb
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # Sort by memory usage descending
        procs.sort(key=lambda x: x["memory_mb"], reverse=True)
    except Exception as e:
        logger.error(f"Error enumerating processes: {e}")
    return {"status": "success", "count": len(procs), "processes": procs[:100]}


@router.post("/attach")
def attach_process(req: AttachRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Attaches memory manager to target process name or PID."""
    global active_mem_mgr, active_btd6_trainer
    target = req.target.strip()

    try:
        target_val = int(target) if target.isdigit() else target
        mgr = MemoryManager(target_val)
        active_mem_mgr = mgr

        # If attaching to BloonsTD6.exe, initialize BTD6 trainer instance
        if "bloonstd6" in str(target).lower():
            active_btd6_trainer = BTD6Trainer(target_pid=mgr.pid)
            active_btd6_trainer.setup()
            active_btd6_trainer.start()

        return {
            "status": "success",
            "message": f"Attached to {target}",
            "pid": mgr.pid,
            "process_name": mgr.process_name,
            "base_address": hex(mgr.base_address),
            "is_64bit": mgr.is_64bit
        }
    except Exception as e:
        logger.error(f"Failed to attach to process '{target}': {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
def get_memory_status(tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Returns current active attachment and trainer status, auto-attaching to BloonsTD6 if running."""
    global active_mem_mgr, active_btd6_trainer
    attached = active_mem_mgr is not None and active_mem_mgr.is_alive()

    # Auto-detect BloonsTD6.exe if running and not yet attached
    if not attached:
        try:
            candidate = BTD6Trainer()
            if candidate.setup():
                candidate.start()
                active_btd6_trainer = candidate
                active_mem_mgr = candidate.mem
                attached = True
        except Exception as e:
            logger.debug(f"Auto-detection check error: {e}")

    trainer_status = None
    if active_btd6_trainer and active_btd6_trainer.mem.is_alive():
        trainer_status = active_btd6_trainer.get_status_dict()

    return {
        "status": "success",
        "attached": attached,
        "pid": active_mem_mgr.pid if attached else None,
        "process_name": active_mem_mgr.process_name if attached else None,
        "base_address": hex(active_mem_mgr.base_address) if attached else "0x0",
        "is_64bit": active_mem_mgr.is_64bit if attached else True,
        "btd6_trainer": trainer_status
    }


@router.post("/read")
def read_memory(req: ReadMemoryRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Reads typed data or raw bytes from a specified memory address."""
    global active_mem_mgr
    if not active_mem_mgr or not active_mem_mgr.is_alive():
        raise HTTPException(status_code=400, detail="No active process attached.")

    try:
        addr = int(req.address, 0)
        dt = req.data_type.lower()
        val = None

        if dt == "int32":
            val = active_mem_mgr.read_int32(addr)
        elif dt == "uint32":
            val = active_mem_mgr.read_uint32(addr)
        elif dt == "int64":
            val = active_mem_mgr.read_int64(addr)
        elif dt == "float":
            val = round(active_mem_mgr.read_float(addr), 4)
        elif dt == "double":
            val = round(active_mem_mgr.read_double(addr), 4)
        elif dt == "string":
            val = active_mem_mgr.read_string(addr, max_length=req.length)
        elif dt == "hex":
            raw = active_mem_mgr.read_bytes(addr, req.length)
            val = raw.hex().upper()
        else:
            raise ValueError(f"Unsupported data type: {dt}")

        return {
            "status": "success",
            "address": hex(addr),
            "data_type": dt,
            "value": val
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Memory read error: {str(e)}")


@router.post("/write")
def write_memory(req: WriteMemoryRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Writes typed data to a specified memory address."""
    global active_mem_mgr
    if not active_mem_mgr or not active_mem_mgr.is_alive():
        raise HTTPException(status_code=400, detail="No active process attached.")

    try:
        addr = int(req.address, 0)
        dt = req.data_type.lower()
        success = False

        if dt == "int32":
            success = active_mem_mgr.write_int32(addr, int(req.value))
        elif dt == "uint32":
            success = active_mem_mgr.write_uint32(addr, int(req.value))
        elif dt == "int64":
            success = active_mem_mgr.write_int64(addr, int(req.value))
        elif dt == "float":
            success = active_mem_mgr.write_float(addr, float(req.value))
        elif dt == "double":
            success = active_mem_mgr.write_double(addr, float(req.value))
        elif dt == "string":
            success = active_mem_mgr.write_bytes(addr, req.value.encode('utf-8') + b'\x00')
        elif dt == "hex":
            raw = bytes.fromhex(req.value.replace(" ", ""))
            success = active_mem_mgr.write_bytes(addr, raw, unprotect=True)
        else:
            raise ValueError(f"Unsupported data type: {dt}")

        return {
            "status": "success" if success else "failed",
            "address": hex(addr),
            "data_type": dt,
            "written": success
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Memory write error: {str(e)}")


@router.get("/profiles")
def get_profiles(tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Returns catalog of pre-configured game & automation trainer profiles."""
    return {
        "status": "success",
        "profiles": [
            {
                "id": "btd6",
                "name": "Bloons TD 6 (Unity IL2CPP)",
                "executable": "BloonsTD6.exe",
                "category": "Single-Player Gaming",
                "quick_keys": [
                    {"key": "NUMPAD 1", "action": "Unlimited Match Cash", "description": "Freezes match money at $9,999,999.0"},
                    {"key": "NUMPAD 2", "action": "Unlimited Match Lives", "description": "Freezes single-player lives at 99,999"},
                    {"key": "NUMPAD 3", "action": "Add $50,000 Cash", "description": "Instantly increments in-game cash by $50,000"},
                    {"key": "NUMPAD 4", "action": "Zero-Cost Placement", "description": "Patches tower placement subtraction to $0"},
                    {"key": "NUMPAD 5", "action": "Instant Ability Cooldowns", "description": "Resets hero and tower active timers"},
                    {"key": "NUMPAD 0", "action": "Reset & Restore", "description": "Disables active cheats and restores normal code"}
                ]
            },
            {
                "id": "mock_titan",
                "name": "Titan Arena (Built-in Mock Target)",
                "executable": "python.exe (target_sandbox.py)",
                "category": "Education & Sandbox",
                "quick_keys": [
                    {"key": "NUMPAD 1", "action": "Infinite Health", "description": "Locks health at 9999 HP"},
                    {"key": "NUMPAD 2", "action": "Infinite Ammo", "description": "Locks weapon ammo at 999"},
                    {"key": "NUMPAD 3", "action": "Add 50,000 Score", "description": "Adds 50,000 points"},
                    {"key": "NUMPAD 4", "action": "Max Overshield", "description": "Locks shield at 200"},
                    {"key": "NUMPAD 5", "action": "Native Invulnerability", "description": "Toggles internal boolean flag"}
                ]
            }
        ]
    }


@router.post("/profile/action")
def trigger_profile_action(req: ProfileActionRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Triggers or toggles a trainer profile feature via the web UI."""
    global active_btd6_trainer

    if req.profile_id == "btd6":
        if not active_btd6_trainer or not active_btd6_trainer.mem.is_alive():
            raise HTTPException(status_code=400, detail="BloonsTD6.exe is not currently attached.")

        # Find matching feature
        matched = False
        target_name = req.feature_name.lower()
        for feat in active_btd6_trainer.features.values():
            if target_name in feat.name.lower():
                feat.toggle()
                matched = True
                return {
                    "status": "success",
                    "feature": feat.name,
                    "enabled": feat.enabled,
                    "action": "toggled" if feat.is_toggle else "triggered"
                }

        if not matched:
            raise HTTPException(status_code=404, detail=f"Feature '{req.feature_name}' not found.")

    raise HTTPException(status_code=400, detail=f"Profile '{req.profile_id}' not active.")


@router.post("/detach")
def detach_process(tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Detaches memory manager and restores all original bytes."""
    global active_mem_mgr, active_btd6_trainer
    if active_btd6_trainer:
        active_btd6_trainer.stop()
        active_btd6_trainer = None
    if active_mem_mgr:
        active_mem_mgr.detach()
        active_mem_mgr = None
    return {"status": "success", "message": "Memory manager detached cleanly."}


@router.post("/scan-cash")
def scan_match_cash(req: ScanCashRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Auto-scans or first-scans for exact match cash in BloonsTD6.exe."""
    global active_btd6_trainer, active_mem_mgr
    if not active_btd6_trainer or not active_btd6_trainer.mem.is_alive():
        try:
            active_btd6_trainer = BTD6Trainer()
            if not active_btd6_trainer.setup():
                raise HTTPException(status_code=400, detail="BloonsTD6.exe is not currently running.")
            active_btd6_trainer.start()
            active_mem_mgr = active_btd6_trainer.mem
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to attach: {e}")

    if req.current_cash is not None:
        matches = active_btd6_trainer.first_scan_cash(req.current_cash)
    else:
        matches = active_btd6_trainer.auto_scan_cash()

    return {
        "status": "success",
        "count": len(matches),
        "candidates_count": len(active_btd6_trainer.cash_candidates),
        "locked_addresses": [hex(a) for a in active_btd6_trainer.cash_addresses],
        "current_values": [active_btd6_trainer.mem.read_double(a) for a in active_btd6_trainer.cash_addresses] if active_btd6_trainer.cash_addresses else []
    }


@router.post("/filter-cash")
def filter_match_cash(req: FilterCashRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Filters cash candidates against updated in-game cash value."""
    global active_btd6_trainer
    if not active_btd6_trainer or not active_btd6_trainer.mem.is_alive():
        raise HTTPException(status_code=400, detail="BloonsTD6.exe is not attached.")

    remaining = active_btd6_trainer.next_scan_cash(req.current_cash)
    return {
        "status": "success",
        "candidates_count": len(active_btd6_trainer.cash_candidates),
        "locked_count": len(active_btd6_trainer.cash_addresses),
        "locked_addresses": [hex(a) for a in active_btd6_trainer.cash_addresses],
        "remaining": [hex(a) for a in remaining[:16]]
    }


@router.post("/set-cash")
def set_match_cash(req: SetCashRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Sets match cash value across all locked addresses and activates the freeze loop."""
    global active_btd6_trainer
    if not active_btd6_trainer or not active_btd6_trainer.mem.is_alive():
        raise HTTPException(status_code=400, detail="BloonsTD6.exe is not attached.")

    if not active_btd6_trainer.cash_addresses:
        active_btd6_trainer.auto_scan_cash()

    if not active_btd6_trainer.cash_addresses:
        raise HTTPException(status_code=400, detail="No cash addresses locked. Scan first.")

    active_btd6_trainer.frozen_cash_val = float(req.value)
    for feat in active_btd6_trainer.features.values():
        if "match cash" in feat.name.lower():
            feat.enabled = True
            break

    for addr in active_btd6_trainer.cash_addresses:
        active_btd6_trainer.mem.write_double(addr, req.value)

    return {
        "status": "success",
        "value": req.value,
        "freeze_active": True,
        "updated_addresses": [hex(a) for a in active_btd6_trainer.cash_addresses]
    }


@router.post("/scan-coins")
def scan_coins(req: ScanCoinsRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Scans for Monkey Money (Coins) as int32."""
    global active_btd6_trainer
    if not active_btd6_trainer or not active_btd6_trainer.mem.is_alive():
        raise HTTPException(status_code=400, detail="BloonsTD6.exe is not attached.")

    matches = active_btd6_trainer.auto_scan_coins(req.current_coins)
    return {
        "status": "success",
        "count": len(matches),
        "freeze_active": True,
        "locked_addresses": [hex(a) for a in matches[:8]]
    }


@router.post("/set-coins")
def set_monkey_money(req: SetCoinsRequest, tenant: str = Depends(get_tenant)) -> Dict[str, Any]:
    """Sets Monkey Money across all locked coin addresses to target value (default 99999) and locks freeze loop."""
    global active_btd6_trainer
    if not active_btd6_trainer or not active_btd6_trainer.mem.is_alive():
        raise HTTPException(status_code=400, detail="BloonsTD6.exe is not attached.")

    if not active_btd6_trainer.coins_addresses:
        raise HTTPException(status_code=400, detail="No coin addresses locked. Scan current coins first.")

    active_btd6_trainer.frozen_coins_val = int(req.value)
    for feat in active_btd6_trainer.features.values():
        if "monkey money" in feat.name.lower():
            feat.enabled = True
            break

    for addr in active_btd6_trainer.coins_addresses:
        active_btd6_trainer.mem.write_int32(addr, req.value)

    return {
        "status": "success",
        "value": req.value,
        "freeze_active": True,
        "updated_addresses": [hex(a) for a in active_btd6_trainer.coins_addresses]
    }

