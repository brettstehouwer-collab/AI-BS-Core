import os
import shutil
import json

results = {
    'disk_usage_gb': {},
    'top_level_directories': [],
    'temp_and_scratch_dirs': [],
    'large_files_mb': [],
    'unreferenced_root_scripts': []
}

root = r'C:\AI-BS'

# 1. Total storage
try:
    total, used, free = shutil.disk_usage(root)
    results['disk_usage_gb'] = {
        'total': round(total / (1024**3), 2),
        'used': round(used / (1024**3), 2),
        'free': round(free / (1024**3), 2)
    }
except Exception as e:
    results['disk_usage_gb']['error'] = str(e)

# 2. Top-level directories analysis
ignore_walk = ['.git', 'node_modules', 'Android Studio', 'pyppeteer_env']
for item in os.listdir(root):
    p = os.path.join(root, item)
    if os.path.isdir(p):
        is_temp = item.startswith('temp') or item.startswith('sandbox') or item == 'scratch'
        if is_temp:
            try:
                c = sum(len(f) for _, _, f in os.walk(p))
                results['temp_and_scratch_dirs'].append({'name': item, 'file_count': c})
            except Exception:
                results['temp_and_scratch_dirs'].append({'name': item})
        if item in ['New folder', 'New folder (2)']:
            results['temp_and_scratch_dirs'].append({'name': item, 'note': 'Empty/unnamed folder'})

# 3. Find files > 50MB in C:\AI-BS
for r, dirs, files in os.walk(root):
    if any(ig in r for ig in ignore_walk):
        continue
    for f in files:
        fp = os.path.join(r, f)
        try:
            sz = os.path.getsize(fp)
            if sz > 50 * (1024**2): # > 50MB
                rel = os.path.relpath(fp, root)
                results['large_files_mb'].append({
                    'file': rel,
                    'size_mb': round(sz / (1024**2), 2)
                })
        except Exception:
            pass

# 4. Check unreferenced root python scripts
# Read Launch_AI_BS.bat and AI_BS_Backend.py to see which root scripts are called
invoked_scripts = set()
for lf in [r'C:\AI-BS\Launch_AI_BS.bat', r'C:\AI-BS\Launch_AI_BS_Dev.bat', r'C:\AI-BS\backend\AI_BS_Backend.py']:
    if os.path.exists(lf):
        with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
            invoked_scripts.update(f.read().split())

root_py_files = [f for f in os.listdir(root) if f.endswith('.py')]
for py in root_py_files:
    # check if mentioned anywhere in launchers
    mentioned = any(py in inv for inv in invoked_scripts)
    if not mentioned:
        results['unreferenced_root_scripts'].append(py)

with open(r'C:\AI-BS\scratch\phase8_dead_code_results.json', 'w', encoding='utf-8') as out:
    json.dump(results, out, indent=2)

print('Phase 8 dead code and redundancy sweep completed!')
