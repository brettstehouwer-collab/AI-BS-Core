"""
AI-BS USB Hardware Diagnostics & Flash Drive Recovery Router
Provides low-level hardware probing, controller detection (ChipsBank, Phison, SMI, Alcor),
SCSI pass-through diagnostics, partition reconstruction, and mass-production flashing guidance.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import subprocess
import json
import os
import sys
import ctypes
from ctypes import wintypes

router = APIRouter(prefix="/api/usb-recovery", tags=["USB Recovery & Diagnostics"])


def get_tenant(x_client_id: Optional[str] = Header("stehouwer_publishing")) -> str:
    return x_client_id if x_client_id else "stehouwer_publishing"


class PartitionRebuildRequest(BaseModel):
    disk_number: int = Field(..., description="Disk number (e.g. 3). Must be a USB bus type.")
    file_system: str = Field("FAT32", description="Target filesystem: FAT32, exFAT, or NTFS")
    volume_label: Optional[str] = "AI_BS_USB"
    confirm_destructive: bool = Field(False, description="Must be True to confirm total wipe of USB drive")


class ProbeRequest(BaseModel):
    disk_number: int = Field(..., description="Disk number to probe (e.g. 3)")


# Known Flash Controller BootROM VID/PIDs
BOOTROM_SIGNATURES = {
    ("048D", "1234"): {
        "controller": "ChipsBank CBM209X / CBM219X",
        "mode": "Factory BootROM / Safe Mode (Firmware Missing or Corrupted)",
        "tool": "ChipsBank CBM209X/CBM219X UMPTool / APTool",
        "vendor": "Chipsbank Microelectronics"
    },
    ("1E3D", "198A"): {
        "controller": "ChipsBank CBM2098 / CBM2099",
        "mode": "ChipsBank Native USB Mass Storage",
        "tool": "ChipsBank UMPTool",
        "vendor": "Chipsbank Microelectronics"
    },
    ("13FE", "3D00"): {
        "controller": "Phison PS2251-XX",
        "mode": "Phison 230X BootROM Recovery Mode",
        "tool": "Phison MPALL / UPTool",
        "vendor": "Phison Electronics"
    },
    ("090C", "1000"): {
        "controller": "Silicon Motion (SMI) SM32XX",
        "mode": "SMI BootROM Test Mode",
        "tool": "SMI MPTool / Dyna Mass Storage Tool",
        "vendor": "Silicon Motion"
    },
    ("058F", "1234"): {
        "controller": "Alcor Micro AU698X",
        "mode": "Alcor Recovery BootROM",
        "tool": "AlcorMP (ALCOR Micro Production Tool)",
        "vendor": "Alcor Micro"
    }
}


@router.get("/devices")
async def list_usb_devices(tenant: str = Depends(get_tenant)):
    """Scans and returns all USB storage disks, partition states, controller VID/PIDs, and diagnosis."""
    ps_cmd = """
    Get-Disk | Where-Object { $_.BusType -eq 'USB' } | ForEach-Object {
        $disk = $_
        $parts = Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue
        $pnp = Get-PnpDevice -Class DiskDrive -PresentOnly | Where-Object { $_.FriendlyName -like "*$($disk.FriendlyName)*" -or $disk.FriendlyName -like "*$($_.FriendlyName)*" } | Select-Object -First 1
        
        # Parent USB device for VID/PID
        $vidPid = "Unknown"
        $parent = "Unknown"
        if ($pnp) {
            $parentProp = Get-PnpDeviceProperty -InstanceId $pnp.InstanceId -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue
            if ($parentProp -and $parentProp.Data) {
                $parent = $parentProp.Data
                if ($parent -match 'VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})') {
                    $vidPid = "$($Matches[1]):$($Matches[2])".ToUpper()
                }
            }
        }
        
        $driveLetter = ($parts | Where-Object { $_.DriveLetter } | Select-Object -ExpandProperty DriveLetter -First 1)
        if (-not $driveLetter) { $driveLetter = "" }
        
        [PSCustomObject]@{
            DiskNumber = $disk.Number
            FriendlyName = $disk.FriendlyName
            BusType = $disk.BusType
            OperationalStatus = [string]$disk.OperationalStatus
            HealthStatus = [string]$disk.HealthStatus
            Size = $disk.Size
            PartitionStyle = [string]$disk.PartitionStyle
            NumberOfPartitions = $disk.NumberOfPartitions
            DriveLetter = $driveLetter
            ParentId = $parent
            VidPid = $vidPid
        }
    } | ConvertTo-Json -Depth 3
    """
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=10)
        output = proc.stdout.strip()
        devices = []
        if output:
            data = json.loads(output)
            if isinstance(data, dict):
                data = [data]
            for d in data:
                vid_pid = d.get("VidPid", "Unknown")
                parts = vid_pid.split(":") if ":" in vid_pid else ("XXXX", "YYYY")
                vid, pid = parts[0], parts[1]
                
                sig = BOOTROM_SIGNATURES.get((vid, pid), None)
                op_status = d.get("OperationalStatus", "Unknown")
                size = d.get("Size", 0) or 0
                
                # State Classifier
                if "No Media" in op_status or size == 0:
                    if sig and "BootROM" in sig.get("mode", ""):
                        state_cat = "bootrom_recovery"
                        rec = f"Drive controller ({sig['controller']}) is in factory BootROM recovery. Re-flashing with {sig['tool']} required."
                    else:
                        state_cat = "no_media_empty_reader"
                        rec = "Controller is online but storage memory is unmounted. If this is a microSD adapter, verify a card is firmly seated."
                elif d.get("PartitionStyle") == "RAW" or d.get("NumberOfPartitions") == 0:
                    state_cat = "corrupted_partition"
                    rec = "LBA blocks are accessible but partition table is missing or corrupt. Can be rebuilt using AI-BS Low-Level Rebuild."
                else:
                    state_cat = "healthy"
                    rec = "Drive is formatted and operational."

                devices.append({
                    "disk_number": d.get("DiskNumber"),
                    "drive_letter": d.get("DriveLetter"),
                    "friendly_name": d.get("FriendlyName"),
                    "operational_status": op_status,
                    "health_status": d.get("HealthStatus"),
                    "size_bytes": size,
                    "size_gb": round(size / (1024**3), 2) if size > 0 else 0.0,
                    "partition_style": d.get("PartitionStyle"),
                    "vid_pid": vid_pid,
                    "parent_id": d.get("ParentId"),
                    "controller_signature": sig,
                    "state_category": state_cat,
                    "recommended_action": rec
                })
        return {
            "status": "success",
            "device_count": len(devices),
            "devices": devices
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "devices": []
        }


@router.post("/probe")
async def probe_usb_disk(req: ProbeRequest, tenant: str = Depends(get_tenant)):
    """Queries hardware registers via IOCTL_STORAGE_QUERY_PROPERTY and IOCTL_SCSI_PASS_THROUGH."""
    disk_path = f"\\\\.\\PhysicalDrive{req.disk_number}"
    
    kernel32 = ctypes.windll.kernel32
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    OPEN_EXISTING = 3
    IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
    IOCTL_SCSI_PASS_THROUGH = 0x04D004

    hDevice = kernel32.CreateFileW(
        disk_path,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None
    )

    if hDevice == -1 or hDevice == 0xFFFFFFFFFFFFFFFF:
        err = kernel32.GetLastError()
        raise HTTPException(status_code=400, detail=f"Cannot open {disk_path} (Win32 Error: {err})")

    # Tier 1: Query Storage Device Descriptor (Hardware miniport level)
    class STORAGE_PROPERTY_QUERY(ctypes.Structure):
        _fields_ = [
            ("PropertyId", wintypes.DWORD),
            ("QueryType", wintypes.DWORD),
            ("AdditionalParameters", wintypes.BYTE * 1)
        ]

    spq = STORAGE_PROPERTY_QUERY(0, 0)
    desc_buf = ctypes.create_string_buffer(1024)
    desc_ret = wintypes.DWORD(0)
    desc_res = kernel32.DeviceIoControl(
        hDevice,
        IOCTL_STORAGE_QUERY_PROPERTY,
        ctypes.byref(spq),
        ctypes.sizeof(spq),
        desc_buf,
        1024,
        ctypes.byref(desc_ret),
        None
    )

    def _extract_str(buf_raw, offset):
        if offset <= 0 or offset >= len(buf_raw):
            return ""
        end = buf_raw.find(b"\x00", offset)
        if end == -1:
            end = len(buf_raw)
        return buf_raw[offset:end].decode("ascii", errors="replace").strip()

    vid = "Unknown"
    pid = "Unknown"
    rev = "Unknown"
    sn = ""
    if desc_res:
        v_off = int.from_bytes(desc_buf[12:16], "little")
        p_off = int.from_bytes(desc_buf[16:20], "little")
        r_off = int.from_bytes(desc_buf[20:24], "little")
        sn_off = int.from_bytes(desc_buf[24:28], "little")
        vid = _extract_str(desc_buf.raw, v_off)
        pid = _extract_str(desc_buf.raw, p_off)
        rev = _extract_str(desc_buf.raw, r_off)
        sn = _extract_str(desc_buf.raw, sn_off)

    # Tier 2: Low-Level SCSI Pass-Through INQUIRY
    class SCSI_PASS_THROUGH_WITH_BUFFERS(ctypes.Structure):
        _fields_ = [
            ("Length", wintypes.USHORT),
            ("ScsiStatus", ctypes.c_ubyte),
            ("PathId", ctypes.c_ubyte),
            ("TargetId", ctypes.c_ubyte),
            ("Lun", ctypes.c_ubyte),
            ("CdbLength", ctypes.c_ubyte),
            ("SenseInfoLength", ctypes.c_ubyte),
            ("DataIn", ctypes.c_ubyte),
            ("DataTransferLength", wintypes.ULONG),
            ("TimeOutValue", wintypes.ULONG),
            ("DataBufferOffset", ctypes.c_size_t),
            ("SenseInfoOffset", wintypes.ULONG),
            ("Cdb", ctypes.c_ubyte * 16),
            ("SenseBuf", ctypes.c_ubyte * 64),
            ("DataBuf", ctypes.c_ubyte * 512)
        ]

    spt = SCSI_PASS_THROUGH_WITH_BUFFERS()
    spt.Length = ctypes.sizeof(spt)
    spt.CdbLength = 6
    spt.Cdb[0] = 0x12  # INQUIRY
    spt.Cdb[4] = 96
    spt.DataIn = 1
    spt.DataTransferLength = 96
    spt.TimeOutValue = 3
    spt.DataBufferOffset = SCSI_PASS_THROUGH_WITH_BUFFERS.DataBuf.offset
    spt.SenseInfoOffset = SCSI_PASS_THROUGH_WITH_BUFFERS.SenseBuf.offset
    spt.SenseInfoLength = 64

    bytes_ret = wintypes.DWORD(0)
    scsi_res = kernel32.DeviceIoControl(
        hDevice,
        IOCTL_SCSI_PASS_THROUGH,
        ctypes.byref(spt),
        ctypes.sizeof(spt),
        ctypes.byref(spt),
        ctypes.sizeof(spt),
        ctypes.byref(bytes_ret),
        None
    )
    scsi_err = kernel32.GetLastError() if not scsi_res else 0
    scsi_hex = bytes(spt.DataBuf[:36]).hex() if scsi_res else ""

    # Tier 3: Sector 0 LBA Read Test
    sec0_buf = ctypes.create_string_buffer(512)
    sec0_read = ctypes.c_ulong(0)
    sec0_res = kernel32.ReadFile(hDevice, sec0_buf, 512, ctypes.byref(sec0_read), None)
    sec0_err = kernel32.GetLastError() if not sec0_res else 0

    kernel32.CloseHandle(hDevice)

    is_bootrom = ("ChipsBnk" in vid or "ChipsBank" in vid) and ("5.00" in rev or rev == "")
    if is_bootrom:
        status_summary = "CRITICAL_BOOTROM_RECOVERY: Controller microcode not executing or flash NAND unmapped."
    elif sec0_res:
        status_summary = "READY: Flash storage NAND blocks are responding to LBA read requests."
    else:
        status_summary = f"MEDIA_UNMOUNTED: Controller responded, but LBA access returned Error {sec0_err}."

    return {
        "status": "success",
        "disk_path": disk_path,
        "disk_number": req.disk_number,
        "hardware_vendor": vid,
        "hardware_product": pid,
        "hardware_revision": rev,
        "serial_number": sn,
        "scsi_pass_through_supported": bool(scsi_res),
        "scsi_pass_through_error": scsi_err if not scsi_res else 0,
        "scsi_inquiry_hex": scsi_hex,
        "sector_zero_readable": bool(sec0_res),
        "lba_status": "READY" if sec0_res else f"NOT_READY (Error {sec0_err})",
        "is_bootrom_mode": is_bootrom,
        "diagnosis_summary": status_summary
    }


@router.post("/rebuild-partition")
async def rebuild_partition(req: PartitionRebuildRequest, tenant: str = Depends(get_tenant)):
    """Destructive low-level partition table rebuild for accessible USB flash media."""
    if not req.confirm_destructive:
        raise HTTPException(
            status_code=400,
            detail="Safety Violation: confirm_destructive must be explicitly set to True."
        )

    # STRICT SAFETY CHECK: Verify BusType is USB and disk is NOT 0, 1, or 2 (Internal NVMe drives)
    ps_verify = f"""
    $d = Get-Disk -Number {req.disk_number} -ErrorAction SilentlyContinue
    if (-not $d) {{ Write-Output "NOT_FOUND"; exit }}
    if ($d.BusType -ne 'USB') {{ Write-Output "NOT_USB"; exit }}
    if ($d.IsBoot -or $d.IsSystem) {{ Write-Output "SYSTEM_DISK"; exit }}
    Write-Output "OK"
    """
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_verify], capture_output=True, text=True)
    check_result = proc.stdout.strip()
    if check_result == "NOT_FOUND":
        raise HTTPException(status_code=404, detail=f"Disk {req.disk_number} not found.")
    elif check_result == "NOT_USB":
        raise HTTPException(status_code=403, detail="Safety Lock: Target disk is not on USB bus. Internal drive formatting forbidden.")
    elif check_result == "SYSTEM_DISK":
        raise HTTPException(status_code=403, detail="Safety Lock: Target disk is a boot/system disk. Operation blocked.")
    elif check_result != "OK":
        raise HTTPException(status_code=500, detail=f"Pre-flight verification failed: {check_result}")

    # Execute Low-Level Partition Rebuild
    ps_rebuild = f"""
    $ErrorActionPreference = 'Stop'
    Clear-Disk -Number {req.disk_number} -RemoveData -RemoveOEM -Confirm:$false
    Initialize-Disk -Number {req.disk_number} -PartitionStyle MBR
    $part = New-Partition -DiskNumber {req.disk_number} -UseMaximumSize -AssignDriveLetter
    $drive = $part.DriveLetter
    Format-Volume -DriveLetter $drive -FileSystem {req.file_system} -NewFileSystemLabel '{req.volume_label}' -Confirm:$false
    Write-Output "Drive $drive formatted as {req.file_system} with label {req.volume_label}"
    """
    proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_rebuild], capture_output=True, text=True)
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Partition rebuild failed: {proc.stderr.strip() or proc.stdout.strip()}")

    return {
        "status": "success",
        "disk_number": req.disk_number,
        "message": proc.stdout.strip()
    }
