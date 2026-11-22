import sqlite3
import glob
import os

print("=== AI-BS API KEY & STOREFRONT PURCHASES AUDIT ===")

db_files = glob.glob("backend/*.db")
for db in db_files:
    print(f"\n--- Database: {db} ---")
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        print("  Tables:", [t[0] for t in tables])
        
        for table in tables:
            t_name = table[0]
            if any(k in t_name.lower() for k in ["key", "license", "pass", "purchase", "transaction", "order", "client", "billing", "token"]):
                rows = cursor.execute(f"SELECT * FROM {t_name} LIMIT 10;").fetchall()
                cols = [desc[0] for desc in cursor.description]
                print(f"  --> Table '{t_name}' ({len(rows)} records found):")
                print(f"      Columns: {cols}")
                for r in rows:
                    print(f"      Data: {r}")
        conn.close()
    except Exception as e:
        print(f"  Error reading {db}: {e}")

# Check license_manager or config files if present
print("\n--- License & API Key File Inspection ---")
for fn in ["license_manager.py", "ai_bs_config.json", "crypto_ledger.json", "telemetry_cache.json"]:
    fp = os.path.join("backend", fn)
    if os.path.exists(fp):
        print(f"File {fn} size: {os.path.getsize(fp)} bytes")
