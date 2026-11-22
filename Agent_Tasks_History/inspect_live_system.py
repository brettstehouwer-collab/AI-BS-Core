import psutil
import socket
import os
import glob
import requests
import json

print("=== ACTIVE AI-BS PROCESSES & PORTS ===")
ports_to_check = [
    (8000, "Go Gateway / aibs_engine"),
    (8001, "ChromaDB Memory (Local)"),
    (8002, "ChromaDB Resource (E:)"),
    (8005, "AI-BS Broadcast Daemon"),
    (8006, "AI-BS Social Daemon"),
    (8007, "Crypto Trader Bot"),
    (8010, "SHM WebSocket Gateway"),
    (8013, "VST3 Audio Daemon"),
    (8080, "FastAPI Master Backend"),
    (8088, "AI-BS Broadcast Kernel"),
    (8089, "Nginx HLS Stream (WSL2)"),
    (8099, "Gemini MCP Server"),
    (8189, "ComfyUI Media Engine"),
    (8888, "Unreal Signaling Server"),
    (11434, "Ollama LLM (stehouwer_llm)"),
    (1935, "RTMP Stream Ingest (WSL2)"),
    (5173, "Main Dashboard (Vite)"),
    (5174, "Broadcast Studio (Vite)")
]

for port, desc in ports_to_check:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    res = sock.connect_ex(('127.0.0.1', port))
    status = "OPEN / LISTENING" if res == 0 else "CLOSED"
    print(f"Port {port} ({desc}): {status}")
    sock.close()

print("\n=== ACTIVE PROCESS DETAILS ===")
relevant_procs = []
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'create_time']):
    try:
        cmdline = " ".join(p.info['cmdline'] or [])
        name = p.info['name'].lower()
        if any(k in name or k in cmdline.lower() for k in [
            'python', 'ollama', 'llama-server', 'comfy', 'aibs', 'mine_pearl',
            'oyster', 'peakminer', 'cloudflared', 'vnc_bridge', 'daemon', 'vite'
        ]):
            mem_mb = (p.info['memory_info'].rss / (1024 * 1024)) if p.info['memory_info'] else 0
            if mem_mb > 15: # filter out tiny subprocesses
                relevant_procs.append({
                    'pid': p.info['pid'],
                    'name': p.info['name'],
                    'mem_mb': round(mem_mb, 1),
                    'cmd': cmdline[:100]
                })
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

relevant_procs.sort(key=lambda x: x['mem_mb'], reverse=True)
for rp in relevant_procs[:25]:
    print(f"PID {rp['pid']} | {rp['name']} | {rp['mem_mb']} MB | {rp['cmd']}")

print("\n=== COMFYUI QUEUE / STATUS ===")
try:
    cq = requests.get('http://127.0.0.1:8189/queue', timeout=1).json()
    print("ComfyUI Running Queue:", len(cq.get('queue_running', [])))
    print("ComfyUI Pending Queue:", len(cq.get('queue_pending', [])))
except Exception as e:
    print("ComfyUI query error:", e)

print("\n=== RECENT LOG FILES (C:\\AI-BS\\logs) ===")
logs = glob.glob(r'C:\AI-BS\logs\*.log')
log_stats = []
for lf in logs:
    try:
        sz = os.path.getsize(lf)
        mtime = os.path.getmtime(lf)
        log_stats.append((lf, sz, mtime))
    except Exception:
        pass
log_stats.sort(key=lambda x: x[2], reverse=True)
for lf, sz, mtime in log_stats[:15]:
    print(f"{os.path.basename(lf)}: {round(sz/1024, 1)} KB (last modified ts: {mtime})")
