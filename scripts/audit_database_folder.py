import os
import sqlite3
import glob

DB_DIRS = [
    r"C:\AI-BS\database",
    r"C:\AI-BS\backend",
    r"C:\AI-BS"
]

def audit_and_optimize():
    print("=" * 65)
    print("       AI-BS UNIVERSAL DATABASE INTEGRITY & WAL ENFORCER")
    print("=" * 65)
    
    seen = set()
    total_audited = 0
    
    for d in DB_DIRS:
        if not os.path.exists(d):
            continue
        dbs = glob.glob(os.path.join(d, "*.db")) + glob.glob(os.path.join(d, "*.sqlite"))
        for db in dbs:
            norm_path = os.path.normpath(db)
            if norm_path in seen:
                continue
            seen.add(norm_path)
            
            name = os.path.basename(db)
            size_mb = round(os.path.getsize(db) / (1024 * 1024), 2)
            
            try:
                conn = sqlite3.connect(db, timeout=2.0)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA busy_timeout=10000;")
                conn.execute("PRAGMA mmap_size=268435456;")
                
                res = conn.execute("PRAGMA quick_check;").fetchone()[0]
                mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                
                print(f"  {name:<28} | {size_mb:>6.2f} MB | {res:<4} | {mode:<4} | Tables: {len(tables)}")
                conn.close()
                total_audited += 1
            except Exception as e:
                print(f"  {name:<28} | Error: {e}")
                
    print("=" * 65)
    print(f"[SUCCESS] Audited & WAL-optimized {total_audited} databases across AI-BS.")
    print("=" * 65)

if __name__ == "__main__":
    audit_and_optimize()