"""Explicit trusted-local checks. Job containment is not filesystem isolation.

Only a per-task acknowledged request reaches this module. No provider request,
service restart, dependency install, automatic application or host fallback.
"""
import ctypes
import copy
from ctypes import wintypes
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sys
import threading
import time

from . import coding_preparation as preparation
from .coding_journal import write_json_record
from .coding_locks import record_lock, repository_lock
from .coding_process import run_bounded_check
from .coding_vm_staging import _write_new_file
from .coding_workflow import STORE as REPOSITORY_LOCK_STORE

ROOT = Path(__file__).resolve().parents[2]
NODE = ROOT/'runtime/devtools/node-v24.22.1-win-x64/node.exe'
NPM = NODE.parent/'node_modules/npm/bin/npm-cli.js'
_KEY = secrets.token_bytes(32)  # Runtime authority; restart never authorizes old apply.
_RUNNING = {}
_REVIEWS = {}
_LOCK = threading.Lock()
TERMINAL = {'VERIFIED', 'FAILED', 'CANCELLED', 'INTERRUPTED'}


def available():
    if os.name != 'nt': return False
    try:
        import win32job, win32process  # noqa: F401
        return True
    except ImportError:
        return False


def _signature(value):
    return hmac.new(_KEY, preparation._encoded(value), hashlib.sha256).hexdigest()


def _save(folder, result):
    unsigned = {k: v for k, v in result.items() if k != 'runtime_seal'}
    result = {**unsigned, 'runtime_seal': _signature(unsigned)}
    write_json_record(folder/'result.json', preparation._sealed(result))
    return result


def _valid(result, value):
    unsigned = {k: v for k, v in result.items() if k != 'runtime_seal'}
    return (result.get('input_sha256') == preparation._hash(value) and
            hmac.compare_digest(str(result.get('runtime_seal', '')), _signature(unsigned)))


def _active(folder):
    with _LOCK:
        worker = _RUNNING.get(str(folder))
        return worker is not None and worker.is_alive()


def read_log(folder, value, check_id):
    result = preparation._load(folder/'result.json')
    if not _valid(result, value):
        raise preparation.PreparationEvidenceError('Runtime log authority is unavailable')
    check = next((c for c in result.get('checks', []) if c['check_id'] == check_id), None)
    if check is None: raise preparation.PreparationNotFound('Check log not found')
    path = folder/'check_logs'/(check_id+'.json')
    with preparation._directory(path.parent), preparation._source_handle(path) as (handle, length):
        if length > 131072: raise preparation.PreparationEvidenceError('Check log exceeds the retained bound')
        raw = preparation._read_bytes(handle, length)
    if hashlib.sha256(raw).hexdigest() != check['log_sha256']:
        raise preparation.PreparationEvidenceError('Checked output log changed')
    import json
    return {'owner': value['owner'], 'execution_id': value['payload']['execution_id'],
            'check_id': check_id, 'evidence': json.loads(raw)}


def _cancelled(folder):
    return (folder/'local_cancel.json').exists()


def _changed(folder, files):
    changed = []
    for entry in files:
        target = folder/'candidate'/entry['relative_path']
        try:
            with preparation._directory(target.parent), preparation._source_handle(target) as (handle, length):
                raw = preparation._read_bytes(handle, length)
            if length != entry['length'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
                changed.append(entry['relative_path'])
        except (OSError, preparation.PreparationNotFound):
            changed.append(entry['relative_path'])
    return changed


def command(argv):
    """Resolve fixed verification profiles; npm's selected script is shell-capable."""
    if argv[:3] == ['python', '-m', 'unittest']:
        return [sys.executable, '-s', '-B', *argv[1:]]
    if argv[:2] == ['node', '--test'] and NODE.is_file():
        return [str(NODE), *argv[1:]]
    if argv[:2] == ['npm', 'run'] and len(argv) == 3 and NODE.is_file() and NPM.is_file():
        return [str(NODE), str(NPM), '--ignore-scripts', '--offline', 'run', argv[2]]
    raise ValueError('Selected verification runtime is unavailable')


def _environment():
    env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}}
    system = Path(os.environ.get('SYSTEMROOT', 'C:/Windows'))
    env.update(PATH=os.pathsep.join([str(Path(sys.executable).parent), str(NODE.parent), str(system/'System32')]),
               PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
               NPM_CONFIG_OFFLINE='true', NPM_CONFIG_IGNORE_SCRIPTS='true',
               NPM_CONFIG_AUDIT='false', NPM_CONFIG_FUND='false',
               NPM_CONFIG_UPDATE_NOTIFIER='false')
    return env


def start(folder, value, intent, static_checks, release):
    if not available(): raise ValueError('Trusted local Windows process controls are unavailable')
    result = {'kind': 'trusted_local_result', 'input_sha256': preparation._hash(value),
              'state': 'RUNNING', 'checks': [], 'static_checks': static_checks,
              'started_at': time.time(), 'worker': preparation.worker_identity(),
              'resource_limits': {'cpu_percent': 20, 'job_memory_bytes': 536870912, 'below_normal_priority': True},
              'npm_policy': 'Selected script may use a shell; pre/post lifecycle hooks disabled; no installation requested.'}
    _save(folder, result)
    def run():
        started = time.monotonic()
        try:
            if any(check['status'] == 'failed' for check in static_checks):
                result.update(state='FAILED', error='Candidate syntax validation failed')
            else:
                for check in value['checks']:
                    if _cancelled(folder):
                        result['state'] = 'CANCELLED'; break
                    remaining = intent['plan']['limits']['total_seconds']-(time.monotonic()-started)
                    if remaining <= 0:
                        result.update(state='FAILED', error='Overall verification deadline exceeded'); break
                    if _changed(folder, value['files']):
                        result.update(state='FAILED', error='Selected candidate inputs changed'); break
                    env = _environment()
                    for kind in ('USER', 'GLOBAL'):
                        config = folder/('empty-'+kind.lower()+'.npmrc')
                        if not config.exists(): _write_new_file(config, b'')
                        env['NPM_CONFIG_'+kind+'CONFIG'] = str(config)
                    evidence = run_bounded_check(command(check['argv']), folder/'candidate', env,
                        timeout_seconds=min(remaining, intent['plan']['limits']['check_seconds']),
                        output_limit=min(intent['plan']['limits']['output_bytes'], 8192),
                        cancelled=lambda: _cancelled(folder), cpu_rate_percent=20,
                        memory_limit_bytes=536870912, below_normal=True)
                    logs = folder/'check_logs'
                    logs.mkdir(exist_ok=True)
                    log = logs/(check['check_id']+'.json')
                    encoded = preparation._encoded(evidence)
                    _write_new_file(log, encoded)
                    result['checks'].append({
                        'check_id': check['check_id'], 'returncode': evidence.get('returncode'),
                        'error': evidence.get('error'), 'execution_time_ms': evidence.get('execution_time_ms'),
                        'stdout': evidence.get('stdout', '')[:256], 'stderr': evidence.get('stderr', '')[:256],
                        'preview_truncated': len(evidence.get('stdout', '')) > 256 or len(evidence.get('stderr', '')) > 256,
                        'log_file': str(log.relative_to(folder)), 'log_sha256': hashlib.sha256(encoded).hexdigest()})
                    _save(folder, result)
                    if evidence.get('error') or evidence.get('returncode') != 0:
                        result['state'] = 'CANCELLED' if _cancelled(folder) else 'FAILED'; break
                else:
                    result['state'] = 'VERIFIED'
                changed = _changed(folder, value['files'])
                if changed:
                    result.update(state='FAILED', error='Checks changed selected source, tests or dependencies', changed_inputs=changed)
                if _cancelled(folder): result['state'] = 'CANCELLED'
        except Exception as error:
            result.update(state='FAILED', error=type(error).__name__)
        finally:
            result.update(finished_at=time.time(), worker=None)
            try: _save(folder, result)
            finally:
                with _LOCK: _RUNNING.pop(str(folder), None)
                release()
    worker = threading.Thread(target=run, name='AI-BS-trusted-local-check', daemon=True)
    with _LOCK: _RUNNING[str(folder)] = worker
    try: worker.start()
    except Exception:
        with _LOCK: _RUNNING.pop(str(folder), None)
        result.update(state='INTERRUPTED', worker=None)
        _save(folder, result)
        raise


def decorate(folder, value, response):
    if not (folder/'result.json').exists():
        if (folder/'local_recovery.json').exists():
            recovery = preparation._load(folder/'local_recovery.json')
            if _valid(recovery, value) and recovery.get('state') == 'INTERRUPTED':
                return {**response, 'state': 'INTERRUPTED', 'replayed': False}
        return {**response, 'state': 'INCOMPLETE', 'blocked_reason': 'Candidate staging was interrupted.'}
    result = preparation._load(folder/'result.json')
    valid = _valid(result, value)
    state = result.get('state') if valid else 'UNCONFIRMED'
    if state == 'RUNNING' and not _active(folder): state = 'INCOMPLETE'
    if (folder/'local_recovery.json').exists():
        recovery = preparation._load(folder/'local_recovery.json')
        if not _valid(recovery, value) or recovery.get('state') != 'INTERRUPTED':
            raise preparation.PreparationEvidenceError('Interrupted recovery receipt changed')
        state = 'INTERRUPTED'
    verified = (state == 'VERIFIED' and len(result.get('checks', [])) == len(value['checks']) and
                all(c.get('returncode') == 0 and not c.get('error') for c in result['checks']))
    application = ({'state': 'ATTENTION_REQUIRED',
                    'reason': 'Application receipt cannot be confirmed in this runtime; inspect retained backups without replay.'}
                   if not valid and (folder/'application.json').exists() else _application(folder, value))
    return {**response, 'state': state, 'execution_backend': 'trusted_host', 'isolation_verified': False,
            'verification_status': 'passed' if verified else ('failed' if state == 'FAILED' else 'not_run'),
            'execution_authorized': True, 'apply_authorized': False, 'can_apply': False,
            'blocked_reason': None if verified else result.get('error', 'Verification is incomplete or requires a fresh trusted-local task.'),
            'checks': result.get('checks', []) if valid else [], 'static_checks': result.get('static_checks', []) if valid else [],
            'runtime_receipt_verified': valid, 'application': application,
            'resource_limits': result.get('resource_limits') if valid else None,
            'npm_policy': result.get('npm_policy'), 'error': result.get('error') if valid else 'Runtime receipt unavailable after restart or evidence change'}


def cancel(folder, value, response):
    if _active(folder):
        if not (folder/'local_cancel.json').exists():
            preparation._save_new(folder/'local_cancel.json', {'owner': value['owner'], 'execution_id': value['payload']['execution_id']})
        return {**decorate(folder, value, response), 'cancel_requested': True}
    return {**decorate(folder, value, response), 'cancel_requested': False}


def recover(folder, value, response):
    with preparation._directory(folder), record_lock(folder/'state.lock'):
        if _active(folder): return {**decorate(folder, value, response), 'replayed': False}
        prior = preparation._load(folder/'result.json') if (folder/'result.json').exists() else None
        if (prior is None or prior.get('state') == 'RUNNING') and not (folder/'local_recovery.json').exists():
            recovery = {'kind': 'trusted_local_recovery', 'input_sha256': preparation._hash(value),
                        'state': 'INTERRUPTED', 'replayed': False}
            preparation._save_new(folder/'local_recovery.json', {**recovery, 'runtime_seal': _signature(recovery)})
    return {**decorate(folder, value, response), 'replayed': False}


def _current(folder, value, intent):
    result = preparation._load(folder/'result.json')
    if (not _valid(result, value) or result.get('state') != 'VERIFIED' or
            len(result.get('checks', [])) != len(value['checks']) or
            any(c.get('returncode') != 0 or c.get('error') for c in result['checks'])):
        raise preparation.PreparationConflict('Fresh verified local checks are required')
    for check in result['checks']:
        read_log(folder, value, check['check_id'])
    if _changed(folder, value['files']):
        raise preparation.PreparationConflict('Checked candidate inputs changed')
    repo = preparation.REPOSITORIES[intent['plan']['repository_id']]
    selection = intent['plan']['files']
    snapshot, _ = preparation.capture_repository_snapshot(repo, selection, allowed_roots=[repo])
    if snapshot['commit'] != intent['snapshot']['commit'] or snapshot['files'] != intent['snapshot']['files']:
        raise preparation.PreparationConflict('Original source, tests, dependencies or repository commit changed')
    return result, Path(repo)


def review(folder, value, intent, response):
    response = decorate(folder, value, response)
    if (folder/'application.json').exists():
        return {**response, 'reason': 'Application already exists; inspect retained application evidence.'}
    with preparation._directory(folder), record_lock(folder/'state.lock'):
        try: result, _ = _current(folder, value, intent)
        except preparation.PreparationConflict as error:
            return {**response, 'reason': str(error)}
        token = secrets.token_urlsafe(32)
        record = {
            'owner': value['owner'], 'execution_id': value['payload']['execution_id'],
            'result_sha256': preparation._hash(result), 'token_sha256': hashlib.sha256(token.encode()).hexdigest(),
            'expires_at': time.time()+900}
        token_hash = record['token_sha256']
        preparation._save_new(folder/('review-'+token_hash+'.json'), {**record, 'runtime_seal': _signature(record)})
        _REVIEWS[str(folder)] = token_hash
        return {**response, 'can_apply': True, 'apply_authorized': True, 'review_token': token,
                'current_sources_rechecked': True, 'reason': None}


def _replace(destination, staged, backup):
    call = ctypes.WinDLL('kernel32', use_last_error=True).ReplaceFileW
    call.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                     wintypes.LPVOID, wintypes.LPVOID]
    call.restype = wintypes.BOOL
    if not call(str(destination), str(staged), str(backup), 0, None, None):
        raise ctypes.WinError(ctypes.get_last_error())


def _application(folder, value):
    if not (folder/'application.json').exists(): return None
    current = preparation._load(folder/'application.json')
    for index in range(23):
        unsigned = {k: v for k, v in current.items() if k != 'runtime_seal'}
        if current.get('input_sha256') != preparation._hash(value) or not hmac.compare_digest(
                str(current.get('runtime_seal', '')), _signature(unsigned)):
            raise preparation.PreparationEvidenceError('Application receipt authority is unavailable')
        path = folder/('application-'+str(index+1)+'.json')
        if not path.exists(): return current
        next_record = preparation._load(path)
        if next_record.get('previous_sha256') != preparation._hash(current):
            raise preparation.PreparationEvidenceError('Application progress chain changed')
        current = next_record
    raise preparation.PreparationEvidenceError('Application progress exceeded its bound')


def _save_application(folder, application, previous=None, index=0):
    if previous is not None: application['previous_sha256'] = preparation._hash(previous)
    unsigned = {k: v for k, v in application.items() if k != 'runtime_seal'}
    signed = copy.deepcopy({**unsigned, 'runtime_seal': _signature(unsigned)})
    path = folder/'application.json' if index == 0 else folder/('application-'+str(index)+'.json')
    preparation._save_new(path, signed)
    return signed


def apply(folder, value, intent, response, token):
    if not isinstance(token, str) or not token:
        raise preparation.PreparationConflict('An explicit current review token is required')
    repo = preparation.REPOSITORIES[intent['plan']['repository_id']]
    # Windows deny-delete directory handles must close before ReplaceFileW.
    # Cooperative task/repository locks remain; external writers are rechecked,
    # but there is no OS-global multi-file compare-and-swap guarantee.
    with record_lock(folder/'state.lock'), repository_lock(REPOSITORY_LOCK_STORE, str(repo)):
        if (folder/'application.json').exists():
            raise preparation.PreparationConflict('Application already has evidence; inspect it without replay')
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if not hmac.compare_digest(str(_REVIEWS.get(str(folder), '')), token_hash):
            raise preparation.PreparationConflict('Review token is stale or unavailable')
        review_record = preparation._load(folder/('review-'+token_hash+'.json'))
        unsigned_review = {k: v for k, v in review_record.items() if k != 'runtime_seal'}
        if not hmac.compare_digest(str(review_record.get('runtime_seal', '')), _signature(unsigned_review)):
            raise preparation.PreparationConflict('Review receipt authority is unavailable')
        result, repo = _current(folder, value, intent)
        if (review_record.get('owner') != value['owner'] or review_record.get('execution_id') != value['payload']['execution_id'] or
                review_record.get('result_sha256') != preparation._hash(result) or time.time() > review_record.get('expires_at', 0) or
                not hmac.compare_digest(str(review_record.get('token_sha256', '')), hashlib.sha256(token.encode()).hexdigest())):
            raise preparation.PreparationConflict('Review token is stale or does not match this task')
        names = [f['relative_path'] for f in value['files'] if f['role'] == 'editable']
        backup_dir = folder/'application_backups'
        backup_dir.mkdir(exist_ok=False)
        application = {'input_sha256': preparation._hash(value), 'state': 'APPLYING',
                       'files': names, 'completed': [], 'backup': str(backup_dir), 'started_at': time.time()}
        previous = _save_application(folder, application)
        sequence = 0
        try:
            for name in names:
                original = next(f for f in intent['snapshot']['files'] if f['relative_path'] == name)
                destination = repo/name
                with preparation._directory(destination.parent), preparation._source_handle(destination) as (handle, length):
                    raw = preparation._read_bytes(handle, length)
                    if hashlib.sha256(raw).hexdigest() != original['sha256']:
                        raise preparation.PreparationConflict('Original source changed during application')
                candidate = folder/'candidate'/name
                with preparation._directory(candidate.parent), preparation._source_handle(candidate) as (handle, length):
                    proposed = preparation._read_bytes(handle, length)
                expected = next(f for f in value['files'] if f['relative_path'] == name)
                if hashlib.sha256(proposed).hexdigest() != expected['sha256']:
                    raise preparation.PreparationConflict('Candidate changed during application')
                staged = destination.with_name(destination.name+'.'+secrets.token_hex(8)+'.codingtmp')
                _write_new_file(staged, proposed)
                backup = backup_dir/name
                backup.parent.mkdir(parents=True, exist_ok=True)
                _replace(destination, staged, backup)
                if destination.read_bytes() != proposed:
                    raise preparation.PreparationEvidenceError('Applied bytes were not confirmed')
                application['completed'].append(name)
                sequence += 1
                previous = _save_application(folder, application, previous, sequence)
            application.update(state='APPLIED', finished_at=time.time())
        except Exception as error:
            application.update(state='PARTIAL', error=type(error).__name__)
            sequence += 1
            _save_application(folder, application, previous, sequence)
            raise
        sequence += 1
        _save_application(folder, application, previous, sequence)
    return decorate(folder, value, response)
