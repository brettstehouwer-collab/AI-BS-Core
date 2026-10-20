import psutil
import json

targets = ['python', 'pythonw', 'node', 'nginx', 'wsl', 'chroma', 'aibs', 'ollama', 'cloudflared', 'Pearl']
procs = []

for p in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
    try:
        pname = p.info['name'] or ''
        cmd = ' '.join(p.info['cmdline'] or [])
        if any(t.lower() in pname.lower() or t.lower() in cmd.lower() for t in targets):
            procs.append({
                'pid': p.info['pid'],
                'name': pname,
                'cmdline': (cmd[:180] + '...') if len(cmd) > 180 else cmd,
                'rss_mb': round(p.info['memory_info'].rss / (1024 * 1024), 1) if p.info['memory_info'] else 0
            })
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

procs.sort(key=lambda x: x['rss_mb'], reverse=True)
with open(r'C:\AI-BS\scripts\process_audit.json', 'w', encoding='utf-8') as f:
    json.dump(procs, f, indent=2)

print(f"Saved {len(procs)} active processes.")
