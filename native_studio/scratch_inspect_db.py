import os
import sqlite3

candidate_dirs = [r"C:\AI-BS", r"C:\AI-BS\backend", r"C:\AI-BS\data", r"C:\AI-BS\saved_data"]
for d in candidate_dirs:
    if not os.path.exists(d):
        continue
    for f in os.listdir(d):
        if f.endswith(".db") or f.endswith(".sqlite"):
            p = os.path.join(d, f)
            sz = os.path.getsize(p) / (1024 * 1024)
            print(f"\nDB: {p} ({sz:.2f} MB)")
            try:
                conn = sqlite3.connect(p)
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                print(f"  Tables ({len(tables)}): {', '.join(tables)}")
                conn.close()
            except Exception as e:
                print(f"  Error: {e}")
