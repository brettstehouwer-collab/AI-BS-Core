import os
import glob
import sqlite3
import py_compile
import json
from collections import defaultdict

backend_dir = r"C:\AI-BS\backend"
all_items = os.listdir(backend_dir)

categories = defaultdict(list)
total_bytes = 0
syntax_errors = []
db_statuses = []

for item in all_items:
    full_path = os.path.join(backend_dir, item)
    if os.path.isdir(full_path):
        categories["Directories"].append((item, 0))
        continue
        
    size = os.path.getsize(full_path)
    total_bytes += size
    ext = os.path.splitext(item)[1].lower()
    
    if ext == ".py":
        categories["Python Source Files"].append((item, size))
        try:
            py_compile.compile(full_path, doraise=True)
        except Exception as e:
            syntax_errors.append((item, str(e)))
    elif ext in [".db", ".sqlite"]:
        categories["SQLite Databases"].append((item, size))
        try:
            conn = sqlite3.connect(full_path, timeout=2.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            res = conn.execute("PRAGMA quick_check;").fetchone()[0]
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            db_statuses.append((item, size, res, mode, len(tables), tables[:3]))
            conn.close()
        except Exception as e:
            db_statuses.append((item, size, f"Error: {e}", "err", 0, []))
    elif ext in [".flv", ".mp4", ".mkv", ".jpg", ".png", ".pdf", ".pt"]:
        categories["Media & Binary Models"].append((item, size))
    elif ext in [".json", ".jsonl", ".csv", ".key", ".pem", ".pfx", ".env"]:
        categories["Configs, Keys & Data"].append((item, size))
    elif ext in [".bat", ".sh", ".ps1"]:
        categories["Launch Scripts"].append((item, size))
    elif ext in [".spec"]:
        categories["PyInstaller Specs"].append((item, size))
    elif ext in [".txt", ".md", ".log"]:
        categories["Documentation & Logs"].append((item, size))
    else:
        categories["Other"].append((item, size))

print("=" * 70)
print("             AI-BS BACKEND ECOSYSTEM DEEP AUDIT")
print("=" * 70)
print(f"Total Items in C:\\AI-BS\\backend : {len(all_items)}")
print(f"Total File Size on Disk        : {round(total_bytes / (1024*1024), 2)} MB\n")

for cat, flist in sorted(categories.items()):
    cat_size = sum(s for _, s in flist)
    print(f"[{cat}] ({len(flist)} items, {round(cat_size / (1024*1024), 2)} MB):")
    for fname, size in sorted(flist, key=lambda x: x[0])[:6]:
        print(f"  - {fname:<44} ({round(size/1024, 1)} KB)")
    if len(flist) > 6:
        print(f"  ... and {len(flist) - 6} more")
    print()

print("=" * 70)
print("             SQLITE DATABASE INTEGRITY & WAL STATUS")
print("=" * 70)
for name, sz, stat, mode, tcount, tbls in db_statuses:
    print(f"  {name:<26} | {round(sz/1024, 1):>7.1f} KB | {stat:<4} | {mode:<4} | Tables: {tcount} {tbls}")

print("\n" + "=" * 70)
print(f"Python Source Compilation Errors : {len(syntax_errors)}")
for fname, err in syntax_errors:
    print(f"  [!] {fname}: {err}")
if not syntax_errors:
    print("  [SUCCESS] All Python source files in backend/ compile with 0 syntax errors.")
print("=" * 70)