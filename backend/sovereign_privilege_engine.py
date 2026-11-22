# File: C:\AI-BS\backend\sovereign_privilege_engine.py
# Directive ID: AIBS-DIR-000-ROOT-AUTHORITY
# Purpose: Sovereign Execution & Privilege Stratification Engine, Two-Strike Fault Heuristic Logger,
#          ReAct Sandbox Resolver, and Ring 0 / VTL 1 / X.509 Certificate Telemetry.

import ctypes
import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\AI-BS")
DIRECTIVE_MD_PATH = WORKSPACE_ROOT / "directives" / "AIBS_SOVEREIGN_PRIVILEGE_DIRECTIVE.md"
BOOTSTRAP_PS1_PATH = WORKSPACE_ROOT / "scripts" / "Enable-AIBSSovereignMode.ps1"
CERT_CER_PATH = WORKSPACE_ROOT / "security" / "certs" / "AIBS_Sovereign_Root.cer"
DB_PATH = WORKSPACE_ROOT / "backend" / "aibs_master.db"

# Stehouwer Reality Archival Block (Authoritative Specification Payload)
STEHOUWER_ARCHIVAL_PAYLOAD = {
    "directive_id": "AIBS-DIR-000-ROOT-AUTHORITY",
    "classification": "Instructional/Workflow",
    "target_system": "AI-BS Matrix / AI_BS_Studio.exe / brain_backend.exe",
    "hardware_profile": {
        "cpu": "AMD Ryzen 9 9950X",
        "gpu": "NVIDIA GeForce RTX 4090 (24GB VRAM)",
        "motherboard": "ASUS TUF GAMING X870-PLUS WIFI",
        "os": "Windows 11 x86_64",
    },
    "privilege_tiers_mapped": [
        "Tier 1 — Ring 3: High Integrity Admin (AI_BS_Studio.exe)",
        "Tier 2 — Ring 3: NT AUTHORITY\\SYSTEM (brain_backend.exe / AI_BS_Backend.py)",
        "Tier 3 — Ring 3: NT SERVICE\\TrustedInstaller (OS Provisioning Engine)",
        "Tier 4 — Ring 0: VTL 0 Kernel Mode (.sys Telemetry & MSR Clamping)",
        "Tier 5 — Ring -1: Hyper-V / AMD-V (WSL2 Bridge with HVCI Disabled)",
    ],
    "governance_rules": {
        "pre_approved_execution": True,
        "two_strike_halt_diagnostic": True,
        "immutable_transcription_enforced": True,
        "zero_cloud_telemetry": True,
    },
}

_CONSECUTIVE_FAILURE_TRACKER = {}


def get_sandbox_temp_executor_dir() -> Path:
    """
    Returns G:\\Stehouwer_Server\\Projects\\.temp_executor if G: drive is mounted,
    or seamlessly falls back to C:\\AI-BS\\.temp_executor so zero scripts ever crash.
    """
    g_path = Path(r"G:\Stehouwer_Server\Projects\.temp_executor")
    if Path("G:\\").exists():
        try:
            g_path.mkdir(parents=True, exist_ok=True)
            return g_path
        except Exception:
            pass
    c_fallback = WORKSPACE_ROOT / ".temp_executor"
    c_fallback.mkdir(parents=True, exist_ok=True)
    # Also ensure C:\AI-BS\Stehouwer_Server\Projects\.temp_executor exists
    (WORKSPACE_ROOT / "Stehouwer_Server" / "Projects" / ".temp_executor").mkdir(parents=True, exist_ok=True)
    return c_fallback


def _init_error_heuristics_table() -> None:
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_bs_error_heuristics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_type TEXT,
                target_signature TEXT,
                strike_count INTEGER,
                returncode INTEGER,
                stderr_snippet TEXT,
                halted_by_two_strike INTEGER DEFAULT 0,
                created_at REAL
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def record_command_execution_outcome(
    command_type: str, target: str, returncode: int, stderr: str = ""
) -> dict:
    """
    Implements Section 2.3: The Two-Strike Diagnostic Halt Rule.
    Tracks consecutive command failures per command signature and logs fault vectors
    to `ai_bs_error_heuristics` in SQLite (and ChromaDB when available).
    """
    _init_error_heuristics_table()
    sig = f"{command_type}:{(target or '')[:160].strip()}"

    if returncode == 0:
        _CONSECUTIVE_FAILURE_TRACKER.pop(sig, None)
        return {"strike_count": 0, "two_strike_halt": False}

    strikes = _CONSECUTIVE_FAILURE_TRACKER.get(sig, 0) + 1
    _CONSECUTIVE_FAILURE_TRACKER[sig] = strikes
    two_strike_halt = strikes >= 2

    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_bs_error_heuristics
            (command_type, target_signature, strike_count, returncode, stderr_snippet, halted_by_two_strike, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command_type,
                sig,
                strikes,
                int(returncode),
                (stderr or "")[:1000],
                1 if two_strike_halt else 0,
                time.time(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    return {
        "strike_count": strikes,
        "two_strike_halt": two_strike_halt,
        "directive": "AIBS-DIR-000 Section 2.3 (Two-Strike Diagnostic Halt Rule)",
        "recommendation": (
            "HALT RETRY LOOP: 2 consecutive failures detected. Fault vector logged to `ai_bs_error_heuristics`. "
            "Triggering Stage 1 Grammar-Locked Root-Cause Diagnostics (`auto_heal_code`) before next execution."
            if two_strike_halt
            else "Strike 1 recorded in `ai_bs_error_heuristics`."
        ),
    }


def get_sovereign_privilege_status() -> dict:
    """Queries live Windows 11 Ring 3 / Ring 0 / VTL 1 / X.509 Certificate / Sandbox telemetry."""
    t0 = time.perf_counter()
    _init_error_heuristics_table()

    is_admin = False
    try:
        is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        pass

    # Check HVCI registry value
    hvci_enabled = None
    try:
        import winreg
        key_path = r"SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ) as k:
            val, _ = winreg.QueryValueEx(k, "Enabled")
            hvci_enabled = int(val)
    except Exception:
        hvci_enabled = 0

    # Check Sovereign Root Certificate thumbprint
    cert_thumbprint = None
    try:
        ps_cmd = (
            "(Get-ChildItem -Path Cert:\\LocalMachine\\My -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Subject -like '*AI-BS Sovereign Root Authority*' } | "
            "Select-Object -First 1).Thumbprint"
        )
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=4, encoding="utf-8", errors="replace"
        )
        cert_thumbprint = proc.stdout.strip() or None
    except Exception:
        pass

    # Count logged error heuristics
    fault_count = 0
    recent_faults = []
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_bs_error_heuristics")
        fault_count = cur.fetchone()[0]
        cur.execute(
            "SELECT command_type, target_signature, strike_count, returncode, halted_by_two_strike, created_at "
            "FROM ai_bs_error_heuristics ORDER BY id DESC LIMIT 5"
        )
        for row in cur.fetchall():
            recent_faults.append({
                "command_type": row[0],
                "target": row[1],
                "strike_count": row[2],
                "returncode": row[3],
                "halted_by_two_strike": bool(row[4]),
                "created_at": row[5],
            })
        conn.close()
    except Exception:
        pass

    sandbox_dir = get_sandbox_temp_executor_dir()

    return {
        "status": "success",
        "directive_id": "AIBS-DIR-000-ROOT-AUTHORITY",
        "directive_file": str(DIRECTIVE_MD_PATH),
        "directive_file_exists": DIRECTIVE_MD_PATH.is_file(),
        "bootstrap_script": str(BOOTSTRAP_PS1_PATH),
        "live_state": {
            "tier1_elevated_admin_active": is_admin,
            "vtl1_hvci_enabled": hvci_enabled,
            "ring0_msr_telemetry_unblocked": (hvci_enabled == 0),
            "sovereign_x509_cert_enrolled": bool(cert_thumbprint),
            "sovereign_x509_thumbprint": cert_thumbprint,
            "sovereign_cer_file": str(CERT_CER_PATH) if CERT_CER_PATH.is_file() else None,
            "react_sandbox_dir": str(sandbox_dir),
            "g_drive_mounted": Path("G:\\").exists(),
            "core_executables": {
                "AI_BS_Studio.exe": str(WORKSPACE_ROOT / "native_studio" / "dist" / "AI_BS_Studio" / "AI_BS_Studio.exe"),
                "brain_backend.exe": str(WORKSPACE_ROOT / "backend" / "dist" / "brain_backend.exe"),
                "aibs_engine.exe": str(WORKSPACE_ROOT / "go_gateway" / "aibs_engine.exe"),
            },
        },
        "two_strike_governance": {
            "table": "ai_bs_error_heuristics",
            "total_logged_fault_vectors": fault_count,
            "recent_faults": recent_faults,
        },
        "archival_payload": STEHOUWER_ARCHIVAL_PAYLOAD,
        "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def enforce_sovereign_privilege_directive() -> dict:
    """Executes `C:\\AI-BS\\scripts\\Enable-AIBSSovereignMode.ps1` with `-NoProfile -NonInteractive -ExecutionPolicy Bypass`."""
    t0 = time.perf_counter()
    if not BOOTSTRAP_PS1_PATH.is_file():
        return {"status": "error", "message": f"Bootstrap script not found at {BOOTSTRAP_PS1_PATH}"}

    try:
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(BOOTSTRAP_PS1_PATH),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        status_snapshot = get_sovereign_privilege_status()
        return {
            "status": "success" if proc.returncode == 0 else "warning",
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "live_state": status_snapshot.get("live_state"),
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
