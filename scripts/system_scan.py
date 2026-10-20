import os
import sys
import socket
import psutil
import json
import time

print("=" * 70)
print("           AI-BS MASTER ECOSYSTEM SYSTEM SCAN (C:\\AI-BS)")
print("=" * 70)

# 1. Directory Structure & Key Files
print("\n[1] REPOSITORY STRUCTURE & COMPONENT SIZES")
root_dir = r"C:\AI-BS"
subdirs = [
    "backend", "frontend", "BroadcastStudioApp", "docs",
    "scripts", "saved_data", "NotebookLM_Records", "pyppeteer_env"
]
for sub in subdirs:
    p = os.path.join(root_dir, sub)
    if os.path.exists(p):
        file_count = 0
        total_size = 0
        for r, d, files in os.walk(p):
            file_count += len(files)
            for f in files:
                try:
                    total_size += os.path.getsize(os.path.join(r, f))
                except:
                    pass
        print(f"  - {sub:<22} : {file_count:>5} files | {total_size / (1024*1024):>8.2f} MB")
    else:
        print(f"  - {sub:<22} : NOT FOUND")

# 2. Port & Network Service Status
print("\n[2] LOCAL SYSTEM PORTS & SERVICES PROBE")
ports_to_probe = [
    (8080, "AI-BS FastAPI Master Core (AI_BS_Backend.py)"),
    (8088, "Broadcast Stream Kernel (aibs_broadcast_kernel.py)"),
    (8005, "Broadcast Daemon Legacy (aibs_broadcast_daemon.py)"),
    (8013, "VST3 DSP Theme Bridge (aibs_vst_daemon.py)"),
    (8002, "ChromaDB Vector Store"),
    (8006, "Social Hub & Twitch IRC Bot"),
    (11434, "Ollama GPU Master (RTX 4090)"),
    (8188, "ComfyUI Diffusion Matrix"),
    (5173, "Frontend Vite Dev Server"),
    (5174, "BS-Studio Vite UI Server"),
    (4455, "OBS Studio v30 WebSocket Bridge")
]

for port, desc in ports_to_probe:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.4)
    res = s.connect_ex(('127.0.0.1', port))
    s.close()
    status_str = "ACTIVE / LISTENING" if res == 0 else "INACTIVE / OFFLINE"
    print(f"  - Port {port:<5} : [{status_str:<18}] -> {desc}")

# 3. Active AI-BS Processes
print("\n[3] RUNNING AI-BS PROCESSES & DAEMONS")
active_procs = []
for p in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        name = p.info['name'] or ''
        if any(k in cmd for k in ['AI_BS', 'aibs', 'broadcast', 'vite', 'electron', 'BS-Studio', 'Ollama', 'comfy', 'uvicorn', 'python.exe']):
            mem_mb = (p.info['memory_info'].rss if p.info['memory_info'] else 0) / (1024*1024)
            if 'AI-BS' in cmd or 'BS-Studio' in cmd or 'aibs' in cmd:
                active_procs.append((p.info['pid'], name, mem_mb, cmd[:80]))
    except:
        pass

if active_procs:
    for pid, name, mem, cmd in active_procs[:15]:
        print(f"  - PID {pid:<6} | {name:<20} | {mem:>6.1f} MB | {cmd}")
else:
    print("  - No active background daemons detected.")

# 4. Cost Constraint / Paid API Compliance Check
print("\n[4] COST CONSTRAINT & PAID API COMPLIANCE SCAN")
violations = []
scan_extensions = ['.js', '.jsx', '.ts', '.tsx', '.py']
for r, d, files in os.walk(root_dir):
    if any(skip in r for skip in ['node_modules', '.git', 'dist', 'dist-electron', 'desktop-build', 'pyppeteer_env']):
        continue
    for f in files:
        if any(f.endswith(ext) for ext in scan_extensions):
            fp = os.path.join(r, f)
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                    if 'getGenerativeModel' in content or 'gemini-3.5-flash' in content or 'openai.api_key' in content or 'anthropic' in content:
                        rel_path = os.path.relpath(fp, root_dir)
                        violations.append((rel_path, "Contains generative model / paid API SDK reference"))
            except:
                pass

if violations:
    print(f"  Found {len(violations)} files with external model references to inspect:")
    for vpath, vreason in violations[:10]:
        print(f"  * {vpath} -> {vreason}")
else:
    print("  100% Free / Local OSS Compliance Verified. No paid API dependencies active.")

# 5. Master Ledger & Version Summary
print("\n[5] MASTER LEDGER & ECOSYSTEM VERSION SUMMARY")
ledger_path = os.path.join(root_dir, "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md")
if os.path.exists(ledger_path):
    with open(ledger_path, 'r', encoding='utf-8', errors='ignore') as fh:
        first_few = [fh.readline() for _ in range(8)]
        for line in first_few:
            if line.startswith('| 2026-') or line.startswith('#'):
                print(f"  {line.strip()[:100]}")

print("\n" + "=" * 70)
print("SCAN COMPLETED.")
print("=" * 70)
