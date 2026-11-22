"""Controlled restoration only; run explicitly after root's source/test review.

No inference, generated-code execution, daemon management or browser requests.
All evidence and the consistent personal database snapshot remain private/local.
An observer failure preserves started identities for inspection; never replaces them.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from dotenv import dotenv_values
import psutil
import requests


ROOT = Path(r'C:\AI-BS')
WORK = ROOT / 'workspace'
CP = Path((WORK / 'proposal_v46_checkpoint.txt').read_text(encoding='utf-8').strip())
PRIOR = ROOT / 'backups/production_readiness_5_329_33_20261024T054356815Z'
SOURCE45 = ROOT / 'backups/planning_controls_5_329_45_20261024T131228359055Z'
FRONTEND_RECORD = ROOT / 'backups/localhost_restore_20261024T1406033034435Z/runtime_verified.json'
GATEWAY_RECORD = ROOT / 'backups/gateway_identity_5_329_37_20261024T072602753556Z/build.json'
MODEL_RECORD = PRIOR / 'chat_acceptance_v34/preflight.json'
FLAGS = (
    'AI_BS_RECDEBUT_OUTBOUND_ENABLED', 'AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED',
    'AI_BS_DISCORD_NOTIFICATIONS_ENABLED', 'AI_BS_BACKEND_MANAGE_DAEMONS',
    'AI_BS_BACKEND_BACKGROUND_ENABLED', 'AI_BS_ALLOW_DESTRUCTIVE_ACTIONS',
)
PERSONAL_TABLES = ('user_profiles', 'memory_facts', 'episodic_logs', 'knowledge_graph_triplets')
ALLOWED_ENV = {
    'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATH', 'PATHEXT', 'TEMP', 'TMP',
    'USERPROFILE', 'USERNAME', 'USERDOMAIN', 'LOCALAPPDATA', 'APPDATA',
    'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'COMMONPROGRAMFILES',
    'COMMONPROGRAMFILES(X86)', 'HOMEDRIVE', 'HOMEPATH', 'NUMBER_OF_PROCESSORS',
    'PROCESSOR_ARCHITECTURE', 'CUDA_PATH',
}
report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'preflight',
          'scope': 'Only existing API, customized model server and gateway restoration; no inference or execution.',
          'processes': {}, 'checks': [], 'local_only': True}
started_processes = {}
runtime = None
session = requests.Session()
session.trust_env = False


def now():
    return datetime.now(timezone.utc).isoformat()


def progress(phase):
    report['phase'] = phase
    print(json.dumps({'phase': phase, 'observed_at_utc': now()}), flush=True)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def exclusive_json(path, data):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def save():
    if runtime is not None:
        # A single fresh run owns this status file; originals from other runs are never used.
        with (runtime / 'process.json').open('w', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())


def check(name, passed, **metadata):
    report['checks'].append({'name': name, 'passed': bool(passed), **metadata})
    assert passed, name


def listeners(port):
    return [c for c in psutil.net_connections(kind='tcp')
            if c.status == psutil.CONN_LISTEN and c.laddr.port == port]


def identity(process):
    return {'pid': process.pid, 'created': process.create_time(), 'exe': process.exe(),
            'argv': process.cmdline(), 'parent_pid': process.ppid()}


def no_link_path(path):
    path = Path(path)
    assert path.is_absolute(), 'Evidence path must be absolute'
    for component in (path, *path.parents):
        assert not component.is_symlink() and not component.is_junction(), 'Linked evidence paths are unsupported'


def frontend_identity():
    reference = read_json(FRONTEND_RECORD)
    original = reference['process']
    actual = listeners(5173)
    assert len(actual) == 1 and actual[0].pid == original['ProcessId'] == 111384
    assert actual[0].laddr.ip == '127.0.0.1', 'Frontend exposure changed'
    process = psutil.Process(actual[0].pid)
    created = datetime.fromisoformat(original['CreationDate']).timestamp()
    assert abs(process.create_time() - created) < 0.001, 'Frontend PID was reused'
    assert os.path.normcase(process.exe()) == os.path.normcase(original['ExecutablePath'])
    expected = [str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1',
                '--port', '5173', '--strictPort']
    assert process.cmdline()[1:] == expected, 'Frontend command differs'
    assert sha(ROOT / 'frontend/vite.config.js') == reference['config_sha256']
    return identity(process)


def verify_documents(phase):
    baseline = read_json(PRIOR / 'document_baseline.json')
    assert baseline['status'] == 'verified'
    results = []
    for label, store in baseline['stores'].items():
        source, backup = Path(store['path']), Path(store['snapshot'])
        no_link_path(source)
        no_link_path(backup)
        current = {}
        for base, directories, names in os.walk(source, followlinks=False):
            for name in directories:
                path = Path(base) / name
                assert not path.is_symlink() and not path.is_junction(), 'Selected document directory became linked'
            for name in names:
                path = Path(base) / name
                assert not path.is_symlink(), 'Selected document file became linked'
                current[path.relative_to(source).as_posix()] = sha(path)
        originals_ok = current == store['hashes']
        copies_ok = all((backup / name).is_file() and sha(backup / name) == digest
                        for name, digest in store['hashes'].items())
        results.append({'store': label, 'files': len(current),
                        'originals_match_baseline': originals_ok, 'saved_copies_match': copies_ok})
        assert originals_ok and copies_ok, 'Creative documents or retained copies changed; preserve for review'
    result = {'observed_at_utc': now(), 'status': 'verified', 'phase': phase, 'documents': results}
    exclusive_json(runtime / ('documents_' + phase + '.json'), result)
    return result


def ro_database(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=8)
    connection.execute('PRAGMA query_only=ON')
    return connection


def personal_snapshot():
    source = ROOT / 'backend/database/aibs_personal_intelligence.db'
    snapshot = runtime / 'personal_intelligence.snapshot.sqlite'
    no_link_path(source)
    assert source.is_file(), 'Existing personal database is unavailable; no empty replacement permitted'
    snapshot.touch(exist_ok=False)
    deadline = time.monotonic() + 45
    def bounded_backup(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError('Consistent personal snapshot deadline reached')
    original = ro_database(source)
    target = sqlite3.connect(snapshot)
    try:
        original.backup(target, pages=256, progress=bounded_backup, sleep=0.1)
        assert target.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        counts = {name: target.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0]
                  for name in PERSONAL_TABLES}
    finally:
        target.close()
        original.close()
    result = {'source': str(source), 'snapshot': str(snapshot), 'snapshot_sha256': sha(snapshot),
              'counts': counts, 'integrity_ok': True, 'local_only': True,
              'scope': 'Consistent private SQLite backup; raw rows never printed or uploaded.'}
    exclusive_json(runtime / 'personal_backup.json', result)
    return result


def verify_personal(saved):
    before, current = ro_database(saved['snapshot']), ro_database(saved['source'])
    result = {'status': 'inspecting', 'tables': {}, 'raw_rows_exported': False}
    try:
        for connection in (before, current):
            connection.execute('BEGIN')
        schema_query = 'SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name'
        result['schema_exact'] = before.execute(schema_query).fetchall() == current.execute(schema_query).fetchall()
        result['integrity_ok'] = current.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        for name in PERSONAL_TABLES:
            old = before.execute('SELECT * FROM "' + name + '" ORDER BY rowid').fetchall()
            new = current.execute('SELECT * FROM "' + name + '" ORDER BY rowid').fetchall()
            result['tables'][name] = {'before': len(old), 'current': len(new), 'every_row_exact': old == new}
        result['snapshot_hash_exact'] = sha(saved['snapshot']) == saved['snapshot_sha256']
        assert result['schema_exact'] and result['integrity_ok'] and result['snapshot_hash_exact']
        assert all(item['every_row_exact'] for item in result['tables'].values()), 'Personal rows changed during restoration'
        result['status'] = 'verified'
    finally:
        before.close()
        current.close()
        exclusive_json(runtime / 'personal_preservation_after.json', result)
    return result


def launch(name, argv, cwd, environment):
    progress('starting_' + name)
    with (runtime / (name + '.log')).open('xb') as stream:
        process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    observed = psutil.Process(process.pid)
    item = {'launcher': identity(observed), 'argv': argv, 'status': 'starting'}
    report['processes'][name] = item
    started_processes[name] = process
    save()
    return process, observed, item


def confirm_serving(name, launcher, argv, port, allowed_exes):
    recorded = report['processes'][name]['launcher']
    assert launcher.create_time() == recorded['created'] and launcher.cmdline() == recorded['argv']
    owners = listeners(port)
    assert owners and len({c.pid for c in owners}) == 1 and all(c.laddr.ip == '127.0.0.1' for c in owners)
    serving = psutil.Process(owners[0].pid)
    assert os.path.normcase(serving.exe()) in {os.path.normcase(str(path)) for path in allowed_exes}
    assert serving.cmdline()[1:] == argv[1:], 'Serving command differs from the reviewed command'
    if serving.pid != launcher.pid:
        parents = serving.parents()
        assert any(p.pid == launcher.pid and p.create_time() == launcher.create_time() for p in parents)
        assert serving.create_time() >= launcher.create_time(), 'Serving process predates launcher'
    return serving


def wait_health(name, process, probe):
    deadline = time.monotonic() + 45
    last_progress = time.monotonic()
    while time.monotonic() < deadline:
        assert process.poll() is None, 'Started process exited; inspect its retained local log without replacement'
        try:
            if probe():
                report['processes'][name]['status'] = 'verified'
                save()
                return
        except requests.RequestException:
            pass
        if time.monotonic() - last_progress >= 10:
            print(json.dumps({'phase': 'waiting_' + name, 'remaining_seconds': max(0, int(deadline-time.monotonic()))}), flush=True)
            last_progress = time.monotonic()
        time.sleep(0.5)
    raise TimeoutError('Started service did not confirm within its bounded observation window')


try:
    assert CP.parent == ROOT / 'backups' and CP.name.startswith('retained_proposal_5_329_46_')
    assert CP.is_dir(), 'Root checkpoint must already exist'
    no_link_path(CP)
    fresh_runtime = CP / 'runtime'
    fresh_runtime.mkdir()  # Exclusive run; an existing runtime is inspection-only.
    runtime = fresh_runtime
    save()
    frontend_before = frontend_identity()
    check('Required service ports are vacant', all(not listeners(p) for p in (8080, 8000, 11434, 11435)))
    report['frontend_before'] = frontend_before
    progress('preserving_originals')
    report['documents_before'] = verify_documents('before')
    personal = personal_snapshot()
    report['personal_snapshot'] = {'snapshot_sha256': personal['snapshot_sha256'],
                                  'counts': personal['counts'], 'integrity_ok': True}

    model = read_json(MODEL_RECORD)
    assert model['store'] == str(ROOT / 'models/ollama') and model['model'] == 'stehouwer_llm:latest'
    assert sha(model['manifest']) == model['manifest_sha256'] == '5213ff76656a20b564e1001cc3cc4e9e9b7f8cc80dd837cde54b341127e60b12'
    assert sha(model['executable']) == model['exe_sha256'] == '0957bdaa7b52e163cdc7feb1275653f27c6b32e8ba309e957bdbb83493e97a4b'
    for layer in model['layers']:
        actual = Path(layer['path']).stat()
        assert actual.st_size == layer['bytes'] and actual.st_mtime_ns == layer['mtime_ns'], 'Existing model layer metadata changed'
    for relative, metadata in model['custom_modelfiles'].items():
        assert sha(ROOT / relative) == metadata['sha256'], 'Customized Modelfile changed'
    report['model_preflight'] = {'executable_sha256': model['exe_sha256'], 'manifest_sha256': model['manifest_sha256'],
                                 'layer_metadata_verified': len(model['layers']), 'weights_fully_rehashed': False,
                                 'custom_modelfiles_verified': len(model['custom_modelfiles']), 'model_pull_or_creation': False}
    build = read_json(GATEWAY_RECORD)
    assert build['status'] == 'built_verified' and build['compiled_version'] == '5.329.37'
    assert sha(build['binary']) == build['sha256'] == '18ed747d07b6a41aaa776175d00c4b16e32f3f3173063c142f4aaa92620c73a9'
    report['gateway_binary'] = {'sha256': build['sha256'], 'compiled_version': build['compiled_version']}
    prior_runtime = read_json(SOURCE45 / 'runtime/process.json')
    source_names = list(prior_runtime['source_hashes'])
    proposal_module = 'backend/core/coding_preparation_proposals.py'
    if (ROOT / proposal_module).is_file():
        source_names.append(proposal_module)
    report['source_hashes'] = {name: sha(ROOT / name) for name in source_names}
    report['source_version'] = (ROOT / 'version.txt').read_text(encoding='utf-8').strip()

    config = dict(os.environ)
    for path in (ROOT / '.env', ROOT / 'backend/.env'):
        if path.is_file():
            config.update({key: value for key, value in dotenv_values(path).items() if value is not None})
    admin_key = config.get('AI_BS_ADMIN_KEY', '')
    assert admin_key and config.get('AI_BS_ADMIN_EMAILS'), 'Existing administrator configuration unavailable; no substitute permitted'
    backend_environment = dict(config)
    backend_environment.update({name: 'false' for name in FLAGS})
    backend_environment.update(PYTHONUNBUFFERED='1', AIBS_DEV_RELOAD='0')
    report['controlled_flags'] = {name: 'false' for name in FLAGS}
    limited_environment = {key: value for key, value in os.environ.items() if key.upper() in ALLOWED_ENV}
    model_environment = dict(limited_environment)
    model_environment.update(OLLAMA_MODELS=model['store'], OLLAMA_HOST='127.0.0.1:11434', CUDA_VISIBLE_DEVICES='0',
                             OLLAMA_NUM_PARALLEL='1', OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_KEEP_ALIVE='5m', OLLAMA_NO_CLOUD='1')
    model_environment.update({name: 'false' for name in FLAGS})
    gateway_environment = dict(limited_environment)
    gateway_environment.update({name: config[name] for name in ('AI_BS_ADMIN_KEY', 'AI_BS_ADMIN_EMAILS')})
    gateway_environment.update({name: 'false' for name in FLAGS})
    save()

    assert not listeners(8080)
    backend_argv = [str(ROOT / 'pyppeteer_env/Scripts/python.exe'), '-m', 'uvicorn', 'AI_BS_Backend:app',
                    '--app-dir', str(ROOT / 'backend'), '--host', '127.0.0.1', '--port', '8080',
                    '--workers', '1', '--no-access-log']
    process, launcher, item = launch('backend', backend_argv, ROOT / 'backend', backend_environment)
    def backend_probe():
        response = session.get('http://127.0.0.1:8080/health', timeout=2)
        if response.status_code != 200:
            return False
        serving = confirm_serving('backend', launcher, backend_argv, 8080,
                                  [backend_argv[0], prior_runtime['serving_exe']])
        values = serving.environ()
        assert all(values.get(name) == 'false' for name in FLAGS)
        item['serving'] = identity(serving)
        item['flags_verified_false'] = True
        item['health_status'] = response.status_code
        return True
    wait_health('backend', process, backend_probe)

    assert not listeners(11434)
    model_argv = [model['executable'], 'serve']
    process, launcher, item = launch('ollama', model_argv, Path(model['executable']).parent, model_environment)
    def model_probe():
        response = session.get('http://127.0.0.1:11434/api/tags', timeout=2)
        if response.status_code != 200:
            return False
        serving = confirm_serving('ollama', launcher, model_argv, 11434, [model['executable']])
        rows = response.json().get('models', [])
        matches = [row for row in rows if row.get('name') == model['model']]
        assert len(matches) == 1 and matches[0].get('digest') == model['manifest_sha256']
        values = serving.environ()
        assert values.get('OLLAMA_MODELS') == model['store'] and values.get('OLLAMA_HOST') == '127.0.0.1:11434'
        assert values.get('OLLAMA_NO_CLOUD') == '1' and all(values.get(name) == 'false' for name in FLAGS)
        item.update(serving=identity(serving), registered_model_digest=matches[0]['digest'], registered_models=len(rows))
        return True
    wait_health('ollama', process, model_probe)

    assert not listeners(8000)
    gateway_argv = [build['binary']]
    process, launcher, item = launch('gateway', gateway_argv, ROOT, gateway_environment)
    def gateway_probe():
        response = session.get('http://127.0.0.1:8000/health', timeout=2)
        if response.status_code != 200:
            return False
        serving = confirm_serving('gateway', launcher, gateway_argv, 8000, [build['binary']])
        assert response.json().get('version') == build['compiled_version']
        values = serving.environ()
        assert all(values.get(name) == 'false' for name in FLAGS)
        statuses = session.get('http://127.0.0.1:8000/api/daemons/status', headers={'X-Admin-Key': admin_key}, timeout=2)
        assert statuses.status_code == 200
        rows = statuses.json()
        assert len(rows) == 11 and all(row.get('running') is False and row.get('pid') == 0 and row.get('state') == 'stopped' for row in rows.values())
        children = serving.children(recursive=True)
        assert all(child.name().lower() == 'conhost.exe' and Path(child.exe()).parent == Path(os.environ['SYSTEMROOT']) / 'System32' for child in children)
        item.update(serving=identity(serving), compiled_version=build['compiled_version'], registered_daemons=11,
                    all_registered_daemons_stopped=True, launched_managed_daemons=False)
        return True
    wait_health('gateway', process, gateway_probe)

    progress('verifying_access_and_preservation')
    path = '/api/chat/coding-tasks/preparations/identity'
    for port in (8080, 8000):
        anonymous = session.get('http://127.0.0.1:' + str(port) + path, timeout=3)
        authorized = session.get('http://127.0.0.1:' + str(port) + path, headers={'X-Admin-Key': admin_key}, timeout=3)
        check('Actual preparation identity authorization on port ' + str(port), anonymous.status_code == 403 and authorized.status_code == 200,
              anonymous_status=anonymous.status_code, administrator_status=authorized.status_code)
        payload = authorized.json()
        check('Verified local owner and no execution authority on port ' + str(port), payload.get('owner') == 'local_admin'
              and 'ai-bs' in payload.get('repository_ids', []) and payload.get('execution_authorized') is False
              and payload.get('verification_status') == 'not_run')
    del admin_key, config, backend_environment, gateway_environment
    check('Embedding listener remains absent', not listeners(11435))
    report['frontend_after'] = frontend_identity()
    check('Frontend listener identity preserved', report['frontend_after'] == frontend_before)
    report['documents_after'] = verify_documents('after')
    report['personal_preservation_after'] = verify_personal(personal)
    check('Loaded source files stayed exact', all(sha(ROOT / name) == digest for name, digest in report['source_hashes'].items()))
    report['status'] = 'healthy_protected_no_inference'
    report['inference_performed'] = False
    report['no_browser_request'] = True
    report['managed_daemons_started'] = False
    report['vm_or_execution_fallback'] = False
except BaseException as error:
    report['status'] = 'inspection_needed'
    report['error_type'] = type(error).__name__
    report['reason'] = str(error) if isinstance(error, AssertionError) else 'Inspect fresh local checkpoint/logs and preserved process identities; no replacement was attempted.'
    report['started_processes_preserved'] = {name: {'pid': process.pid, 'exit_code': process.poll()}
                                              for name, process in started_processes.items()}
finally:
    report['observed_at_utc'] = now()
    save()
    session.close()
    print(json.dumps({'status': report['status'], 'phase': report.get('phase'),
                      'processes': {name: {'pid': item['launcher']['pid'], 'status': item['status']}
                                    for name, item in report['processes'].items()},
                      'checks_passed': sum(item['passed'] for item in report['checks']),
                      'checks_total': len(report['checks']), 'error_type': report.get('error_type')}), flush=True)

raise SystemExit(report['status'] != 'healthy_protected_no_inference')
