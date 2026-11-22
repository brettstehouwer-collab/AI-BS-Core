from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from dotenv import dotenv_values
import psutil
import requests

root = Path(r'C:\AI-BS')
cp = Path((Path(__file__).parent / 'proposal_history_v48_checkpoint.txt').read_text(encoding='utf-8').strip())
audit = json.loads((cp / 'source_audit.json').read_text(encoding='utf-8'))
assert audit['passed'] == audit['count'] and audit['count'] == 23
assert json.loads((cp / 'preservation_before_restart.json').read_text(encoding='utf-8'))['status'] == 'verified'
old = json.loads((cp / 'source46_runtime_for_identity.json').read_text(encoding='utf-8'))
assert json.loads((cp / 'verified.json').read_text(encoding='utf-8'))['passed']
assert json.loads((cp / 'client_green.json').read_text(encoding='utf-8'))['passed'] == 84
assert json.loads((cp / 'view_green.json').read_text(encoding='utf-8'))['passed'] == 30
runtime = cp / 'runtime_after_connection_closed'
runtime.mkdir()
state_path = runtime / 'process.json'
report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'preflight',
          'controlled_stop': {}, 'source_version': '5.329.48'}
flags = ['AI_BS_RECDEBUT_OUTBOUND_ENABLED', 'AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED',
         'AI_BS_DISCORD_NOTIFICATIONS_ENABLED', 'AI_BS_BACKEND_MANAGE_DAEMONS',
         'AI_BS_BACKEND_BACKGROUND_ENABLED', 'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS']
session = requests.Session()
session.trust_env = False


def save():
    state_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def listeners(port):
    return [c for c in psutil.net_connections(kind='tcp') if c.status == 'LISTEN' and c.laddr.port == port]


try:
    serving, launcher = psutil.Process(old['serving_pid']), psutil.Process(old['pid'])
    assert serving.create_time() == old['serving_created'] and serving.exe() == old['serving_exe'] and serving.ppid() == launcher.pid
    assert launcher.create_time() == old['created'] and launcher.cmdline() == old['argv'] and serving.cmdline()[1:] == old['argv'][1:]
    current = listeners(8080)
    assert current and all(c.pid == serving.pid and c.laddr.ip == '127.0.0.1' for c in current)
    assert not serving.children(), 'Serving process has active child work; preserve it'
    assert not session.get('http://127.0.0.1:11434/api/ps', timeout=5).json().get('models'), 'Loaded model work must be preserved'
    actual_environment = serving.environ()
    assert all(actual_environment.get(key) == 'false' for key in flags)
    del actual_environment
    environment = dict(os.environ)
    for path in (root / '.env', root / 'backend/.env'):
        if path.is_file():
            environment.update({k: v for k, v in dotenv_values(path).items() if v is not None})
    key = environment.get('AI_BS_ADMIN_KEY', '')
    assert key, 'Configured administrator credential is unavailable'
    tasks = session.get('http://127.0.0.1:8080/api/chat/coding-tasks', headers={'X-Admin-Key': key}, timeout=5)
    assert tasks.status_code == 200 and isinstance(tasks.json().get('items'), list)
    rows = tasks.json()['items']
    active_states = {'RUNNING', 'GENERATING', 'TESTING', 'APPLYING', 'VALIDATING', 'REPAIRING', 'VERIFYING', 'ADMITTED'}
    active = [r for r in rows if str(r.get('state', '')).upper() in active_states or str(r.get('application_state', '')).upper() == 'APPLYING']
    assert not active, 'Task history reports potentially active work; preserve and inspect'
    report['listed_task_records_checked'] = len(rows)
    del rows, tasks, key
    session.close()
    session = requests.Session()
    session.trust_env = False
    report['other_listeners_before'] = [{'port': p, 'pid': c.pid, 'created': psutil.Process(c.pid).create_time()} for p in (8000, 5173, 11434, 11435) for c in listeners(p)]
    assert not [c for c in serving.net_connections(kind='tcp') if c.status == psutil.CONN_ESTABLISHED and c.laddr and c.laddr.port == 8080], 'Inbound API connection is active; preserve it'
    report['controlled_stop'] = {'serving_pid': serving.pid, 'launcher_pid': launcher.pid,
                                 'identity_checked': True, 'quiescent_inbound_children_model_checked': True}
    save()
    serving.terminate()
    serving.wait(timeout=15)
    launcher.wait(timeout=15)
    report['controlled_stop']['terminal_confirmed'] = True
    assert not listeners(8080)
    for key in flags:
        environment[key] = 'false'
    environment.update(PYTHONUNBUFFERED='1', AIBS_DEV_RELOAD='0')
    argv = [str(root / 'pyppeteer_env/Scripts/python.exe'), '-m', 'uvicorn', 'AI_BS_Backend:app',
            '--app-dir', str(root / 'backend'), '--host', '127.0.0.1', '--port', '8080', '--workers', '1', '--no-access-log']
    with (runtime / 'backend.log').open('xb') as stream:
        process = subprocess.Popen(argv, cwd=root / 'backend', env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    identity = psutil.Process(process.pid)
    report.update(status='starting', pid=process.pid, created=identity.create_time(), exe=identity.exe(), argv=argv,
                  source_hashes={n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in
                                 ['backend/AI_BS_Backend.py', 'backend/core/http_fallback.py', 'backend/core/hybrid_reasoning_engine.py', 'backend/core/personal_intelligence_memory.py', 'backend/core/personal_memory_scope.py', 'backend/routers/personal_intelligence_router.py', 'backend/core/owned_vault.py', 'backend/core/chat_archive.py', 'backend/routers/memory_router.py', 'backend/core/sovereign_reasoning/memory_vault.py', 'backend/core/coding_preparation_proposals.py', 'backend/core/coding_preparation_planning.py', 'backend/core/coding_preparation.py', 'backend/routers/coding_preparation_router.py', 'backend/routers/coding_review_router.py', 'backend/core/coding_journal.py', 'backend/core/coding_recovery.py', 'backend/core/coding_repository_snapshot.py']},
                  controlled_flags={key: 'false' for key in flags})
    save()
    print(json.dumps({'status': 'starting', 'pid': process.pid, 'state': str(state_path)}), flush=True)
    for _ in range(45):
        if process.poll() is not None:
            report.update(status='exited', exit_code=process.returncode)
            break
        try:
            response = session.get('http://127.0.0.1:8080/health', timeout=1)
            if response.status_code == 200:
                current = listeners(8080)
                assert current and len({c.pid for c in current}) == 1 and all(c.laddr.ip == '127.0.0.1' for c in current)
                child = psutil.Process(current[0].pid)
                assert child.ppid() == identity.pid and child.cmdline()[1:] == argv[1:]
                assert os.path.normcase(child.exe()) == os.path.normcase(sys._base_executable)
                values = child.environ()
                assert all(values.get(k) == 'false' for k in flags)
                del values
                report.update(status='healthy', serving_pid=child.pid, serving_created=child.create_time(), serving_exe=child.exe())
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    else:
        report['status'] = 'still_starting'
    report['other_listeners_after'] = [{'port': p, 'pid': c.pid, 'created': psutil.Process(c.pid).create_time()} for p in (8000, 5173, 11434, 11435) for c in listeners(p)]
    assert report['other_listeners_after'] == report['other_listeners_before'], 'Unrelated listener identity changed; inspect without restarting it'
except BaseException as error:
    report.update(status='inspection_needed', error_type=type(error).__name__,
                  reason=str(error) if isinstance(error, AssertionError) else 'Retain exact process/log state and inspect; do not restart on observer failure')
finally:
    report['observed_at_utc'] = datetime.now(timezone.utc).isoformat()
    save()
    session.close()
    print(json.dumps(report), flush=True)
raise SystemExit(report['status'] != 'healthy')
