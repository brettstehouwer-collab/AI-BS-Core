"""
AI-BS Headless Matrix Boot Orchestrator
Dispatches all core engines and background daemons with dedicated logging and port verification.
"""

import os
import sys
import subprocess
import time
import socket

BASE_DIR = r"C:\AI-BS"
PY_EXE = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
CHROMA_EXE = r"C:\AI-BS\pyppeteer_env\Scripts\chroma.exe"
LOG_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(LOG_DIR, exist_ok=True)

def is_port_open(port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.3)
        res = s.connect_ex(('127.0.0.1', port))
        s.close()
        return res == 0
    except Exception:
        return False

def spawn_daemon(name, cmd, cwd=BASE_DIR, env=None):
    log_out = open(os.path.join(LOG_DIR, f"{name}.out.log"), "a", encoding="utf-8")
    log_err = open(os.path.join(LOG_DIR, f"{name}.err.log"), "a", encoding="utf-8")
    
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
        
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=merged_env,
        stdout=log_out,
        stderr=log_err,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    print(f"[BOOT] Spawned {name:<25} (PID: {proc.pid})")
    return proc

def boot_all():
    print("=" * 80)
    print("              AI-BS SOVEREIGN MATRIX ENGINE BOOT SEQUENCE")
    print("=" * 80)

    # 1. Ollama Sovereign
    ollama_env = {
        "CUDA_VISIBLE_DEVICES": "0",
        "OLLAMA_IGPU_ENABLE": "0",
        "OLLAMA_MODELS": r"E:\AI_BS_Resources\Ollama",
        "OLLAMA_HOST": "0.0.0.0:11434",
        "OLLAMA_KEEP_ALIVE": "15m",
        "OLLAMA_NUM_PARALLEL": "1",
        "OLLAMA_MAX_LOADED_MODELS": "1",
        "OLLAMA_FLASH_ATTENTION": "1"
    }
    ollama_exe = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
    if os.path.exists(ollama_exe):
        spawn_daemon("ollama_11434", [ollama_exe, "serve"], cwd=BASE_DIR, env=ollama_env)
        
    # Also spawn E-Drive Ollama on 11435 if separate instance configured
    ollama_env_11435 = ollama_env.copy()
    ollama_env_11435["OLLAMA_HOST"] = "0.0.0.0:11435"
    if os.path.exists(ollama_exe):
        spawn_daemon("ollama_11435", [ollama_exe, "serve"], cwd=BASE_DIR, env=ollama_env_11435)

    # 2. ChromaDB (Port 8002)
    if os.path.exists(CHROMA_EXE):
        spawn_daemon("chromadb_8002", [CHROMA_EXE, "run", "--path", r"E:\AI_BS_Resources\ChromaDB", "--port", "8002", "--host", "127.0.0.1"])

    # 3. Node Backend (Port 3001)
    spawn_daemon("node_backend_3001", ["node.exe", "server.js"], cwd=os.path.join(BASE_DIR, "backend"))

    # 4. FastAPI Core Backend (Port 8080)
    spawn_daemon("fastapi_backend_8080", [PY_EXE, "AI_BS_Backend.py"], cwd=os.path.join(BASE_DIR, "backend"))

    # 5. Go Matrix Gateway (Port 8000)
    go_exe = os.path.join(BASE_DIR, "go-core", "aibs_engine.exe")
    if os.path.exists(go_exe):
        spawn_daemon("go_gateway_8000", [go_exe], cwd=os.path.join(BASE_DIR, "go-core"))

    # 6. SHM WebSocket Gateway (Port 8010)
    spawn_daemon("shm_gateway_8010", [PY_EXE, "shm_websocket_gateway.py"], cwd=os.path.join(BASE_DIR, "backend"))

    # 7. Daemons (Gemini MCP 8099, Broadcast Kernel 8088, Social 8006, VST 8013, Crypto 8007)
    spawn_daemon("gemini_mcp_8099", [PY_EXE, "gemini_mcp_server.py"], cwd=os.path.join(BASE_DIR, "backend"))
    spawn_daemon("broadcast_kernel_8088", [PY_EXE, "aibs_broadcast_kernel.py"], cwd=os.path.join(BASE_DIR, "backend"))
    spawn_daemon("broadcast_daemon_8005", [PY_EXE, "aibs_broadcast_daemon.py"], cwd=os.path.join(BASE_DIR, "backend"))
    spawn_daemon("social_daemon_8006", [PY_EXE, "aibs_social_daemon.py"], cwd=os.path.join(BASE_DIR, "backend"))
    spawn_daemon("vst_daemon_8013", [PY_EXE, "aibs_vst_daemon.py"], cwd=os.path.join(BASE_DIR, "backend"))
    spawn_daemon("crypto_trader_8007", [PY_EXE, "crypto_trader_bot.py"], cwd=os.path.join(BASE_DIR, "backend"))

    # 8. Cloudflared Tunnel
    cloudflared_exe = os.path.join(BASE_DIR, "cloudflared.exe")
    if os.path.exists(cloudflared_exe):
        spawn_daemon("cloudflared_tunnel", [cloudflared_exe, "tunnel", "run", "ai-bs"])

    # 9. Frontend Vite Dev Server (Port 5173)
    if not is_port_open(5173):
        spawn_daemon("frontend_vite_5173", ["cmd.exe", "/c", "npm", "run", "dev"], cwd=os.path.join(BASE_DIR, "frontend"))

    print("-" * 80)
    print("Waiting 5 seconds for sockets to bind...")
    time.sleep(5)

    # Verification Sweep
    ports_to_verify = [
        (8080, "FastAPI Core Backend"),
        (11434, "Ollama Primary"),
        (11435, "Ollama E-Drive"),
        (8002, "ChromaDB Store"),
        (3001, "Node Backend"),
        (8000, "Go Gateway"),
        (8010, "SHM Telemetry Gateway"),
        (8099, "Gemini MCP"),
        (8088, "Broadcast Kernel"),
        (8006, "Social Hub"),
        (8007, "Crypto Trader"),
        (5173, "Vite Frontend")
    ]

    print("\n--- Socket Verification ---")
    active_cnt = 0
    for port, sname in ports_to_verify:
        ok = is_port_open(port)
        if ok:
            active_cnt += 1
            print(f"  * Port {port:<6} [{sname:<28}] : \033[92mONLINE\033[0m")
        else:
            print(f"  * Port {port:<6} [{sname:<28}] : [STARTING / PENDING]")

    print("=" * 80)
    print(f"Boot Summary: {active_cnt}/{len(ports_to_verify)} target matrix sockets verified active.")
    print("=" * 80)

if __name__ == "__main__":
    boot_all()
