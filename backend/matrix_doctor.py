import os
import time
import socket
import sqlite3
import json
import psutil

PORTS = {
    8080: "FastAPI Core Backend",
    8000: "Go Matrix Gateway",
    8001: "Theatrical Gateway",
    8002: "ChromaDB Vector Store (E-Drive)",
    8005: "Broadcast Studio Daemon",
    8006: "Twitch/IRC Social Hub",
    8008: "Supabase Kong Gateway",
    8010: "SHM Telemetry Gateway",
    8013: "VST3 Audio Bridge",
    8085: "Ubuntu-Bio Bridge",
    8088: "Broadcast Kernel (Multi-Track)",
    8099: "Gemini MCP Server",
    8189: "ComfyUI Diffusion Studio",
    8888: "Unreal Engine Signaling",
    4455: "OBS Studio WebSocket",
    3001: "Node.js Backend Server",
    5173: "Primary React Dashboard",
    5174: "BroadcastStudioApp Vite",
    11434: "Ollama Primary LLM (C-Drive)",
    11435: "Ollama Secondary LLM (E-Drive)"
}

DATABASES = [
    ("C:/AI-BS/backend/aibs_master.db", "Primary Consolidated Master (27 Tables)"),
    ("C:/AI-BS/backend/lexicon_vault.db", "Lexicon Vector & Vocabulary Store"),
    ("C:/AI-BS/database/audio_catalog.db", "Audio Catalog & DSP Vector Store"),
    ("C:/AI-BS/database/LLM_CrossCheck_Ledger.db", "LLM Inference CrossCheck Ledger"),
    ("C:/AI-BS/backend/state.db", "Legacy Store (Consolidated into Master)"),
    ("C:/AI-BS/backend/clients.db", "Legacy Store (Consolidated into Master)"),
    ("C:/AI-BS/backend/unreal_assets.db", "Legacy Store (Consolidated into Master)"),
    ("C:/AI-BS/backend/stehouwer_vault.db", "Legacy Store (Consolidated into Master)"),
    ("C:/AI-BS/backend/stehouwer_accounting.db", "Legacy Store (Consolidated into Master)"),
    ("C:/AI-BS/backend/west_michigan.db", "Legacy Store (Consolidated into Master)"),
    ("C:/AI-BS/backend/drip_ledger.db", "Legacy Store (Consolidated into Master)")
]

def check_port(port: int, host: str = "127.0.0.1") -> tuple:
    start_t = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        is_open = s.connect_ex((host, port)) == 0
        latency_ms = round((time.perf_counter() - start_t) * 1000, 2)
        return is_open, latency_ms

def check_sqlite_integrity(db_path: str) -> str:
    if not os.path.exists(db_path):
        return "MISSING"
    try:
        conn = sqlite3.connect(db_path, timeout=1.0)
        res = conn.execute("PRAGMA quick_check;").fetchone()[0]
        conn.close()
        return res
    except Exception as e:
        return f"ERROR: {e}"

def run_diagnostics():
    print("=" * 70)
    print("        AI-BS MATRIX DOCTOR DIAGNOSTIC SUITE (v5.263.0)")
    print("=" * 70)
    print("\n[1/3] Scanning 20 Core Service Ports & Measuring Latency...")
    port_results = {}
    online_count = 0
    for p, name in PORTS.items():
        is_open, latency = check_port(p)
        if is_open:
            online_count += 1
            status = f"ONLINE  [OK] ({latency}ms)"
        else:
            status = "OFFLINE [..]"
        port_results[p] = {"name": name, "online": is_open, "latency_ms": latency if is_open else None}
        print(f"  Port {p:<5} | {name:<32} | {status}")

    print(f"\n  -> Total Services Online: {online_count} / {len(PORTS)}")

    print("\n[2/3] Checking SQLite Database Health & Consolidated Master WAL...")
    db_results = {}
    for db_path, role in DATABASES:
        name = os.path.basename(db_path)
        status = check_sqlite_integrity(db_path)
        db_results[name] = {"status": status, "role": role}
        print(f"  {name:<26} | Status: {status:<8} | Role: {role}")

    print("\n[3/3] Checking System RAM, CPU & Platform Telemetry...")
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.2)
    print(f"  CPU Usage: {cpu}% | RAM: {ram.percent}% ({round((ram.total - ram.available)/(1024**3), 2)}GB / {round(ram.total/(1024**3), 2)}GB)")
    print("=" * 70)

    report = {
        "timestamp": time.time(),
        "version": "v5.263.0",
        "services_online": online_count,
        "services_total": len(PORTS),
        "ports": port_results,
        "databases": {name: d["status"] for name, d in db_results.items()},
        "database_roles": {name: d["role"] for name, d in db_results.items()},
        "cpu_percent": cpu,
        "ram_percent": ram.percent,
        "ram_used_gb": round((ram.total - ram.available)/(1024**3), 2),
        "ram_total_gb": round(ram.total/(1024**3), 2)
    }

    try:
        report_path = "C:/AI-BS/backend/matrix_health_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  [Report] Saved matrix telemetry snapshot -> {report_path}")
    except Exception as e:
        print(f"  [Report Warning] Failed to write report: {e}")

    print("Matrix Doctor Diagnostic complete.\n")
    return report

if __name__ == "__main__":
    run_diagnostics()