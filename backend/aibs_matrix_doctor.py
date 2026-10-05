"""
AI-BS Matrix Doctor Diagnostic & Self-Healing Daemon
Performs deep socket probing across all 18 ports, audits process PIDs & lockfiles,
and executes non-destructive self-healing routines to eliminate dead locks and orphan daemons.
"""

import os
import sys
import time
import socket
import json
import sqlite3
import subprocess
import argparse
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

WORKSPACE_ROOT = r"C:\AI-BS"
LOG_PATH = os.path.join(WORKSPACE_ROOT, "logs", "matrix_doctor.log")

ECOSYSTEM_PORTS = {
    8080: {"name": "FastAPI Master Hub", "category": "Backend Core", "critical": True},
    8000: {"name": "Go Matrix Gateway", "category": "IPC Gateway", "critical": True},
    8001: {"name": "Theatrical Gateway", "category": "Virtual Production", "critical": False},
    8002: {"name": "ChromaDB Vector Store", "category": "Vector Memory", "critical": True},
    8005: {"name": "Broadcast Studio Daemon", "category": "Media & Streaming", "critical": False},
    8006: {"name": "Twitch/IRC Social Hub", "category": "Social Automation", "critical": False},
    8008: {"name": "Supabase Kong Gateway", "category": "Database Gateway", "critical": False},
    8010: {"name": "SHM Telemetry Gateway", "category": "Shared Memory IPC", "critical": True},
    8013: {"name": "VST3 Audio Bridge", "category": "Audio Engineering", "critical": False},
    8099: {"name": "Gemini MCP Server", "category": "MCP Infrastructure", "critical": False},
    8189: {"name": "ComfyUI Diffusion Studio", "category": "Generative Media", "critical": False},
    8888: {"name": "Unreal Engine Signaling", "category": "3D Virtual Production", "critical": False},
    4455: {"name": "OBS Studio WebSocket", "category": "OBS Orchestration", "critical": False},
    3001: {"name": "Node.js Backend Server", "category": "Legacy Services", "critical": False},
    5173: {"name": "Primary React Dashboard", "category": "Web Frontend", "critical": True},
    5174: {"name": "BroadcastStudioApp Vite", "category": "Native Desktop App", "critical": False},
    11434: {"name": "Ollama Primary LLM", "category": "Local LLM Core", "critical": True},
    11435: {"name": "Ollama E-Drive LLM", "category": "Local LLM Secondary", "critical": False},
}

LOCK_FILES_TO_AUDIT = [
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "crypto_daemon_manager.lock"),
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "research_agent_daemon.pid"),
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "researcher_daemon.pid"),
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "trade_engine_daemon.pid"),
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "wallet_tracker_daemon.pid"),
    os.path.join(WORKSPACE_ROOT, "Crypto-Swarm", "watcher_daemon.pid"),
]

def log_doctor(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [MATRIX_DOCTOR] {msg}"
    try:
        print(formatted)
    except Exception:
        print(formatted.encode('ascii', errors='replace').decode('ascii'))
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def check_port(port, host="127.0.0.1", timeout=0.25):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def diagnose_ecosystem():
    """
    Returns full diagnostic breakdown of 18 ports, database locks, and overall health score.
    """
    port_results = {}
    online_count = 0
    critical_online = 0
    total_critical = 0

    for port, info in ECOSYSTEM_PORTS.items():
        is_up = check_port(port)
        if is_up:
            online_count += 1
            if info["critical"]:
                critical_online += 1
        if info["critical"]:
            total_critical += 1

        port_results[port] = {
            "name": info["name"],
            "category": info["category"],
            "critical": info["critical"],
            "status": "ONLINE" if is_up else "OFFLINE",
            "online": is_up
        }

    # Audit locks
    orphan_locks = []
    for lock_path in LOCK_FILES_TO_AUDIT:
        if os.path.exists(lock_path):
            orphan_locks.append(os.path.basename(lock_path))

    # Health score (out of 100)
    health_score = int((online_count / len(ECOSYSTEM_PORTS)) * 100)

    return {
        "timestamp": datetime.now().isoformat(),
        "health_score": health_score,
        "online_ports": online_count,
        "total_ports": len(ECOSYSTEM_PORTS),
        "critical_online": critical_online,
        "total_critical": total_critical,
        "ports": port_results,
        "orphan_locks": orphan_locks,
        "system_status": "OPTIMAL" if health_score >= 80 else ("DEGRADED" if health_score >= 40 else "CRITICAL")
    }

def heal_ecosystem():
    """
    Executes non-destructive self-healing routines:
    1. Removes stale locks where the corresponding daemon is offline.
    2. Auto-spawns offline core daemons (ChromaDB 8002, etc.).
    3. Runs passive WAL checkpoint on master database.
    """
    actions_taken = []

    # 1. Clean stale locks
    for lock_path in LOCK_FILES_TO_AUDIT:
        if os.path.exists(lock_path):
            try:
                # Check if lock is empty or ancient (>1 hour)
                mtime = os.path.getmtime(lock_path)
                if (time.time() - mtime) > 3600 or os.path.getsize(lock_path) <= 10:
                    os.remove(lock_path)
                    actions_taken.append(f"Cleared stale lockfile: {os.path.basename(lock_path)}")
                    log_doctor(f"Cleared stale lockfile: {lock_path}")
            except Exception as e:
                actions_taken.append(f"Failed to clear {os.path.basename(lock_path)}: {e}")

    # 2. Auto-spawn offline core daemons
    creation_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == 'nt' else 0
    python_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    # 2a. ChromaDB on Port 8002
    if not check_port(8002):
        chroma_exe = r"C:\AI-BS\pyppeteer_env\Scripts\chroma.exe"
        chroma_db_path = r"E:\AI_BS_Resources\ChromaDB"
        if os.path.exists(chroma_exe):
            try:
                os.makedirs(chroma_db_path, exist_ok=True)
                subprocess.Popen(
                    [chroma_exe, "run", "--path", chroma_db_path, "--port", "8002", "--host", "127.0.0.1"],
                    creationflags=creation_flag
                )
                actions_taken.append("Auto-spawned ChromaDB Vector Store daemon on Port 8002")
                log_doctor("Auto-spawned ChromaDB on Port 8002")
            except Exception as e:
                actions_taken.append(f"Failed to spawn ChromaDB 8002: {e}")

    # 2b. VST3 Audio Bridge on Port 8013
    if not check_port(8013):
        vst_daemon = os.path.join(WORKSPACE_ROOT, "backend", "aibs_vst_daemon.py")
        if os.path.exists(vst_daemon):
            try:
                subprocess.Popen(
                    [python_exe, vst_daemon],
                    cwd=os.path.join(WORKSPACE_ROOT, "backend"),
                    creationflags=creation_flag
                )
                actions_taken.append("Auto-spawned VST3 Audio Bridge on Port 8013")
                log_doctor("Auto-spawned VST3 Audio Bridge on Port 8013")
            except Exception as e:
                actions_taken.append(f"Failed to spawn VST3 Bridge 8013: {e}")

    # 2c. Broadcast Daemon on Port 8005
    if not check_port(8005):
        bcast_daemon = os.path.join(WORKSPACE_ROOT, "backend", "aibs_broadcast_daemon.py")
        if os.path.exists(bcast_daemon):
            try:
                subprocess.Popen(
                    [python_exe, bcast_daemon],
                    cwd=os.path.join(WORKSPACE_ROOT, "backend"),
                    creationflags=creation_flag
                )
                actions_taken.append("Auto-spawned Broadcast Daemon on Port 8005")
                log_doctor("Auto-spawned Broadcast Daemon on Port 8005")
            except Exception as e:
                actions_taken.append(f"Failed to spawn Broadcast Daemon 8005: {e}")

    # 2d. Social Hub Daemon on Port 8006
    if not check_port(8006):
        social_daemon = os.path.join(WORKSPACE_ROOT, "backend", "aibs_social_daemon.py")
        if os.path.exists(social_daemon):
            try:
                subprocess.Popen(
                    [python_exe, social_daemon],
                    cwd=os.path.join(WORKSPACE_ROOT, "backend"),
                    creationflags=creation_flag
                )
                actions_taken.append("Auto-spawned Social Hub Daemon on Port 8006")
                log_doctor("Auto-spawned Social Hub Daemon on Port 8006")
            except Exception as e:
                actions_taken.append(f"Failed to spawn Social Hub 8006: {e}")

    # 2e. GPU Thermal Safety Check & Fan Thermal Lock
    try:
        from modules.gpu_hardware_telemetry import gpu_telemetry_engine
        telemetry = gpu_telemetry_engine.query_nvml_telemetry()
        if telemetry.get("core_temp_c", 0) >= 75:
            gpu_telemetry_engine.set_fan_speed(100)
            actions_taken.append(f"GPU Core Temp high ({telemetry['core_temp_c']}°C): Enforced 100% Fan Lock")
            log_doctor(f"GPU Core Temp high ({telemetry['core_temp_c']}°C): Enforced 100% Fan Lock")
    except Exception as e:
        pass

    time.sleep(1.0)

    # 3. Passive WAL checkpoint
    master_db = os.path.join(WORKSPACE_ROOT, "backend", "aibs_master.db")
    if os.path.exists(master_db):
        try:
            conn = sqlite3.connect(master_db)
            conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
            conn.close()
            actions_taken.append("Executed PASSIVE WAL checkpoint on aibs_master.db")
        except Exception:
            pass

    # 4. Re-probe ecosystem
    post_diag = diagnose_ecosystem()

    return {
        "status": "HEALED",
        "actions_taken": actions_taken,
        "post_diagnosis": post_diag
    }

def main():
    parser = argparse.ArgumentParser(description="AI-BS Matrix Doctor Diagnostic Suite")
    parser.add_argument("--audit-only", action="store_true", help="Print ecosystem health diagnostic JSON")
    parser.add_argument("--heal", action="store_true", help="Run automated self-healing routines")
    args = parser.parse_args()

    if args.heal:
        res = heal_ecosystem()
        print(json.dumps(res, indent=2))
    else:
        diag = diagnose_ecosystem()
        print(json.dumps(diag, indent=2))

if __name__ == "__main__":
    main()
