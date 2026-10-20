import os
import glob
import sqlite3
import py_compile
from collections import defaultdict

scratch_dir = r"C:\AI-BS\scratch"
files = glob.glob(os.path.join(scratch_dir, "*"))

categories = defaultdict(list)
total_size = 0

syntax_errors = []
db_statuses = []

for f in files:
    if os.path.isdir(f):
        categories["Directories"].append((os.path.basename(f), 0))
        continue
        
    name = os.path.basename(f)
    size = os.path.getsize(f)
    total_size += size
    ext = os.path.splitext(name)[1].lower()
    
    if ext == ".py":
        categories["Python Scripts"].append((name, size))
        try:
            py_compile.compile(f, doraise=True)
        except Exception as e:
            syntax_errors.append((name, str(e)))
    elif ext in [".db", ".sqlite"]:
        categories["Databases"].append((name, size))
        try:
            conn = sqlite3.connect(f, timeout=1.0)
            res = conn.execute("PRAGMA quick_check;").fetchone()[0]
            conn.close()
            db_statuses.append((name, res))
        except Exception as e:
            db_statuses.append((name, f"Error: {e}"))
    elif ext in [".json", ".jsonl", ".yaml"]:
        categories["Data & Configs"].append((name, size))
    elif ext in [".jsx", ".js"]:
        categories["JavaScript / React"].append((name, size))
    elif ext in [".zip", ".tar", ".gz"]:
        categories["Archives"].append((name, size))
    elif ext in [".png", ".jpg", ".wav", ".opus"]:
        categories["Media Assets"].append((name, size))
    elif ext in [".txt", ".md", ".log"]:
        categories["Text & Logs"].append((name, size))
    elif ext in [".bat", ".ps1"]:
        categories["Shell Scripts"].append((name, size))
    else:
        categories["Other"].append((name, size))

print("=" * 65)
print("             AI-BS SCRATCH DIRECTORY DEEP AUDIT")
print("=" * 65)
print(f"Total Files in Scratch : {len(files)}")
print(f"Total Size on Disk     : {round(total_size / (1024*1024), 2)} MB\n")

for cat, flist in sorted(categories.items()):
    cat_size = sum(s for _, s in flist)
    print(f"[{cat}] ({len(flist)} items, {round(cat_size / (1024*1024), 2)} MB):")
    for fname, size in sorted(flist, key=lambda x: x[0])[:8]:
        print(f"  - {fname:<42} ({round(size/1024, 1)} KB)")
    if len(flist) > 8:
        print(f"  ... and {len(flist) - 8} more")
    print()

print("=" * 65)
print(f"Databases Audited : {len(db_statuses)}")
for dbname, stat in db_statuses:
    print(f"  - {dbname:<30} : {stat}")

print(f"\nPython Syntax Errors Detected : {len(syntax_errors)}")
for fname, err in syntax_errors:
    print(f"  - {fname}: {err}")
print("=" * 65)