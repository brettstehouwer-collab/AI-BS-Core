import os
import glob
import json
import re

search_dirs = [
    r"C:\Users\footb\Downloads",
    r"C:\Users\footb\Documents",
    r"C:\Users\footb\OneDrive",
    r"C:\AI-BS\saved_data",
    r"C:\AI-BS\backend"
]

patterns = ["*.csv", "*.xlsx", "*.xls", "*.json", "*.txt"]
keywords = ["roster", "contact", "athlete", "prospect", "debut", "export", "phone", "email", "recruit", "showcase", "camp", "tournament", "las vegas", "vegas", "ballislife", "prep"]

print("=== SEARCHING FOR CONTACT/ROSTER/EXPORT FILES ===")
found_files = []

for sdir in search_dirs:
    if not os.path.exists(sdir):
        continue
    for root, dirs, files in os.walk(sdir):
        # Skip heavy node_modules, .git, venv, brain
        dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", ".system_generated", "cache", "__pycache__", "brain"]]
        for f in files:
            f_lower = f.lower()
            if any(f_lower.endswith(ext.replace("*", "")) for ext in patterns):
                if any(k in f_lower for k in keywords):
                    full_p = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(full_p)
                        if 100 < sz < 50_000_000: # between 100 bytes and 50MB
                            found_files.append((full_p, sz))
                    except Exception:
                        pass

print(f"Total matching files found: {len(found_files)}")
for p, s in sorted(found_files, key=lambda x: x[1], reverse=True)[:40]:
    print(f"  {s:8d} bytes: {p}")
