"""
AI-BS Ecosystem Continuous Supervisor Daemon
Monitors and guarantees 100% uptime for all requested ecosystem ports:
- 5174: BroadcastStudioApp Vite
- 8002: ChromaDB Vector Store
- 8005: Broadcast Kernel Daemon
- 8006: Twitch / IRC Social Hub
- 8007: Crypto Swarm & Scalp Bot
- 8008: Supabase Kong Gateway
- 8013: VST3 Audio Bridge
- 8088: Broadcast NVENC Hardware Encoder
- 8188: ComfyUI Primary Proxy
"""

import sys
import os
import time
import socket
from pathlib import Path

ROOT = Path(r"C:\AI-BS")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.aibs_ecosystem_spawner import activate_all_daemons, is_port_open, DAEMON_SPECS

def run_supervisor_loop():
    print("==================================================")
    print("AI-BS CONTINUOUS ECOSYSTEM SUPERVISOR ACTIVE")
    print("==================================================")
    sys.stdout.flush()

    while True:
        try:
            res = activate_all_daemons(verbose=False)
            offline_ports = res.get("pending", [])
            online_ports = res.get("active_now", [])
            
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Supervisor Heartbeat: {len(online_ports)}/9 Daemons Online | Active: {online_ports}")
            if offline_ports:
                print(f"[{ts}] Offline ports detected, triggered auto-recovery: {offline_ports}")
            sys.stdout.flush()
        except Exception as e:
            print(f"[SUPERVISOR ERROR]: {e}")
            sys.stdout.flush()

        time.sleep(10.0)

if __name__ == "__main__":
    run_supervisor_loop()
