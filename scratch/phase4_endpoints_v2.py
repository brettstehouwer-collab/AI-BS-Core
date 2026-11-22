#!/usr/bin/env python3
"""
PHASE 4, STAGES 2 & 3: INTEGRATED FASTAPI ENDPOINTS
Combines disk lifecycle (Stage 2) and visual buffer (Stage 3)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import asyncio
import threading

from hypervisor_controller_daemon import (
    get_hypervisor_controller,
    VMConfig,
)
from disk_image_manager_v2 import (
    get_disk_image_manager_v2,
    DiskImageSpec,
)
try:
    from vnc_buffer_bridge_daemon import get_vnc_bridge_daemon
except ImportError:
    def get_vnc_bridge_daemon():
        raise Exception("vnc_buffer_bridge_daemon module is missing (likely compiled to vnc_bridge.exe). VNC status is handled externally.")

router = APIRouter(prefix="/api/phase4", tags=["Phase 4: Virtualization"])


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2: DISK LIFECYCLE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class CreateDiskRequest(BaseModel):
    name: str
    size_mb: int = 1024
    task_id: str = ""
    persistent: bool = False


class CloneDiskRequest(BaseModel):
    source_volume: str
    task_id: str


class AttachDiskRequest(BaseModel):
    volume_name: str
    vm_id: str
    container_id: str
    mount_path: str = "/mnt/data"


@router.post("/disk/create")
async def create_disk(request: CreateDiskRequest):
    """Create a new virtual disk image"""
    try:
        manager = get_disk_image_manager_v2()
        
        spec = DiskImageSpec(
            name=request.name,
            size_mb=request.size_mb,
            task_id=request.task_id,
            persistent=request.persistent,
        )
        
        result = manager.create_image(spec)
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disk/{volume_name}/clone")
async def clone_disk(volume_name: str, request: CloneDiskRequest):
    """Clone an existing disk for a new task"""
    try:
        manager = get_disk_image_manager_v2()
        result = manager.clone_image(volume_name, request.task_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disk/{volume_name}/attach")
async def attach_disk(volume_name: str, request: AttachDiskRequest):
    """Attach a disk to a running VM"""
    try:
        manager = get_disk_image_manager_v2()
        result = manager.attach_disk_to_vm(
            volume_name,
            request.vm_id,
            request.container_id,
            request.mount_path,
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disk/{volume_name}/detach")
async def detach_disk(volume_name: str):
    """Detach a disk from a VM"""
    try:
        manager = get_disk_image_manager_v2()
        result = manager.detach_disk(volume_name)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disk/{volume_name}")
async def get_disk_info(volume_name: str):
    """Get information about a disk"""
    try:
        manager = get_disk_image_manager_v2()
        result = manager.get_disk_info(volume_name)
        
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Disk {volume_name} not found")
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/disk/list")
async def list_disks():
    """List all disk images"""
    try:
        manager = get_disk_image_manager_v2()
        result = manager.list_images()
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disk/{volume_name}/cleanup")
async def cleanup_disk(volume_name: str, force: bool = False):
    """Delete a disk image"""
    try:
        manager = get_disk_image_manager_v2()
        result = manager.cleanup_image(volume_name, force=force)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        if result.get("status") == "protected":
            raise HTTPException(status_code=409, detail=result.get("error"))
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3: VNC VISUAL BUFFER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/vnc/status")
async def vnc_bridge_status():
    """Get VNC bridge status"""
    try:
        daemon = get_vnc_bridge_daemon()
        
        return {
            "status": "operational",
            "bridge_port": daemon.bridge_port,
            "active_sessions": len(daemon.sessions),
            "sessions": {
                vm_id: {
                    "vnc_host": session.vnc_host,
                    "vnc_port": session.vnc_port,
                    "active": session.active,
                    "clients": len(session.websocket_clients),
                }
                for vm_id, session in daemon.sessions.items()
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/vnc/start-bridge")
async def start_vnc_bridge_background(background_tasks: BackgroundTasks):
    """Start the VNC bridge server"""
    try:
        daemon = get_vnc_bridge_daemon()
        
        # Run in background thread
        def run_bridge():
            asyncio.new_event_loop().run_until_complete(daemon.start_bridge())
        
        thread = threading.Thread(target=run_bridge, daemon=True)
        thread.start()
        
        return {
            "status": "started",
            "bridge_port": daemon.bridge_port,
            "ws_endpoint": f"ws://localhost:{daemon.bridge_port}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATED HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status")
async def phase4_status():
    """Get complete Phase 4 status (Stage 1, 2, 3)"""
    try:
        controller = get_hypervisor_controller()
        disk_manager = get_disk_image_manager_v2()
        vnc_daemon = get_vnc_bridge_daemon()
        
        vm_list = controller.list_vms()
        disk_list = disk_manager.list_images()
        vnc_status = vnc_daemon.sessions
        
        return {
            "status": "operational",
            "stage1_vms": {
                "active": vm_list["count"],
                "vms": vm_list["vms"],
            },
            "stage2_disks": {
                "total": disk_list["count"],
                "disks": disk_list["images"],
            },
            "stage3_vnc": {
                "bridge_port": vnc_daemon.bridge_port,
                "active_sessions": len(vnc_status),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
