import os
import json
import sqlite3
import re

print("=" * 80)
print("     DEEP VERIFICATION OF 4 FLAGGED REVIEW ITEMS")
print("=" * 80)

# 1. Check PrestigeMobileWash & JuliesPlace
pmw_env = r"C:\AI-BS\PrestigeMobileWash\.env"
pmw_cap = r"C:\AI-BS\PrestigeMobileWash\capacitor.config.json"
print("[1/4] PrestigeMobileWash & JuliesPlace:")
if os.path.exists(pmw_env):
    with open(pmw_env, "r", encoding="utf-8") as f:
        print(f"  * PrestigeMobileWash .env: {f.read().strip()}")
if os.path.exists(pmw_cap):
    with open(pmw_cap, "r", encoding="utf-8") as f:
        cap_json = json.load(f)
        print(f"  * Capacitor AppId: {cap_json.get('appId')}, AppName: {cap_json.get('appName')}")

# 2. Check ComfyUI Port Standardization
print("\n[2/4] ComfyUI Port 8189 Verification across all callers:")
comfy_files = [
    r"C:\AI-BS\Launch_AI_BS.bat",
    r"C:\AI-BS\backend\comfy_bridge.py",
    r"C:\AI-BS\backend\routers\comfyui_router.py",
    r"C:\AI-BS\ComfyUI\run_nvidia_gpu.bat",
    r"C:\AI-BS\ComfyUI\run_nvidia_gpu_fast_fp16_accumulation.bat"
]
for cf in comfy_files:
    if os.path.exists(cf):
        with open(cf, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            port_matches = re.findall(r'818[89]', content)
            print(f"  * {os.path.basename(cf)}: ports referenced -> {set(port_matches)}")

# 3. Check Supabase Kong Port Remap
print("\n[3/4] Supabase Kong Port in docker-compose.yml:")
supa_dc = r"C:\AI-BS\self_hosted_supabase\docker-compose.yml"
if os.path.exists(supa_dc):
    with open(supa_dc, "r", encoding="utf-8") as f:
        dc_text = f.read()
        kong_ports = [line.strip() for line in dc_text.splitlines() if "8008:8000" in line or "8000:8000" in line]
        print(f"  * Kong port mapping lines: {kong_ports}")

# 4. Check Database Integrity of stehouwer_vault.db & Stehouwer_Persona_Dataset.jsonl
print("\n[4/4] Stehouwer Vault & Dataset Verification:")
vault_db = r"C:\AI-BS\backend\stehouwer_vault.db"
if os.path.exists(vault_db):
    conn = sqlite3.connect(vault_db)
    cur = conn.cursor()
    integrity = cur.execute("PRAGMA integrity_check;").fetchall()
    journal = cur.execute("PRAGMA journal_mode;").fetchone()[0]
    count = cur.execute("SELECT count(*) FROM vault_data;").fetchone()[0]
    conn.close()
    print(f"  * stehouwer_vault.db: integrity={integrity[0][0]}, journal_mode={journal}, records={count}")

persona_file = r"C:\AI-BS\database\Stehouwer_Persona_Dataset.jsonl"
if os.path.exists(persona_file):
    valid_turns = 0
    with open(persona_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    obj = json.loads(line)
                    if "messages" in obj:
                        valid_turns += 1
                except Exception:
                    pass
    print(f"  * Stehouwer_Persona_Dataset.jsonl: {valid_turns} validated JSON dialogue turns")

print("=" * 80)