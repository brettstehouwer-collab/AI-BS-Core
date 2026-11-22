import os
import sys
import shutil
import sqlite3
import httpx
import json
import psutil

scan_results = {
    "c_drive_storage": {},
    "c_root_directories": [],
    "aibs_health": {
        "ports": {},
        "databases": [],
        "system_resources": {},
        "ollama_models": []
    }
}

# 1. Scan C:\ Drive Storage
try:
    total, used, free = shutil.disk_usage("C:/")
    scan_results["c_drive_storage"] = {
        "total_gb": round(total / (1024**3), 2),
        "used_gb": round(used / (1024**3), 2),
        "free_gb": round(free / (1024**3), 2),
        "free_pct": round((free / total) * 100, 1)
    }
except Exception as e:
    scan_results["c_drive_storage"]["error"] = str(e)

# 2. Scan C:\ Root Directories
try:
    for item in os.listdir("C:/"):
        p = os.path.join("C:/", item)
        is_dir = os.path.isdir(p)
        scan_results["c_root_directories"].append({
            "name": item,
            "type": "DIRECTORY" if is_dir else "FILE"
        })
except Exception as e:
    scan_results["c_root_directories"] = [{"error": str(e)}]

# 3. System Resources (RAM & CPU)
try:
    mem = psutil.virtual_memory()
    scan_results["aibs_health"]["system_resources"] = {
        "total_ram_gb": round(mem.total / (1024**3), 2),
        "available_ram_gb": round(mem.available / (1024**3), 2),
        "ram_usage_pct": mem.percent,
        "cpu_usage_pct": psutil.cpu_percent(interval=0.5),
        "cpu_cores_logical": psutil.cpu_count(logical=True)
    }
except Exception as e:
    scan_results["aibs_health"]["system_resources"]["error"] = str(e)

# 4. Port Health Check
ports = {
    8000: "Go Matrix / FastAPI Gateway",
    8189: "ComfyUI (RTX 4090 Native)",
    8080: "Unreal Engine 5.8 Bridge",
    8088: "OBS Zero-Copy D3D11 Streamer",
    11434: "Ollama Swarm Daemon",
    5173: "Vite React Dev Server"
}

for port, desc in ports.items():
    try:
        with httpx.Client(timeout=1.5) as client:
            res = client.get(f"http://127.0.0.1:{port}/", follow_redirects=True)
            scan_results["aibs_health"]["ports"][port] = {
                "desc": desc,
                "status": "ONLINE",
                "code": res.status_code
            }
    except Exception:
        scan_results["aibs_health"]["ports"][port] = {
            "desc": desc,
            "status": "IDLE / OFFLINE"
        }

# 5. Database Health in C:/AI-BS/database
db_dir = "C:/AI-BS/database"
if os.path.exists(db_dir):
    for f in os.listdir(db_dir):
        if f.endswith(".db"):
            db_path = os.path.join(db_dir, f)
            size_kb = round(os.path.getsize(db_path) / 1024, 2)
            try:
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in c.fetchall()]
                conn.close()
                scan_results["aibs_health"]["databases"].append({
                    "name": f,
                    "size_kb": size_kb,
                    "table_count": len(tables),
                    "status": "HEALTHY"
                })
            except Exception as e:
                scan_results["aibs_health"]["databases"].append({
                    "name": f,
                    "size_kb": size_kb,
                    "status": f"ERROR: {e}"
                })

# 6. Ollama Local Models
try:
    with httpx.Client(timeout=2.0) as client:
        r = client.get("http://127.0.0.1:11434/api/tags")
        if r.status_code == 200:
            scan_results["aibs_health"]["ollama_models"] = [m["name"] for m in r.json().get("models", [])]
except Exception as e:
    scan_results["aibs_health"]["ollama_models"] = [f"Error: {e}"]

with open("C:/AI-BS/c_drive_scan_report.json", "w", encoding="utf-8") as out:
    json.dump(scan_results, out, indent=2)

print("Scan Complete! Output saved to C:/AI-BS/c_drive_scan_report.json")
