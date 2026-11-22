import os
import sys
import httpx
import json
import psutil
import subprocess

results = {
    "ecosystem_path": "C:/AI-BS",
    "services": {},
    "git_branch": "",
    "git_uncommitted_changes": 0,
    "system_telemetry": {},
    "backend_endpoints": {}
}

# 1. Check Services
ports = {
    8000: "Go Matrix / FastAPI Gateway (Port 8000)",
    8189: "ComfyUI RTX 4090 (Port 8189)",
    8080: "Unreal Engine 5.8 Bridge (Port 8080)",
    11434: "Ollama Multi-Model Swarm Daemon (Port 11434)",
    5173: "Vite React Local Dev Server (Port 5173)"
}

for port, name in ports.items():
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get(f"http://127.0.0.1:{port}/", follow_redirects=True)
            results["services"][name] = {"status": "ONLINE", "code": r.status_code}
    except Exception:
        results["services"][name] = {"status": "OFFLINE / IDLE"}

# 2. Check Git Status
try:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd="C:/AI-BS", text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd="C:/AI-BS", text=True).strip()
    results["git_branch"] = branch
    results["git_uncommitted_changes"] = len(status.splitlines()) if status else 0
except Exception as e:
    results["git_status_error"] = str(e)

# 3. Check System Memory & CPU
mem = psutil.virtual_memory()
results["system_telemetry"] = {
    "ram_total_gb": round(mem.total / (1024**3), 2),
    "ram_available_gb": round(mem.available / (1024**3), 2),
    "ram_usage_pct": mem.percent,
    "cpu_usage_pct": psutil.cpu_percent(interval=0.5)
}

# 4. Check Key Backend Endpoints
endpoints = [
    ("http://127.0.0.1:8000/api/health", "GET"),
    ("http://127.0.0.1:8000/api/screenwriting/studio_voices", "GET"),
    ("http://127.0.0.1:11434/api/tags", "GET")
]

for url, method in endpoints:
    try:
        with httpx.Client(timeout=2.0) as client:
            if method == "GET":
                res = client.get(url)
            results["backend_endpoints"][url] = {
                "status": "HEALTHY" if res.status_code == 200 else f"HTTP {res.status_code}",
                "status_code": res.status_code
            }
    except Exception as err:
        results["backend_endpoints"][url] = {"status": f"CONNECTION ERROR: {err}"}

with open("C:/AI-BS/live_check_report.json", "w", encoding="utf-8") as out:
    json.dump(results, out, indent=2)

print("Check Complete! Results written to live_check_report.json")
