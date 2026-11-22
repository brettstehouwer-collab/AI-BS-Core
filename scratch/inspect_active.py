import json
import os

with open(r'C:\AI-BS\py_health_audit.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== ACTIVE ROOT, BACKEND & SCRIPT PYTHON FILES ===")
for d in data['details']:
    if d['root'] == r'C:\AI-BS' and not d['is_archive']:
        dirname = os.path.dirname(d['rel_file'])
        if dirname in ('', 'backend', 'scripts', 'tests'):
            bp = d['broken_paths']
            print(f"File: {d['rel_file']:<45} | Size: {d['size']:<6}B | Status: {d['status']:<10} | Broken Paths: {len(bp)}")
            if bp:
                for p in bp:
                    print(f"   -> Hardcoded missing path: {p}")
