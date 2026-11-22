import sqlite3
import json
import os
import glob
from datetime import datetime

print("==================================================")
print("       AI-BS BS-CHAT & SYSTEM MONITOR STATUS       ")
print("==================================================")

# 1. Databases audit
for db_name in ['stehouwer_vault.db', 'aibs_master.db']:
    db_path = os.path.join(r"C:\AI-BS\backend", db_name)
    if os.path.exists(db_path):
        print(f"\n[Database: {db_name}]")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            cur.execute(f"SELECT count(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"  - {t}: {cnt} records")
            # If table is chat or action, print last 2 rows
            if any(k in t.lower() for k in ['chat', 'action', 'message', 'prompt', 'log', 'vault']):
                try:
                    cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 2")
                    rows = cur.fetchall()
                    if rows:
                        print(f"    Latest row preview: {str(rows[0])[:120]}...")
                except Exception:
                    pass

# 2. Check Sandbox & Error files
print("\n[Sandbox & Self-Correction Status]")
sandbox_dir = r"C:\AI-BS\backend\sandbox"
errs = glob.glob(os.path.join(sandbox_dir, "*.error"))
print(f"  - Errors in sandbox: {len(errs)}")
if errs:
    for e in errs[:3]:
        print(f"    -> {os.path.basename(e)}")

# 3. Check UI Mutations & Memory Buffer
ui_req = r"C:\AI-BS\backend\ui_mutations"
reqs = glob.glob(os.path.join(ui_req, "*.json"))
print(f"  - Pending UI Mutation requests: {len(reqs)}")

# 4. Check Datasets
datasets_dir = r"C:\AI-BS\datasets"
jsonls = glob.glob(os.path.join(datasets_dir, "*.jsonl"))
print(f"\n[Compiled Datasets in C:\\AI-BS\\datasets: {len(jsonls)}]")
for jf in jsonls:
    size = os.path.getsize(jf)
    with open(jf, "r", encoding="utf-8") as f:
        lines = sum(1 for _ in f)
    print(f"  - {os.path.basename(jf)}: {lines} SFT samples ({size} bytes)")

# 5. Check Ingest Manifest
manifest_path = r"C:\AI-BS\ingest_manifest.json"
if os.path.exists(manifest_path):
    try:
        with open(manifest_path, "r", encoding="utf-8") as mf:
            m_data = json.load(mf)
        print(f"\n[RAG Ingest Manifest]")
        print(f"  - Status: {m_data.get('status')}")
        print(f"  - Total Files: {m_data.get('total_files')}")
        print(f"  - Total Bytes: {m_data.get('total_bytes')}")
        print(f"  - Last Updated: {m_data.get('last_updated')}")
    except Exception as e:
        print(f"  - Error reading manifest: {e}")
