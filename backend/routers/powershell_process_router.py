import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.powershell_process_engine import PowerShellProcessEngine

router = APIRouter(prefix="/api/v1/system/powershell", tags=["PowerShell & Process Maintenance"])


class PowerShellRequest(BaseModel):
    command: str = Field(..., description="PowerShell command string to execute")
    execution_policy: Optional[str] = Field("Bypass", description="PowerShell execution policy: Bypass, RemoteSigned, Unrestricted")
    timeout_seconds: Optional[int] = Field(120, description="Execution timeout in seconds")
    working_directory: Optional[str] = Field(r"C:\AI-BS", description="Working directory")


class ChromeSyncRequest(BaseModel):
    action: Optional[str] = Field("status", description="'status', 'unlock', or 'sync'")
    profile_name: Optional[str] = Field(None, description="Specific profile name e.g. 'Default'")


class DirectoryInspectRequest(BaseModel):
    target_dir: Optional[str] = Field(r"C:\AI-BS", description="Target directory to inspect")


@router.post("/execute")
async def execute_powershell_endpoint(req: PowerShellRequest):
    """
    Executes elevated PowerShell scripts targeting ExecutionPolicy Bypass with real-time capture.
    """
    res = PowerShellProcessEngine.execute_powershell(
        command_or_script=req.command,
        execution_policy=req.execution_policy or "Bypass",
        timeout_seconds=req.timeout_seconds or 120,
        working_directory=req.working_directory or r"C:\AI-BS"
    )
    return res


@router.post("/chrome/profiles")
async def manage_chrome_profiles_endpoint(req: ChromeSyncRequest):
    """
    Inspects, unlocks, and reconciles background Google Chrome profiles and session locks.
    """
    return PowerShellProcessEngine.manage_chrome_profiles(
        action=req.action or "status",
        profile_name=req.profile_name
    )


@router.post("/directory/inspect")
async def inspect_directory_endpoint(req: DirectoryInspectRequest):
    """
    Inspects directory state, file counts, disk usage, and 4-mirror parity.
    """
    return PowerShellProcessEngine.inspect_directory_state(target_dir=req.target_dir or r"C:\AI-BS")


@router.get("/ecosystem/ports")
async def get_ecosystem_ports():
    """
    Returns active PIDs and processes listening on the 18-port collision matrix.
    """
    return PowerShellProcessEngine.list_ecosystem_processes()
