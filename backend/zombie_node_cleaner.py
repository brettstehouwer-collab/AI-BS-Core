"""
AI-BS Zombie Node & Orphan Process Cleaner
Scans active processes for true zombies, dead-parent orphans, and defunct workers,
safely reclaiming host RAM while strictly protecting all active AI-BS services and IDE processes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Set
import psutil

# Core services and active engines that must NEVER be killed
PROTECTED_CMDLINE_TOKENS = [
    "ai_bs_backend",
    "ai_bs_studio",
    "native_studio",
    "vite",
    "dev",
    "server.js",
    "shm_websocket_gateway",
    "ollama",
    "comfyui",
    "aibs_broadcast",
    "aibs_social",
    "aibs_vst",
    "aibs_matrix",
    "antigravity",
    "gemini",
    "pytest",
    "comprehensive_interactive_audit",
    "context_ingestor_daemon",
    "compute_monetization_daemon",
    "telemetry_hub",
    "aibs_engine",
]

TARGET_PROCESS_NAMES = {
    "node.exe",
    "node",
    "python.exe",
    "python",
    "pythonw.exe",
    "pythonw",
    "llama-server.exe",
    "t-rex.exe",
    "unrealeditor.exe",
    "ai_bs_hub.exe",
    "gradle",
    "java.exe",
}


def get_active_listening_pids() -> Set[int]:
    """Identify PIDs of processes holding active listening network ports via native fast netstat."""
    active_pids: Set[int] = set()
    try:
        creation_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == 'nt' else 0
        output = subprocess.check_output(
            ["netstat", "-ano", "-p", "tcp"],
            creationflags=creation_flag,
            text=True,
            timeout=3.0,
        )
        for line in output.splitlines():
            if "LISTENING" in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid_str = parts[-1]
                    if pid_str.isdigit():
                        active_pids.add(int(pid_str))
    except Exception:
        pass

    # Always include current process and parent
    active_pids.add(os.getpid())
    if hasattr(os, "getppid"):
        try:
            ppid = os.getppid()
            if ppid:
                active_pids.add(ppid)
        except Exception:
            pass
    return active_pids


def audit_zombie_nodes() -> Dict[str, Any]:
    """Audits running processes and returns all identified zombie/orphan nodes without terminating them."""
    active_pids = get_active_listening_pids()
    all_pids = set(psutil.pids())

    zombies: List[Dict[str, Any]] = []
    total_mem_reclaimable = 0

    for pid in all_pids:
        try:
            p = psutil.Process(pid)
            pname = p.name().lower()
            if pname not in TARGET_PROCESS_NAMES or pid in active_pids:
                continue

            # Target process holding 0 listening ports
            cmdline_str = ""
            try:
                cmdline_str = " ".join(p.cmdline()).lower()
            except Exception:
                pass

            if any(token in cmdline_str for token in PROTECTED_CMDLINE_TOKENS):
                continue

            ppid = None
            try:
                ppid = p.ppid()
            except Exception:
                pass

            mem = 0
            try:
                mem = p.memory_info().rss
            except Exception:
                pass

            status = ""
            try:
                status = p.status()
            except Exception:
                pass

            # Check if zombie status or dead parent
            is_zombie_status = (status == psutil.STATUS_ZOMBIE)
            is_dead_parent = (ppid is not None and ppid not in all_pids and ppid != 0)

            # Check if ancient suspended process
            c_time = 0
            try:
                c_time = p.create_time()
            except Exception:
                pass
            is_ancient_idle = (c_time > 0 and (time.time() - c_time > 1800) and mem < 65536)

            if is_zombie_status or is_dead_parent or is_ancient_idle:
                zombies.append({
                    "pid": pid,
                    "ppid": ppid,
                    "name": pname,
                    "status": str(status),
                    "mem_bytes": mem,
                    "mem_mb": round(mem / (1024 * 1024), 2),
                    "cmdline": cmdline_str[:120],
                    "reason": "zombie_status" if is_zombie_status else ("dead_parent" if is_dead_parent else "ancient_idle")
                })
                total_mem_reclaimable += mem
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return {
        "timestamp": time.time(),
        "count": len(zombies),
        "total_reclaimable_mb": round(total_mem_reclaimable / (1024 * 1024), 2),
        "zombies": zombies
    }


def sweep_zombie_nodes(dry_run: bool = False) -> Dict[str, Any]:
    """
    Terminates identified orphaned/zombie processes holding no listening ports,
    safely reclaiming host RAM.
    """
    audit = audit_zombie_nodes()
    zombies = audit["zombies"]
    terminated_count = 0
    freed_bytes = 0
    actions: List[str] = []

    for z in zombies:
        pid = z["pid"]
        name = z["name"]
        mem_mb = z["mem_mb"]
        reason = z["reason"]

        if not dry_run:
            try:
                p = psutil.Process(pid)
                p.kill()
                terminated_count += 1
                freed_bytes += z["mem_bytes"]
                msg = f"Terminated {name} (PID: {pid}, reason: {reason}) - Reclaimed {mem_mb} MB"
                actions.append(msg)
            except Exception as e:
                actions.append(f"Could not terminate PID {pid}: {e}")
        else:
            actions.append(f"[DRY-RUN] Would terminate {name} (PID: {pid}) - Reclaim {mem_mb} MB")

    freed_mb = round(freed_bytes / (1024 * 1024), 2)
    return {
        "status": "COMPLETED",
        "dry_run": dry_run,
        "terminated_count": terminated_count if not dry_run else len(zombies),
        "freed_mb": freed_mb if not dry_run else audit["total_reclaimable_mb"],
        "actions": actions,
        "details": zombies
    }


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    res = sweep_zombie_nodes(dry_run=dry)
    print(f"[Zombie Node Cleaner] Terminated: {res['terminated_count']} | Freed: {res['freed_mb']} MB")
    for a in res["actions"]:
        print("  ->", a)
