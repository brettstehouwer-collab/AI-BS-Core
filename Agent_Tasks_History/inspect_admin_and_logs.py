import sqlite3
import os
import glob
import json

print("=== SQLITE DATABASES & ADMIN SUBMISSIONS ===")
dbs = glob.glob(r'C:\AI-BS\*.db') + glob.glob(r'C:\AI-BS\backend\*.db') + glob.glob(r'C:\AI-BS\saved_data\*.db')
for db in dbs:
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cur.fetchall()]
        print(f"DB: {os.path.basename(db)} | Tables: {tables}")
        for t in tables[:3]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = cur.fetchone()[0]
                print(f"   -> Table '{t}': {cnt} records")
            except Exception:
                pass
        conn.close()
    except Exception as e:
        print(f"DB {os.path.basename(db)} err: {e}")

print("\n=== COMFYUI GENERATED OUTPUTS & HISTORY ===")
output_dir = r'E:\ComfyUI_windows_portable\ComfyUI\output'
if not os.path.exists(output_dir):
    output_dir = r'C:\AI-BS\ComfyUI\output'
print("ComfyUI output dir exists:", os.path.exists(output_dir), output_dir)
if os.path.exists(output_dir):
    files = glob.glob(os.path.join(output_dir, '*.*'))
    print(f"Total media outputs: {len(files)}")
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    for f in files[:10]:
        print(f"   {os.path.basename(f)} ({round(os.path.getsize(f)/1024, 1)} KB)")

print("\n=== ERROR LOGS SCANNING ===")
# Scan last 100 lines of top log files for [ERROR], [CRITICAL], Traceback, Exception, or Timeout
for lf in glob.glob(r'C:\AI-BS\logs\*.log'):
    try:
        with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            err_lines = [l.strip() for l in lines[-100:] if any(k in l.upper() for k in ['ERROR', 'CRITICAL', 'TRACEBACK', 'EXCEPTION', 'TIMEOUT', 'FAILED'])]
            if err_lines:
                print(f"\n[Log: {os.path.basename(lf)}] found {len(err_lines)} error/warning events in last 100 lines:")
                for el in err_lines[-4:]:
                    print(f"   {el[:140]}")
    except Exception as e:
        pass
