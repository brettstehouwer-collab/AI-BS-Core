import os
import glob
import datetime

log_dir = r'C:\AI-BS\logs'
targets = [
    'news_ingest_daemon.log',
    'finance_ingest_daemon.log',
    'vast_clore_pearl_watchdog.log',
    'media_ingest_daemon.log',
    'AI_BS_Universal_Data_Ingestor.log',
    'researcher_daemon.log',
    'drip_trader_daemon.log',
    'news_firehose_daemon.log',
    'auto_healer_daemon.log',
    'broadcast_daemon.log'
]

for t in targets:
    p = os.path.join(log_dir, t)
    if os.path.exists(p):
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime('%Y-%m-%d %H:%M:%S')
        size = os.path.getsize(p)
        print(f"=== {t} (Size: {size} bytes, Modified: {mtime}) ===")
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                tail = lines[-10:] if len(lines) >= 10 else lines
                for l in tail:
                    print("  ", l.strip())
        except Exception as e:
            print("  Err reading:", e)
        print()
    else:
        print(f"=== {t} DOES NOT EXIST ===")
