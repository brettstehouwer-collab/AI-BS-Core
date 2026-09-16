import os
import sys
import glob
import time
import json
import sqlite3
import socket
import psutil
import requests
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Header, Depends, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/operations", tags=["Omni Operations & Live Audit"])

BASE_DIR = Path("C:/AI-BS")
LOGS_DIR = BASE_DIR / "logs"
COMFY_OUTPUT_DIRS = [
    Path("C:/AI-BS/ComfyUI/output"),
    Path("E:/ComfyUI_windows_portable/ComfyUI/output")
]

# ═════════════════════════════════════════════════════════════════════════════
# IN-MEMORY TTL CACHE LAYER (Prevents Event-Loop & Threadpool Starvation)
# ═════════════════════════════════════════════════════════════════════════════
_cache_lock = threading.Lock()
_cache_store: Dict[str, Dict[str, Any]] = {}

def get_cached(key: str, ttl: float = 5.0) -> Optional[Dict[str, Any]]:
    with _cache_lock:
        entry = _cache_store.get(key)
        if entry and (time.time() - entry["timestamp"] < ttl):
            return entry["data"]
    return None

def set_cached(key: str, data: Dict[str, Any]):
    with _cache_lock:
        _cache_store[key] = {
            "timestamp": time.time(),
            "data": data
        }

def probe_single_port(item: Dict[str, Any]) -> Dict[str, Any]:
    is_open = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.03)
        res = s.connect_ex(("127.0.0.1", item["port"]))
        is_open = (res == 0)
        s.close()
    except Exception:
        pass
    return {
        "port": item["port"],
        "name": item["name"],
        "category": item["category"],
        "status": "LISTENING" if is_open else "INACTIVE",
        "is_open": is_open
    }

# Multi-tenant Header Dependency
def get_tenant(x_client_id: Optional[str] = Header(default="stehouwer_publishing")) -> str:
    return x_client_id or "stehouwer_publishing"

KNOWN_PORTS = [
    {"port": 8000, "name": "Go IPC Gateway / aibs_engine", "category": "core"},
    {"port": 8001, "name": "ChromaDB Memory (Local)", "category": "database"},
    {"port": 8002, "name": "ChromaDB Resource (E: Drive)", "category": "database"},
    {"port": 8005, "name": "AI-BS Broadcast Daemon", "category": "broadcast"},
    {"port": 8006, "name": "AI-BS Social Daemon", "category": "social"},
    {"port": 8007, "name": "Crypto Trader Bot", "category": "finance"},
    {"port": 8010, "name": "SHM WebSocket Gateway", "category": "core"},
    {"port": 8013, "name": "VST3 Audio Daemon", "category": "audio"},
    {"port": 8080, "name": "FastAPI Master Backend", "category": "core"},
    {"port": 8088, "name": "AI-BS Broadcast Kernel", "category": "broadcast"},
    {"port": 8089, "name": "Nginx HLS Stream (WSL2)", "category": "broadcast"},
    {"port": 8099, "name": "Gemini MCP Server", "category": "ai"},
    {"port": 8189, "name": "ComfyUI Media Engine", "category": "media"},
    {"port": 8888, "name": "Unreal Engine Signaling Server", "category": "3d"},
    {"port": 11434, "name": "Ollama LLM (stehouwer_llm)", "category": "ai"},
    {"port": 1935, "name": "RTMP Stream Ingest (WSL2)", "category": "broadcast"},
    {"port": 5173, "name": "Main Dashboard (Vite)", "category": "ui"},
    {"port": 5174, "name": "Broadcast Studio (Vite)", "category": "ui"}
]


class ProcessActionRequest(BaseModel):
    pid: int
    action: str # "terminate" or "kill"


@router.get("/processes")
def get_live_processes(tenant: str = Depends(get_tenant)):
    """
    Returns real-time operating system processes, memory footprints, CPU utilization,
    and live port listening states for the entire AI-BS ecosystem. Zero mock data.
    """
    cached = get_cached(f"processes_{tenant}", ttl=5.0)
    if cached:
        return cached

    try:
        # 1. System host hardware metrics
        try:
            mem = psutil.virtual_memory()
            total_ram_gb = round(mem.total / (1024**3), 2)
            used_ram_gb = round(mem.used / (1024**3), 2)
            ram_percent = mem.percent
        except Exception:
            total_ram_gb = 0.0
            used_ram_gb = 0.0
            ram_percent = 0.0

        try:
            cpu_pct = psutil.cpu_percent(interval=None)
        except Exception:
            cpu_pct = 0.0

        try:
            logical_cores = psutil.cpu_count(logical=True) or 1
        except Exception:
            logical_cores = 1

        # 2. Probe active listening ports in parallel (ThreadPoolExecutor cuts ~550ms sequential lag to <35ms)
        with ThreadPoolExecutor(max_workers=min(20, len(KNOWN_PORTS))) as executor:
            port_status = list(executor.map(probe_single_port, KNOWN_PORTS))

        # 3. Filter relevant AI-BS processes (Phase 1: fast name filter with zero memory-table overhead)
        active_procs = []
        name_keywords = [
            "python", "ollama", "llama", "comfy", "aibs", "mine_pearl",
            "peakminer", "oyster", "cloudflared", "vnc_bridge", "daemon", "vite", "node", "powershell"
        ]

        try:
            for p in psutil.process_iter(["pid", "name"]):
                try:
                    raw_name = p.info.get("name") or ""
                    pname = str(raw_name).lower()
                    if not any(k in pname for k in name_keywords):
                        continue

                    # Phase 2: Fetch memory info and status ONLY for matching candidate processes
                    try:
                        mem_info = p.memory_info()
                        rss_mb = round((mem_info.rss / (1024 * 1024)), 1)
                    except Exception:
                        rss_mb = 0.0

                    try:
                        pstatus = p.status()
                    except Exception:
                        pstatus = "running"

                    # Skip low-footprint processes unless Vite
                    if rss_mb < 5.0 and "vite" not in pname:
                        continue

                    # Phase 3: fetch cmdline only for matching candidates
                    try:
                        cmd_list = p.cmdline()
                        cmd = " ".join(cmd_list or [])
                    except Exception:
                        cmd = raw_name

                    cmd_lower = cmd.lower()

                    # Identify human-readable role
                    role = "Generic Worker"
                    if "ai_bs_backend" in cmd_lower:
                        role = "FastAPI Master Engine (8080)"
                    elif "comfyui" in cmd_lower:
                        role = "ComfyUI Media Engine (8189)"
                    elif "ollama" in pname or "llama" in pname:
                        role = "Ollama LLM Engine (11434)"
                    elif "peakminer" in cmd_lower or "mine_pearl" in cmd_lower:
                        role = "Pearl PoW Miner (HeroMiners)"
                    elif "oyster" in pname:
                        role = "Pearl Desktop Node (SPV)"
                    elif "crypto_trader" in cmd_lower:
                        role = "Crypto Trader Bot (8007)"
                    elif "shm_websocket" in cmd_lower:
                        role = "SHM WebSocket Bridge (8010)"
                    elif "cloudflared" in pname:
                        role = "Cloudflare Tunnel (ai-bs)"
                    elif "broadcast_kernel" in cmd_lower:
                        role = "Broadcast Kernel (8088)"
                    elif "broadcast_daemon" in cmd_lower:
                        role = "Broadcast Daemon (8005)"
                    elif "vst_daemon" in cmd_lower:
                        role = "VST3 Audio Daemon (8013)"
                    elif "memory_daemon" in cmd_lower:
                        role = "Episodic Memory Daemon"
                    elif "social_daemon" in cmd_lower:
                        role = "Social Outreach Daemon (8006)"
                    elif "discord_bot" in cmd_lower:
                        role = "Discord Community Bot"
                    elif "research_agent" in cmd_lower:
                        role = "Research Agent Daemon"
                    elif "chroma" in cmd_lower:
                        role = "ChromaDB Vector Store"
                    elif "vite" in cmd_lower and "5173" in cmd_lower:
                        role = "Main Dashboard Vite Server (5173)"
                    elif "vite" in cmd_lower:
                        role = "Broadcast Studio Vite Server"
                    elif "powershell" in pname and "mine_pearl" in cmd_lower:
                        role = "Pearl Miner Launcher"
                    elif "powershell" in pname:
                        continue

                    active_procs.append({
                        "pid": p.pid,
                        "name": raw_name,
                        "role": role,
                        "cmd": cmd[:160],
                        "memory_mb": rss_mb,
                        "status": pstatus
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, Exception):
                    pass
        except Exception:
            pass

        active_procs.sort(key=lambda x: x.get("memory_mb", 0.0), reverse=True)

        res_payload = {
            "timestamp": time.time(),
            "client_id": tenant,
            "host_hardware": {
                "total_ram_gb": total_ram_gb,
                "used_ram_gb": used_ram_gb,
                "ram_percent": ram_percent,
                "cpu_percent": cpu_pct,
                "logical_cores": logical_cores
            },
            "ports": port_status,
            "total_active_processes": len(active_procs),
            "processes": active_procs
        }
        set_cached(f"processes_{tenant}", res_payload)
        return res_payload
    except Exception as e:
        return {
            "timestamp": time.time(),
            "client_id": tenant,
            "error": str(e),
            "host_hardware": {
                "total_ram_gb": 0.0,
                "used_ram_gb": 0.0,
                "ram_percent": 0.0,
                "cpu_percent": 0.0,
                "logical_cores": 1
            },
            "ports": [],
            "total_active_processes": 0,
            "processes": []
        }


@router.post("/process-action")
def control_process(req: ProcessActionRequest, tenant: str = Depends(get_tenant)):
    """
    Terminates or kills a specific process by PID.
    """
    try:
        proc = psutil.Process(req.pid)
        name = proc.name()
        if req.action == "kill":
            proc.kill()
        else:
            proc.terminate()
        return {"success": True, "message": f"Sent {req.action} to PID {req.pid} ({name})"}
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail=f"Process PID {req.pid} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to control process: {str(e)}")


@router.get("/media-workloads")
def get_media_workloads(tenant: str = Depends(get_tenant)):
    """
    Real-time query of ComfyUI queue, prompt execution history, generated photo/video assets,
    and WSL2 RTMP/HLS streaming ingestion status. Zero mock data.
    """
    cached = get_cached(f"media_workloads_{tenant}", ttl=5.0)
    if cached:
        return cached

    comfy_status = {"online": False, "running_queue": [], "pending_queue": [], "queue_remaining": 0}
    try:
        cq = requests.get("http://127.0.0.1:8189/queue", timeout=0.15)
        if cq.status_code == 200:
            data = cq.json()
            comfy_status["online"] = True
            comfy_status["running_queue"] = data.get("queue_running", [])
            comfy_status["pending_queue"] = data.get("queue_pending", [])
            comfy_status["queue_remaining"] = len(data.get("queue_running", [])) + len(data.get("queue_pending", []))
    except Exception:
        pass

    # Scan output directories for physical media files
    recent_outputs = []
    for out_dir in COMFY_OUTPUT_DIRS:
        if out_dir.exists():
            for f in out_dir.glob("*.*"):
                ext = f.suffix.lower()
                if ext in [".png", ".jpg", ".jpeg", ".mp4", ".webp", ".gif"]:
                    try:
                        st = f.stat()
                        recent_outputs.append({
                            "filename": f.name,
                            "path": str(f),
                            "ext": ext.replace(".", "").upper(),
                            "size_kb": round(st.st_size / 1024, 1),
                            "mtime": st.st_mtime,
                            "media_url": f"/api/operations/media-file?filename={f.name}"
                        })
                    except Exception:
                        pass

    recent_outputs.sort(key=lambda x: x["mtime"], reverse=True)

    # Check WSL2 RTMP / HLS
    rtmp_open = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.04)
        rtmp_open = (s.connect_ex(("127.0.0.1", 1935)) == 0)
        s.close()
    except Exception:
        pass

    hls_open = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.04)
        hls_open = (s.connect_ex(("127.0.0.1", 8089)) == 0)
        s.close()
    except Exception:
        pass

    result_payload = {
        "timestamp": time.time(),
        "client_id": tenant,
        "comfyui": comfy_status,
        "streaming_ingest": {
            "rtmp_1935": "ONLINE" if rtmp_open else "OFFLINE",
            "hls_8089": "ONLINE" if hls_open else "OFFLINE"
        },
        "total_generated_media": len(recent_outputs),
        "recent_outputs": recent_outputs[:24]
    }
    set_cached(f"media_workloads_{tenant}", result_payload)
    return result_payload


@router.get("/media-file")
def get_media_file(filename: str):
    """
    Safely serves generated media assets from ComfyUI output directories.
    """
    safe_name = os.path.basename(filename)
    for out_dir in COMFY_OUTPUT_DIRS:
        target = out_dir / safe_name
        if target.exists() and target.is_file():
            ext = target.suffix.lower()
            media_type = "image/png"
            if ext in [".jpg", ".jpeg"]:
                media_type = "image/jpeg"
            elif ext == ".mp4":
                media_type = "video/mp4"
            elif ext == ".webp":
                media_type = "image/webp"
            elif ext == ".gif":
                media_type = "image/gif"
            return FileResponse(str(target), media_type=media_type)
    raise HTTPException(status_code=404, detail="Media file not found")


@router.get("/saves-and-work")
def get_saves_and_work(tenant: str = Depends(get_tenant)):
    """
    Continuous autosaves, episodic memory transactions, and recent file changes across AI-BS.
    """
    cached = get_cached(f"saves_and_work_{tenant}", ttl=5.0)
    if cached:
        return cached

    recent_saves = []

    # 1. State DB continuous autosaves (Checking aibs_master.db with fallback to state.db)
    master_db = BASE_DIR / "backend" / "aibs_master.db"
    state_db = master_db if master_db.exists() else (BASE_DIR / "backend" / "state.db")
    db_label = "aibs_master.db" if master_db.exists() else "state.db"
    if state_db.exists():
        try:
            conn = sqlite3.connect(str(state_db), timeout=5.0)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            # Inspect table metadata
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in c.fetchall()]
            for t in ["file_state", "scheduled_posts_queue", "omnidrive_index", "client_profiles", "vault_data", "accounting_entries", "assets", "properties"]:
                if t in tables:
                    c.execute(f"SELECT COUNT(*) as count FROM {t}")
                    cnt = c.fetchone()["count"]
                    recent_saves.append({
                        "source": f"{db_label} :: {t}",
                        "type": "Database Records",
                        "records_count": cnt,
                        "mtime": state_db.stat().st_mtime,
                        "details": f"Persistent SQLite table maintaining {cnt} entries"
                    })
            conn.close()
        except Exception as e:
            recent_saves.append({"source": db_label, "error": str(e)})

    # 2. Master Architectural Ledger state
    ledger_path = BASE_DIR / "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
    if ledger_path.exists():
        st = ledger_path.stat()
        recent_saves.append({
            "source": "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
            "type": "Master Architectural Ledger",
            "size_kb": round(st.st_size / 1024, 1),
            "mtime": st.st_mtime,
            "details": "Central system chronology, ports, and architectural lineage"
        })

    # 3. Fast targeted scan of modified files across AI-BS in the last 24 hours (bypasses recursive 6s os.walk)
    now = time.time()
    one_day_ago = now - 86400
    recently_modified_files = []

    cached_files = get_cached("recently_modified_files_cache", ttl=30.0)
    if cached_files is not None:
        recently_modified_files = cached_files
    else:
        scan_targets = [
            BASE_DIR,
            BASE_DIR / "backend",
            BASE_DIR / "backend" / "routers",
            BASE_DIR / "backend" / "modules",
            BASE_DIR / "saved_data" / "artifacts",
            BASE_DIR / "frontend" / "src",
            BASE_DIR / "frontend" / "components"
        ]
        seen_paths = set()
        for sdir in scan_targets:
            if not sdir.exists():
                continue
            try:
                for entry in os.scandir(sdir):
                    if entry.is_file() and entry.name.endswith((".py", ".jsx", ".js", ".json", ".md", ".db", ".bat", ".html")):
                        try:
                            st = entry.stat()
                            if st.st_mtime >= one_day_ago and entry.path not in seen_paths:
                                seen_paths.add(entry.path)
                                recently_modified_files.append({
                                    "relative_path": str(Path(entry.path).relative_to(BASE_DIR)),
                                    "size_bytes": st.st_size,
                                    "mtime": st.st_mtime
                                })
                        except Exception:
                            pass
            except Exception:
                pass

        recently_modified_files.sort(key=lambda x: x["mtime"], reverse=True)
        set_cached("recently_modified_files_cache", recently_modified_files)

    result_payload = {
        "timestamp": now,
        "client_id": tenant,
        "system_saves": recent_saves,
        "total_modified_last_24h": len(recently_modified_files),
        "recent_modified_files": recently_modified_files[:30]
    }
    set_cached(f"saves_and_work_{tenant}", result_payload)
    return result_payload


@router.get("/admin-submissions")
def get_admin_submissions(tenant: str = Depends(get_tenant)):
    """
    Live aggregated table of administrative records submitted across all SQLite databases
    (clients, leads, quotes, power washing jobs, accounting, and vault entries).
    Zero mock data.
    """
    cached = get_cached(f"admin_submissions_{tenant}", ttl=5.0)
    if cached:
        return cached

    db_configs = [
        {"path": BASE_DIR / "backend" / "aibs_master.db", "name": "aibs_master.db (Consolidated Master)", "tables": ["client_profiles", "growth_leads", "campaign_subscribers", "vault_keys", "vault_data", "tenant_user_credits", "accounting_entries", "ag_competitors", "ag_fleet", "assets", "properties", "trades", "scheduled_posts_queue"]},
        {"path": BASE_DIR / "backend" / "state.db", "name": "state.db", "tables": ["client_profiles", "growth_leads", "campaign_subscribers"]},
        {"path": BASE_DIR / "backend" / "stehouwer_vault.db", "name": "stehouwer_vault.db", "tables": ["vault_keys", "vault_data", "tenant_user_credits"]},
        {"path": BASE_DIR / "backend" / "stehouwer_accounting.db", "name": "stehouwer_accounting.db", "tables": ["accounting_entries"]},
        {"path": BASE_DIR / "clients.db", "name": "clients.db", "tables": ["ag_competitors", "ag_outreach", "ag_fleet"]},
        {"path": BASE_DIR / "leads_store.db", "name": "leads_store.db", "tables": ["client_crm_leads", "joey_enriched_leads"]},
        {"path": BASE_DIR / "prestige_powerwash.db", "name": "prestige_powerwash.db", "tables": ["clients", "jobs", "fleet_units"]},
        {"path": BASE_DIR / "west_michigan.db", "name": "west_michigan.db", "tables": ["properties"]},
        {"path": BASE_DIR / "drip_ledger.db", "name": "drip_ledger.db", "tables": ["trades"]}
    ]

    aggregated_tables = []
    total_records_count = 0

    for cfg in db_configs:
        db_file = cfg["path"]
        if not db_file.exists():
            continue
        try:
            conn = sqlite3.connect(str(db_file), timeout=5.0)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [r[0] for r in c.fetchall()]

            for t in cfg["tables"]:
                if t not in existing_tables:
                    continue
                try:
                    c.execute(f"SELECT COUNT(*) as cnt FROM {t}")
                    cnt = c.fetchone()["cnt"]
                    total_records_count += cnt

                    # Fetch up to 5 most recent records
                    c.execute(f"SELECT * FROM {t} LIMIT 5")
                    rows = c.fetchall()
                    sample_records = []
                    for r in rows:
                        d = dict(r)
                        # Sanitize binary or giant strings
                        clean_d = {}
                        for k, v in d.items():
                            if isinstance(v, (str, int, float, bool)) or v is None:
                                clean_d[k] = str(v)[:100] if isinstance(v, str) else v
                            else:
                                clean_d[k] = "<binary/blob>"
                        sample_records.append(clean_d)

                    aggregated_tables.append({
                        "database": cfg["name"],
                        "table": t,
                        "count": cnt,
                        "sample_records": sample_records
                    })
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

    result_payload = {
        "timestamp": time.time(),
        "client_id": tenant,
        "total_admin_records": total_records_count,
        "total_tables_monitored": len(aggregated_tables),
        "tables": aggregated_tables
    }
    set_cached(f"admin_submissions_{tenant}", result_payload)
    return result_payload


@router.get("/error-diagnostics")
def get_error_diagnostics(tenant: str = Depends(get_tenant)):
    r"""
    Scans all 30+ log files in C:\AI-BS\logs\ extracting real errors, tracebacks,
    exceptions, and detecting stopped or hung daemons based on heartbeat timestamps.
    Zero mock data.
    """
    cached = get_cached(f"error_diagnostics_{tenant}", ttl=5.0)
    if cached:
        return cached

    log_files = glob.glob(str(LOGS_DIR / "*.log"))
    now = time.time()
    
    daemon_health = []
    error_events = []

    error_keywords = [
        "ERROR", "CRITICAL", "TRACEBACK", "EXCEPTION", "MODULENOTFOUNDERROR",
        "SYNTAXERROR", "INDENTATIONERROR", "TIMEOUT", "FAILED", "CANNOT CONNECT", "WINERROR"
    ]

    for lf in log_files:
        p = Path(lf)
        try:
            st = p.stat()
            sz_kb = round(st.st_size / 1024, 1)
            mtime = st.st_mtime
            age_sec = now - mtime
            
            # Determine health based on last modification
            # If a daemon has not written a log in > 24 hours, mark idle/stopped
            status = "HEALTHY"
            if age_sec > 86400 * 3:
                status = "STOPPED / INACTIVE"
            elif age_sec > 3600:
                status = "IDLE"
            
            recent_errs_count = 0
            recent_error_lines = []

            # Fast tail read: read only the last 32 KB chunk rather than whole file
            with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                if st.st_size > 32768:
                    f.seek(st.st_size - 32768)
                chunk = f.read()
                tail_lines = chunk.splitlines()[-100:]
                for line in tail_lines:
                    line_str = line.strip()
                    line_upper = line_str.upper()
                    if any(k in line_upper for k in error_keywords):
                        recent_errs_count += 1
                        if len(recent_error_lines) < 4:
                            recent_error_lines.append(line_str[:160])
                        error_events.append({
                            "log_file": p.name,
                            "line": line_str[:200],
                            "timestamp_approx": mtime
                        })

            if recent_errs_count > 10:
                status = "ERRORS DETECTED"

            daemon_health.append({
                "logfile": p.name,
                "size_kb": sz_kb,
                "last_modified": mtime,
                "age_seconds": int(age_sec),
                "status": status,
                "error_count_in_tail": recent_errs_count,
                "recent_errors": recent_error_lines
            })
        except Exception:
            pass

    daemon_health.sort(key=lambda x: (x["error_count_in_tail"], -x["last_modified"]), reverse=True)
    error_events.sort(key=lambda x: x["timestamp_approx"], reverse=True)

    result_payload = {
        "timestamp": now,
        "client_id": tenant,
        "total_log_files": len(daemon_health),
        "total_recent_errors_extracted": len(error_events),
        "daemons": daemon_health,
        "error_feed": error_events[:50]
    }
    set_cached(f"error_diagnostics_{tenant}", result_payload)
    return result_payload


@router.get("/log-tail")
def tail_log_file(logfile: str = Query(...), lines: int = Query(default=100), tenant: str = Depends(get_tenant)):
    """
    Streams the exact tail of any selected daemon log file for forensic inspection.
    """
    safe_name = os.path.basename(logfile)
    target = LOGS_DIR / safe_name
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Log file '{safe_name}' not found")
    
    try:
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            tail = all_lines[-lines:]
        return {
            "logfile": safe_name,
            "total_lines_in_file": len(all_lines),
            "lines_returned": len(tail),
            "content": "".join(tail)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")
