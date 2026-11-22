import os
import glob
import subprocess
import psutil
import datetime

print('=== 1. RUNNING PROCESSES ===')
running = []
for p in psutil.process_iter(['pid', 'name', 'exe', 'create_time', 'status']):
    try:
        p_name = (p.info['name'] or '').lower()
        p_exe = (p.info['exe'] or '').lower()
        if 'salad' in p_name or 'kale' in p_name or 'salad' in p_exe or 'kale' in p_exe:
            t = datetime.datetime.fromtimestamp(p.info['create_time']).strftime('%Y-%m-%d %H:%M:%S')
            running.append((p.info['pid'], p.info['name'], p.info['exe'], t, p.info['status']))
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

if running:
    for pid, name, exe, t, status in running:
        print(f'  [ACTIVE] PID {pid}: {name} | Exe: {exe} | Started: {t} | Status: {status}')
else:
    print('  NO ACTIVE SALAD / KALE PROCESSES FOUND RUNNING.')

print('\n=== 2. WINDOWS SERVICES ===')
try:
    cmd = ['sc', 'query', 'type=', 'service', 'state=', 'all']
    out = subprocess.check_output(cmd, text=True, errors='ignore')
    salad_services = [line for line in out.splitlines() if 'salad' in line.lower() or 'kale' in line.lower()]
    if salad_services:
        for s in salad_services:
            print('  Found service line:', s)
    else:
        print('  No Salad or Kale Windows services registered.')
except Exception as e:
    print('  Service query error:', e)

print('\n=== 3. SCHEDULED TASKS ===')
try:
    cmd = ['schtasks', '/query', '/fo', 'LIST', '/v']
    out = subprocess.check_output(cmd, text=True, errors='ignore')
    tasks = []
    current_task = {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith('TaskName:'):
            if current_task and ('salad' in str(current_task).lower() or 'kale' in str(current_task).lower()):
                tasks.append(current_task)
            current_task = {'TaskName': line}
        elif ':' in line and current_task:
            k, v = line.split(':', 1)
            current_task[k.strip()] = v.strip()
    if current_task and ('salad' in str(current_task).lower() or 'kale' in str(current_task).lower()):
        tasks.append(current_task)
    if tasks:
        for t in tasks:
            print(f"  TASK: {t.get('TaskName')} | Status: {t.get('Status')} | Next Run: {t.get('Next Run Time')} | Action: {t.get('Task To Run')}")
    else:
        print('  No scheduled tasks related to Salad found.')
except Exception as e:
    print('  Schtasks error:', e)

print('\n=== 4. APPDATA / LOCALAPPDATA / E: SALAD DIRECTORIES ===')
user_profile = os.environ.get('USERPROFILE', '')
appdata = os.environ.get('APPDATA', '')
localappdata = os.environ.get('LOCALAPPDATA', '')

paths_to_check = [
    os.path.join(appdata, 'Salad'),
    os.path.join(localappdata, 'Salad'),
    os.path.join(localappdata, 'Programs', 'Salad'),
    r'E:\Salad',
    r'E:\Salad\Kale',
    r'E:\Salad\logs'
]

for p in paths_to_check:
    if os.path.exists(p):
        print(f'  FOUND: {p}')
        recent = []
        for root, dirs, files in os.walk(p):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(fp)
                    recent.append((mtime, fp, os.path.getsize(fp)))
                except OSError:
                    pass
        recent.sort(reverse=True)
        print(f'    Total files: {len(recent)}')
        print('    Top 5 most recently modified files:')
        for mt, fp, sz in recent[:5]:
            t_str = datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%d %H:%M:%S')
            print(f'      [{t_str}] {fp} ({sz} bytes)')
print('\n=== 5. FORENSIC LOG & WORKLOAD ANALYSIS ===')
import re

log_files = [
    r'E:\SaladData\ProgramData\Salad\logs\log-20260907.txt',
    r'E:\SaladData\ProgramData\Salad\logs\log-20260906.txt',
    r'E:\SaladData\ProgramData\Salad\logs\log-20260905.txt',
    r'E:\SaladData\ProgramData\Salad\logs\log-20260901.txt',
    r'E:\SaladData\ProgramData\Salad\logs\log-20260825.txt',
    r'E:\SaladData\ProgramData\Salad\logs\log-20260815.txt'
]

for lp in log_files:
    if os.path.exists(lp):
        with open(lp, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        workloads = [l.strip() for l in lines if any(k in l.lower() for k in ['startworkload', 'stopworkload', 'miner started', 'mining started', 't-rex', 'rigel', 'earning', 'sgs-client', 'container started'])]
        errors = [l.strip() for l in lines if '[err]' in l.lower() or '[fat]' in l.lower()]
        print(f'File: {os.path.basename(lp)} ({len(lines)} lines)')
        print(f'  Workload Events ({len(workloads)}):')
        for w in workloads[:5]:
            print(f'    {w[:130]}')
        if not workloads:
            print('    (No active workload start/stop events - daemon was in idle/heartbeat-only state)')

print('\n=== 7. LEVELDB ACCOUNT & EARNINGS INSPECTION ===')
ldb_dir = os.path.join(appdata, 'Salad', 'Local Storage', 'leveldb')
if os.path.exists(ldb_dir):
    for f in os.listdir(ldb_dir):
        fp = os.path.join(ldb_dir, f)
        if os.path.isfile(fp):
            try:
                with open(fp, 'rb') as lf:
                    data = lf.read().decode('latin1', errors='ignore')
                    for match in re.finditer(r'(balance|earned|lifetime|currentBalance|totalEarnings)[\"\'\s:=]+([0-9\.]+)', data, re.IGNORECASE):
                        print(f'  Match in {f}: {match.group(0)}')
                    for match in re.finditer(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', data):
                        print(f'  Email in {f}: {match.group(0)}')
            except Exception as e:
                pass


