"""
AI-BS Comprehensive Ecosystem Boot Status Auditor
Audits the complete 18-Port Collision Matrix, system processes, and core daemons.
"""

import socket
import urllib.request
import urllib.error
import json
import subprocess
import sys

PORTS_MAP = [
    (80, "Nginx Gateway (StehouwerPublishing)", "HTTP/Proxy"),
    (3001, "Node Backend", "REST/WS"),
    (4455, "OBS WebSocket", "OBS Control"),
    (5173, "Vite Frontend Dashboard", "Vite Dev"),
    (5174, "Broadcast Studio Vite", "Vite Dev"),
    (8000, "Go Matrix Gateway", "Go API"),
    (8001, "Theatrical Gateway", "NoCo Vision"),
    (8002, "ChromaDB Vector Store (E-Drive)", "Vector DB"),
    (8005, "AI-BS Broadcast Daemon", "FastAPI"),
    (8006, "Social Hub (Twitch/IRC)", "FastAPI"),
    (8007, "Crypto Swarm & Scalp Bot", "Python Daemon"),
    (8010, "SHM Telemetry Gateway", "WebSocket"),
    (8013, "VST3 Audio Bridge", "Audio Engine"),
    (8055, "WSL2 TheSimpleChef Webroot", "Nginx Vhost"),
    (8080, "FastAPI Core Backend", "Primary Backend"),
    (8085, "Ubuntu-Bio Bridge", "WSL2 Daemon"),
    (8088, "Broadcast Kernel & NVENC", "Video Pipeline"),
    (8089, "WSL HLS Streaming Ingest", "Media Server"),
    (8099, "Gemini MCP Server", "MCP Engine"),
    (8189, "ComfyUI Renderer / Screenplay", "Diffusion Engine"),
    (8888, "Unreal Signaling Server", "WebRTC/WS"),
    (11434, "Ollama Primary Host", "LLM Inference"),
    (11435, "Ollama E-Drive Host", "LLM Inference")
]

def check_port_socket(port, timeout=0.4):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        res = s.connect_ex(('127.0.0.1', port))
        s.close()
        return res == 0
    except Exception:
        return False

def get_process_list():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            universal_newlines=True
        )
        procs = {}
        for line in out.strip().splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                name = parts[0]
                pid = parts[1]
                procs.setdefault(name, []).append(pid)
        return procs
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 85)
    print("                 AI-BS MATRIX ECOSYSTEM BOOT AUDIT REPORT")
    print("=" * 85)
    
    online_count = 0
    total_ports = len(PORTS_MAP)
    
    print(f"{'Port':<8} | {'Service Name':<38} | {'Type':<16} | {'Status':<12}")
    print("-" * 85)
    
    for port, name, ptype in PORTS_MAP:
        is_online = check_port_socket(port)
        if is_online:
            online_count += 1
            status_str = "\033[92mONLINE\033[0m" if sys.stdout.isatty() else "[ONLINE]"
        else:
            status_str = "[STOPPED]"
        print(f"{port:<8} | {name:<38} | {ptype:<16} | {status_str:<12}")
        
    print("=" * 85)
    print(f"Topology Summary: {online_count}/{total_ports} Sockets Active.")
    print("=" * 85)
    
    procs = get_process_list()
    target_procs = ["python.exe", "node.exe", "ollama.exe", "nginx.exe", "aibs_engine.exe", "chroma.exe", "cloudflared.exe", "UnrealEditor.exe"]
    
    print("\n--- Active Daemon Processes ---")
    for tp in target_procs:
        pids = procs.get(tp, [])
        if pids:
            print(f"  * {tp:<20} : RUNNING ({len(pids)} instances, PIDs: {', '.join(pids[:8])}{'...' if len(pids)>8 else ''})")
        else:
            print(f"  * {tp:<20} : NOT RUNNING")
            
    print("=" * 85)

if __name__ == "__main__":
    main()
