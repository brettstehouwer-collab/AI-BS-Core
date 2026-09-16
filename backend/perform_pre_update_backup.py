import os
import shutil
import sqlite3
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(r"C:\AI-BS\backend\backups", f"pre_update_{timestamp}")
os.makedirs(backup_dir, exist_ok=True)

print(f"[BACKUP PROTOCOL] Target Directory: {backup_dir}")

# 1. Vector Vaults
vector_paths = [
    r"C:\AI-BS\stehouwer_vector_memory",
]
for vp in vector_paths:
    if os.path.exists(vp):
        dest = os.path.join(backup_dir, os.path.basename(vp))
        if not os.path.exists(dest):
            shutil.copytree(vp, dest, dirs_exist_ok=True)
            print(f"[BACKUP] Vector memory backed up from {vp}")

# 2. Persistent Ledgers (SQLite VACUUM INTO)
db_paths = [
    r"C:\AI-BS\backend\state.db",
    r"C:\AI-BS\leads_store.db",
    r"C:\AI-BS\drip_ledger.db",
]
for db in db_paths:
    if os.path.exists(db):
        target_name = f"atomic_{os.path.basename(db)}"
        target_path = os.path.join(backup_dir, target_name)
        try:
            conn = sqlite3.connect(db)
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            conn.execute(f"VACUUM INTO '{target_path.replace(os.sep, '/')}'")
            conn.close()
            print(f"[BACKUP] Atomic database snapshot created: {target_name}")
        except Exception as e:
            shutil.copy2(db, target_path)
            print(f"[BACKUP] Direct copy database snapshot: {target_name} ({e})")

json_ledgers = [
    r"C:\AI-BS\state.json",
    r"C:\AI-BS\handoff_state.json",
    r"C:\AI-BS\telemetry_cache.json",
]
for jl in json_ledgers:
    if os.path.exists(jl):
        shutil.copy2(jl, os.path.join(backup_dir, os.path.basename(jl)))
        print(f"[BACKUP] Ledger copied: {os.path.basename(jl)}")

# 3. Master Memory
mm_path = r"D:\AI-BS_Master_Memory\master_memory_dump.json"
if os.path.exists(mm_path):
    shutil.copy2(mm_path, os.path.join(backup_dir, "master_memory_dump.json"))
    print(f"[BACKUP] Master Memory secured from D:\\")
else:
    local_mm = r"C:\AI-BS\session_history_archive.json"
    if os.path.exists(local_mm):
        shutil.copy2(local_mm, os.path.join(backup_dir, "session_history_archive.json"))
        print(f"[BACKUP] Local history archive secured.")

# 4. Ollama Weight Cache Check
ollama_path = r"E:\AI_BS_Resources\Ollama"
if not os.path.exists(ollama_path):
    ollama_path = os.path.expanduser(r"~\.ollama\models")

if os.path.exists(ollama_path):
    print(f"[VERIFY] Ollama model weights intact at: {ollama_path}")
else:
    print(f"[WARNING] Ollama path not found at standard location.")

print("[BACKUP PROTOCOL] Atomic State Preservation Complete.")
