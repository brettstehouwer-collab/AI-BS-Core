import os
import sys
import socket
import urllib.request
import json
import psutil
import subprocess
import time

print("=" * 80)
print("       AI-BS FULL ECOSYSTEM COMPREHENSIVE HEALTH AUDIT & RECONCILIATION")
print("=" * 80)

# 1. Probe & Ensure Critical Background Daemons are Running
print("\n[PHASE 1] SERVER & DAEMON STATUS VERIFICATION")

def check_port(port, timeout=0.3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    res = s.connect_ex(('127.0.0.1', port))
    s.close()
    return res == 0

# Check Port 8088 (Broadcast Kernel) - if offline, start it in background!
if not check_port(8088):
    print("  * Port 8088 (aibs_broadcast_kernel.py) is OFFLINE. Spawning daemon in background...")
    py_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
    script = r"C:\AI-BS\backend\aibs_broadcast_kernel.py"
    if os.path.exists(py_exe) and os.path.exists(script):
        subprocess.Popen([py_exe, script], cwd=r"C:\AI-BS\backend", creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        time.sleep(2.5)

endpoints_to_test = [
    ("FastAPI Master Core", "http://127.0.0.1:8080/api/windows", "Windows/Game Listing"),
    ("FastAPI Master Core", "http://127.0.0.1:8080/api/active_game", "Active Game Detection"),
    ("FastAPI Master Core", "http://127.0.0.1:8080/api/vst/scan", "VST3 DSP Plugin Scanner"),
    ("FastAPI Master Core", "http://127.0.0.1:8080/api/audio/search?q=kick", "101k Audio Sample Vault"),
    ("Broadcast Kernel (NVENC)", "http://127.0.0.1:8088/api/windows", "DirectX 11 Windows Hook"),
    ("Broadcast Kernel (NVENC)", "http://127.0.0.1:8088/api/active_game", "Live Game Scanner Hook"),
    ("Broadcast Daemon Legacy", "http://127.0.0.1:8005/api/windows", "FFmpeg Hardware Streamer"),
    ("VST3 DSP Theme Bridge", "http://127.0.0.1:8013/api/vst/theme-state", "Tone.js Theme Telemetry"),
    ("ChromaDB Vector Store", "http://127.0.0.1:8002/api/v2/heartbeat", "Neural Memory Heartbeat"),
    ("Ollama GPU LLM Master", "http://127.0.0.1:11434/api/version", "RTX 4090 Inference Version")
]

for service, url, desc in endpoints_to_test:
    try:
        req = urllib.request.Request(url, headers={'X-Client-ID': 'stehouwer_publishing', 'User-Agent': 'AI-BS-Health-Audit'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            elapsed = round((time.time() - t0) * 1000, 1)
            status_code = resp.getcode()
            data_sample = resp.read()[:80].decode('utf-8', errors='ignore')
            print(f"  [PASS] {service:<24} | {status_code} OK ({elapsed:>5.1f}ms) | {desc} -> {data_sample[:40]}...")
    except Exception as e:
        print(f"  [WARN] {service:<24} | Error: {str(e)[:45]} | {desc} ({url})")

# 2. Frontend Tab & Subsystem Module Integrity Check
print("\n[PHASE 2] FRONTEND TABS & MODULES CODEBASE VERIFICATION")
tabs_dir = r"C:\AI-BS\frontend\src\components"
if os.path.exists(tabs_dir):
    tab_files = [f for f in os.listdir(tabs_dir) if f.endswith(('.jsx', '.js', '.tsx'))]
    print(f"  Found {len(tab_files)} active frontend tab components:")
    error_count = 0
    for f in tab_files[:18]:
        fp = os.path.join(tabs_dir, f)
        sz_kb = os.path.getsize(fp) / 1024
        print(f"    - {f:<35} ({sz_kb:>6.1f} KB)")
    if len(tab_files) > 18:
        print(f"    ... and {len(tab_files) - 18} additional modular tab components.")
else:
    print("  Tabs directory not found!")

# 3. BS-Studio Standalone Workstation Modules Check
print("\n[PHASE 3] BS-STUDIO STANDALONE WORKSTATION MODULES")
bs_components_dir = r"C:\AI-BS\BroadcastStudioApp\src\components"
if os.path.exists(bs_components_dir):
    for root, dirs, files in os.walk(bs_components_dir):
        rel = os.path.relpath(root, bs_components_dir)
        js_files = [f for f in files if f.endswith(('.jsx', '.js'))]
        if js_files:
            print(f"  * Module Group: {rel if rel != '.' else 'Root Components'}")
            for f in js_files:
                fp = os.path.join(root, f)
                print(f"    - {f:<30} ({os.path.getsize(fp)/1024:>5.1f} KB)")

print("\n" + "=" * 80)
print("AUDIT EXECUTION COMPLETE.")
print("=" * 80)
