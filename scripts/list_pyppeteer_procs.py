import psutil
import datetime

print("--- Scanning for pyppeteer_env processes ---")
for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time', 'ppid']):
    try:
        exe = p.info.get('exe') or ''
        cmd = ' '.join(p.info.get('cmdline') or [])
        if 'pyppeteer_env' in exe.lower() or 'pyppeteer_env' in cmd.lower():
            ctime = datetime.datetime.fromtimestamp(p.info['create_time']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"PID: {p.info['pid']} | PPID: {p.info['ppid']} | Created: {ctime} | Name: {p.info['name']} | Cmd: {cmd}")
    except Exception:
        pass
