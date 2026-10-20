import psutil
import datetime

for p in psutil.process_iter(['pid', 'name', 'create_time', 'cmdline']):
    try:
        t = datetime.datetime.fromtimestamp(p.info['create_time'])
        if t.hour == 14 and t.minute == 0 and 20 <= t.second <= 35:
            cmd = ' '.join(p.info.get('cmdline') or [])
            print(f"{t.strftime('%H:%M:%S')} | PID={p.info['pid']} | {p.info['name']} | {cmd}")
    except Exception:
        pass
