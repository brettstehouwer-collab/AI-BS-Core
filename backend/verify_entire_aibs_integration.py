import os
import json
import requests

results = {}

# 1. Check DAW Junctions
daw_junctions_dir = r"C:\AI-BS\shared_cloud_drive\4 media\Cymatics_Sample_Packs"
if os.path.exists(daw_junctions_dir):
    j_list = os.listdir(daw_junctions_dir)
    results["daw_sample_suites_linked"] = len(j_list)
else:
    results["daw_sample_suites_linked"] = 0

# 2. Check VST3 Plugins
vst3_dir = r"C:\Program Files\Common Files\VST3"
vst_set = set()
if os.path.exists(vst3_dir):
    for root, dirs, files in os.walk(vst3_dir):
        for d in dirs:
            if d.endswith(".vst3"):
                vst_set.add(d.replace(".vst3", ""))
        for f in files:
            if f.endswith(".vst3"):
                vst_set.add(f.replace(".vst3", ""))
results["vst3_plugins_installed"] = len(vst_set)

# 3. Check Watchdog Heartbeat
hb_path = r"C:\AI-BS\saved_data\cymatics_heartbeat.json"
if os.path.exists(hb_path):
    try:
        hb_data = json.load(open(hb_path, "r", encoding="utf-8"))
        results["watchdog_status"] = hb_data.get("status")
        results["watchdog_pid"] = hb_data.get("pid")
        results["watchdog_cards_polled"] = hb_data.get("channels_stats", {}).get("total_cards")
    except:
        results["watchdog_status"] = "ERROR_READING"
else:
    results["watchdog_status"] = "MISSING"

# 4. Check Backend Routers Mounted in AI_BS_Backend.py
backend_py = r"C:\AI-BS\backend\AI_BS_Backend.py"
if os.path.exists(backend_py):
    content = open(backend_py, "r", encoding="utf-8").read()
    results["vst_router_mounted"] = "vst_router" in content
    results["drop_sniffer_router_mounted"] = "drop_sniffer_router" in content
    results["shared_drive_router_mounted"] = "shared_drive_router" in content
    results["matrix_router_mounted"] = "matrix_router" in content

# 5. Check Ledger & Manual Version
ledger = open(r"C:\AI-BS\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md", "r", encoding="utf-8").read()
manual = open(r"C:\AI-BS\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md", "r", encoding="utf-8").read()
results["ledger_version_5_120_0"] = "5.120.0" in ledger[:200]
results["manual_version_5_120_0"] = "5.120.0" in manual[:200]

print("=== AI-BS COMPREHENSIVE INTEGRATION AUDIT ===")
print(json.dumps(results, indent=2))
