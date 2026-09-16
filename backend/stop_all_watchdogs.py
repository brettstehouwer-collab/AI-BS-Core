import psutil
import os
import json

killed_count = 0

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = " ".join(p.info.get('cmdline') or [])
        if any(k in cmdline for k in ['aibs_drop_watchdog', 'aibs_cymatics_sniper', 'drop_sniffer_module']):
            print(f"Terminating Watchdog Process PID {p.pid}: {cmdline[:80]}...")
            p.terminate()
            killed_count += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

print(f"Total Watchdog Processes Stopped: {killed_count}")

# Update heartbeat status to STOPPED
hb_path = r"C:\AI-BS\saved_data\cymatics_heartbeat.json"
if os.path.exists(hb_path):
    try:
        data = json.load(open(hb_path, "r", encoding="utf-8"))
        data["status"] = "STOPPED"
        data["pid"] = None
        json.dump(data, open(hb_path, "w", encoding="utf-8"), indent=2)
        print("Updated cymatics_heartbeat.json status to STOPPED.")
    except Exception as e:
        print("Error updating heartbeat JSON:", e)
