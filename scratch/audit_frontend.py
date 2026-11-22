import os
import json
import re

results = {
    'frontend_src_components_count': 0,
    'frontend_components_legacy_count': 0,
    'duplicates_found': [],
    'navigation_tabs_count': 0,
    'media_routing_violations': [],
    'vite_config_chunks': {},
    'trainer_frontend_files': {}
}

# 1. Inspect frontend/src/components vs frontend/components
src_comp_dir = r'C:\AI-BS\frontend\src\components'
legacy_comp_dir = r'C:\AI-BS\frontend\components'

if os.path.exists(src_comp_dir):
    src_files = set(os.listdir(src_comp_dir))
    results['frontend_src_components_count'] = len(src_files)
else:
    src_files = set()

if os.path.exists(legacy_comp_dir):
    legacy_files = set(os.listdir(legacy_comp_dir))
    results['frontend_components_legacy_count'] = len(legacy_files)
    overlap = src_files.intersection(legacy_files)
    results['duplicates_found'] = sorted(list(overlap))[:30]

# 2. Check navigationConfig.js tabs
nav_path = os.path.join(src_comp_dir, 'navigationConfig.js')
if os.path.exists(nav_path):
    with open(nav_path, 'r', encoding='utf-8', errors='ignore') as f:
        nav_content = f.read()
    tabs = re.findall(r'id:\s*[\'"]([^\'"]+)[\'"]', nav_content)
    results['navigation_tabs_count'] = len(tabs)

# 3. Check vite.config.js
vite_path = r'C:\AI-BS\frontend\vite.config.js'
if os.path.exists(vite_path):
    with open(vite_path, 'r', encoding='utf-8', errors='ignore') as f:
        vite_code = f.read()
    results['vite_config_chunks'] = {
        'has_manualChunks': 'manualChunks' in vite_code,
        'has_firebase': 'firebase' in vite_code,
        'has_recharts': 'recharts' in vite_code,
        'has_lucide': 'lucide-react' in vite_code or 'lucide' in vite_code,
        'has_xyflow': 'xyflow' in vite_code
    }

# 4. Media routing audit in JSX files
media_regex = re.compile(r'<img[^>]+src=[\'"](/[^>]+)[\'"]')
for root, dirs, files in os.walk(src_comp_dir):
    for f in files:
        if f.endswith('.jsx') or f.endswith('.tsx'):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8', errors='ignore') as jf:
                text = jf.read()
            matches = media_regex.findall(text)
            if matches:
                rel = os.path.relpath(p, src_comp_dir)
                results['media_routing_violations'].append({'file': rel, 'matches': matches[:3]})

# 5. Trainer Frontend
tf_dir = r'C:\AI-BS\trainer_frontend'
if os.path.exists(tf_dir):
    results['trainer_frontend_files'] = {
        'has_main_ts': os.path.exists(os.path.join(tf_dir, 'src', 'main', 'index.ts')),
        'has_preload_ts': os.path.exists(os.path.join(tf_dir, 'src', 'preload', 'index.ts')),
        'has_renderer_tsx': os.path.exists(os.path.join(tf_dir, 'src', 'renderer', 'src', 'App.tsx')),
        'has_daemon_resource': os.path.exists(os.path.join(tf_dir, 'resources', 'btd6_trainer_daemon.exe'))
    }

with open(r'C:\AI-BS\scratch\phase3_frontend_audit_results.json', 'w', encoding='utf-8') as out:
    json.dump(results, out, indent=2)

print('Phase 3 frontend audit script completed!')
