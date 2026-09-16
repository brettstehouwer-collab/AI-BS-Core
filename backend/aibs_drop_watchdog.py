"""
AI-BS Enterprise Drop Sniffer Watchdog Supervisor
Monitors sniper daemon heartbeat and process health.
Auto-restarts sniper instantly if heartbeat becomes stale (>6s) or process terminates.
"""

import time
import os
import json
import subprocess
import sys

WATCHDOG_LOG = r"C:\AI-BS\saved_data\cymatics_watchdog.log"
HEARTBEAT_FILE = r"C:\AI-BS\saved_data\cymatics_heartbeat.json"
PYTHON_EXE = sys.executable or r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"

os.makedirs(os.path.dirname(HEARTBEAT_FILE), exist_ok=True)

def log_event(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{ts}] [WATCHDOG] {msg}\n"
    print(entry, end='', flush=True)
    try:
        with open(WATCHDOG_LOG, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass

def is_heartbeat_healthy():
    if not os.path.exists(HEARTBEAT_FILE):
        return False
    try:
        with open(HEARTBEAT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        age = time.time() - data.get('timestamp', 0)
        return age < 6.0
    except Exception:
        return False

def start_sniper_process():
    log_event("Spawning fresh AI-BS Cymatics Drop Sniffer Engine (drop_sniffer_module)...")
    proc = subprocess.Popen(
        [PYTHON_EXE, "-u", "-m", "drop_sniffer_module.engine"],
        cwd=r"C:\AI-BS\backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return proc

def run_watchdog():
    log_event("Watchdog Supervisor Active (2.0s Heartbeat Check).")
    proc = start_sniper_process()

    while True:
        time.sleep(2.0)
        
        # Check process status
        poll_res = proc.poll()
        heartbeat_ok = is_heartbeat_healthy()

        if poll_res is not None or not heartbeat_ok:
            reason = f"Process Exited (code {poll_res})" if poll_res is not None else "Heartbeat Stale (>6s)"
            log_event(f"Anomaly detected: {reason}. Triggering immediate fail-safe restart...")
            try:
                proc.kill()
            except Exception:
                pass
            time.sleep(0.5)
            proc = start_sniper_process()

if __name__ == "__main__":
    run_watchdog()
