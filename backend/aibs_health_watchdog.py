"""
AI-BS Unified Ecosystem Health Watchdog Daemon
Monitors 15 ecosystem ports, audits SQLite WAL sizes, and optimizes database checkpoints.
"""

import os
import sys
import time
import socket
import sqlite3
import json
import argparse

WATCHED_PORTS = {
    8080: "FastAPI Core Backend",
    8000: "Go Matrix Gateway",
    8001: "Theatrical Gateway",
    8002: "ChromaDB Vector Store",
    8005: "Broadcast Studio Daemon",
    8006: "Twitch/IRC Social Hub",
    8008: "Supabase Kong Gateway",
    8010: "SHM Telemetry Gateway",
    8013: "VST3 Audio Bridge",
    8099: "Gemini MCP Server",
    8189: "ComfyUI Diffusion Studio",
    8888: "Unreal Engine Signaling",
    4455: "OBS Studio WebSocket",
    3001: "Node.js Backend Server",
    5173: "Primary React Dashboard",
    5174: "BroadcastStudioApp Vite",
    11434: "Ollama Primary LLM",
    11435: "Ollama E-Drive LLM"
}

DATABASES_TO_AUDIT = [
    r"C:\AI-BS\backend\stehouwer_vault.db",
    r"C:\AI-BS\leads_store.db",
    r"C:\AI-BS\data\leads_store.db",
    r"C:\AI-BS\data\reasoning_traces_pending.db",
    r"C:\AI-BS\data\telemetry_checkpoint.sqlite",
    r"C:\AI-BS\data\trade_queue.db",
    r"C:\AI-BS\data\vision_sync_state.db",
    r"C:\AI-BS\Crypto-Swarm\trade_queue.db",
    r"C:\AI-BS\tests\test_state.db"
]

def check_port(host, port, timeout=0.3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def audit_wal_databases(checkpoint_threshold_mb=50.0):
    db_results = []
    for db_path in DATABASES_TO_AUDIT:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            # Check WAL file size
            wal_path = db_path + "-wal"
            wal_size_mb = (os.path.getsize(wal_path) / (1024 * 1024)) if os.path.exists(wal_path) else 0.0
            
            checkpointed = False
            if wal_size_mb > checkpoint_threshold_mb:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                checkpointed = True
                
            integrity = conn.execute("PRAGMA integrity_check;").fetchall()[0][0]
            conn.close()
            
            db_results.append({
                "database": os.path.basename(db_path),
                "path": db_path,
                "integrity": integrity,
                "wal_size_mb": round(wal_size_mb, 2),
                "checkpointed": checkpointed
            })
        except Exception as e:
            db_results.append({
                "database": os.path.basename(db_path),
                "path": db_path,
                "integrity": f"ERROR: {e}",
                "wal_size_mb": 0.0,
                "checkpointed": False
            })
    return db_results

def run_health_scan():
    print("=" * 75)
    print("             AI-BS MASTER ECOSYSTEM HEALTH WATCHDOG SCAN")
    print("=" * 75)
    
    port_status = {}
    online_count = 0
    for port, name in WATCHED_PORTS.items():
        is_open = check_port("127.0.0.1", port)
        status_str = "[ONLINE]" if is_open else "[OFFLINE/ON-DEMAND]"
        port_status[port] = {"service": name, "online": is_open}
        if is_open:
            online_count += 1
        print(f"  * Port {port:<5} | {name:<28} : {status_str}")
        
    print(f"\nPorts Probed: {len(WATCHED_PORTS)} | Active Services: {online_count}")
    print("\n--- Auditing SQLite WAL Databases & Journal State ---")
    
    db_results = audit_wal_databases()
    for db in db_results:
        chk_str = " (AUTO-TRUNCATED)" if db["checkpointed"] else ""
        print(f"  * {db['database']:<28} | WAL: {db['wal_size_mb']:>5.2f} MB | Integrity: {db['integrity']}{chk_str}")
        
    print("=" * 75)
    print("Health Watchdog Scan Completed Successfully.")
    return {"ports": port_status, "databases": db_results}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-BS Health Watchdog")
    parser.add_argument("--test-scan", action="store_true", help="Run immediate one-shot health scan")
    args = parser.parse_args()
    
    run_health_scan()