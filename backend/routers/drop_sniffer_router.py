"""
AI-BS FastAPI Router for Drop Sniffer & Watchdog Subsystem
Exposes live telemetry, drop history, Hub inventory, and drop card status on Port 8080.
"""

import os
import json
import time
from fastapi import APIRouter, HTTPException, Depends
from drop_sniffer_module.hub_sync import HubSynchronizer

router = APIRouter(prefix="/api/drop-sniffer", tags=["Drop Sniffer & Watchdog Telemetry"])

HEARTBEAT_FILE = r"C:\AI-BS\saved_data\cymatics_heartbeat.json"
DROP_LOG_FILE = r"C:\AI-BS\saved_data\cymatics_drop_log.json"
DISCOVERED_FREE_FILE = r"C:\AI-BS\saved_data\cymatics_discovered_free_drops.json"

hub_sync = HubSynchronizer()

@router.get("/status")
async def get_sniffer_status():
    """Returns live watchdog heartbeat, PID, status, and 5-channel ingestion metrics."""
    if not os.path.exists(HEARTBEAT_FILE):
        return {
            "status": "STOPPED",
            "message": "Heartbeat file not found.",
            "is_alive": False
        }
    try:
        with open(HEARTBEAT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = time.time() - data.get('timestamp', 0)
        data['heartbeat_age_seconds'] = round(age, 2)
        data['is_alive'] = age < 6.0
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drops")
async def get_detected_drops():
    """Returns real-time log of detected and sniped drops."""
    if not os.path.exists(DROP_LOG_FILE):
        return []
    try:
        with open(DROP_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

@router.get("/inventory")
async def get_hub_inventory():
    """Returns parsed Cymatics Hub inventory and exclusion list counts."""
    return hub_sync.get_inventory_summary()

@router.get("/catalog-free")
async def get_free_catalog_drops():
    """Returns discovered 100% free $0.00 items from the storewide feed."""
    if not os.path.exists(DISCOVERED_FREE_FILE):
        return []
    try:
        with open(DISCOVERED_FREE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

@router.get("/cross-check")
async def get_cross_check_matrix():
    """Returns the full unified cross-check matrix (84 Checked Off vs 120 Unclaimed Free)."""
    matrix_file = r"C:\AI-BS\saved_data\cymatics_cross_check_matrix.json"
    if not os.path.exists(matrix_file):
        return []
    try:
        with open(matrix_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []
