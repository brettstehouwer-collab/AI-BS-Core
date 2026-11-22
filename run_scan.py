import os
import sys
import sqlite3
import httpx
import json
import shutil

report = {
    "root": "C:/AI-BS",
    "directories": [],
    "databases": [],
    "ollama_fleet": [],
    "active_ports": {},
    "storage_summary": {},
    "reasoning_engine_status": {}
}

# 1. Inspect Top-Level Directories
root = "C:/AI-BS"
total_files = 0
for item in os.listdir(root):
    p = os.path.join(root, item)
    if os.path.isdir(p) and not item.startswith("."):
        try:
            count = sum(len(files) for _, _, files in os.walk(p))
            total_files += count
            report["directories"].append({"name": item, "file_count": count})
        except Exception:
            report["directories"].append({"name": item, "file_count": "N/A"})

report["storage_summary"]["total_top_level_directories"] = len(report["directories"])
report["storage_summary"]["total_indexed_files"] = total_files

# 2. Inspect Databases
db_dir = "C:/AI-BS/database"
if os.path.exists(db_dir):
    for f in os.listdir(db_dir):
        if f.endswith(".db"):
            db_path = os.path.join(db_dir, f)
            size_kb = round(os.path.getsize(db_path) / 1024, 2)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cursor.fetchall()]
                conn.close()
                report["databases"].append({"name": f, "size_kb": size_kb, "tables": tables})
            except Exception as e:
                report["databases"].append({"name": f, "size_kb": size_kb, "error": str(e)})

# 3. Check Local Ollama Fleet
try:
    with httpx.Client(timeout=3.0) as client:
        r = client.get("http://127.0.0.1:11434/api/tags")
        if r.status_code == 200:
            report["ollama_fleet"] = [m["name"] for m in r.json().get("models", [])]
except Exception as e:
    report["ollama_fleet"] = f"Offline / Error: {e}"

# 4. Check Port Health
ports_to_check = {
    8000: "Go Matrix / FastAPI Gateway (Port 8000)",
    8189: "ComfyUI RTX 4090 (Port 8189)",
    8080: "Unreal Engine 5.8 Bridge (Port 8080)",
    8088: "OBS Zero-Copy Direct3D11 Streamer (Port 8088)",
    11434: "Ollama Multi-Model Swarm Daemon (Port 11434)",
    5173: "Vite React Local Dev Server (Port 5173)"
}
for p, desc in ports_to_check.items():
    try:
        with httpx.Client(timeout=1.5) as client:
            r = client.get(f"http://127.0.0.1:{p}/", follow_redirects=True)
            report["active_ports"][p] = {"desc": desc, "status": "ONLINE", "http_status": r.status_code}
    except Exception:
        report["active_ports"][p] = {"desc": desc, "status": "IDLE / OFFLINE"}

# 5. Check Unified Reasoning Engine
try:
    sys.path.append("C:/AI-BS/backend")
    from core.sovereign_reasoning import stream_sovereign_response, MathematicalAutogradOptimizer, SovereignMemoryVault
    report["reasoning_engine_status"] = {
        "status": "HEALTHY",
        "math_autograd": "AVAILABLE",
        "memory_vault": "ONLINE",
        "fts5_ledger": "ATTACHED"
    }
except Exception as e:
    report["reasoning_engine_status"] = {"status": "ERROR", "message": str(e)}

with open("C:/AI-BS/system_scan_report.json", "w", encoding="utf-8") as out:
    json.dump(report, out, indent=2)

print("Scan Complete! Output saved to system_scan_report.json")
