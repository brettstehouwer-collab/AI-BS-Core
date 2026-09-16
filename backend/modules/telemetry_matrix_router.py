import os
import psutil
import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, Query
from modules.user_session_telemetry import user_telemetry_engine

router = APIRouter(prefix="/api/telemetry", tags=["Universal Creation Suite Telemetry"])


class SessionHeartbeatRequest(BaseModel):
    session_id: str
    user_email: str
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    user_role: Optional[str] = None
    current_tab: str = "dashboard"
    activity_label: Optional[str] = None
    client_platform: str = "Desktop Windows"
    dwell_seconds: Optional[float] = None


class SessionCloseRequest(BaseModel):
    session_id: str
    exit_tab: Optional[str] = None
    duration_seconds: Optional[float] = None


class SyncUsersRequest(BaseModel):
    users: List[Dict[str, Any]]


@router.get("/matrix")
def get_telemetry_matrix():
    """Returns multi-layer live telemetry data for the Input Matrix."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net_io = psutil.net_io_counters()
    active_processes = len(psutil.pids())

    return {
        "status": "success",
        "timestamp": time.time(),
        "matrix": {
            "hardware": {
                "cpu_percent": cpu_percent,
                "ram_percent": memory.percent,
                "ram_available_mb": round(memory.available / (1024 * 1024), 2),
                "disk_percent": disk.percent,
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
            },
            "system": {
                "active_processes": active_processes,
                "uptime": time.time() - psutil.boot_time(),
            },
            "sensors": {
                "CO2": cpu_percent * 10,
                "TEMP": 30 + (cpu_percent * 0.5),
                "MFC": memory.percent,
            },
        },
    }


# ─── Live User Presence & Session Audit Telemetry ──────────────────────────────

@router.post("/user-sessions/heartbeat")
def record_user_heartbeat(payload: SessionHeartbeatRequest):
    """
    Receives live user heartbeats from any client running AI-BS.
    Tracks live online state, dwell time, current tab, and activity.
    """
    return user_telemetry_engine.record_heartbeat(
        session_id=payload.session_id,
        user_email=payload.user_email,
        user_name=payload.user_name,
        user_avatar=payload.user_avatar,
        user_role=payload.user_role,
        current_tab=payload.current_tab,
        activity_label=payload.activity_label,
        client_platform=payload.client_platform,
        dwell_seconds=payload.dwell_seconds
    )


@router.post("/user-sessions/close")
def close_user_session(payload: SessionCloseRequest):
    """
    Called upon window.beforeunload or tab exit to record final duration and exit tab.
    """
    return user_telemetry_engine.close_session(
        session_id=payload.session_id,
        exit_tab=payload.exit_tab,
        duration_seconds=payload.duration_seconds
    )


@router.get("/user-sessions/summary")
def get_user_sessions_summary():
    """
    Returns complete real-time user presence & session audit summary:
    - Currently active live users with dwell times & current activities
    - Last seen timestamp, duration, and exit activity for every team member
    - Chronological recent sessions history with open/close timestamps
    - Aggregated time spent analytics per user
    """
    return user_telemetry_engine.get_summary()


@router.post("/user-sessions/sync-users")
def sync_authorized_users(payload: SyncUsersRequest):
    """
    Syncs authorized users saved in Firebase Firestore to the local SQLite telemetry database.
    Ensures any and all team members or authorized users appear in telemetry widgets and filters.
    """
    return user_telemetry_engine.sync_authorized_users(payload.users)
