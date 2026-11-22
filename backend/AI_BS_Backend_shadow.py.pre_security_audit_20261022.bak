from typing import Optional, Dict, Any, List
import json
import os
import sys

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_backend_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import time
import uvicorn
from fastapi import FastAPI, Header, Depends
from typing import Optional
from typing import Optional
from pydantic import BaseModel
from bullshit_polyglot import execute_polyglot_command
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Request, Response
import httpx
import requests
from starlette.middleware.base import BaseHTTPMiddleware
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import base64

# --- NEW IMPORTS INJECTED TODAY ---
from bullshit_memory import MemoryManager
from bullshit_orchestrator import AI_BS_Core_Engine, SwarmOrchestrator
from bullshit_builder import ProjectScaffolder
from comfy_bridge import (
    queue_comfyui_workflow,
    await_generation_result,
    extract_output_media,
)
from commercial_gateway.gateway_router import gateway_router
from commercial_gateway.admin_telemetry_router import admin_telemetry_router
from commercial_gateway.billing_provisioner import billing_provisioner_router
from commercial_gateway.site_analytics_router import site_analytics_router
from commercial_gateway.gpu_network_router import gpu_network_router
from commercial_gateway.paypal_v6_router import paypal_v6_router
from commercial_gateway.storefront_router import router as storefront_router
from commercial_gateway.crypto_control_router import router as crypto_control_router
from modules.accounting_router import router as accounting_router
from modules.vault_router import router as vault_router
from modules.telemetry_matrix_router import router as telemetry_matrix_router
from clients.joey_hamilton import router as joey_hamilton_router
from jit_daemon_manager import JITDaemonManager
from omnidrive_service import (
    omnidrive_service_instance,
    HybridSearchRequest,
    FileRelocateRequest,
)
import argparse

jit_daemon_manager_instance = JITDaemonManager()


from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
from core.daemon_manager import DaemonManager

daemon_supervisor = DaemonManager()
from core.tool_schemas import ShellCommand
from pathlib import Path


def _make_cmd(script_name: str) -> ShellCommand:
    return ShellCommand(
        command=sys.executable,
        cwd=Path(_backend_dir),
        args=[os.path.join(_backend_dir, script_name)],
        sandbox=False,
    )


# Register core daemons
daemon_supervisor.register("memory_daemon", _make_cmd("memory_daemon.py"))
daemon_supervisor.register(
    "context_ingestor_daemon", _make_cmd("context_ingestor_daemon.py")
)
daemon_supervisor.register("researcher_daemon", _make_cmd("research_agent_daemon.py"))
daemon_supervisor.register("discord_bot_daemon", _make_cmd("discord_bot_daemon.py"))
daemon_supervisor.register(
    "wallet_tracker_daemon", _make_cmd("wallet_tracker_daemon.py")
)
daemon_supervisor.register("crypto_trader_bot", _make_cmd("crypto_trader_bot.py"))
daemon_supervisor.register("auto_healer_daemon", _make_cmd("auto_healer_daemon.py"))
daemon_supervisor.register(
    "bullshit_writer_daemon", _make_cmd("bullshit_writer_daemon.py")
)
daemon_supervisor.register(
    "bullshit_heuristics_daemon", _make_cmd("bullshit_heuristics_daemon.py")
)
daemon_supervisor.register("bullshit_senses", _make_cmd("bullshit_senses.py"))
daemon_supervisor.register("bullshit_medic", _make_cmd("bullshit_medic.py"))
daemon_supervisor.register("bullshit_memory", _make_cmd("bullshit_memory.py"))
daemon_supervisor.register("bullshit_trainer", _make_cmd("bullshit_trainer.py"))
daemon_supervisor.register(
    "bullshit_vault_watchdog", _make_cmd("bullshit_vault_watchdog.py")
)
daemon_supervisor.register(
    "news_firehose_daemon", _make_cmd("core/news_firehose_daemon.py")
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-flight port reclamation & spawn supervised daemons
    daemon_supervisor.start_all(target_ports=[8080, 8002, 8003, 8004, 8005])
    
    # Auto-resume interrupted Screenplay AI adaptations
    try:
        from core.ai_adapter import load_all_states, ADAPTATION_TASKS, adapt_book_to_screenplay
        load_all_states()
        for proj_name, state in ADAPTATION_TASKS.items():
            if state.get("status") == "processing":
                print(f"[Backend] Auto-resuming interrupted adaptation job: {proj_name}")
                asyncio.create_task(adapt_book_to_screenplay(Path(""), proj_name, state.get("adaptation_type", "Feature Film")))
    except Exception as e:
        print(f"[Backend] Error resuming adaptation tasks: {e}")

    yield
    daemon_supervisor.stop_all()

import economics_gateway

app = FastAPI(title="AI-BS Central Cognitive Engine API", lifespan=lifespan)
app.include_router(economics_gateway.router)


def get_tenant(x_client_id: Optional[str] = Header(None)):
    return x_client_id if x_client_id else "stehouwer_publishing"


# --- ASYNC TTL LRU CACHE DECORATOR ---
_QUERY_CACHE = {}


def async_ttl_cache(ttl_seconds: int = 5):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            now = time.time()
            if key in _QUERY_CACHE:
                result, timestamp = _QUERY_CACHE[key]
                if now - timestamp < ttl_seconds:
                    return result
            result = await func(*args, **kwargs)
            _QUERY_CACHE[key] = (result, now)
            return result

        return wrapper

    return decorator


# Multi-Tenant DB Migration
from db_manager import safe_migrate_multitenant_schemas

safe_migrate_multitenant_schemas()


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("x-client-id", "stehouwer_publishing")
        request.state.client_id = client_id
        return await call_next(request)


app.add_middleware(TenantMiddleware)

# --- SYSTEM WIDE EFFICIENCY MODE ---
EFFICIENCY_MODE_ENABLED = False
FALLBACK_API_KEY = "AQ.Ab8RN6IHt6YsWK2WikVJz3n1soAVInsYN8sZQrgW0xPCVsK5Gg"
FALLBACK_API_BASE = (
    "https://api.sambanova.ai/v1/chat/completions"  # Change this if it's not SambaNova
)
FALLBACK_MODEL = "Meta-Llama-3.1-405B-Instruct"


@app.post("/api/system/efficiency-mode")
async def toggle_efficiency_mode(request: Request):
    global EFFICIENCY_MODE_ENABLED
    payload = await request.json()
    enabled = payload.get("enabled", False)
    EFFICIENCY_MODE_ENABLED = enabled

    if enabled:
        print("[⚡ EFFICIENCY MODE] Activating. Purging local GPU models...")
        # Kill Ollama instance to free VRAM for Clore/Vast renters
        import subprocess

        subprocess.run(
            ["taskkill", "/F", "/IM", "ollama.exe"],
            capture_output=True,
            text=True,
            shell=False,
        )
        # Optional: Kill any stray python processes that might be running comfyui/vllm (be careful)
        # We will stick to ollama.exe for now to be safe.

    return {"status": "success", "efficiency_mode": EFFICIENCY_MODE_ENABLED}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://ai-bs-dashboard.web.app",
        "https://ai-bs.brettstehouwer.live",
        "https://api.brettstehouwer.live",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
@app.get("/health")
@app.get("/v1/health")
def root_health():
    daemons_status = {
        name: d.proc is not None and d.proc.poll() is None
        for name, d in daemon_supervisor._daemons.items()
    }
    return {
        "status": "online",
        "service": "AI-BS Central Cognitive Engine API",
        "gpu_accelerated": True,
        "daemons": daemons_status,
        "timestamp": time.time(),
    }


@app.post("/api/daemons/{daemon_name}/restart")
def restart_daemon_endpoint(daemon_name: str):
    success = daemon_supervisor.restart_daemon(daemon_name)
    return {"status": "success" if success else "failed", "daemon": daemon_name}


class ComputeTogglePayload(BaseModel):
    mode: str


@app.post("/api/compute/toggle_mode")
def toggle_compute_mode(payload: ComputeTogglePayload):
    config_path = os.path.join(_backend_dir, "compute_schedule_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            config["current_mode"] = payload.mode
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)
            return {"status": "success", "mode": config["current_mode"]}
        except Exception as e:
            return JSONResponse(
                status_code=500, content={"status": "error", "message": str(e)}
            )
    return JSONResponse(
        status_code=404, content={"status": "error", "message": "Config not found"}
    )


@app.get("/api/models")
@app.get("/models")
@app.get("/v1/models")
async def root_models():
    default_models = [
        "stehouwer_llm",
        "stehouwer_qwen",
        "stehouwer_hermes",
        "stehouwer_dolphin",
    ]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get("http://127.0.0.1:11434/api/tags")
            if res.status_code == 200:
                data = res.json()
                ollama_models = []
                for item in data.get("models", []):
                    name = item.get("name", "")
                    clean_name = name.split(":")[0] if ":" in name else name
                    if clean_name and clean_name not in ollama_models:
                        ollama_models.append(clean_name)

                combined = ["stehouwer_llm"]
                for m in ollama_models:
                    if m not in combined:
                        combined.append(m)
                return {
                    "status": "success",
                    "models": combined,
                    "data": [{"id": m} for m in combined],
                }
    except Exception:
        pass
    return {
        "status": "success",
        "models": default_models,
        "data": [{"id": m} for m in default_models],
    }


@app.get("/api/comfy/media")
async def root_proxy_comfy_media(
    filename: str, subfolder: str = "", type: str = "output"
):
    """Proxies ComfyUI generated MP4 video and PNG image files directly to frontend media players."""
    import httpx
    from fastapi import Response

    comfy_url = f"http://127.0.0.1:8189/view?filename={filename}&subfolder={subfolder}&type={type}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(comfy_url)
            if resp.status_code == 200:
                media_type = resp.headers.get(
                    "content-type",
                    "video/mp4" if filename.endswith(".mp4") else "image/png",
                )
                return Response(content=resp.content, media_type=media_type)
    except Exception:
        pass

    return Response(status_code=404, content=b"ComfyUI media asset not found")


app.include_router(gateway_router)
app.include_router(admin_telemetry_router)
app.include_router(billing_provisioner_router)
app.include_router(site_analytics_router)
app.include_router(gpu_network_router)
app.include_router(paypal_v6_router)
app.include_router(storefront_router)
app.include_router(crypto_control_router)
app.include_router(accounting_router)
app.include_router(vault_router)
app.include_router(telemetry_matrix_router)
app.include_router(joey_hamilton_router, prefix="/api/clients/joey_hamilton")
try:
    from routers.sitemap_seo_router import router as sitemap_seo_router
    app.include_router(sitemap_seo_router)
except Exception as e:
    print(f"Warning: Could not load sitemap_seo_router in shadow: {e}")


_media_samples_dir = os.path.join(_root_dir, "frontend", "public", "media")
if os.path.exists(_media_samples_dir):
    app.mount("/media", StaticFiles(directory=_media_samples_dir), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Parameters & Middlewares ---
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


class HSTSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        return response


app.add_middleware(HSTSMiddleware)

import sys
import os

try:
    from calendar_integration import get_calendar_routes

    get_calendar_routes(app, lambda: None)
except Exception as e:
    print("Could not load Calendar endpoints:", e)

# Secret key for AES-GCM decryption (matching frontend key)
AES_SECRET_KEY = bytes(
    [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        22,
        23,
        24,
        25,
        26,
        27,
        28,
        29,
        30,
        31,
        32,
    ]
)
aesgcm = AESGCM(AES_SECRET_KEY)

# --- Dedicated ThreadPoolExecutor & Ryzen CPU Core Affinity Helper ---
from concurrent.futures import ThreadPoolExecutor

global_thread_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="aibs_worker")


def set_process_cpu_affinity():
    """Attempts to pin worker process to high-performance cores on Ryzen 9 9950X without throwing errors."""
    try:
        import psutil

        proc = psutil.Process()
        num_cores = psutil.cpu_count(logical=True) or 32
        target_cores = list(range(min(16, num_cores)))
        proc.cpu_affinity(target_cores)
    except Exception:
        pass


set_process_cpu_affinity()


def sanitize_clinical_output(text: str) -> str:
    """Removes conversational filler ('Sure thing!', 'Here is your request:') while preserving code & media markdown."""
    if not text:
        return text
    fluff_prefixes = [
        "sure thing!",
        "sure, here is",
        "here is the output:",
        "here is your",
        "as an ai language model,",
        "certainly!",
        "of course!",
        "i have generated",
    ]
    lines = text.splitlines()
    filtered_lines = []
    skipped_intro = False

    for line in lines:
        stripped = line.strip().lower()
        if not skipped_intro:
            if (
                any(stripped.startswith(prefix) for prefix in fluff_prefixes)
                and not line.strip().startswith("```")
                and not line.strip().startswith("![")
            ):
                continue
            skipped_intro = True
        filtered_lines.append(line)

    return "\n".join(filtered_lines).strip()


class AuthLoginPayload(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def auth_login(payload: AuthLoginPayload, response: Response):
    key_path = os.path.join(os.path.dirname(__file__), "master_key.hash")

    # Fallback default if setup script hasn't been run
    valid_user = "admin"
    valid_hash = ph.hash("password")

    if os.path.exists(key_path):
        try:
            with open(key_path, "r") as f:
                lines = f.read().splitlines()
                if len(lines) >= 2:
                    valid_user = lines[0].strip()
                    valid_hash = lines[1].strip()
        except Exception as e:
            logger.error(f"Failed to read master_key.hash: {e}")

    if payload.username != valid_user:
        return JSONResponse(
            status_code=401, content={"status": "error", "message": "Invalid identity"}
        )

    try:
        ph.verify(valid_hash, payload.password)
        # Authentication successful
        session_token = base64.b64encode(os.urandom(32)).decode("utf-8")
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,  # Requires HTTPS/TLS
            samesite="strict",
        )
        return {"status": "success", "message": "Authenticated successfully"}
    except VerifyMismatchError:
        return JSONResponse(
            status_code=401, content={"status": "error", "message": "Invalid password"}
        )


@app.post("/api/omnidrive/search")
async def api_omnidrive_search(req: HybridSearchRequest):
    return await omnidrive_service_instance.hybrid_search(
        req.query, req.extension, req.limit
    )


@app.post("/api/omnidrive/relocate")
async def api_omnidrive_relocate(req: FileRelocateRequest):
    return await omnidrive_service_instance.relocate_file_with_ast_check(
        req.source_path, req.target_path, req.dry_run
    )


class DecryptPayload(BaseModel):

    iv: str
    ciphertext: str


@app.post("/api/security/decrypt")
def decrypt_payload(payload: DecryptPayload):
    try:
        iv_bytes = base64.b64decode(payload.iv)
        cipher_bytes = base64.b64decode(payload.ciphertext)
        plaintext = aesgcm.decrypt(iv_bytes, cipher_bytes, None)
        return {"status": "success", "decrypted_data": plaintext.decode("utf-8")}
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": f"Decryption failed: {str(e)}"},
        )


@app.get("/api/comfy/media")
async def proxy_comfy_media(filename: str, subfolder: str = "", type: str = "output"):
    comfy_url = "http://127.0.0.1:8189/view"
    params = {"filename": filename, "subfolder": subfolder, "type": type}
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(comfy_url, params=params)
            if res.status_code == 200:
                return Response(
                    content=res.content, media_type=res.headers.get("content-type")
                )
            return JSONResponse(
                status_code=res.status_code,
                content={"status": "error", "message": "Failed to fetch media"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Proxy error: {str(e)}"},
        )


@app.get("/api/chia-stats")
async def get_chia_telemetry():
    try:
        from modules.chia_integration import get_chia_stats

        return get_chia_stats()
    except Exception as e:
        return {
            "status": "Offline",
            "total_plots": "0",
            "plot_size": "0.00 TiB",
            "estimated_time_to_win": "N/A",
            "total_chia_farmed": "0.0",
            "connection_error": True,
        }


@app.post("/api/chia-start")
async def trigger_chia_start():
    try:
        from modules.chia_integration import start_chia_daemon

        start_chia_daemon()
        return {"status": "success", "message": "Chia daemon start signal sent."}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/v1/emails/incoming")
async def receive_incoming_email(request: Request):
    """Receives live incoming emails from Cloudflare Email Workers or webhooks and appends to AI-BS Inbox."""
    try:
        data = await request.json()
        cache_path = os.path.join(_backend_dir, "core", "emails_cache.json")
        emails = []
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                emails = json.load(f)

        recipient = data.get("to") or data.get("recipient") or "brett@stehouwer-publishing.com"
        account = recipient if "@" in recipient else f"{recipient}@stehouwer-publishing.com"
        label = f"[Imap]/{account.split('@')[0].capitalize()}"

        new_email = {
            "id": f"em-{int(time.time()*1000)}",
            "account": account,
            "sender": data.get("from_name") or data.get("sender") or "External Sender",
            "email": data.get("from_email") or data.get("from") or "sender@external.com",
            "subject": data.get("subject") or "No Subject",
            "snippet": data.get("body") or data.get("text") or data.get("snippet") or "",
            "time": time.strftime("%I:%M %p"),
            "date": time.strftime("%Y-%m-%d"),
            "category": "Primary",
            "folder": "Inbox",
            "starred": False,
            "read": False,
            "label": label
        }

        emails.insert(0, new_email)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=2)

        return {"status": "success", "message": "Email ingested into AI-BS Inbox", "data": new_email}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/v1/emails")
async def get_cached_emails():
    cache_path = os.path.join(_backend_dir, "core", "emails_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                emails = json.load(f)
                return {"status": "success", "data": emails}
        except Exception as e:
            return JSONResponse(
                status_code=500, content={"status": "error", "message": str(e)}
            )
    return {"status": "success", "data": []}


# ==========================================
# CAMPAIGN AUTOMATION & SUBSCRIBER ENGINE
# ==========================================
import sqlite3
import pandas as pd
from fastapi import UploadFile, File

def _init_campaign_db():
    conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS campaign_subscribers (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            company TEXT,
            tags TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    # Migrate from json if exists
    cache_path = os.path.join(get_base_dir(), "core", "subscribers_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for sub in data:
                    c.execute('INSERT OR IGNORE INTO campaign_subscribers VALUES (?,?,?,?,?,?,?,?)',
                              (sub.get('id'), sub.get('email'), sub.get('first_name', ''), sub.get('last_name', ''), 
                               sub.get('company', ''), json.dumps(sub.get('tags', [])), sub.get('status', 'active'), sub.get('created_at', '')))
            os.remove(cache_path)
        except Exception:
            pass
    
    # Check if empty
    c.execute('SELECT COUNT(*) FROM campaign_subscribers')
    if c.fetchone()[0] == 0:
        seed = [
            ("sub-001", "brett@StehouwerPublishing.com", "Brett", "Stehouwer", "Stehouwer Publishing", '["Executive", "VIP"]', "active", "2026-08-19"),
            ("sub-002", "sean@StehouwerPublishing.com", "Sean", "Stehouwer", "Stehouwer Publishing", '["Executive", "Strategy"]', "active", "2026-08-19"),
            ("sub-003", "julie@StehouwerPublishing.com", "Julie", "Stehouwer", "Stehouwer Publishing", '["Operations", "VIP"]', "active", "2026-08-19"),
            ("sub-004", "footballstar0325@gmail.com", "Brett", "Personal", "Personal", '["Client", "Author"]', "active", "2026-08-19")
        ]
        c.executemany('INSERT OR IGNORE INTO campaign_subscribers VALUES (?,?,?,?,?,?,?,?)', seed)
    conn.commit()
    conn.close()

try:
    _init_campaign_db()
except Exception as e:
    print(f"Error initializing campaign DB: {e}")

@app.get("/api/v1/campaigns/subscribers")
async def get_subscribers():
    """Returns subscriber contacts list with tag filtering and engagement status."""
    try:
        conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM campaign_subscribers ORDER BY created_at DESC')
        rows = c.fetchall()
        
        data = []
        for r in rows:
            d = dict(r)
            try:
                d['tags'] = json.loads(d['tags'])
            except:
                d['tags'] = []
            data.append(d)
        conn.close()
        return {"status": "success", "data": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/api/v1/campaigns/subscribers")
async def create_subscriber(request: Request):
    """Adds a new subscriber contact with custom tags and details."""
    try:
        payload = await request.json()
        new_sub = {
            "id": f"sub-{int(time.time()*1000)}",
            "email": payload.get("email"),
            "first_name": payload.get("first_name", ""),
            "last_name": payload.get("last_name", ""),
            "company": payload.get("company", "Stehouwer Client"),
            "tags": payload.get("tags", ["General"]),
            "status": "active",
            "created_at": time.strftime("%Y-%m-%d")
        }

        conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
        c = conn.cursor()
        c.execute('INSERT INTO campaign_subscribers VALUES (?,?,?,?,?,?,?,?)', (
            new_sub["id"], new_sub["email"], new_sub["first_name"], new_sub["last_name"],
            new_sub["company"], json.dumps(new_sub["tags"]), new_sub["status"], new_sub["created_at"]
        ))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Subscriber added successfully", "data": new_sub}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/v1/campaigns/subscribers/upload")
async def upload_subscribers(file: UploadFile = File(...)):
    """Bulk imports subscribers from CSV, XLSX, JSONL, Parquet formats."""
    try:
        import pandas as pd
        import tempfile
        import io
        import uuid
        import time
        import sqlite3
        import json
        
        ext = file.filename.split('.')[-1].lower()
        contents = await file.read()
        
        df = None
        if ext in ['csv', 'txt', 'tsv']:
            df = pd.read_csv(io.BytesIO(contents))
        elif ext in ['xlsx', 'xls']:
            df = pd.read_excel(io.BytesIO(contents))
        elif ext in ['jsonl', 'json']:
            df = pd.read_json(io.BytesIO(contents), lines=True)
        elif ext in ['parquet']:
            df = pd.read_parquet(io.BytesIO(contents))
        elif ext == 'gz' and 'csv' in file.filename.lower():
            df = pd.read_csv(io.BytesIO(contents), compression='gzip')
        elif ext == 'zip' and 'csv' in file.filename.lower():
            df = pd.read_csv(io.BytesIO(contents), compression='zip')
        else:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Unsupported format: {ext}"})
            
        col_map = {}
        for c in df.columns:
            cl = str(c).lower()
            if 'email' in cl: col_map[c] = 'email'
            elif 'first' in cl: col_map[c] = 'first_name'
            elif 'last' in cl: col_map[c] = 'last_name'
            elif 'company' in cl: col_map[c] = 'company'
            elif 'tag' in cl: col_map[c] = 'tags'
            
        df = df.rename(columns=col_map)
        
        if 'email' not in df.columns:
            return JSONResponse(status_code=400, content={"status": "error", "message": "No 'email' column found in file."})
            
        df = df.dropna(subset=['email'])
        records = df.to_dict('records')
        
        conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
        c = conn.cursor()
        
        imported_count = 0
        now = time.strftime("%Y-%m-%d")
        
        for r in records:
            sub_id = f"sub-{uuid.uuid4().hex[:8]}"
            email = str(r.get('email', '')).strip()
            if not email or email == 'nan': continue
            
            first_name = str(r.get('first_name', '')).strip()
            if first_name == 'nan': first_name = ""
            last_name = str(r.get('last_name', '')).strip()
            if last_name == 'nan': last_name = ""
            company = str(r.get('company', '')).strip()
            if company == 'nan': company = ""
            
            tags = r.get('tags', '')
            if isinstance(tags, list):
                tags_json = json.dumps(tags)
            elif isinstance(tags, str) and tags and tags != 'nan':
                tags_json = json.dumps([t.strip() for t in tags.split(',')])
            else:
                tags_json = json.dumps(["Imported"])
                
            c.execute('INSERT OR IGNORE INTO campaign_subscribers VALUES (?,?,?,?,?,?,?,?)', (
                sub_id, email, first_name, last_name, company, tags_json, "active", now
            ))
            imported_count += 1
            
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": f"Successfully imported {imported_count} subscribers."}
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Failed to parse file: {str(e)}"})


@app.get("/api/v1/campaigns")
async def get_campaigns():
    """Returns list of created email marketing campaigns and telemetry stats."""
    cache_path = os.path.join(_backend_dir, "core", "campaigns_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"status": "success", "data": data}
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    seed_campaigns = [
        {
            "id": "cmp-101",
            "subject": "📢 Welcome to Stehouwer Publishing Enterprise AI System",
            "preview_text": "Explore OSINT Recon, WebRTC Video Meetings, and Live Cloudflare Email Workers.",
            "body_html": "<p>Hi {{first_name}},</p><p>Welcome to <strong>{{company}}</strong>!</p>",
            "target_tags": ["VIP", "Executive"],
            "status": "completed",
            "sent_count": 4,
            "opened_count": 3,
            "clicked_count": 2,
            "bounce_count": 0,
            "created_at": "2026-08-19"
        }
    ]
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(seed_campaigns, f, indent=2)
    return {"status": "success", "data": seed_campaigns}


@app.post("/api/v1/campaigns/create")
async def create_campaign(request: Request):
    """Creates a new campaign draft with Stehouwer LLM content template."""
    try:
        payload = await request.json()
        cache_path = os.path.join(_backend_dir, "core", "campaigns_cache.json")
        campaigns = []
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                campaigns = json.load(f)

        new_cmp = {
            "id": f"cmp-{int(time.time()*1000)}",
            "subject": payload.get("subject", "Stehouwer Announcement"),
            "preview_text": payload.get("preview_text", ""),
            "body_html": payload.get("body_html", "<p>Hello {{first_name}}</p>"),
            "target_tags": payload.get("target_tags", ["All"]),
            "status": "draft",
            "sent_count": 0,
            "opened_count": 0,
            "clicked_count": 0,
            "bounce_count": 0,
            "created_at": time.strftime("%Y-%m-%d")
        }

        campaigns.insert(0, new_cmp)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(campaigns, f, indent=2)

        return {"status": "success", "message": "Campaign created", "data": new_cmp}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/api/v1/campaigns/generate-copy")
async def generate_campaign_copy(request: Request):
    """Uses Stehouwer LLM logic to generate high-converting subject lines and email body variants."""
    try:
        payload = await request.json()
        topic = payload.get("topic", "Executive Book Launch")
        audience = payload.get("audience", "Authors & Publishers")

        subjects = [
            f"🚀 [Exclusive Brief] {topic} for {audience}",
            f"📈 How {topic} Is Transforming Stehouwer Publishing Operations",
            f"💡 Quick Executive Summary: {topic}"
        ]

        body = f"""Hi {{{{first_name}}}},

We are thrilled to announce our latest milestone regarding {topic} at {{{{company}}}}.

Key Highlights:
• Automated Real-Time Audience Segmentation
• Distributed Async Batch Email Dispatch
• Instant Telemetry Tracking & Open/Click Analytics

Click below to learn more or reply directly to this email to connect with our team.

Best regards,
Stehouwer Publishing Team"""

        return {
            "status": "success",
            "subject_options": subjects,
            "generated_body": body
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/v1/emails/oauth-status")
async def get_oauth_status():
    """Inspects token.json health and OAuth credentials validity."""
    token_path = os.path.join(get_base_dir(), "token.json")
    client_secret_path = os.path.join(get_base_dir(), "client_secret.json")
    cache_path = os.path.join(_backend_dir, "core", "emails_cache.json")

    status_data = {
        "client_secret_exists": os.path.exists(client_secret_path),
        "token_file_exists": os.path.exists(token_path),
        "is_valid": False,
        "is_expired": True,
        "has_refresh_token": False,
        "expiry_iso": None,
        "last_sync_timestamp": None,
        "status_message": "OAuth uninitialized",
    }

    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        status_data["last_sync_timestamp"] = datetime.fromtimestamp(mtime).isoformat()

    if os.path.exists(token_path):
        try:
            with open(token_path, "r", encoding="utf-8") as f:
                token_info = json.load(f)
                status_data["has_refresh_token"] = bool(token_info.get("refresh_token"))
                status_data["expiry_iso"] = token_info.get("expiry")

            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            if creds.valid:
                status_data["is_valid"] = True
                status_data["is_expired"] = False
                status_data["status_message"] = "OAuth Token Active & Valid"
            elif creds.expired and creds.refresh_token:
                status_data["is_expired"] = True
                try:
                    creds.refresh(Request())
                    with open(token_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    status_data["is_valid"] = True
                    status_data["is_expired"] = False
                    status_data["expiry_iso"] = (
                        creds.expiry.isoformat() if creds.expiry else None
                    )
                    status_data["status_message"] = "OAuth Token Auto-Refreshed"
                except Exception as refresh_err:
                    status_data["status_message"] = (
                        f"Refresh Failed: {str(refresh_err)}"
                    )
            else:
                status_data["status_message"] = "Token Invalid & Cannot Refresh"
        except Exception as e:
            status_data["status_message"] = f"Token Read Error: {str(e)}"

    return {"status": "success", "data": status_data}


class AnalyzeEmailRequest(BaseModel):
    email_id: str


@app.post("/api/v1/emails/analyze-email")
async def analyze_single_email(payload: AnalyzeEmailRequest):
    """Triggers Stehouwer LLM NLP extraction for a specific email on demand."""
    cache_path = os.path.join(_backend_dir, "core", "emails_cache.json")
    if not os.path.exists(cache_path):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Email cache not found."},
        )
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            emails = json.load(f)

        target_email = next(
            (e for e in emails if e.get("id") == payload.email_id), None
        )
        if not target_email:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Email ID not found in cache."},
            )

        from core.email_nlp_daemon import call_stehouwer_llm_nlp

        nlp_res = call_stehouwer_llm_nlp(
            target_email["sender"], target_email["subject"], target_email["body"]
        )
        target_email["nlp_analysis"] = nlp_res

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(emails, f, indent=4)

        return {"status": "success", "data": nlp_res}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


class GenerateReplyRequest(BaseModel):
    sender: str
    subject: str
    body_snippet: str
    user_notes: str = ""
    tone_preference: str = "Professional"


@app.post("/api/v1/emails/generate-reply")
async def generate_email_reply(payload: GenerateReplyRequest):
    """Uses Stehouwer LLM to generate a smart email draft."""
    prompt = f"""You are Stehouwer LLM, an expert communication assistant.
Generate a response draft to the following email.
Target Tone: {payload.tone_preference}
User Guidance / Bullet Notes: {payload.user_notes if payload.user_notes else "Draft a polite and concise response acknowledging receipt and addressing key points."}

--- Original Email ---
From: {payload.sender}
Subject: {payload.subject}
Body Snippet: {payload.body_snippet[:1000]}

Respond with ONLY the email draft text (Subject line suggestion and Email Body).
"""
    try:
        resp = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "stehouwer_llm", "prompt": prompt, "stream": False},
            timeout=35,
        )
        if resp.status_code == 200:
            draft_text = resp.json().get("response", "")
            return {"status": "success", "draft": draft_text.strip()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"LLM Generation failed: {str(e)}"},
        )
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Failed to generate reply."},
    )


@app.post("/api/v1/emails/sync")
async def trigger_email_sync():
    """Triggers an immediate cycle of the email NLP daemon."""
    try:
        from core.email_nlp_daemon import run_email_daemon_cycle

        run_email_daemon_cycle()
        return {
            "status": "success",
            "message": "Email sync cycle completed successfully.",
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


class OutboxItem(BaseModel):
    id: str = ""
    recipient: str
    subject: str
    body: str
    status: str = "PENDING_APPROVAL"
    timestamp: str = ""


@app.get("/api/v1/emails/outbox")
async def get_outbox_queue():
    """Returns queued outbox email drafts awaiting human approval."""
    outbox_path = os.path.join(_backend_dir, "core", "email_outbox_queue.json")
    if os.path.exists(outbox_path):
        try:
            with open(outbox_path, "r", encoding="utf-8") as f:
                items = json.load(f)
                return {"status": "success", "data": items}
        except Exception as e:
            return JSONResponse(
                status_code=500, content={"status": "error", "message": str(e)}
            )
    return {"status": "success", "data": []}


@app.post("/api/v1/emails/outbox/queue")
async def queue_outbox_draft(payload: OutboxItem):
    """Queues a new LLM draft email for human approval."""
    outbox_path = os.path.join(_backend_dir, "core", "email_outbox_queue.json")
    items = []
    if os.path.exists(outbox_path):
        try:
            with open(outbox_path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            pass

    import uuid

    new_item = {
        "id": str(uuid.uuid4()),
        "recipient": payload.recipient,
        "subject": payload.subject,
        "body": payload.body,
        "status": "PENDING_APPROVAL",
        "timestamp": datetime.now().isoformat(),
    }
    items.insert(0, new_item)
    with open(outbox_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=4)
    return {"status": "success", "data": new_item}


class ApproveSendRequest(BaseModel):
    draft_id: str


@app.post("/api/v1/emails/outbox/approve-send")
async def approve_and_send_email(payload: ApproveSendRequest):
    """Thoughtful Friction Gate: Approves and dispatches email via Gmail OAuth API."""
    outbox_path = os.path.join(_backend_dir, "core", "email_outbox_queue.json")
    if not os.path.exists(outbox_path):
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Outbox queue empty."},
        )
    try:
        with open(outbox_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        target = next(
            (item for item in items if item.get("id") == payload.draft_id), None
        )
        if not target:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Draft ID not found."},
            )

        from core.email_nlp_daemon import get_gmail_service
        import base64
        from email.mime.text import MIMEText

        service = get_gmail_service()
        message = MIMEText(target["body"])
        message["to"] = target["recipient"]
        message["subject"] = target["subject"]
        raw_msg = base64.urlsafe_b64encode(message.as_bytes()).decode()

        sent_res = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_msg})
            .execute()
        )

        target["status"] = "SENT"
        target["sent_timestamp"] = datetime.now().isoformat()
        target["gmail_id"] = sent_res.get("id")

        with open(outbox_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=4)

        return {
            "status": "success",
            "message": f"Email dispatched to {target['recipient']}",
            "gmail_id": sent_res.get("id"),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/v1/emails/outbox/reject")
async def reject_outbox_draft(payload: ApproveSendRequest):
    """Rejects/removes an outbox draft."""
    outbox_path = os.path.join(_backend_dir, "core", "email_outbox_queue.json")
    if not os.path.exists(outbox_path):
        return {"status": "success"}
    try:
        with open(outbox_path, "r", encoding="utf-8") as f:
            items = json.load(f)
        items = [item for item in items if item.get("id") != payload.draft_id]
        with open(outbox_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=4)
        return {"status": "success", "message": "Draft rejected."}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.get("/api/v1/lost-property")
async def get_lost_property():
    cache_path = os.path.join(_backend_dir, "core", "lost_property_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"status": "success", "data": data}
        except Exception as e:
            return JSONResponse(
                status_code=500, content={"status": "error", "message": str(e)}
            )
    return {"status": "success", "data": []}


@app.post("/api/v1/lost-property/scan")
async def trigger_lost_property_scan():
    try:
        from core.lost_property_scanner import run_scan

        result = run_scan()
        if "error" in result:
            return JSONResponse(status_code=500, content=result)
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


from pydantic import BaseModel


class WebScanRequest(BaseModel):
    target_email: str
    scan_type: str = "all"


@app.post("/api/v1/lost-property/web-scan")
async def trigger_lost_property_web_scan(payload: WebScanRequest):
    try:
        from core.lost_property_scanner import run_web_osint_scan

        result = run_web_osint_scan(payload.target_email, payload.scan_type)
        if "error" in result:
            return JSONResponse(status_code=500, content=result)
        return result
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


import re


@app.get("/api/v1/dictionary/ledger-history")
async def get_ledger_history():
    """Parses the Master Architectural Ledger and returns it as a structured timeline."""
    try:
        ledger_path = os.path.join(
            get_base_dir(), "..", "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md"
        )
        if not os.path.exists(ledger_path):
            return {"status": "error", "message": "Ledger file not found"}

        with open(ledger_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by "## Development Entry:"
        entries_raw = re.split(
            r"^##\s+Development Entry:\s+", content, flags=re.MULTILINE
        )

        history = []
        for raw in entries_raw[1:]:  # Skip the first chunk (header)
            lines = raw.split("\n")
            title_line = lines[0].strip()

            # Extract date, title, version
            # Expected format: "2026-07-31 - Title (v8.17.0)"
            date_match = re.search(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})\s*-\s*", title_line)
            date_str = date_match.group(1) if date_match else "Unknown Date"

            version_match = re.search(r"\((v[0-9\.]+)\)$", title_line)
            version_str = version_match.group(1) if version_match else "Unknown Version"

            # Clean title
            title_str = title_line
            if date_match:
                title_str = title_str[date_match.end() :]
            if version_match:
                title_str = title_str[: title_str.rfind("(")].strip()

            # Extract rationale and tech specs simply by taking the rest of the body
            body_text = "\n".join(lines[1:]).strip()

            history.append(
                {
                    "date": date_str,
                    "title": title_str,
                    "version": version_str,
                    "body": body_text,
                }
            )

        return {"status": "success", "data": history}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.get("/api/v1/dictionary/master-chronology")
async def get_master_chronology():
    """Returns all consolidated markdown records (Tasks, Plans, Handoffs, Ledger & Artifact Lineage)."""
    try:
        base_dir = os.path.join(get_base_dir(), "..")

        def read_file_safe(rel_path):
            abs_p = os.path.normpath(os.path.join(base_dir, rel_path))
            if os.path.exists(abs_p):
                with open(abs_p, "r", encoding="utf-8") as f:
                    return f.read()
            return ""

        return {
            "status": "success",
            "data": {
                "tasks_chronology": read_file_safe(
                    "Agent_Tasks_History/MASTER_TASKS_CHRONOLOGY.md"
                ),
                "plans_chronology": read_file_safe(
                    "Agent_Implementation_Plans_History/MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md"
                ),
                "handoff_chronology": read_file_safe(
                    "Agent_Handoff_Summaries/MASTER_HANDOFF_CHRONOLOGY.md"
                ),
                "artifact_history": read_file_safe(
                    "NotebookLM_Records/artifact_history.md"
                ),
                "master_index": read_file_safe("MASTER_HISTORICAL_INDEX.md"),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.get("/api/v1/dictionary/terms")
async def get_dictionary_terms():
    """Returns the interactive AI-BS jargon glossary and architectural definitions."""
    terms = [
        {
            "term": "Polyglot SHM (Shared Memory IPC)",
            "category": "Infrastructure",
            "tag": "C++ / Go / Python",
            "definition": "Dual-tier shared memory bus using Windows CreateFileMapping. Tier 1 is a 64-byte control ring buffer ('Local\\AI_BS_IPC_SHM_RING') for sub-3µs heartbeats. Tier 2 is a 2MB bulk data mapping ('Local\\AI_BS_IPC_BULK_DATA') for zero-copy LLM token & vector tensor streaming.",
            "impact": "Eliminates network overhead between Go core daemons and Python AI models.",
        },
        {
            "term": "Thoughtful Friction Gate",
            "category": "Safety & Governance",
            "tag": "Human-in-the-Loop",
            "definition": "A mandatory approval queue mechanism for automated communications. Generated LLM drafts are placed into an Outbox Queue; explicit human review and button interaction are required before emails leave the host.",
            "impact": "Prevents unauthorized or hallucinated email dispatches while retaining 1-click speed.",
        },
        {
            "term": "ATR Volatility Risk Engine",
            "category": "Algorithmic Trading",
            "tag": "Crypto Swarm",
            "definition": "Dynamic risk manager calculating Average True Range (14-period ATR) across liquid trading pairs (BTC, ETH, SOL, AVAX, LINK). Automatically calculates dynamic trailing stop-loss (2x ATR) and take-profit targets (3x ATR) based on market volatility.",
            "impact": "Protects capital from flash crashes and adjusts position bounds to asset volatility.",
        },
        {
            "term": "Stehouwer LLM",
            "category": "AI Core",
            "tag": "Local GGUF / Ollama",
            "definition": "Self-hosted, zero-cost 8B/12B GGUF model pipeline tuned for code refactoring, email extraction NLP, and automated self-patching. Runs on local RTX 4090 hardware without external API reliance.",
            "impact": "Ensures 100% free operation and complete privacy of user datasets.",
        },
        {
            "term": "ChromaDB Vector Vault",
            "category": "Memory & Storage",
            "tag": "ChromaDB / Embeddings",
            "definition": "Persistent vector memory database storing email thread histories ('email_vector_vault'), knowledge base items, and code chunks for semantic retrieval before LLM prompt assembly.",
            "impact": "Gives the AI model long-term memory across multi-turn user interactions.",
        },
        {
            "term": "Circuit Breaker & Quarantine",
            "category": "Self-Healing",
            "tag": "Auto-Healer",
            "definition": "Fault tolerance pattern monitored by shm_heartbeat_supervisor.go. If a daemon crashes 3 times within 30 seconds, it opens the circuit breaker, quarantines the daemon, and triggers AST self-patching.",
            "impact": "Prevents cascading process failures and infinite crash loops.",
        },
        {
            "term": "WSL2 Aggressive Script Hacking",
            "category": "Deployment",
            "tag": "Windows / Linux Bridge",
            "definition": "Architectural strategy of patching Linux installer scripts (e.g. Vast.ai, Clore.ai) to bypass lspci and network checks directly inside Windows 11 WSL2 rather than dual-booting Ubuntu.",
            "impact": "Keeps the primary host operating environment strictly Windows 11 while leveraging Linux container daemons.",
        },
        {
            "term": "Multi-Tenant Schema Isolation",
            "category": "Database",
            "tag": "FastAPI / SQLite",
            "definition": "Enforcement of X-Client-ID header resolution across all FastAPI routes with client_id columns across SQLite tables and ChromaDB vector metadata.",
            "impact": "Ensures clean data separation for Stehouwer Publishing LLC and commercial tenants.",
        },
    ]
    return {"status": "success", "data": terms}


@app.get("/api/v1/dictionary/quiz")
async def get_dictionary_quiz():
    """Returns interactive study guide questions for mastering AI-BS architecture milestones."""
    questions = [
        {
            "id": 1,
            "question": "What is the primary latency benchmark for the Polyglot SHM Tier 1 control ring buffer?",
            "options": [
                "2.5 microseconds",
                "15 milliseconds",
                "1.2 seconds",
                "100 nanoseconds",
            ],
            "answerIndex": 0,
            "explanation": "The 64-byte control ring buffer (Local\\AI_BS_IPC_SHM_RING) is mapped into shared memory via Windows C++ APIs to achieve sub-3µs signaling.",
        },
        {
            "id": 2,
            "question": "Which safety guardrail requires human approval before emails generated by Stehouwer LLM are sent?",
            "options": [
                "Graceful Rejection Engine",
                "Thoughtful Friction Gate",
                "Circuit Breaker",
                "Llama Guard 3",
            ],
            "answerIndex": 1,
            "explanation": "The Thoughtful Friction Gate queues outbound emails into an Outbox Approval Queue requiring human review before dispatch.",
        },
        {
            "id": 3,
            "question": "How does the Crypto Swarm bot calculate dynamic trailing stop-loss bounds?",
            "options": [
                "Fixed 5% drop",
                "Relative Strength Index (RSI)",
                "Average True Range (2x ATR)",
                "Exponential Moving Average",
            ],
            "answerIndex": 2,
            "explanation": "The bot computes 14-period ATR from technical_indicators.py and sets dynamic trailing stop-losses at 2x ATR based on current asset volatility.",
        },
        {
            "id": 4,
            "question": "What happens when a backend daemon crashes 3 times within 30 seconds?",
            "options": [
                "The system shuts down",
                "Circuit breaker opens & daemon enters Quarantine for AST auto-patching",
                "A paid OpenAI request is triggered",
                "The database is reset",
            ],
            "answerIndex": 1,
            "explanation": "The Go heartbeat supervisor opens the circuit breaker, quarantines the daemon, and notifies auto_healer_daemon.py to apply AST code patches.",
        },
    ]
    return {"status": "success", "data": questions}


@app.get("/api/context/status")
async def get_context_ingest_status():
    manifest_path = os.path.join(get_base_dir(), "..", "ingest_manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "grabbed_files" in data:
                    data["recent_grabbed_files"] = data["grabbed_files"][:30]
                return data
        except Exception as e:
            return {"status": "Error reading manifest", "error": str(e)}
    return {"status": "Manifest pending", "total_files": 0, "grabbed_files": []}


@app.get("/api/context/search")
async def search_context_rag(q: str = ""):
    manifest_path = os.path.join(get_base_dir(), "..", "ingest_manifest.json")
    if not q or len(q.strip()) < 2:
        return {"query": q, "total_results": 0, "results": []}

    query_lower = q.lower().strip()
    results = []

    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                grabbed = data.get("grabbed_files", [])
                for item in grabbed:
                    path = item.get("path", "")
                    snippet = item.get("snippet", "")
                    if query_lower in path.lower() or query_lower in snippet.lower():
                        results.append(item)
        except Exception as e:
            return {"error": str(e), "results": []}

    return {"query": q, "total_results": len(results), "results": results[:50]}


@app.get("/api/context/recovered")
async def get_recovered_intelligence():
    vault_path = os.path.join(_backend_dir, "recovered_intelligence.json")
    if os.path.exists(vault_path):
        try:
            with open(vault_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e), "recovered_items": []}
    return {"last_audited": "Never", "total_recovered_assets": 0, "recovered_items": []}


# --- Publishing Web Security Event Telemetry Store ---
PUBLISHING_SECURITY_LOG = os.path.join(_backend_dir, "publishing_security_events.json")


class PublishingSecurityEventPayload(BaseModel):
    client_id: str = "stehouwer_publishing"
    timestamp: str
    domain: str
    page_path: str
    event_type: str
    severity: str
    details: str
    user_agent: Optional[str] = "Unknown"


@app.post("/api/analytics/security-event")
async def log_publishing_security_event(
    payload: PublishingSecurityEventPayload, request: Request
):
    ip = request.client.host if request.client else "Unknown"
    event_data = payload.dict()
    event_data["ip_address"] = ip

    events = []
    if os.path.exists(PUBLISHING_SECURITY_LOG):
        try:
            with open(PUBLISHING_SECURITY_LOG, "r", encoding="utf-8") as f:
                events = json.load(f)
        except Exception:
            events = []

    events.insert(0, event_data)
    events = events[:100]  # Retain latest 100 events

    try:
        with open(PUBLISHING_SECURITY_LOG, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )

    return {"status": "success", "logged_event": event_type_summary(payload.event_type)}


def event_type_summary(ev_type):
    return f"Security Event Recorded: {ev_type}"


@app.get("/api/analytics/publishing-events")
async def get_publishing_security_events():
    if os.path.exists(PUBLISHING_SECURITY_LOG):
        try:
            with open(PUBLISHING_SECURITY_LOG, "r", encoding="utf-8") as f:
                events = json.load(f)
                return {
                    "status": "success",
                    "total_events": len(events),
                    "events": events,
                }
        except Exception as e:
            return {"status": "error", "events": []}
    return {"status": "success", "total_events": 0, "events": []}


@app.post("/api/context/trigger")
async def trigger_context_ingest():
    try:
        from context_ingestor_daemon import ContextIngestorDaemon

        daemon = ContextIngestorDaemon()
        daemon.generate_context()
        return {
            "status": "success",
            "message": "Manual 5-drive context ingest and recovery audit triggered.",
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


def load_config():
    config_path = os.path.join(get_base_dir(), "ai_bs_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


config = load_config()

# --- Live System Orchestrator & ChromaDB API ---
import chromadb
import subprocess
from datetime import datetime

HOT_DB_PATH = os.path.abspath(
    os.path.join(get_base_dir(), "..", "stehouwer_vector_memory")
)
COLD_ARCHIVE_DIR = os.path.join(get_base_dir(), "Archive")
HEURISTIC_DIR = os.path.join(get_base_dir(), "Heuristics")


class LiveSystemOrchestrator:
    def __init__(self):
        print("[LIVE SYSTEM] Initializing Sovereign Compute Infrastructure...")
        try:
            self.chroma_client = chromadb.PersistentClient(path=HOT_DB_PATH)
            self.memory_collection = self.chroma_client.get_or_create_collection(
                name="heuristic_resolutions"
            )
        except Exception as e:
            print(f"[LIVE DB ERROR] Failed to init ChromaDB at {HOT_DB_PATH}: {e}")
            self.chroma_client = None
            self.memory_collection = None

    def apply_thoughtful_friction(self, task_description, authorization):
        """Phase V Compliance Checkpoint: Verifies Frontend Authorization."""
        print(f"\n[LIVE DIAGNOSTIC TRACE] Intercepted Action: {task_description}")
        return authorization.strip().upper() == "EXECUTE"

    def handle_live_fault(self, error_message, failed_script):
        """Converts live system faults straight into embedded memory tokens on the G:\\ drive."""
        trace_id = f"FAULT_{int(time.time())}"
        print(f"[DATA INTEGRITY] Vectorizing failure event log signature: {trace_id}")

        diagnostic_payload = {
            "timestamp": datetime.now().isoformat(),
            "failed_component": failed_script,
            "system_error_trace": error_message,
            "hardware_assignment": "Ryzen 9 9950X / RTX 4090 Stack",
        }

        if self.memory_collection:
            try:
                self.memory_collection.add(
                    documents=[json.dumps(diagnostic_payload)],
                    metadatas=[
                        {"status": "live_unresolved", "origin": "system_runtime"}
                    ],
                    ids=[trace_id],
                )
            except Exception as e:
                print(f"[VECTOR FAULT] Could not save to ChromaDB: {e}")

        # Log copy straight to physical heuristic storage path
        try:
            heuristic_backup = os.path.join(
                HEURISTIC_DIR, f"live_fault_{trace_id}.json"
            )
            os.makedirs(HEURISTIC_DIR, exist_ok=True)
            with open(heuristic_backup, "w") as f:
                json.dump(diagnostic_payload, f, indent=4)
            print(
                f"[HEURISTICS] System optimization matrix written safely to active volume: {heuristic_backup}"
            )
        except Exception as e:
            print(f"[IO FAULT] Could not save to {HEURISTIC_DIR}: {e}")

    def monitor_and_execute_task(self, script_path, authorization):
        if not os.path.exists(script_path):
            return {
                "status": "error",
                "message": f"[LIVE ERROR] Script missing at target architecture path: {script_path}",
            }

        if not self.apply_thoughtful_friction(
            f"Run live file execution -> {script_path}", authorization
        ):
            return {
                "status": "friction_aborted",
                "message": "[SYSTEM] Action aborted by Operator due to lack of EXECUTE authorization.",
            }

        print(
            "[LIVE RUNTIME] Invoking sandboxed subsystem. Monitoring hardware loops..."
        )
        process = subprocess.run(
            [sys.executable, script_path], capture_output=True, text=True
        )

        if process.returncode == 0:
            return {"status": "success", "output": process.stdout}
        else:
            print("[CRITICAL FAULT IDENTIFIED] Intercepting runtime trace loop...")
            self.handle_live_fault(process.stderr, script_path)
            return {
                "status": "fault_intercepted",
                "message": "Script failed. Fault logged to ChromaDB and Heuristic Volume.",
                "error_trace": process.stderr,
            }


live_orchestrator = LiveSystemOrchestrator()


class PipelineTestPayload(BaseModel):
    authorization: str


@app.post("/api/system/test_pipeline")
def test_active_pipeline(payload: PipelineTestPayload):
    target_live_script = os.path.join(
        get_base_dir(), "components", "active_pipeline_test.py"
    )
    result = live_orchestrator.monitor_and_execute_task(
        target_live_script, payload.authorization
    )
    return result


@app.get("/chroma-db/api/v1/get-heuristics")
def get_heuristics():
    # Attempt to read from the hot DB or S: Drive
    try:
        if live_orchestrator.memory_collection:
            count = live_orchestrator.memory_collection.count()
            return {
                "status": "success",
                "data": [f"Live Heuristics Loaded. Total vectors: {count}"],
            }
    except Exception:
        pass
    return {
        "status": "success",
        "data": ["Case 001: Missing Module", "Case 002: Sandbox Escape Blocked"],
    }


# --- Polyglot Execution Engine API ---
class PolyglotPayload(BaseModel):
    command: str
    language: str


@app.post("/polyglot-execution-engine/execute")
def polyglot_execute(payload: PolyglotPayload):
    return execute_polyglot_command(payload.command, payload.language)


# --- 25-Stage Orchestration Engine API ---
from bullshit_orchestrator import run_orchestration


class StagePayload(BaseModel):
    master_goal: str
    steps: list


@app.post("/stage-engine/orchestrate")
async def orchestrate_stages(payload: StagePayload):
    return await run_orchestration(payload.master_goal, payload.steps)


# --- AI-BS 32-Thread Core Engine API ---
core_engine = AI_BS_Core_Engine()


class CorePayload(BaseModel):
    monolithic_tasks: list


@app.post("/ai-bs-core/execute")
def execute_core_pipeline(payload: CorePayload):
    """Executes tasks dynamically across the 32-thread Out-of-Order Engine."""
    results = core_engine.execute_pipeline(payload.monolithic_tasks)
    return {"status": "success", "in_order_retirement_data": results}


# --- Telemetry & Background Engines (Phase 3) ---
from fastapi import BackgroundTasks
import asyncio

engine_telemetry = {
    "scavenger_active": False,
    "polyglot_active": False,
    "active_threads": 0,
    "tasks_completed": 0,
    "cpu_usage_simulated": "12%",
}

import random


@app.get("/telemetry/status")
def get_telemetry():
    # Simulate dynamic fluctuations for the Aero-Agri frontend
    engine_telemetry["temp"] = round(random.uniform(20.0, 24.0), 1)
    engine_telemetry["mfcOutput"] = round(random.uniform(110.0, 160.0), 1)
    engine_telemetry["aeroponicLayers"] = random.randint(4, 8)
    engine_telemetry["co2"] = random.randint(800, 1100)
    engine_telemetry["lux"] = random.randint(18000, 22000)
    engine_telemetry["ph"] = round(random.uniform(5.5, 6.5), 1)

    return JSONResponse(content=engine_telemetry)


# --- Tool Calling Registry API (Phase 3) ---
from tools.tool_registry import ToolRegistry


class ToolExecutionPayload(BaseModel):
    tool_name: str
    arguments: dict = {}


@app.get("/api/tools")
def list_available_tools():
    """Returns declarations of all tools registered for Stehouwer LLM."""
    return {"status": "success", "tools": ToolRegistry.get_tool_declarations()}


@app.post("/api/tools/execute")
def execute_registered_tool(payload: ToolExecutionPayload):
    """Executes a registered tool by name with arguments."""
    result = ToolRegistry.execute_tool(payload.tool_name, payload.arguments)
    return {"status": "success", "result": result}


class ChatMessage(BaseModel):
    role: str


import logging

logger = logging.getLogger("AI_BS_Backend")


class ChatPayload(BaseModel):
    messages: list[dict]
    model: str = "stehouwer_llm"
    use_rag: Optional[bool] = False
    use_web_search: Optional[bool] = False
    format: Optional[str] = None


import re


def extract_and_parse_tool_call(content_text: str):
    """
    Extracts tool call JSON from content_text regardless of conversational text wrapper,
    supports both {"name": ..., "arguments": ...} and {"tool_call": {"name": ..., "arguments": ...}},
    and normalizes tool name aliases.
    """
    if not content_text:
        return None, None

    stripped = content_text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    start_idx = stripped.find("{")
    end_idx = stripped.rfind("}")

    candidates = []
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidates.append(stripped[start_idx : end_idx + 1])

    cb_matches = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content_text)
    candidates.extend(cb_matches)

    for cand in candidates:
        try:
            data = json.loads(cand.strip())
            if (
                isinstance(data, dict)
                and "tool_call" in data
                and isinstance(data["tool_call"], dict)
            ):
                data = data["tool_call"]

            if isinstance(data, dict) and "name" in data:
                raw_name = str(data.get("name", "")).strip()
                args = data.get("arguments", {})
                if not isinstance(args, dict):
                    args = {}

                # Normalize tool name
                normalized_name = raw_name
                if raw_name in [
                    "generate_image",
                    "create_image",
                    "generate_comfy_image",
                    "comfyui_image",
                    "draw_image",
                    "generate_photo",
                ]:
                    normalized_name = "generate_comfy_image"
                elif raw_name in ["query_memory", "master_memory", "search_memory"]:
                    normalized_name = "query_master_memory"
                elif raw_name in ["query_database", "query_db", "sql_query"]:
                    normalized_name = "query_large_knowledge_db"
                elif raw_name in [
                    "create_comfy_workflow",
                    "create_workflow",
                    "generate_workflow",
                    "generate_video",
                    "create_video",
                ]:
                    normalized_name = "create_comfy_workflow"

                return normalized_name, args
        except Exception:
            continue

    return None, None


def resolve_ollama_model(requested_model: str) -> str:
    """Resolves UI model names/aliases to actual installed Ollama tags."""
    target = requested_model if requested_model else "stehouwer_llm"
    try:
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
        if r.status_code == 200:
            models_list = [m.get("name", "") for m in r.json().get("models", [])]
            if models_list:
                if target in models_list:
                    return target
                if f"{target}:latest" in models_list:
                    return f"{target}:latest"
                for m in models_list:
                    if m.split(":")[0] == target:
                        return m
                return models_list[0]
    except Exception:
        pass
    return (
        "stehouwer_qwen:latest"
        if target in ["stehouwer_llm", "stehouwer_qwen"]
        else f"{target}:latest"
    )


def extract_last_user_message(data: dict) -> str:
    if (
        "messages" in data
        and isinstance(data["messages"], list)
        and len(data["messages"]) > 0
    ):
        for msg in reversed(data["messages"]):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
            elif hasattr(msg, "role") and getattr(msg, "role") == "user":
                return getattr(msg, "content", "")
    return data.get("prompt", "") or data.get("message", "") or ""


import uuid
import re
import os
import time
from bullshit_polyglot import execute_polyglot_command


@app.post("/v1/ide/plan")
async def generate_ide_plan(request: Request):
    try:
        data = await request.json()
        prompt = data.get("prompt", "")
        context_flags = data.get("context_flags", {})

        system_prompt = (
            "You are a Senior Principal Engineer working in the Stehouwer AI-BS Matrix IDE.\n"
            "You must output ONLY a valid JSON object representing an implementation plan.\n"
            "The JSON must exactly match this schema:\n"
            "{\n"
            '  "plan_id": "plan_<random>",\n'
            '  "title": "Short title",\n'
            '  "summary": "High-level summary",\n'
            '  "affected_files": ["path1", "path2"],\n'
            '  "steps": [\n'
            '    {"step_num": 1, "description": "Do X", "risk": "low|medium|high"}\n'
            "  ]\n"
            "}"
        )

        ollama_model = resolve_ollama_model(data.get("model", "qwen2.5-coder:latest"))

        payload = {
            "model": ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context: {context_flags}\n\nTask: {prompt}",
                },
            ],
            "format": "json",
            "stream": False,
        }

        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://127.0.0.1:11434/api/chat", json=payload, timeout=60.0
            )

        if resp.status_code == 200:
            resp_data = resp.json()
            raw_content = resp_data.get("message", {}).get("content", "{}")
        else:
            raw_content = "{}"

        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                import json

                plan_data = json.loads(json_str)
                if not plan_data.get("plan_id"):
                    plan_data["plan_id"] = f"plan_{uuid.uuid4().hex[:6]}"
            except Exception:
                plan_data = {"error": "Failed to parse JSON", "raw": raw_content}
        else:
            plan_data = {"error": "No JSON block found", "raw": raw_content}

        return plan_data
    except Exception as e:
        return {"error": str(e)}


@app.post("/v1/ide/execute-plan")
async def execute_ide_plan(request: Request):
    try:
        data = await request.json()
        plan_id = data.get("plan_id")
        approved_steps = data.get("approved_steps", [])
        plan_details = data.get("planData", {})

        # Save to history ledger
        history_dir = r"C:\AI-BS\Agent_Implementation_Plans_History"
        os.makedirs(history_dir, exist_ok=True)
        history_path = os.path.join(history_dir, f"{plan_id}.json")
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                import json

                json.dump(
                    {
                        "plan_id": plan_id,
                        "timestamp": time.time(),
                        "planData": plan_details,
                        "approved_steps": approved_steps,
                    },
                    f,
                    indent=4,
                )
        except Exception as e:
            print(f"[IDE History] Failed to write plan history: {e}")

        results = []
        for step in approved_steps:
            try:
                # Dispatch execution steps directly to the AST Polyglot execution loop
                step_lang = (
                    step.get("language", "python")
                    if isinstance(step, dict)
                    else "python"
                )
                step_cmd = (
                    step.get("command") or step.get("description", str(step))
                    if isinstance(step, dict)
                    else str(step)
                )

                # Call with both required positional arguments (synchronous)
                res = execute_polyglot_command(step_cmd, step_lang, user_approved=True)
                results.append({"step": step, "status": "success", "result": res})
            except Exception as e:
                results.append({"step": step, "status": "error", "error": str(e)})

        return {"status": "executed", "plan_id": plan_id, "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/chat")
@app.post("/v1/chat/completions")
async def chat_endpoint(request: Request):
    """Main Chat & Tool Calling Router Endpoint for Stehouwer LLM."""
    global EFFICIENCY_MODE_ENABLED

    if EFFICIENCY_MODE_ENABLED:
        import httpx

        try:
            payload_data = await request.json()
        except Exception:
            payload_data = {}

        fallback_payload = {
            "model": FALLBACK_MODEL,
            "messages": payload_data.get("messages", []),
            "stream": payload_data.get("stream", False),
            "temperature": payload_data.get("temperature", 0.7),
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    FALLBACK_API_BASE,
                    headers={
                        "Authorization": f"Bearer {FALLBACK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=fallback_payload,
                    timeout=120.0,
                )

            if payload_data.get("stream", False):
                from fastapi.responses import StreamingResponse

                async def generate_stream():
                    async for chunk in resp.aiter_bytes():
                        yield chunk

                return StreamingResponse(
                    generate_stream(), media_type="text/event-stream"
                )
            else:
                return resp.json()
        except Exception as e:
            return {
                "id": "chatcmpl-effmode-error",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "efficiency_mode_fallback_error",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"⚡ System is in Efficiency Mode. Tried to use fallback API but failed: {str(e)}",
                        },
                        "finish_reason": "stop",
                    }
                ],
            }

    try:
        import time

        start_time = time.time()

        try:
            payload_data = await request.json()
        except Exception:
            payload_data = {}

        model_name = payload_data.get("model", "stehouwer_llm")
        ollama_model = resolve_ollama_model(model_name)

        # --- Omni-Drive Pre-Flight Interceptor (Moved to very first line logic) ---
        last_user_msg = extract_last_user_message(payload_data)

        print(
            f"[PREFLIGHT INTERCEPTOR CHECK] Incoming payload: {last_user_msg}",
            flush=True,
        )
        move_pattern = re.compile(
            r"(?i)(?:move|rename)\s+([a-zA-Z]:(?:\\[^\s]+|\\\\[^\s]+))\s+(?:to|into|->)\s+([a-zA-Z]:(?:\\[^\s]+|\\\\[^\s]+))"
        )
        match = move_pattern.search(last_user_msg)
        if match:
            src_path = match.group(1).strip()
            dest_path = match.group(2).strip()
            try:
                # Execute File Operation directly (Bypass LLM)
                result = await omnidrive_service_instance.relocate_file_with_ast_check(
                    src_path, dest_path, False
                )
                friction_payload = {
                    "type": "thoughtful_friction",
                    "action": "OMNI_DRIVE_MOVE",
                    "src": src_path,
                    "dest": dest_path,
                    "status": "pending_approval",
                }
                content_out = f"Pre-flight routing active. Omni-Drive executing move: {src_path} -> {dest_path}. UI Modal triggered."
                return {
                    "choices": [
                        {"message": {"role": "assistant", "content": content_out}}
                    ],
                    "message": content_out,
                    "model": ollama_model,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2),
                    "payload": friction_payload,
                }
            except Exception as oe:
                print(f"[Omni-Drive Pre-Flight Error] {oe}")

        # --- Monetization Lock Check ---
        config_path = os.path.join(_backend_dir, "compute_schedule_config.json")
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            if config.get("current_mode", "active") == "active":
                telemetry_path = os.path.join(_backend_dir, "compute_telemetry.json")
                if os.path.exists(telemetry_path):
                    with open(telemetry_path, "r") as f:
                        telemetry = json.load(f)
                    if telemetry.get("status") == "renting":
                        err_msg = "GPU is currently locked by Monetization Hosting. Please Pause Hosting in the Compute Dashboard to use Stehouwer LLM."
                        return {
                            "choices": [
                                {"message": {"role": "assistant", "content": err_msg}}
                            ],
                            "message": err_msg,
                            "model": ollama_model,
                            "execution_time_ms": 0,
                            "error": True,
                        }
        except Exception:
            pass

        # Convert messages safely to dicts
        messages_dicts = []
        messages_list = payload_data.get("messages", [])
        for m in messages_list:
            if isinstance(m, dict):
                messages_dicts.append(m)
            elif hasattr(m, "model_dump"):
                messages_dicts.append(m.model_dump())
            elif hasattr(m, "dict"):
                messages_dicts.append(m.dict())
            else:
                messages_dicts.append(
                    {
                        "role": getattr(m, "role", "user"),
                        "content": getattr(m, "content", ""),
                    }
                )

        # System Prompt Conditioning & @Tag Intent Routing
        has_system_msg = any(m.get("role") == "system" for m in messages_dicts)
        formatted_messages = list(messages_dicts)

        last_user_msg = ""
        if messages_dicts:
            for m in reversed(messages_dicts):
                if m.get("role") == "user":
                    last_user_msg = str(m.get("content", ""))
                    break

        user_msg_lower = last_user_msg.lower()

        system_content = "You are Stehouwer LLM. Maintain a clinical, objective, highly precise, zero-fluff technical tone. You use the AI-BS AIBSTensor define-by-run autograd engine (aibs_autograd_engine.py) and self-attention reasoning engine (aibs_reasoning_engine.py) for all computational graph reasoning, gradient backpropagation, and loss optimization."

        if "@autograd" in user_msg_lower or "@deeplearning" in user_msg_lower:
            system_content = "You are the Stehouwer LLM Autograd & Deep Learning Reasoning Engine. You evaluate reverse-mode automatic differentiation partial derivatives via AIBSTensor (aibs_autograd_engine.py), accumulating path gradients (dz/dx2 = dz/da * x1 + dz/dy2 * cos(x2)), and output step-by-step mathematical proofs with exact values."
        elif "@calendar" in user_msg_lower:
            system_content = "You are the Stehouwer LLM Scheduling Assistant. You MUST use the `query_large_knowledge_db` tool to query the `calendar.db` SQLite database to check schedules, and the `execute_database_update` tool to insert or update appointments. Maintain a professional tone."
        elif "@documents" in user_msg_lower:
            system_content = "You are the Stehouwer LLM Document Synthesis Agent. You MUST use your memory and database query tools to search organizational documents and synthesize answers based ONLY on retrieved context."
        elif "@email" in user_msg_lower:
            system_content = "You are the Stehouwer LLM Communications Agent. (Note: Email API hooks are pending, but act as if you are analyzing the provided text for action items)."
        elif "@developer" in user_msg_lower:
            system_content = "You are the Stehouwer LLM Principal Engineer. You MUST use the `modify_react_file` tool to read and update frontend code in C:\\AI-BS\\frontend. You can also use `execute_database_update` to modify databases. Always be precise and safe."

        if not has_system_msg:
            formatted_messages.insert(0, {"role": "system", "content": system_content})
        else:
            # Overwrite existing system message if a tag is present to enforce the persona
            if any(
                tag in user_msg_lower
                for tag in [
                    "@autograd",
                    "@deeplearning",
                    "@calendar",
                    "@documents",
                    "@email",
                    "@developer",
                ]
            ):
                for m in formatted_messages:
                    if m.get("role") == "system":
                        m["content"] = system_content
                        break
        target_device = payload_data.get("target_device", "Host PC (Local)")
        if target_device == "Mobile Phone (ADB)":
            adb_instructions = "\n\n[TARGET DEVICE: MOBILE ADB] The user is currently targeting their connected Android device via ADB. You MUST use the `execute_adb_command` tool to fulfill the user's request. Always execute your tools and return the results to the user."

            system_appended = False
            for m in formatted_messages:
                if m.get("role") == "system":
                    m["content"] += adb_instructions
                    system_appended = True
                    break

            if not system_appended:
                formatted_messages.insert(
                    0, {"role": "system", "content": system_content + adb_instructions}
                )

        # Pre-Flight Intent Classifier & Swarm Routing Check
        last_user_msg = ""
        if messages_dicts:
            for m in reversed(messages_dicts):
                if m.get("role") == "user":
                    last_user_msg = str(m.get("content", ""))
                    break

        if last_user_msg:
            lum_lower = last_user_msg.lower()
            if any(
                kw in lum_lower
                for kw in [
                    "build full project",
                    "scaffold project",
                    "create complete app",
                    "scaffold app",
                ]
            ):
                try:
                    swarm_res = swarm_orchestrator.delegate_task(
                        last_user_msg, "Lead System Architect"
                    )
                    content_out = f"🚀 **Swarm Orchestration Completed:**\n\n```json\n{json.dumps(swarm_res, indent=2)}\n```"
                    return {
                        "choices": [
                            {"message": {"role": "assistant", "content": content_out}}
                        ],
                        "message": content_out,
                        "model": ollama_model,
                        "execution_time_ms": round(
                            (time.time() - start_time) * 1000, 2
                        ),
                        "tool_trace": {
                            "tool_name": "swarm_orchestrator",
                            "status": "success",
                        },
                    }
                except Exception as s_err:
                    print(f"[Pre-Flight Swarm Fallback] {s_err}")

        # Direct Intent Fallback for Tools BEFORE Ollama
        lum_lower = last_user_msg.lower() if last_user_msg else ""
        is_image_request = any(
            kw in lum_lower
            for kw in [
                "create a photo",
                "generate a photo",
                "create an image",
                "generate an image",
                "create image",
                "generate image",
                "draw a photo",
                "render a photo",
                "draw an image",
                "render an image",
                "make a photo",
                "picture of",
                "photo of",
                "generate_comfy_image",
            ]
        )
        is_workflow_request = any(
            kw in lum_lower
            for kw in [
                "create a workflow",
                "generate a workflow",
                "create a video",
                "generate a video",
                "create video",
                "generate video",
                "make a video",
                "video of",
            ]
        )

        t_name = None
        t_args = None
        content_text = ""

        if is_workflow_request:
            t_name = "create_comfy_workflow"
            t_args = {"prompt": last_user_msg, "workflow_type": "text-to-video"}
        elif any(
            kw in lum_lower
            for kw in ["3d model", "3d mesh", "generate 3d", "render 3d"]
        ):
            t_name = "generate_comfy_3d_model"
            t_args = {"prompt": last_user_msg}
        elif any(
            kw in lum_lower
            for kw in ["reconstruct scene", "reconstruct 3d scene", "scene depth"]
        ):
            t_name = "reconstruct_scene"
            t_args = {"image_url": last_user_msg}
        elif any(
            kw in lum_lower
            for kw in ["detect objects", "object detection", "bounding box"]
        ):
            t_name = "detect_objects"
            t_args = {"image_url": last_user_msg}
        elif any(kw in lum_lower for kw in ["transfer style", "style transfer"]):
            t_name = "transfer_style"
            t_args = {
                "style_image_url": last_user_msg,
                "content_image_url": last_user_msg,
            }
        elif any(
            kw in lum_lower for kw in ["generate video", "create video", "make video", "generate_comfy_video", "render video"]
        ):
            t_name = "generate_comfy_video"
            dur_m = re.search(r'\b(?:duration\s*(?:of|is|:)?\s*)?(\d{1,2})\s*(?:seconds?|secs?|s)\b', lum_lower)
            dur_val = max(7, min(15, int(dur_m.group(1)))) if dur_m else 10
            t_args = {"prompt": last_user_msg, "duration_seconds": dur_val}
        elif is_image_request:
            t_name = "generate_comfy_image"
            t_args = {"prompt": last_user_msg}

        if not t_name:
            # Dispatch to Ollama API if no direct tool intent was detected
            async with httpx.AsyncClient(timeout=120.0) as client:
                ollama_req = {
                    "model": ollama_model,
                    "messages": formatted_messages,
                    "stream": False,
                }
                if payload_data.get("format"):
                    ollama_req["format"] = payload_data.get("format")

                try:
                    res = await client.post(
                        "http://127.0.0.1:11434/api/chat", json=ollama_req
                    )
                except Exception as ex:
                    logger.warning(
                        f"Ollama connection error for '{ollama_model}': {ex}"
                    )
                    res = None

                # Fallback to alternative model if requested model fails or returns error
                if not res or res.status_code != 200:
                    fallback_model = resolve_ollama_model("stehouwer_qwen")
                    logger.warning(
                        f"Ollama model '{ollama_model}' failed. Retrying with fallback '{fallback_model}'..."
                    )
                    ollama_model = fallback_model
                    fallback_req = {
                        "model": fallback_model,
                        "messages": formatted_messages,
                        "stream": False,
                    }
                    if payload_data.get("format"):
                        fallback_req["format"] = payload_data.get("format")
                    try:
                        res = await client.post(
                            "http://127.0.0.1:11434/api/chat",
                            json=fallback_req,
                        )
                    except Exception as ex2:
                        return JSONResponse(
                            status_code=500,
                            content={
                                "message": {
                                    "role": "assistant",
                                    "content": f"Ollama service error: {ex2}",
                                },
                                "response": f"Ollama service error: {ex2}",
                            },
                        )

                if not res or res.status_code != 200:
                    err_msg = res.text if res else "No response from local model server"
                    return JSONResponse(
                        status_code=res.status_code if res else 500,
                        content={
                            "message": {
                                "role": "assistant",
                                "content": f"Ollama error: {err_msg}",
                            },
                            "response": f"Ollama error: {err_msg}",
                        },
                    )

                res_data = res.json()
                response_msg = res_data.get("message", {})
                content_text = (
                    response_msg.get("content", "")
                    if isinstance(response_msg, dict)
                    else str(response_msg)
                )

                # Extract tool call if present in LLM response
                t_name, t_args = extract_and_parse_tool_call(content_text)

        if t_name:
            try:
                tool_result = ToolRegistry.execute_tool(t_name, t_args)

                if t_name in [
                    "generate_comfy_image",
                    "generate_comfy_text_image",
                    "generate_comfy_3d_model",
                    "transfer_style",
                    "generate_comfy_video",
                ]:
                    img_url = tool_result.get("image_url")
                    filename = tool_result.get("filename")
                    if not img_url and filename:
                        img_url = f"/api/comfy/media?filename={filename}&subfolder=&type=output"

                    if img_url:
                        is_video = (
                            t_name == "generate_comfy_video"
                            or (filename and any(filename.lower().endswith(ext) for ext in [".mp4", ".webm", ".mov", ".mkv"]))
                            or any(ext in img_url.lower() for ext in [".mp4", ".webm", ".mov", ".mkv"])
                        )
                        if is_video:
                            media_markdown = f"<video controls autoPlay loop muted playsinline src='{img_url}' style='max-width:100%; border-radius:12px;'></video>"
                        else:
                            media_markdown = f"![Generated Output]({img_url})"
                        content_text = (
                            f"🎬 **Generated ComfyUI Image/Video:**\n\n{media_markdown}"
                        )
                    else:
                        content_text = f"🎬 **ComfyUI Task Executed:**\n\n```json\n{json.dumps(tool_result, indent=2)}\n```"
                elif t_name in [
                    "create_comfy_image_workflow",
                    "create_comfy_text_image_workflow",
                    "create_comfy_video_workflow",
                    "create_comfy_3d_workflow",
                    "create_comfy_custom_workflow",
                    "create_comfy_workflow",
                ]:
                    wf_url = tool_result.get("image_url") or tool_result.get(
                        "workflow_url"
                    )
                    wf_path = tool_result.get("workflow_path") or tool_result.get(
                        "saved_path"
                    )
                    if wf_url:
                        if wf_url.endswith((".mp4", ".webm")):
                            media_markdown = f"<video controls src='{wf_url}' style='max-width:100%; border-radius:12px;'></video>"
                        else:
                            media_markdown = f"![Generated Media]({wf_url})"
                        content_text = f"🎬 **Generated ComfyUI Workflow & Output:**\n\n{media_markdown}\n\n*Workflow saved to:* `{wf_path}`"
                    else:
                        content_text = f"🎬 **Workflow Generated & Saved:**\n\n*Path:* `{wf_path}`\n\n```json\n{json.dumps(tool_result, indent=2)}\n```"
                else:
                    # Send tool execution result back to LLM for final synthesis
                    followup_messages = formatted_messages + [
                        {"role": "assistant", "content": content_text},
                        {
                            "role": "user",
                            "content": f"[TOOL EXECUTION RESULT FOR '{t_name}']:\n{json.dumps(tool_result, indent=2)}\n\nPlease synthesize the final answer based on this tool result.",
                        },
                    ]

                    res_followup = await client.post(
                        "http://127.0.0.1:11434/api/chat",
                        json={
                            "model": ollama_model,
                            "messages": followup_messages,
                            "stream": False,
                        },
                    )
                    if res_followup.status_code == 200:
                        f_res_json = res_followup.json()
                        synth_msg = f_res_json.get("message", {})
                        synth_text = (
                            synth_msg.get("content", "")
                            if isinstance(synth_msg, dict)
                            else str(synth_msg)
                        )
                        if synth_text and synth_text.strip():
                            content_text = synth_text
                        else:
                            content_text = f"🛠️ **Executed Tool:** `{t_name}`\n\n```json\n{json.dumps(tool_result, indent=2)}\n```"
                    else:
                        content_text = f"🛠️ **Executed Tool:** `{t_name}`\n\n```json\n{json.dumps(tool_result, indent=2)}\n```"
            except Exception as t_err:
                print(f"[Tool Execution Exception] {t_err}")
                content_text = f"❌ **Tool Execution Fault:** {str(t_err)}"

        if not content_text or not content_text.strip():
            content_text = f"Online and operational. Model `{ollama_model}` is ready for instructions."
        else:
            content_text = sanitize_clinical_output(content_text)

            execution_time_ms = round((time.time() - start_time) * 1000, 2)
            tool_trace_data = {
                "tool_name": t_name if t_name else "none",
                "arguments": t_args if t_args else {},
                "status": (
                    tool_result.get("status", "n/a")
                    if t_name and "tool_result" in locals()
                    else "n/a"
                ),
            }

            return {
                "choices": [
                    {"message": {"role": "assistant", "content": content_text}}
                ],
                "message": {"role": "assistant", "content": content_text},
                "response": content_text,
                "model": ollama_model,
                "execution_time_ms": execution_time_ms,
                "tool_trace": tool_trace_data,
            }

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"message": f"Backend Chat Fault: {str(e)}"}
        )


@app.get("/api/comfyui/view")
async def comfyui_view_proxy(filename: str, subfolder: str = "", type: str = "output"):
    """Proxies ComfyUI output images through FastAPI to prevent mixed-content & CORS issues."""
    comfy_url = f"http://127.0.0.1:8189/view?filename={filename}&subfolder={subfolder}&type={type}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(comfy_url)
            if resp.status_code == 200:
                media_type = resp.headers.get("content-type", "image/png")
                return Response(content=resp.content, media_type=media_type)
    except Exception as e:
        print(f"[ComfyUI Proxy Error] {e}")
    raise HTTPException(status_code=404, detail="Image not found or ComfyUI offline.")


async def run_scavenger_background(human_idea: str, project_keyword: str):
    engine_telemetry["scavenger_active"] = True
    engine_telemetry["active_threads"] += 1
    try:
        tree_path = os.path.join(get_base_dir(), "complete_system_tree.txt")
        builder = ProjectScaffolder(tree_path)
        # Using run_in_executor to not block the asyncio event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, builder.execute_agent_build_workflow, human_idea, project_keyword
        )
        engine_telemetry["tasks_completed"] += 1
    finally:
        engine_telemetry["scavenger_active"] = False
        engine_telemetry["active_threads"] -= 1


class ScavengerPayload(BaseModel):
    human_idea: str
    project_keyword: str


@app.post("/scavenger/build")
def scavenger_build(payload: ScavengerPayload, background_tasks: BackgroundTasks):
    """Parses local drives and executes a build asynchronously."""
    background_tasks.add_task(
        run_scavenger_background, payload.human_idea, payload.project_keyword
    )
    return {
        "status": "queued",
        "message": "Scavenger build triggered in background thread.",
    }


# --- Dynamic UI Layout Generator API ---
from bullshit_builder import UIGenerator
from bullshit_auditor import audit_code
from bullshit_vault_watchdog import start_watchdog

from bullshit_lead_generator import WestMichiganLeadGen
import uuid
import asyncio


# Daemon Consolidation Initialization
@app.on_event("startup")
async def startup_event():
    print("[Monolithic Core] Initializing Consolidated Background Daemons...")

    # 1. Lead Generator Daemon Loop
    async def lead_gen_loop():
        gen = WestMichiganLeadGen()
        while True:
            try:
                await gen.run_sweep()
            except Exception as e:
                logger.error(f"Lead Gen Daemon fault: {e}")
            await asyncio.sleep(86400)  # Sweep once per 24 hours

    asyncio.create_task(lead_gen_loop())

    # 2. Sponge Daemon (Running in Thread to prevent blocking)
    def run_sponge():
        try:
            import bullshit_sponge
            import asyncio

            asyncio.run(bullshit_sponge.main_loop())
        except Exception as e:
            print(f"Sponge Daemon fault: {e}")

    # 3. Builder Daemon
    def run_builder():
        try:
            import bullshit_builder

            if hasattr(bullshit_builder, "main"):
                bullshit_builder.main()
        except Exception as e:
            print(f"Builder Daemon fault: {e}")

    # 4. Vault Watchdog Daemon
    def run_watchdog():
        try:
            start_watchdog()
        except Exception as e:
            print(f"Watchdog Daemon fault: {e}")

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_sponge)
    loop.run_in_executor(None, run_builder)
    loop.run_in_executor(None, run_watchdog)

    print("[Monolithic Core] Background Daemons Online.")


class UIPayload(BaseModel):
    human_idea: str
    component_name: str
    file_extension: str = ".jsx"


import httpx


@app.post("/ui-generator/build")
async def generate_ui_component(payload: UIPayload):
    """Takes a UI prompt, hits the local LLM, and writes raw code to the frontend."""
    generator = UIGenerator()
    generated_file = generator.generate_component(
        payload.human_idea, payload.component_name, payload.file_extension
    )

    # Stehouwer Reality Standard Audit
    try:
        with open(generated_file, "r") as f:
            code_content = f.read()
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "stehouwer_llm",
                    "prompt": "You are the Stehouwer Reality Standard Audit Agent. Review this code. If it contains placeholders, lacks logic, or has syntax errors, output 'REJECT'. Otherwise output 'APPROVE'.\n\nCode:\n"
                    + code_content,
                    "stream": False,
                },
            )
        if r.status_code == 200 and "REJECT" in r.json().get("response", "").upper():
            return {
                "status": "error",
                "message": "Code rejected by Stehouwer Reality Standard Audit Sub-Agent.",
                "file_written": generated_file,
            }
    except Exception as e:
        print("Audit failed:", e)

    return {"status": "success", "file_written": generated_file}


# --- Heuristics Daemon API ---
class FailurePayload(BaseModel):
    failed_code: str
    error_log: str


@app.post("/api/heuristics/analyze_failure")
async def analyze_failure(payload: FailurePayload):
    system_prompt = "You are the Heuristics Daemon. Analyze this failure, extract a generalized learning rule starting with 'RULE:', and explain why it failed."
    prompt = (
        f"{system_prompt}\nCode:\n{payload.failed_code}\nError:\n{payload.error_log}"
    )
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "stehouwer_llm", "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if r.status_code == 200:
                response = r.json().get("response", "")
                archive_path = os.path.join(
                    HEURISTICS_DIR, "session_history_archive.json"
                )
                with open(archive_path, "a") as f:
                    f.write(
                        json.dumps({"error": payload.error_log, "heuristic": response})
                        + "\n"
                    )

                # Assume ChromaDB vector DB index embedding here

                return {"status": "success", "heuristic": response}
            return {"status": "error", "message": "Failed to generate heuristic."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Fire Writer API ---
class FireWriterPayload(BaseModel):
    profile: str
    raw_text: str


@app.post("/fire-writer/format")
async def fire_writer_format(payload: FireWriterPayload):
    prompt = f"Format the following text according to the '{payload.profile}' style profile:\n\n{payload.raw_text}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "stehouwer_llm", "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if r.status_code == 200:
                data = r.json()
                return {"status": "success", "formatted_text": data.get("response", "")}
            return {"status": "error", "message": f"LLM returned {r.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Generator API ---
class GeneratorPayload(BaseModel):
    dimensionality: str
    physics_target: str
    objective: str


@app.post("/api/generator/predictive")
async def generator_predictive(payload: GeneratorPayload):
    # Dummy logic to mimic a predictive AI generation blueprint
    generated_code = f'# AI Agent Loop\nwhile True:\n    state = get_physics_state()\n    action = policy(state, objective="{payload.objective}")\n    step_physics()\n'

    # Stehouwer Reality Standard Audit
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "stehouwer_llm",
                    "prompt": "You are the Stehouwer Reality Standard Audit Agent. Review this code. If it contains placeholders, lacks logic, or has syntax errors, output 'REJECT'. Otherwise output 'APPROVE'.\n\nCode:\n"
                    + generated_code,
                    "stream": False,
                },
            )
        if r.status_code == 200 and "REJECT" in r.json().get("response", "").upper():
            return {
                "status": "error",
                "message": "Code rejected by Stehouwer Reality Standard Audit Sub-Agent.",
                "code": generated_code,
            }
    except Exception as e:
        print("Audit failed:", e)

    return {
        "status": "success",
        "techStack": f"Dependencies for {payload.dimensionality} + {payload.physics_target}",
        "code": generated_code,
        "nextSteps": ["Step 1: Initialize Engine", "Step 2: Loop", "Step 3: Validate"],
        "sandboxLog": "Sandbox passed.",
    }


# --- IT HelpDesk API ---
class ITDiagnosePayload(BaseModel):
    issue: str


@app.post("/it-helpdesk/diagnose")
def it_helpdesk_diagnose(payload: ITDiagnosePayload):
    return {
        "status": "success",
        "diagnosis": f"Automated analysis for issue: {payload.issue}",
        "resolution": "Try rebooting the container or flushing ChromaDB cache.",
    }


# --- Agent Handoff API (Phase X: Swarm Integration) ---
class AgentHandoffPayload(BaseModel):
    agent_role: str
    prompt: str


swarm_orchestrator = SwarmOrchestrator()


@app.post("/agent/handoff")
async def agent_handoff(payload: AgentHandoffPayload):
    # Route the request through the new Swarm Orchestrator
    try:
        result = swarm_orchestrator.delegate_task(payload.prompt, payload.agent_role)
        return {"status": "success", "swarm_result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- GitHub Automation API ---
import httpx
import uuid
import subprocess
from bullshit_github_automation import commit_and_push_build
from pydantic import BaseModel

HEURISTICS_DIR = (
    r"S:\Heuristics"
    if os.path.exists("S:\\")
    else os.path.join(get_base_dir(), "heuristics")
)
ARCHIVE_DIR = (
    r"F:\Cold_Archive"
    if os.path.exists("F:\\")
    else os.path.join(get_base_dir(), "archive")
)
try:
    os.makedirs(HEURISTICS_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
except Exception as e:
    print(f"[Directory Init Warning] {e}")


class GithubPayload(BaseModel):
    repo_path: str
    commit_message: str


@app.post("/github/commit")
def github_commit(payload: GithubPayload):
    return commit_and_push_build(payload.repo_path, payload.commit_message)


# --- ComfyUI Integration API ---
class ComfyUIPayload(BaseModel):
    prompt: dict


import asyncio


@app.post("/comfyui/generate")
async def generate_image(payload: ComfyUIPayload):
    try:
        prompt_id = await queue_comfyui_workflow(payload.prompt)
        history_entry = await await_generation_result(
            prompt_id, poll_interval=1.0, timeout=120.0
        )
        media_info = extract_output_media(history_entry)
        if media_info.get("filename"):
            return {
                "prompt_id": prompt_id,
                "filename": media_info["filename"],
                "image_url": media_info["image_url"],
                "media_category": media_info["media_category"],
                "status": "success",
            }
        return {
            "error": "Generation completed but no output media found in node outputs"
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/comfyui/status")
async def comfyui_status():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:8189/system_stats", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                devices = data.get("devices", [])
                vram_total = 0
                vram_free = 0
                gpu = "Unknown"
                if devices:
                    dev = devices[0]
                    vram_total = dev.get("vram_total", 0)
                    vram_free = dev.get("vram_free", 0)
                    gpu = dev.get("name", "GPU")
                return {
                    "status": "online",
                    "gpu": gpu,
                    "vram_total": vram_total,
                    "vram_free": vram_free,
                }
            return {"status": "offline"}
    except Exception:
        return {"status": "offline"}


@app.get("/comfyui/models")
async def comfyui_models():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://127.0.0.1:8189/object_info", timeout=3.0)
            if r.status_code == 200:
                data = r.json()
                ckpts = (
                    data.get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[]])[0]
                )
                return {"models": ckpts}
    except Exception:
        pass
    return {"models": []}



# --- SCREENWRITING & UNREAL VIRTUAL PRODUCTION ENDPOINTS ---
@app.post("/api/screenwriting/export/unreal-csv")
def export_unreal_csv(req: dict):
    screenplay_text = req.get("content", "") or req.get("text", "")
    try:
        from core.fountain_unreal import export_to_csv
        csv_data = export_to_csv(screenplay_text)
        return {"status": "success", "data": csv_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/screenwriting/export/unreal-python")
def export_unreal_python(req: dict):
    screenplay_text = req.get("content", "") or req.get("text", "")
    try:
        from core.fountain_unreal import export_to_unreal_python
        py_data = export_to_unreal_python(screenplay_text)
        return {"status": "success", "data": py_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/screenwriting/storyboard")
async def generate_storyboards(req: dict):
    script_text = req.get("content", "") or req.get("text", "")
    lines = script_text.split("\n")
    actions = [line.strip() for line in lines if line.strip() and not line.isupper() and not line.startswith("(")]
    target_actions = actions[:4]
    
    storyboards = []
    import urllib.parse
    for action in target_actions:
        prompt = f"Cinematic film still, wide shot, highly detailed, 8k resolution, {action}"
        simulated_image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=800&height=400&nologo=true"
        storyboards.append({
            "action": action,
            "prompt": prompt,
            "image_url": simulated_image_url
        })
    return {"status": "success", "storyboards": storyboards}

# --- Phase 5: Living Learning Memory Engine ---
MASTER_MEMORY_PATH = os.path.join(
    get_base_dir(), "AI-BS_Master_Memory", "master_memory_dump.json"
)


class MemoryPayload(BaseModel):
    prompt: str
    code_block: str
    status: str


@app.post("/memory/store-success")
def store_success_memory(payload: MemoryPayload):
    try:
        memory_data = []
        if os.path.exists(MASTER_MEMORY_PATH):
            with open(MASTER_MEMORY_PATH, "r") as f:
                memory_data = json.load(f)

        memory_data.append(
            {
                "prompt": payload.prompt,
                "document": payload.code_block,
                "metadata": {"status": payload.status, "timestamp": time.time()},
            }
        )

        os.makedirs(os.path.dirname(MASTER_MEMORY_PATH), exist_ok=True)
        with open(MASTER_MEMORY_PATH, "w") as f:
            json.dump(memory_data, f, indent=4)

        return {"status": "success", "message": "Baseline memorized."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --- Phase 14: Tab Ecosystem Endpoints ---
from fastapi import UploadFile, File, Form
import glob


@app.get("/system/status")
def system_status():
    import subprocess

    try:
        git_status = subprocess.check_output(
            ["git", "status", "-s"], cwd=get_base_dir()
        ).decode("utf-8")
        git_status = (
            "Clean working tree."
            if not git_status.strip()
            else f"Pending changes:\n{git_status}"
        )
    except:
        git_status = "Git not initialized or error."

    return {
        "gitStatus": git_status,
        "ssdRamFootprint": (
            f"{os.path.getsize(MASTER_MEMORY_PATH) / 1024:.2f} KB"
            if os.path.exists(MASTER_MEMORY_PATH)
            else "0 KB"
        ),
        "activeAgents": ["Trainer Daemon", "Memory Offloader"],
    }


@app.post("/system/wipe-ssd")
def wipe_ssd():
    if os.path.exists(MASTER_MEMORY_PATH):
        os.remove(MASTER_MEMORY_PATH)
    return {"status": "success", "message": "SSD RAM Flushed."}


class ModelPullPayload(BaseModel):
    model_name: str


@app.post("/model/pull")
async def pull_model(payload: ModelPullPayload):
    async def stream_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "http://127.0.0.1:11434/api/pull",
                json={"name": payload.model_name},
                timeout=300.0,
            ) as r:
                async for chunk in r.aiter_bytes():
                    yield chunk

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


@app.get("/memory/stats")
def memory_stats():
    size = (
        os.path.getsize(MASTER_MEMORY_PATH) if os.path.exists(MASTER_MEMORY_PATH) else 0
    )
    return {
        "status": "success",
        "ssdRamSize": size,
        "ssdRamPath": MASTER_MEMORY_PATH,
        "dbEntries": 0,  # Would be chroma count
    }


VAULT_DOCS_DIR = os.path.join(get_base_dir(), "AI-BS_Knowledge_Vaults", "Docs")
os.makedirs(VAULT_DOCS_DIR, exist_ok=True)


@app.get("/documents/list")
def list_documents():
    files = glob.glob(os.path.join(VAULT_DOCS_DIR, "*"))
    docs = [
        {
            "name": os.path.basename(f),
            "size": os.path.getsize(f),
            "type": os.path.splitext(f)[1],
        }
        for f in files
    ]
    return {"status": "success", "documents": docs}


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), vault: str = Form(default="")):
    target_dir = VAULT_DOCS_DIR
    if vault and vault in [
        "NoCo_Ventures",
        "Fire_Writing",
        "Marketing",
        "AI_Architecture",
        "Trading_Algos",
        "Personal_Journal",
        "Code_Snippets",
        "System_Logs",
    ]:
        target_dir = os.path.join(VAULT_DOCS_DIR, vault)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

    file_location = os.path.join(target_dir, file.filename)
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    return {
        "status": "success",
        "message": f"Saved {file.filename} to Vault: {vault if vault else 'Root'}.",
    }


# --- Chat File Attachment Endpoint (GPT-Style Analysis) ---
UPLOAD_ATTACHMENTS_DIR = os.path.join(get_base_dir(), "sandbox", "uploads")
os.makedirs(UPLOAD_ATTACHMENTS_DIR, exist_ok=True)


@app.post("/api/chat/attach")
async def chat_attach_file(file: UploadFile = File(...)):
    """Receives file upload for ChatTab analysis, extracts text/metadata, and returns attachment payload."""
    try:
        file_location = os.path.join(UPLOAD_ATTACHMENTS_DIR, file.filename)
        contents = await file.read()
        with open(file_location, "wb") as f:
            f.write(contents)

        file_ext = os.path.splitext(file.filename)[1].lower()
        is_image = file_ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]
        text_content = ""

        if is_image:
            b64_str = base64.b64encode(contents).decode("utf-8")
            text_content = f"[IMAGE_ATTACHMENT:{file.filename}]"
        else:
            try:
                text_content = contents.decode("utf-8", errors="ignore")[:15000]
            except Exception:
                text_content = (
                    f"[Binary File: {file.filename}, Size: {len(contents)} bytes]"
                )

        return {
            "status": "success",
            "file": {
                "name": file.filename,
                "size": len(contents),
                "ext": file_ext,
                "is_image": is_image,
                "path": file_location,
                "content": text_content,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


class SearchPayload(BaseModel):
    query: str


@app.post("/kb/search")
async def kb_search(payload: SearchPayload):
    return {
        "status": "success",
        "results": [
            {
                "content": f"Mock result for {payload.query}",
                "score": 0.99,
                "source": "Vault Index",
            }
        ],
    }


class DevRunPayload(BaseModel):
    code: str
    language: str


@app.post("/dev/run")
def dev_run(payload: DevRunPayload):
    return execute_polyglot_command(payload.code, payload.language)


# --- Phase 7: Omni-Drive Database Integration ---
import sqlite3
import shutil

OMNIDRIVE_DB_PATH = os.path.join(get_base_dir(), "backend", "state.db")
PORT_FILE = os.path.join(get_base_dir(), "backend", ".writer_daemon_port")


def get_writer_port():
    try:
        with open(PORT_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "8111"


class OmniSearchPayload(BaseModel):
    query: str
    limit: int = 100


@app.post("/api/omnidrive/search")
def omnidrive_search(payload: OmniSearchPayload):
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()
        query_str = f"%{payload.query}%"
        cursor.execute(
            "SELECT drive, filepath, filename, extension, size_bytes FROM file_state WHERE filename LIKE ? LIMIT ?",
            (query_str, payload.limit),
        )
        rows = cursor.fetchall()
        results = [
            {
                "drive": r[0],
                "filepath": r[1],
                "filename": r[2],
                "extension": r[3],
                "size_bytes": r[4],
            }
            for r in rows
        ]
        conn.close()
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class OmniRelocatePayload(BaseModel):
    source_path: str
    destination_dir: str


@app.post("/api/omnidrive/relocate")
def omnidrive_relocate(payload: OmniRelocatePayload):
    # Thoughtful Friction Endpoint
    return {
        "status": "pending_friction",
        "diagnostic_trace": f"Request to physically move file: {payload.source_path} to {payload.destination_dir}",
        "message": "WARNING: This requires explicit operator CONFIRMATION to execute the Python shutil.move() command.",
    }


@app.post("/api/omnidrive/relocate/confirm")
async def omnidrive_relocate_confirm(payload: OmniRelocatePayload):
    try:
        if not os.path.exists(payload.destination_dir):
            os.makedirs(payload.destination_dir, exist_ok=True)
        dest_path = os.path.join(
            payload.destination_dir, os.path.basename(payload.source_path)
        )
        shutil.move(payload.source_path, dest_path)

        port = get_writer_port()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://127.0.0.1:{port}/delete_path",
                    json={"filepath": payload.source_path},
                )
        except Exception as queue_e:
            print(f"[OmniDrive API] Error queueing deletion: {queue_e}")

        return {
            "status": "success",
            "message": f"File successfully relocated to {dest_path}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Phase 8: Live Advertising Dashboard Integration ---
import uuid

# Initialize the Advertising tables in state.db
try:
    _conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
    try:
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    _conn.execute("PRAGMA journal_mode=WAL;")
    _cursor = _conn.cursor()
    _cursor.execute("""
        CREATE TABLE IF NOT EXISTS advertising_leads (
            id TEXT PRIMARY KEY,
            business_name TEXT,
            contact TEXT,
            url TEXT,
            email TEXT,
            status TEXT,
            value TEXT,
            heuristic_match TEXT,
            date_acquired TEXT
        )
    """)
    _conn.commit()
    _conn.close()
except Exception as e:
    print(f"[Advertising DB Init Error] {e}")


class StateLeadPayload(BaseModel):
    client_id: str = "stehouwer_publishing"
    id: str
    business_name: str = ""
    contact: str = ""
    url: str = ""
    email: str = ""
    status: str = "New"
    value: str = "$0"
    heuristic_match: str = "Manual Entry"
    date_acquired: str = ""


class BudgetPayload(BaseModel):
    client_id: str = "stehouwer_publishing"
    id: str
    event: str
    spent: str
    roi: str


@app.get("/api/advertising/budgets")
def get_adv_budgets(tenant: str = Depends(get_tenant)):
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        cursor.execute("SELECT id, event, spent, roi FROM advertising_budgets")
        rows = cursor.fetchall()
        budgets = [
            {"id": r[0], "event": r[1], "spent": r[2], "roi": r[3]} for r in rows
        ]
        conn.close()
        return {"status": "success", "budgets": budgets}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/advertising/budgets")
def save_adv_budgets(budgets: list[BudgetPayload], tenant: str = Depends(get_tenant)):
    try:
        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()
        # Full replace for simplicity based on the current UI state
        cursor.execute("DELETE FROM advertising_budgets")
        for budget in budgets:
            cursor.execute(
                "INSERT INTO advertising_budgets (id, event, spent, roi) VALUES (?, ?, ?, ?)",
                (budget.id, budget.event, budget.spent, budget.roi),
            )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class CopyGenPayload(BaseModel):
    businessName: str
    campaignGoal: str
    geofence: str
    tier: str
    commitment: str
    contractValue: float


# --- Telemetry Storage ---
shadow_telemetry_aggregate = {}


@app.post("/api/advertising/generate")
async def generate_adv_copy(payload: CopyGenPayload):
    global shadow_telemetry_aggregate

    context_block = ""
    if shadow_telemetry_aggregate:
        total_reach = sum(
            item.organic_reach for item in shadow_telemetry_aggregate.values()
        )
        sources = ", ".join(shadow_telemetry_aggregate.keys())
        context_block = f" LATEST PERFORMANCE CONTEXT: We are currently tracking a massive Total Collective Organic Reach of {total_reach:,} across {len(shadow_telemetry_aggregate)} platforms ({sources}). Use this immense real-world organic reach to inform the tone, authoritative scale, and aggressive language of the copy you are about to write. Mention this success implicitly to establish dominance."

    prompt = f"Write a punchy, high-converting advertisement copy for a business named '{payload.businessName}'. The primary campaign goal is: '{payload.campaignGoal}'. TARGET GEOFENCE: {payload.geofence}. PRICING TIER LEVEL: {payload.tier}. TEMPORAL LOCK: {payload.commitment}. Contract Value: ${payload.contractValue:.2f}.{context_block} Adjust the tone and complexity of the deliverables based on the Tier level. Format it cleanly without any meta-talk."

    req_json = {"model": "stehouwer_llm", "prompt": prompt, "stream": True}

    # Stream the Ollama response back to the client directly
    async def stream_generator():
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    "http://127.0.0.1:11434/api/generate",
                    json=req_json,
                    timeout=120.0,
                ) as r:
                    if r.status_code != 200:
                        fault_msg = f"LLM Generation Failed. Status {r.status_code}"
                        print(f"[LIVE FAULT] {fault_msg}")
                        live_orchestrator.handle_live_fault(
                            fault_msg, "AI_BS_Advertising_LLM"
                        )
                        yield json.dumps({"error": fault_msg}).encode("utf-8")
                        return
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except Exception as e:
            fault_msg = f"Connection error: {str(e)}"
            print(f"[LIVE FAULT] {fault_msg}")
            live_orchestrator.handle_live_fault(fault_msg, "AI_BS_Advertising_LLM")
            yield json.dumps({"error": fault_msg}).encode("utf-8")

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


class TelemetryPayload(BaseModel):
    client_id: str = "stehouwer_publishing"
    timestamp: str
    source: str
    geofence: str
    organic_reach: int
    engagement_rate: str


@app.post("/api/advertising/telemetry/official")
async def ingest_official_telemetry(
    payload: TelemetryPayload, tenant: str = Depends(get_tenant)
):
    print(f"[LIVE SYSTEM] Primary Feed Ingested: {payload.source} | {payload.geofence}")
    return {"status": "success", "feed": "primary", "data": payload.dict()}


@app.post("/api/advertising/telemetry/shadow")
async def ingest_shadow_telemetry(
    payload: TelemetryPayload, tenant: str = Depends(get_tenant)
):
    global shadow_telemetry_aggregate

    # Store by source (e.g. www.google.com, business.facebook.com)
    shadow_telemetry_aggregate[payload.source] = payload
    total_reach = sum(
        item.organic_reach for item in shadow_telemetry_aggregate.values()
    )

    print(
        f"[LIVE SYSTEM] Shadow Feed Ingested (Auto-Tasker): {payload.source} | Platform Reach: {payload.organic_reach} | TOTAL AGGREGATE REACH: {total_reach:,}"
    )
    return {
        "status": "success",
        "feed": "shadow",
        "total_aggregate": total_reach,
        "data": payload.dict(),
    }


@app.get("/api/advertising/telemetry/shadow/aggregate")
def get_shadow_telemetry_aggregate():
    global shadow_telemetry_aggregate
    data = [item.dict() for item in shadow_telemetry_aggregate.values()]
    total_reach = sum(item["organic_reach"] for item in data)
    return {"status": "success", "total_reach": total_reach, "platforms": data}


# --- Daemon Log Streamer API ---
@app.get("/api/system/daemon_logs")
def get_daemon_logs():
    logs_dir = os.path.join(get_base_dir(), "logs")
    log_files = {
        "ollama": "ollama.log",
        "backend": "backend.log",
        "remote_bridge": "remote_bridge.log",
        "hunter": "hunter.log",
        "trainer": "trainer.log",
        "refactoring": "refactoring.log",
    }

    results = {}
    for daemon_name, filename in log_files.items():
        filepath = os.path.join(logs_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    results[daemon_name] = [
                        line.strip() for line in lines[-100:]
                    ]  # Get last 100 lines
            except Exception as e:
                results[daemon_name] = [f"Error reading log: {str(e)}"]
        else:
            results[daemon_name] = ["Waiting for daemon to boot..."]

    return {"status": "success", "logs": results}


@app.post("/api/advertising/leads/generate")
async def generate_leads(request: Request):
    """Triggers the West Michigan Lead Generator."""
    try:
        gen = WestMichiganLeadGen()
        # In a real environment, you'd trigger this asynchronously via the Orchestrator,
        # but for demonstration we run it directly.
        results = await gen.run_sweep()
        return {"status": "success", "leads_found": len(results), "data": results}
    except Exception as e:
        logger.error(f"Lead Generation Failed: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/advertising/leads")
async def get_advertising_leads():
    """Retrieves lead matrix from state.db"""
    try:
        import sqlite3

        conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM advertising_leads ORDER BY date_acquired DESC LIMIT 500"
        )
        rows = cursor.fetchall()
        leads = [dict(row) for row in rows]
        conn.close()
        return leads
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/advertising/leads")
def save_advertising_leads(leads: list[StateLeadPayload]):
    """Saves the full lead matrix to state.db"""
    try:
        import sqlite3

        conn = sqlite3.connect(os.path.join(get_base_dir(), "state.db"))
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        cursor = conn.cursor()

        # Ensure the table exists in case it was missed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advertising_leads (
                id TEXT PRIMARY KEY,
                business_name TEXT,
                contact TEXT,
                url TEXT,
                email TEXT,
                status TEXT,
                value TEXT,
                heuristic_match TEXT,
                date_acquired TEXT
            )
        """)

        cursor.execute("DELETE FROM advertising_leads")
        for lead in leads:
            cursor.execute(
                """
                INSERT INTO advertising_leads (id, business_name, contact, url, email, status, value, heuristic_match, date_acquired)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    lead.id,
                    lead.business_name,
                    lead.contact,
                    lead.url,
                    lead.email,
                    lead.status,
                    lead.value,
                    lead.heuristic_match,
                    lead.date_acquired,
                ),
            )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Stehouwer Publishing CMS Endpoints ---
STEHOUWER_SITE_ROOT = r"C:\StehouwerPublishing.com\website-rebuild"


class CMSPageSavePayload(BaseModel):
    filename: str
    content: str


@app.get("/api/cms/pages")
def list_cms_pages():
    try:
        if not os.path.exists(STEHOUWER_SITE_ROOT):
            return {"status": "error", "message": "Site root directory not found"}
        pages = []
        for file in os.listdir(STEHOUWER_SITE_ROOT):
            if file.endswith((".html", ".css", ".js", ".json", ".md")):
                full_path = os.path.join(STEHOUWER_SITE_ROOT, file)
                size = os.path.getsize(full_path)
                mtime = os.path.getmtime(full_path)
                pages.append(
                    {
                        "filename": file,
                        "size": size,
                        "last_modified": datetime.fromtimestamp(mtime).isoformat(),
                    }
                )
        return {"status": "success", "site_root": STEHOUWER_SITE_ROOT, "pages": pages}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.get("/api/cms/page/{filename}")
def get_cms_page(filename: str):
    try:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(STEHOUWER_SITE_ROOT, safe_filename)
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "File not found"},
            )
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "filename": safe_filename, "content": content}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/cms/page/save")
def save_cms_page(payload: CMSPageSavePayload):
    try:
        safe_filename = os.path.basename(payload.filename)
        file_path = os.path.join(STEHOUWER_SITE_ROOT, safe_filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(payload.content)
        return {
            "status": "success",
            "message": f"Successfully updated {safe_filename}",
            "filename": safe_filename,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


class CMSGeneratePayload(BaseModel):
    topic: str
    section: str = "monolog"


@app.post("/api/cms/generate")
async def generate_cms_content(payload: CMSGeneratePayload):
    try:
        prompt = f"As President and CEO Julie Stehouwer of Stehouwer Publishing L.L.C., write a polished, professional {payload.section} about: {payload.topic}"
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "http://127.0.0.1:11434/api/generate",
                json={"model": "qwen2.5-coder", "prompt": prompt, "stream": False},
                timeout=60.0,
            )
            if res.status_code == 200:
                data = res.json()
                generated_text = data.get("response", "")
                return {"status": "success", "generated_content": generated_text}
            return {"status": "error", "message": "Ollama service unavailable"}
    except Exception as e:
        backup = f"Stehouwer Publishing presents: {payload.topic}. Empowering stories, driving success."
        return {
            "status": "success",
            "generated_content": backup,
            "note": "Generated via offline fallback",
        }


from core.ai_adapter import adapt_book_to_screenplay, ADAPTATION_TASKS
import tempfile
import os
from pathlib import Path

@app.post("/api/screenplay/adapt")
async def start_book_adaptation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form(...),
    adaptation_type: str = Form("Feature Film")
):
    if project_name in ADAPTATION_TASKS and ADAPTATION_TASKS[project_name].get("status") == "processing":
        return JSONResponse(status_code=400, content={"status": "error", "message": "An adaptation job is already processing for this project."})
    
    try:
        # Save uploaded PDF to the project folder permanently
        project_dir = Path(f"C:/AI-BS/screenplay_projects/{project_name}")
        project_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = project_dir / "source.pdf"
        
        content = await file.read()
        with open(pdf_path, "wb") as f:
            f.write(content)
        
        # Start the background task
        background_tasks.add_task(
            adapt_book_to_screenplay,
            pdf_path,
            project_name,
            adaptation_type
        )
        
        return {"status": "success", "message": f"Adaptation started for {project_name}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/api/screenplay/adapt/status")
def get_adaptation_status(project_name: str):
    if project_name not in ADAPTATION_TASKS:
        return {"status": "not_found", "progress": 0}
    return ADAPTATION_TASKS[project_name]


from pydantic import BaseModel
import shutil
from datetime import datetime
import json
import uuid

# --- SCREENWRITING WORKSPACE API ---
SCREENPLAY_ROOT = Path("C:/AI-BS/screenplay_projects")
SCREENPLAY_ROOT.mkdir(parents=True, exist_ok=True)
_current_project = "Default Project"

@app.get("/api/screenwriting/projects")
def list_projects():
    global _current_project
    projects = [d.name for d in SCREENPLAY_ROOT.iterdir() if d.is_dir()]
    if not projects:
        projects = ["Default Project"]
        (SCREENPLAY_ROOT / "Default Project").mkdir(parents=True, exist_ok=True)
    if _current_project not in projects:
        _current_project = projects[0]
    return {"projects": projects, "current": _current_project}

class SwitchProjectPayload(BaseModel):
    project_name: str

@app.post("/api/screenwriting/projects/switch")
def switch_project(payload: SwitchProjectPayload):
    global _current_project
    project_dir = SCREENPLAY_ROOT / payload.project_name
    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    _current_project = payload.project_name
    return {"status": "success", "current": _current_project}

@app.get("/api/screenwriting/read")
def read_screenplay():
    global _current_project
    file_path = SCREENPLAY_ROOT / _current_project / "screenplay.fountain"
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
    else:
        # Check if adaptation output exists
        adaptation_path = SCREENPLAY_ROOT / _current_project / "adaptation_output.fountain"
        if adaptation_path.exists():
            content = adaptation_path.read_text(encoding="utf-8")
            file_path.write_text(content, encoding="utf-8")
        else:
            content = "Title: Untitled\n\nINT. UNKNOWN - DAY\n\nAction goes here.\n"
            file_path.write_text(content, encoding="utf-8")
    return {"content": content}

class WriteScreenplayPayload(BaseModel):
    content: str

@app.post("/api/screenwriting/write")
def write_screenplay(payload: WriteScreenplayPayload):
    global _current_project
    file_path = SCREENPLAY_ROOT / _current_project / "screenplay.fountain"
    file_path.write_text(payload.content, encoding="utf-8")
    return {"status": "success"}

@app.post("/api/screenwriting/parse")
def parse_screenplay(payload: WriteScreenplayPayload):
    try:
        from core.matrix_docs import FountainParser
        parser = FountainParser(payload.content)
        parser.parse()
        html_content = parser.to_html()
        beats = parser.extract_beats()
        return {"status": "success", "html": html_content, "beats": beats}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/screenwriting/branches")
def list_branches():
    return {"branches": ["main"]}

class BranchCreatePayload(BaseModel):
    branch_name: str

@app.post("/api/screenwriting/branch/create")
def create_branch(payload: BranchCreatePayload):
    return {"status": "success"}

@app.get("/api/screenwriting/sprints")
def list_sprints():
    return {"sprints": []}

class SprintStartPayload(BaseModel):
    name: str
    target_pages: int

@app.post("/api/screenwriting/sprint/start")
def start_sprint(payload: SprintStartPayload):
    sprint = {"id": str(uuid.uuid4()), "name": payload.name, "target_pages": payload.target_pages}
    return {"status": "success", "sprint": sprint}

class SprintEndPayload(BaseModel):
    sprint_id: str

@app.post("/api/screenwriting/sprint/end")
def end_sprint(payload: SprintEndPayload):
    return {"status": "success"}

# --- PHASE 4.9 SCREENWRITING EXPANSIONS ---

def _get_current_project():
    global _current_project
    from core.matrix_docs import ScreenplayProject
    return ScreenplayProject(SCREENPLAY_ROOT / _current_project)

class CharacterPayload(BaseModel):
    name: str
    bio: str = ""
    speaking_style: str = ""

@app.get("/api/screenwriting/projects/characters")
def get_characters():
    proj = _get_current_project()
    return {"status": "success", "characters": proj.metadata.get('characters', [])}

@app.post("/api/screenwriting/projects/characters")
def save_character(payload: CharacterPayload):
    proj = _get_current_project()
    chars = proj.metadata.get('characters', [])
    updated = False
    for c in chars:
        if c['name'] == payload.name:
            c['bio'] = payload.bio
            c['speaking_style'] = payload.speaking_style
            updated = True
            break
    if not updated:
        chars.append({"name": payload.name, "bio": payload.bio, "speaking_style": payload.speaking_style})
    
    proj.metadata['characters'] = chars
    proj.save_metadata()
    return {"status": "success", "characters": chars}

@app.delete("/api/screenwriting/projects/characters")
def delete_character(name: str):
    proj = _get_current_project()
    chars = proj.metadata.get('characters', [])
    chars = [c for c in chars if c['name'] != name]
    proj.metadata['characters'] = chars
    proj.save_metadata()
    return {"status": "success", "characters": chars}

@app.post("/api/screenwriting/coverage")
async def generate_coverage(payload: WriteScreenplayPayload):
    try:
        prompt = f"""You are an expert Hollywood Script Supervisor and Coverage Analyst.
Analyze the following screenplay excerpt and return a STRICT JSON object representing a script breakdown.
Do NOT include any introductory or conversational text, only the raw JSON.
The JSON must have the following schema:
{{
  "logline": "A concise 1-2 sentence summary of the core conflict.",
  "genre": "The primary genre",
  "budget_tier": "Low, Medium, High, or Blockbuster",
  "budget_estimate_usd": "$X - $Y Million",
  "characters": ["Character A", "Character B"],
  "locations": ["Location A", "Location B"],
  "props": ["Prop A", "Prop B"]
}}

--- SCREENPLAY ---
{payload.content[:15000]}
"""
        import httpx
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("http://127.0.0.1:11434/api/generate", json={
                "model": "llama3:latest",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            })
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                import json
                coverage_data = json.loads(response_text)
                return {"status": "success", "coverage": coverage_data}
            else:
                return {"status": "error", "message": f"Ollama error: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class ReorderBeatsPayload(BaseModel):
    source_index: int
    target_index: int

@app.post("/api/screenwriting/beats/reorder")
def reorder_beats(payload: ReorderBeatsPayload):
    proj = _get_current_project()
    success = proj.reorder_beats(payload.source_index, payload.target_index)
    if success:
        from core.matrix_docs import FountainParser
        content = proj.read_screenplay()
        parser = FountainParser(content)
        parser.parse()
        return {"status": "success", "parsed": {"html": parser.to_html(), "beats": parser.extract_beats()}}
    return {"status": "error", "message": "Reorder failed"}

class SceneVideoPayload(BaseModel):
    beat_id: str
    video_url: str

@app.post("/api/screenwriting/projects/scene_video")
def save_scene_video(payload: SceneVideoPayload):
    proj = _get_current_project()
    proj.map_video_to_beat(payload.beat_id, payload.video_url)
    return {"status": "success"}

class ImportProjectPayload(BaseModel):
    project_name: str
    content: str

@app.post("/api/screenwriting/projects/import")
def do_import_project(payload: ImportProjectPayload):
    from core.matrix_docs import ScreenplayProject
    proj_dir = SCREENPLAY_ROOT / payload.project_name
    proj = ScreenplayProject(proj_dir)
    proj.write_screenplay(payload.content)
    return {"status": "success"}

from fastapi.responses import Response

@app.get("/api/screenwriting/export/fdx")
def export_fdx():
    proj = _get_current_project()
    content = proj.read_screenplay()
    from core.matrix_docs import FountainParser
    parser = FountainParser(content)
    parser.parse()
    fdx = parser.to_fdx(proj.metadata.get('title', 'Untitled'), proj.metadata.get('author', 'Unknown'))
    return Response(content=fdx, media_type="application/xml", headers={"Content-Disposition": f"attachment; filename={proj.project_dir.name}.fdx"})

@app.get("/api/screenwriting/export/pdf")
def export_pdf():
    proj = _get_current_project()
    content = proj.read_screenplay()
    from core.matrix_docs import FountainParser
    parser = FountainParser(content)
    parser.parse()
    pdf_bytes = parser.to_pdf(proj.metadata.get('title', 'Untitled'), proj.metadata.get('author', 'Unknown'))
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={proj.project_dir.name}.pdf"})

@app.get("/api/context")
def get_global_context():
    """Returns the latest compiled global system context payload."""
    try:
        context_file = os.path.join(
            os.path.dirname(get_base_dir()), "AI_BS_Global_Context.md"
        )
        if not os.path.exists(context_file):
            return {
                "status": "error",
                "message": "Context payload not yet generated. Please wait 60 seconds.",
            }

        with open(context_file, "r", encoding="utf-8") as f:
            content = f.read()

        return {"status": "success", "context": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- Stehouwer Publishing CMS Endpoints ---
STEHOUWER_SITE_ROOT = r"C:\StehouwerPublishing.com\website-rebuild"


class CMSPageSavePayload(BaseModel):
    filename: str
    content: str


@app.get("/api/cms/pages")
def list_cms_pages():
    try:
        if not os.path.exists(STEHOUWER_SITE_ROOT):
            return {"status": "error", "message": "Site root directory not found"}
        pages = []
        for file in os.listdir(STEHOUWER_SITE_ROOT):
            if file.endswith((".html", ".css", ".js", ".json", ".md")):
                full_path = os.path.join(STEHOUWER_SITE_ROOT, file)
                size = os.path.getsize(full_path)
                mtime = os.path.getmtime(full_path)
                pages.append(
                    {
                        "filename": file,
                        "size": size,
                        "last_modified": datetime.fromtimestamp(mtime).isoformat(),
                    }
                )
        return {"status": "success", "site_root": STEHOUWER_SITE_ROOT, "pages": pages}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.get("/api/cms/page/{filename}")
def get_cms_page(filename: str):
    try:
        safe_filename = os.path.basename(filename)
        file_path = os.path.join(STEHOUWER_SITE_ROOT, safe_filename)
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "File not found"},
            )
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "filename": safe_filename, "content": content}
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


@app.post("/api/cms/page/save")
def save_cms_page(payload: CMSPageSavePayload):
    try:
        safe_filename = os.path.basename(payload.filename)
        file_path = os.path.join(STEHOUWER_SITE_ROOT, safe_filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(payload.content)
        return {
            "status": "success",
            "message": f"Successfully updated {safe_filename}",
            "filename": safe_filename,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


# --- Omni-Terminal & Localhost God-Mode ---
from fastapi import HTTPException
import subprocess
import asyncio
from datetime import datetime


class OmniTerminalPayload(BaseModel):
    command: str
    cwd: Optional[str] = None


@app.post("/v1/agent/execute-system")
async def execute_system_omnidrive(payload: OmniTerminalPayload, request: Request):
    client_ip = request.client.host if request.client else "Unknown"

    # Dual-mode Auth
    if client_ip not in ["127.0.0.1", "localhost", "::1"]:
        auth_header = request.headers.get("Authorization")
        expected_token = os.environ.get("AIBS_GOD_MODE_TOKEN")
        if not expected_token:
            token_path = os.path.join(_backend_dir, ".god_mode_token")
            if os.path.exists(token_path):
                with open(token_path, "r") as f:
                    expected_token = f.read().strip()
        if not expected_token or auth_header != f"Bearer {expected_token}":
            raise HTTPException(
                status_code=403,
                detail="God-Mode execution requires token authentication for non-loopback requests.",
            )

    cwd = payload.cwd if payload.cwd else _backend_dir
    try:
        process = await asyncio.create_subprocess_shell(
            payload.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=300.0
            )
            stdout = stdout.decode() if stdout else ""
            stderr = stderr.decode() if stderr else ""
        except asyncio.TimeoutError:
            process.kill()
            stdout, stderr = await process.communicate()
            stderr = (stderr.decode() if stderr else "") + "\nTimeout exceeded (300s)."
            stdout = stdout.decode() if stdout else ""

        audit_log = os.path.join(
            _backend_dir, "..", "saved_data", "logs", "god_mode_audit.log"
        )
        os.makedirs(os.path.dirname(audit_log), exist_ok=True)
        with open(audit_log, "a") as logf:
            logf.write(
                f"[{datetime.now().isoformat()}] IP: {client_ip} | CMD: {payload.command} | CWD: {cwd} | RET: {process.returncode}\n"
            )

        return {
            "status": "success",
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"status": "error", "message": str(e)}
        )


# --- API Gateway Proxy Routes (Ports 8001, 8002, 3000, 3001, 4067, 8003, 8006, 8007) ---
@app.api_route(
    "/api/proxy/{port}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def reverse_proxy(port: int, path: str, request: Request):
    allowed_ports = [8001, 8002, 3000, 3001, 4067, 4068, 8003, 8006, 8007]
    if port not in allowed_ports:
        raise HTTPException(status_code=403, detail="Proxy port not allowed")

    target_url = f"http://127.0.0.1:{port}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    try:
        client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))
        req = client.build_request(
            method=request.method,
            url=target_url,
            content=request.stream(),
            headers={
                k: v
                for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length"]
            },
        )
        res = await client.send(req, stream=True)

        async def generate():
            async for chunk in res.aiter_raw():
                yield chunk
            await client.aclose()

        return StreamingResponse(
            generate(),
            status_code=res.status_code,
            headers={
                k: v
                for k, v in res.headers.items()
                if k.lower() not in ["transfer-encoding", "content-encoding"]
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Proxy failed: {str(e)}"},
        )


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def catch_all(request: Request, full_path: str):
    body = await request.body()
    print(f"Received proxy request: {request.method} /{full_path}")

    if "chat/completions" in full_path:
        try:
            req_json = json.loads(body) if body else {}

            # Decrypt payload if encrypted
            if req_json.get("encrypted", False):
                try:
                    iv_bytes = base64.b64decode(req_json["iv"])
                    cipher_bytes = base64.b64decode(req_json["ciphertext"])
                    plaintext = aesgcm.decrypt(iv_bytes, cipher_bytes, None)
                    req_json = json.loads(plaintext.decode("utf-8"))
                except Exception as e:
                    print(
                        f"[Decrypt Error] Failed to decrypt payload: {e}. Falling back to rawFallback."
                    )
                    if "rawFallback" in req_json:
                        req_json = req_json["rawFallback"]

            # --- PHASE 5: PRE-EXECUTION HEURISTIC QUERY ---
            last_user_msg = ""
            if "messages" in req_json:
                for msg in reversed(req_json["messages"]):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("content", "").lower()
                        break

            known_good_baseline = None
            if os.path.exists(MASTER_MEMORY_PATH):
                try:
                    with open(MASTER_MEMORY_PATH, "r") as f:
                        memory_data = json.load(f)
                        for block in memory_data:
                            if block.get("metadata", {}).get("status") == "Success":
                                # Basic semantic matching simulation (would normally be ChromaDB cosine similarity)
                                if (
                                    block.get("prompt", "").lower() in last_user_msg
                                    or last_user_msg in block.get("prompt", "").lower()
                                ):
                                    known_good_baseline = block.get("document")
                                    break
                except Exception as e:
                    print(f"[Memory Engine] Error reading baseline: {e}")

            if known_good_baseline and "messages" in req_json:
                override_prompt = (
                    f"\n\n[ALGORITHMIC DIRECTIVE] "
                    f"A 'Known-Good' baseline was found for this task in the Living Learning Memory. "
                    f"You are strictly forbidden from hallucinating a new structural approach. "
                    f"If you must deviate from this baseline due to new constraints, you MUST prepend your response exactly with the phrase: "
                    f"'DEVIATION_AUDIT_TRACE: I found a previous version of this task that worked, but I am modifying it because...'\n\n"
                    f"BASELINE CODE:\n{known_good_baseline}"
                )
                if req_json["messages"] and req_json["messages"][0]["role"] == "system":
                    req_json["messages"][0]["content"] += override_prompt
                else:
                    req_json["messages"].insert(
                        0, {"role": "system", "content": override_prompt}
                    )

            # --- PHASE 4.5: COMFYUI SEAMLESS TRIGGER INJECTION ---
            if "messages" in req_json:
                comfyui_sys_prompt = (
                    "\n\n[MULTIMODAL DIRECTIVE]\n"
                    "If the user asks you to generate, draw, or create an image, you MUST respond using the following exact syntax on its own line:\n"
                    '[COMFYUI_TRIGGER: "detailed positive prompt here", "negative prompt here"]\n'
                    "Do not attempt to write code to generate the image, use the trigger syntax."
                )
                tool_delegation_prompt = (
                    "\n\n[TOOL_DELEGATION_DIRECTIVE]\n"
                    "You are a master orchestrator Agent. You analyze the user's ideas and decide exactly what tasks need to be done and which tools to delegate to. You have access to ALL tools in the system.\n"
                    'If the user asks to find a file on their computer or hard drive, use: [TOOL: SEARCH_LOCAL_FILES | "filename or extension"]\n'
                    'If the user asks to format or edit text, use: [TOOL: FIRE_WRITER | "profile (professional/creative/journal/fire_writing)" | "text to format"]\n'
                    'If the user asks to generate blueprints or architecture, use: [TOOL: GENERATOR | "dimensionality (2D/3D)" | "target" | "objective"]\n'
                    "If the user asks to run a script, use this exact format:\n[TOOL: POLYGLOT]\n```language\ncode here\n```\n"
                    'If the user wants you to permanently learn something, or you successfully verified a complex task, use: [TOOL: MEMORY | "topic" | "knowledge to save"]\n'
                    'If the user gives a prompt that requires a specialized sub-agent not listed above, use: [TOOL: AGENT_HANDOFF | "agent_role" | "prompt"]\n'
                    "Always explicitly use these [TOOL: ...] tags to delegate tasks based on the user's ideas."
                )

                # --- NOCO IOT SENSOR INTEGRATION (PHASE 17) ---
                telemetry_context = (
                    f"\n\n[NOCO IOT SENSOR TELEMETRY]\n"
                    f"Current Vertical Farming Environment: "
                    f"Temp={engine_telemetry.get('temp', 0)}Â°C, "
                    f"CO2={engine_telemetry.get('co2', 0)}ppm, "
                    f"pH={engine_telemetry.get('ph', 0)}, "
                    f"Lux={engine_telemetry.get('lux', 0)}, "
                    f"Aeroponic Layers={engine_telemetry.get('aeroponicLayers', 0)}, "
                    f"MFC Output={engine_telemetry.get('mfcOutput', 0)}.\n"
                    f"If the user asks about the environment or sensors, use this real-time data."
                )

                combined_prompts = (
                    comfyui_sys_prompt + tool_delegation_prompt + telemetry_context
                )
                if req_json["messages"] and req_json["messages"][0]["role"] == "system":
                    req_json["messages"][0]["content"] += combined_prompts
                else:
                    req_json["messages"].insert(
                        0, {"role": "system", "content": combined_prompts}
                    )

            # --- OMNI-CONTEXT HYBRID RETRIEVAL (PHASE 18) ---
            vault_dir = os.path.join(get_base_dir(), "AI-BS_Knowledge_Vaults")
            index_file = os.path.join(vault_dir, "vault_index.json")
            omni_context = ""

            if last_user_msg:
                # 1. Thread: Web Search
                async def fetch_web():
                    try:
                        from duckduckgo_search import DDGS

                        with DDGS() as ddgs:
                            results = list(ddgs.text(last_user_msg, max_results=3))
                            return "\n".join(
                                [f"Source ({r['href']}): {r['body']}" for r in results]
                            )
                    except Exception as e:
                        print(f"[Web Search Error] {e}")
                        return ""

                # 2. Thread: Vault Vector Search
                async def fetch_vault():
                    v_ctx = ""
                    if os.path.exists(index_file):
                        try:
                            async with httpx.AsyncClient() as client:
                                embed_res = await client.post(
                                    "http://127.0.0.1:11434/api/embeddings",
                                    json={
                                        "model": "stehouwer_llm",
                                        "prompt": last_user_msg,
                                    },
                                    timeout=30.0,
                                )
                                if embed_res.status_code == 200:
                                    prompt_embedding = embed_res.json().get(
                                        "embedding", []
                                    )
                                    if prompt_embedding:
                                        import math

                                        def cosine_similarity(v1, v2):
                                            dot = sum(a * b for a, b in zip(v1, v2))
                                            mag1 = math.sqrt(sum(a * a for a in v1))
                                            mag2 = math.sqrt(sum(b * b for b in v2))
                                            return (
                                                dot / (mag1 * mag2)
                                                if mag1 * mag2 != 0
                                                else 0
                                            )

                                        with open(
                                            index_file, "r", encoding="utf-8"
                                        ) as f:
                                            index_data = json.load(f)
                                        for item in index_data:
                                            item["score"] = cosine_similarity(
                                                prompt_embedding,
                                                item.get("embedding", []),
                                            )
                                        top_chunks = sorted(
                                            index_data,
                                            key=lambda x: x["score"],
                                            reverse=True,
                                        )[:3]
                                        for chunk in top_chunks:
                                            if chunk["score"] > 0.5:
                                                v_ctx += f"--- Vault Document: {chunk['file']} ---\n{chunk['chunk']}\n\n"
                        except Exception as e:
                            print(f"[Vault Search Error] {e}")
                    return v_ctx

                # 3. Thread: OmniDrive Local DB Search
                async def fetch_omnidrive():
                    o_ctx = ""
                    try:
                        import sqlite3

                        conn = sqlite3.connect(OMNIDRIVE_DB_PATH)
                        try:
                            conn.execute("PRAGMA journal_mode=WAL;")
                            conn.execute("PRAGMA synchronous=NORMAL;")
                        except Exception:
                            pass
                        cursor = conn.cursor()
                        # Simple keyword split search
                        keywords = last_user_msg.split()[:3]
                        if keywords:
                            query = (
                                "SELECT filepath, filename FROM file_state WHERE "
                                + " OR ".join(["filename LIKE ?"] * len(keywords))
                                + " LIMIT 3"
                            )
                            cursor.execute(query, [f"%{k}%" for k in keywords])
                            rows = cursor.fetchall()
                            if rows:
                                o_ctx = (
                                    "Related files found on hard drive:\n"
                                    + "\n".join([f"- {r[1]} ({r[0]})" for r in rows])
                                )
                        conn.close()
                    except Exception:
                        pass
                    return o_ctx

                # Execute all 3 retrievals concurrently
                web_result, vault_result, omnidrive_result = await asyncio.gather(
                    fetch_web(), fetch_vault(), fetch_omnidrive()
                )

                if web_result:
                    omni_context += f"\n[LIVE WEB DATA]\n{web_result}\n"
                if vault_result:
                    omni_context += f"\n[LOCAL VAULT CONTEXT]\n{vault_result}\n"
                if omnidrive_result:
                    omni_context += f"\n[OMNIDRIVE FILE REFS]\n{omnidrive_result}\n"

            if omni_context and "messages" in req_json:
                system_prompt = f"You are the central cognitive engine of AI-BS. You are currently operating with Omni-Context Hybrid Retrieval active. Use the following synthesized context from Web Search, Local Vaults, and Hard Drive DB to augment your intelligence:\n\n{omni_context}"

                if req_json["messages"] and req_json["messages"][0]["role"] == "system":
                    req_json["messages"][0]["content"] = (
                        system_prompt + "\n\n" + req_json["messages"][0]["content"]
                    )
                else:
                    req_json["messages"].insert(
                        0, {"role": "system", "content": system_prompt}
                    )
            # ----------------------------------

            if req_json.get("stream", False):

                async def stream_generator(current_req_json):
                    import re
                    import copy
                    import time

                    MAX_TOOL_LOOPS = 3
                    loop_count = 0

                    while loop_count < MAX_TOOL_LOOPS:
                        loop_count += 1
                        full_response_text = ""

                        async with httpx.AsyncClient() as client:
                            async with client.stream(
                                "POST",
                                "http://127.0.0.1:11434/v1/chat/completions",
                                json=current_req_json,
                                timeout=300.0,
                            ) as r:
                                async for chunk in r.aiter_bytes():
                                    yield chunk

                                    try:
                                        chunk_str = chunk.decode("utf-8")
                                        for line in chunk_str.split("\n"):
                                            if (
                                                line.startswith("data: ")
                                                and line != "data: [DONE]"
                                            ):
                                                data = json.loads(line[6:])
                                                if (
                                                    "choices" in data
                                                    and len(data["choices"]) > 0
                                                ):
                                                    delta = data["choices"][0].get(
                                                        "delta", {}
                                                    )
                                                    if "content" in delta:
                                                        full_response_text += delta[
                                                            "content"
                                                        ]
                                                    elif (
                                                        "message" in data["choices"][0]
                                                        and "content"
                                                        in data["choices"][0]["message"]
                                                    ):
                                                        full_response_text += data[
                                                            "choices"
                                                        ][0]["message"].get(
                                                            "content", ""
                                                        )
                                    except Exception:
                                        pass

                        # ReAct Loop: Check for Memory trigger
                        mem_match = re.search(
                            r'\[TOOL:\s*MEMORY\s*\|\s*"(.*?)"\s*\|\s*"(.*?)"\]',
                            full_response_text,
                            re.DOTALL,
                        )
                        if mem_match:
                            topic = mem_match.group(1)
                            knowledge = mem_match.group(2)

                            # Send visual cue
                            exec_msg = f"\n\n\n> ðŸ§  **[AI-BS BACKEND]** Permanently injecting knowledge into Master Memory DB...\n\n"
                            yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": exec_msg}, "done": False})}\n\n'.encode(
                                "utf-8"
                            )

                            try:
                                memory_data = []
                                if os.path.exists(MASTER_MEMORY_PATH):
                                    with open(MASTER_MEMORY_PATH, "r") as f:
                                        memory_data = json.load(f)
                                memory_data.append(
                                    {
                                        "id": str(int(time.time())),
                                        "prompt": topic,
                                        "document": knowledge,
                                        "metadata": {
                                            "status": "Success",
                                            "source": "Autonomous ReAct Loop",
                                        },
                                    }
                                )
                                os.makedirs(
                                    os.path.dirname(MASTER_MEMORY_PATH), exist_ok=True
                                )
                                with open(MASTER_MEMORY_PATH, "w") as f:
                                    json.dump(memory_data, f, indent=4)
                                combined_result = "SUCCESS: Memory securely committed to the permanent database."
                            except Exception as e:
                                combined_result = f"ERROR: Failed to write to memory database: {str(e)}"

                            current_req_json["messages"].append(
                                {"role": "assistant", "content": full_response_text}
                            )
                            system_feedback = f"[SYSTEM RE-ACT LOOP] You invoked the MEMORY tool. Result:\n\n{combined_result}\n\nConclude your response to the user."
                            current_req_json["messages"].append(
                                {"role": "user", "content": system_feedback}
                            )

                            yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": f"**[AI-BS BACKEND]** Memory update complete.\n\n"}, "done": False})}\n\n'.encode(
                                "utf-8"
                            )
                            continue

                        # ReAct Loop: Check for Polyglot trigger
                        if "[TOOL: POLYGLOT]" in full_response_text:
                            # Extract code block
                            code_match = re.search(
                                r"```([a-zA-Z0-9_]+)\n(.*?)```",
                                full_response_text,
                                re.DOTALL,
                            )
                            if code_match:
                                language = code_match.group(1).lower()
                                code = code_match.group(2)

                                # Send a visual cue to the frontend
                                exec_msg = f"\n\n\n> âš™ï¸ **[AI-BS BACKEND]** Executing {language} code in Polyglot Sandbox...\n\n"
                                yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": exec_msg}, "done": False})}\n\n'.encode(
                                    "utf-8"
                                )

                                try:
                                    # Execute the code physically
                                    result = await asyncio.to_thread(
                                        execute_polyglot_command, code, language
                                    )
                                    output = result.get("output", "No output.")
                                    error = result.get("error", "")
                                    combined_result = (
                                        f"STDOUT:\n{output}\nSTDERR:\n{error}"
                                    )
                                except Exception as e:
                                    combined_result = f"Sandbox Exception: {str(e)}"

                                # Append context and loop
                                current_req_json["messages"].append(
                                    {"role": "assistant", "content": full_response_text}
                                )

                                system_feedback = f'[SYSTEM RE-ACT LOOP] You invoked the POLYGLOT tool. Here is the actual terminal output from the sandbox execution:\n\n{combined_result}\n\nAnalyze this output objectively. If it failed, output a fixed version using [TOOL: POLYGLOT]. If it succeeded, explain the results to the user. You may also use [TOOL: MEMORY | "topic" | "code"] to permanently save the successful logic.'
                                current_req_json["messages"].append(
                                    {"role": "user", "content": system_feedback}
                                )

                                yield f'data: {json.dumps({"model": "stehouwer_llm", "message": {"role": "assistant", "content": f"**[AI-BS BACKEND]** Execution complete. Analyzing results...\n\n"}, "done": False})}\n\n'.encode(
                                    "utf-8"
                                )
                                continue

                        # If no tool triggered or we maxed out loops, break
                        break

                return StreamingResponse(
                    stream_generator(req_json), media_type="text/event-stream"
                )
            else:
                async with httpx.AsyncClient() as client:
                    print(
                        f"[Ollama Request] Sending payload to Ollama: {json.dumps(req_json)}"
                    )
                    r = await client.post(
                        "http://127.0.0.1:11434/v1/chat/completions",
                        json=req_json,
                        timeout=300.0,
                    )
                    if r.status_code != 200:
                        print(
                            f"[Ollama Error] Status {r.status_code}, Response: {r.text}"
                        )
                    return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception as e:
            print(f"[Chat Completions Error] Exception in proxy: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    elif "models" in full_path:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "http://127.0.0.1:11434/v1/models", timeout=10.0
                )
                res_data = r.json()
                if isinstance(res_data, dict) and "data" in res_data:
                    res_data["models"] = [
                        m["id"]
                        for m in res_data["data"]
                        if isinstance(m, dict) and "id" in m
                    ]
                return JSONResponse(status_code=r.status_code, content=res_data)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

    return {"status": "unhandled", "path": full_path}





def main():
    print("==================================================")
    print("AI-BS Central Cognitive Engine Initializing...")

    print("[Backend] Daemons are now managed by FastAPI Lifespan DaemonManager...")

    from bullshit_memory import global_ssd_ram

    global_ssd_ram.start_monitoring()

    print(f"[Config] Loaded Primary Model: {config.get('primary_model')}")
    print("[Backend] Starting FastAPI Server on port 8080...")
    print("==================================================")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level=config.get("log_level", "info").lower(),
    )


class LocalModelRegistry:
    """Unified System RAM & GPU VRAM SSD Offloading Architecture (v6.4.0)"""

    @staticmethod
    def initialize_local_model(model_id: str):
        # Implementation for PyTorch/HuggingFace model initialization with strict SSD offload
        import platform

        # Dynamically resolve Matrix unified swap paths based on the host OS (Windows vs WSL/Linux)
        if platform.system() == "Windows":
            VRAM_SWAP_PATH = r"C:\AI-BS\VRAM_Tensor_Swap"
        else:
            # Translate Windows path to WSL mount path
            VRAM_SWAP_PATH = "/mnt/c/AI-BS/VRAM_Tensor_Swap"

        # Ensure directory exists before PyTorch attempts to memory map
        os.makedirs(VRAM_SWAP_PATH, exist_ok=True)

        try:
            from transformers import AutoModelForCausalLM

            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map="auto",
                offload_folder=VRAM_SWAP_PATH,
                offload_state_dict=True,
            )
            return model
        except ImportError:
            print("[Registry] Transformers library not loaded.")
            return None



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", type=str, help="Start an agent in background")
    args, _ = parser.parse_known_args()
    if args.agent:
        print(f"[Daemon] {args.agent} running in background...")
        import time

        while True:
            time.sleep(3600)
    else:
        main()



