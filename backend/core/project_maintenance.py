"""Authenticated local build/update jobs independent of the API's lifetime.

This module is inert on import. Its fixed local checks do not deploy to a cloud,
install dependencies, synchronize mirrors or execute generated programs. The
existing arbitrary-program/custom-command builder remains a separate contract.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

import httpx
import psutil

from .coding_journal import write_json_record
from .coding_locks import record_lock
from .coding_process import run_bounded_check

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = {'succeeded', 'failed', 'interrupted'}
_ID = re.compile(r'[0-9a-f]{32}\Z')
_SKIP = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'dist', 'build', 'data', 'logs', 'saved_data', '.pytest_cache'}
_DBS = ('backend/aibs_master.db', 'backend/state.db', 'backend/data/aibs_master.db', 'backend/backend/state.db', 'backend/stehouwer_vault.db',
        'database/aibs_master.db', 'database/ai_bs_omnidrive.db', 'database/security_events.db', 'saved_data/rec_debut.db',
        'stehouwer_vector_memory/chroma.sqlite3')
FRONTEND_CHECKS = (
    'test_chat_takeover.mjs', 'test_bs_chat_provider.mjs', 'test_chat_current_intent.mjs', 'test_chat_media.mjs',
    'test_chat_archive_preservation.mjs', 'test_host_action_browser_auth.cjs', 'test_executive_status_truth204.cjs',
    'test_ai_provider_settings_takeover.mjs', 'test_rag_source_pipeline.mjs', 'test_project_maintenance.mjs',
    'test_screenplay_handoff.mjs', 'test_screenplay_source_layout.mjs', 'test_screenplay_pdf_handlers.mjs',
    'test_attached_sources.mjs',
    'test_novelizer_drafts_takeover.mjs', 'test_novelizer_modal_takeover.mjs',
    'test_project_rag_drawer.mjs', 'test_fdx_rich_roundtrip.mjs', 'test_fdx_rich_workflow.mjs',
    'test_fdx_browser_history.mjs',
    'test_local_chat_metadata.mjs',
)
# Existing release-version.cjs authority paths: pinned, never bumped/synchronized.
_VERSION_INPUTS = ('version.txt', 'release.json', 'package.json', 'package-lock.json',
    'frontend/package.json', 'frontend/package-lock.json', 'BroadcastStudioApp/package.json', 'BroadcastStudioApp/package-lock.json',
    'frontend/version.js', 'frontend/src/version.js', 'frontend/components/version.js', 'frontend/components/components/version.js',
    'frontend/src/components/version.js', 'frontend/src/components/components/version.js', 'BroadcastStudioApp/src/version.js', 'frontend/public/version.json')
_FIXED_HELPERS = ('scripts/run_takeover_checks.py', 'scripts/release-version.cjs',
    'backend/core/project_maintenance.py', 'backend/core/project_maintenance_worker.py',
    'backend/core/coding_process.py', 'backend/core/coding_locks.py', 'backend/core/coding_journal.py',
    'frontend/node_modules/typescript/bin/tsc', 'frontend/node_modules/typescript/package.json',
    'frontend/node_modules/vite/bin/vite.js', 'frontend/node_modules/vite/package.json')


def utc():
    return datetime.now(timezone.utc).isoformat()


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _plain(path):
    path = Path(path).absolute()
    need(not any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in (path, *path.parents)),
         'Maintenance paths must not redirect through symbolic links/junctions')
    return path


def _folder(root, job_id):
    need(isinstance(job_id, str) and _ID.fullmatch(job_id), 'Expected a canonical maintenance job identifier')
    return _plain(Path(root) / 'state/project_maintenance' / job_id)


def maintenance_target(value, root=ROOT):
    """Return only fixed canonical local project lanes; never reinterpret custom projects."""
    if not isinstance(value, str) or not value.strip():
        return None
    aliases = {'ai-bs': 'all', 'ai_bs': 'all', 'frontend': 'frontend', 'backend': 'backend'}
    if value.strip().lower() in aliases:
        return aliases[value.strip().lower()]
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = Path(root) / candidate
    resolved = os.path.normcase(str(candidate.resolve()))
    for relative, lane in (('', 'all'), ('frontend', 'frontend'), ('backend', 'backend')):
        if resolved == os.path.normcase(str((Path(root) / relative).resolve())):
            return lane
    return None


def _read(path):
    need(path.is_file() and path.stat().st_size <= 4 * 1024 * 1024, 'Missing or oversized maintenance receipt')
    return json.loads(path.read_text(encoding='utf-8'))


def get_job(job_id, root=ROOT):
    folder = _folder(root, job_id)
    need((folder / 'state.json').is_file(), 'Maintenance job was not found')
    # Atomic JSON replacement permits nonblocking readers while the worker
    # journals progress. Acquire a lock only for orphan-state reconciliation.
    record = _read(folder / 'state.json')
    worker = record.get('worker')
    if record['state'] in TERMINAL or not worker:
        return record
    try:
        process = psutil.Process(worker['pid'])
        alive = abs(process.create_time() - worker['created']) < .001
    except (psutil.Error, KeyError):
        alive = False
    if alive:
        return record
    try:
        with record_lock(folder / 'receipt.lock'):
            latest = _read(folder / 'state.json')
            if latest['state'] in TERMINAL or latest.get('worker') != worker:
                return latest
            latest.update(state='interrupted', status='error', completed_at=utc(),
                          message='Maintenance worker ended before a terminal receipt; partial evidence retained. No automatic replay.')
            write_json_record(folder / 'state.json', latest)
            return latest
    except ValueError:
        # An active writer owns the receipt. Report the last observed progress;
        # never turn brief lock contention into a failed build or replay.
        return record


def _event(folder, record, state, **fields):
    with record_lock(folder / 'receipt.lock'):
        record.update(state=state, updated_at=utc(), **fields)
        record['status'] = 'success' if state == 'succeeded' else 'error' if state in TERMINAL else 'queued'
        sequence = len(list((folder / 'events').glob('*.json'))) + 1
        write_json_record(folder / 'events' / f'{sequence:04d}-{state}.json', record, exclusive=True)
        write_json_record(folder / 'state.json', record)


def _server_identity(pid):
    process = psutil.Process(pid)
    args = process.cmdline()
    need(len(args) >= 4 and args[1:4] == ['-m', 'uvicorn', 'AI_BS_Backend:app'],
         'Local maintenance requires the verified canonical Uvicorn API worker')
    need(args.count('--host') == 1 and args[args.index('--host') + 1] == '127.0.0.1'
         and args.count('--port') == 1 and args[args.index('--port') + 1] == '8080'
         and '--reload' not in args,
         'Only the existing loopback API on8080 can be restarted')
    need(Path(process.cwd()).resolve() == (ROOT / 'backend').resolve(), 'Unexpected API working directory')
    return {'pid': process.pid, 'created': process.create_time(), 'argv': args, 'cwd': process.cwd()}


def submit(lane='all', operation='build_update', job_id=None, *, root=ROOT, server_pid=None):
    """Create one durable job and detach its worker; acknowledgement precedes restart."""
    root = _plain(root)
    need(lane in {'all', 'frontend', 'backend'}, 'Unknown fixed local project lane')
    need(operation in {'build_update', 'restart'}, 'Unknown local maintenance operation')
    job_id = job_id or uuid.uuid4().hex
    folder = _folder(root, job_id)
    store = folder.parent
    store.mkdir(parents=True, exist_ok=True)
    with record_lock(store / 'submission.lock'):
        if folder.exists():
            previous = get_job(job_id, root)
            need(previous.get('lane') == lane and previous.get('operation') == operation,
                 'Maintenance identifier already belongs to a different request')
            return previous
        pending = []
        for path in store.glob('*/state.json'):
            if _ID.fullmatch(path.parent.name):
                previous = get_job(path.parent.name, root)
                if previous['state'] not in TERMINAL:
                    pending.append(previous)
        need(len(pending) < 8, 'Local maintenance queue is full; existing jobs are retained')
        identity = _server_identity(server_pid or os.getpid())
        environment = psutil.Process(identity['pid']).environ()  # Memory only; never journal credentials.
        need(environment.get('AI_BS_BACKEND_MANAGE_DAEMONS', '').lower() != 'true',
             'This job may not acquire/restart the independent daemon fleet')
        folder.mkdir();(folder / 'events').mkdir()
        record = dict(job_id=job_id, state='queued', status='queued', lane=lane, operation=operation,
                      created_at=utc(), project_dir=str(root / (lane if lane != 'all' else '')),
                      server=identity, cloud_deployed=False, provider_generation_requests=0,
                      full_backend_rollback_available=False,
                      message='Local maintenance queued. Existing drafts stay open; no forced page reload.')
        write_json_record(folder / 'request.json', record, exclusive=True)
        write_json_record(folder / 'state.json', record, exclusive=True)
        try:
            with (folder / 'worker.stdout.local.log').open('xb') as output, (folder / 'worker.stderr.local.log').open('xb') as errors:
                worker = subprocess.Popen([identity['argv'][0], '-X', 'utf8', '-B', '-m',
                    'core.project_maintenance_worker', '--job-id', job_id], cwd=root / 'backend', env=environment,
                    stdin=subprocess.DEVNULL, stdout=output, stderr=errors,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
            record['worker'] = {'pid': worker.pid, 'created': psutil.Process(worker.pid).create_time()}
            write_json_record(folder / 'state.json', record)
            # The detached worker cannot act before durable admission/identity.
            write_json_record(folder / 'dispatch-ready.json', {'job_id': job_id}, exclusive=True)
        except Exception as error:
            _event(folder, record, 'failed', completed_at=utc(), error_type=type(error).__name__,
                   message='Maintenance worker did not start; existing release remains unchanged.')
            raise
    return record


def dispatch(target, build_command=None, *, maintenance_action='start', job_id=None):
    lane = maintenance_target(target)
    if maintenance_action == 'status':
        return get_job(job_id)
    need(maintenance_action in {'start', 'restart'}, 'Unknown maintenance action')
    # Explicit custom commands retain the existing arbitrary-project builder.
    if lane is None or build_command:
        need(maintenance_action == 'start' and job_id is None, 'Maintenance status/restart requires the canonical local project')
        return None
    return submit(lane, 'restart' if maintenance_action == 'restart' else 'build_update', job_id)


def _inputs(root, lane):
    paths = set()
    if lane in {'all', 'frontend'}:
        frontend = root / 'frontend'
        paths.update(p for p in frontend.iterdir() if p.is_file() and p.suffix.lower() in {'.json', '.js', '.cjs', '.mjs', '.html', '.ts'})
        for name in ('src', 'components', 'utils', 'public'):
            base = frontend / name
            if base.is_dir():
                paths.update(p for p in base.rglob('*') if p.is_file())
    # Every lane restarts this API, so its complete runtime Python source is an
    # input even when the requested artifact is only the frontend.
    for directory, children, names in os.walk(root / 'backend', followlinks=False):
        children[:] = [name for name in children if name.lower() not in _SKIP]
        paths.update(Path(directory) / name for name in names if name.endswith('.py'))
    for name in (*_VERSION_INPUTS, *_FIXED_HELPERS):
        if (root / name).is_file():
            paths.add(root / name)
    # Pin actual check sources/native Python consumed by the curated backend
    # suites; synthetic fixtures can omit these optional source trees.
    for base in (root / 'scripts/tests', root / 'native_studio'):
        for directory, children, names in os.walk(base, followlinks=False):
            children[:] = [name for name in children if name.lower() not in _SKIP | {'releases', 'archives'}]
            paths.update(Path(directory) / name for name in names if Path(name).suffix.lower() in {'.py', '.js', '.mjs', '.cjs'})
    need(len(paths) <= 75000, 'Build input count exceeds the bounded local profile')
    return {p.relative_to(root).as_posix(): digest(_plain(p)) for p in sorted(paths)}


def _source_preimages(root, folder, manifest):
    for name in manifest:
        path = Path(name)
        if path.suffix.lower() not in {'.py', '.jsx', '.tsx', '.js', '.cjs', '.mjs', '.ts', '.json', '.css', '.html'} or 'public' in path.parts:
            continue
        target = folder / 'source-before' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as output:
            output.write((root / path).read_bytes())


def _tree(path):
    if not path.exists():
        return {}
    rows = {}
    for file in path.rglob('*'):
        _plain(file)
        if file.is_file():
            need(len(rows) < 16000, 'Local artifact count exceeds its bounded profile')
            rows[file.relative_to(path).as_posix()] = digest(file)
    return rows


def _validate_web(candidate):
    from urllib.parse import unquote, urlsplit
    index = candidate / 'index.html'
    need(index.is_file() and 0 < index.stat().st_size <= 4 * 1024 * 1024, 'Built frontend index is absent/oversized')
    for value in re.findall(r'(?:src|href)=[\"\']([^\"\']+)', index.read_text(encoding='utf-8')):
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or value.startswith('#'):
            continue
        path = (candidate / unquote(parsed.path).lstrip('/')).resolve()
        need(path.is_relative_to(candidate.resolve()) and path.is_file(), 'Built frontend index references a missing/escaping artifact')
    need(bool(_tree(candidate)), 'Built frontend is empty')


def _apply_web(root, candidate, backup):
    """Two recoverable same-volume renames; keep old hashed assets for open tabs."""
    current = _plain(root / 'frontend/dist')
    before = _tree(current)
    # Old HTML/chunk graphs stay usable without reloading an active draft.
    if (current / 'assets').is_dir():
        for file in (current / 'assets').rglob('*'):
            _plain(file)
            if not file.is_file():
                continue
            relative = file.relative_to(current)
            target = candidate / relative
            if target.exists():
                hashed = re.search(r'(?:-[A-Za-z0-9_-]{8,16}|[0-9a-f]{64})\.[^.]+\Z', file.name)
                need(not hashed or digest(target) == digest(file), 'A reused content-addressed asset name has different bytes; preserve the active release')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, target)
    _validate_web(candidate)
    after = _tree(candidate)
    backup.parent.mkdir(parents=True, exist_ok=True)
    need(not backup.exists(), 'Dist backup already exists; preserve prior evidence')
    if current.exists():
        os.replace(current, backup)
    try:
        os.replace(candidate, current)
    except BaseException:
        if backup.exists() and not current.exists():
            os.replace(backup, current)
        raise
    return {'before': before, 'after': after, 'backup': str(backup), 'path': str(current)}


def _restore_web(applied, failed_destination):
    current = Path(applied['path']);backup = Path(applied['backup'])
    need(_tree(current) == applied['after'], 'Frontend changed after activation; retained old release requires conflict-aware recovery')
    os.replace(current, failed_destination)
    if backup.exists():
        os.replace(backup, current)
    return 'previous-dist-restored' if backup.exists() is False and applied['before'] else 'previously-absent-dist-restored'


class Runtime:
    """Actual host adapter; fixtures inject a separate adapter, never an HTTP flag."""
    def resolve_server(self, root, request, folder):
        old = request['server']
        try:
            if _server_identity(old['pid']) == old:
                return request
        except (psutil.Error, ValueError):
            pass
        # Another completed job in this same serial queue may have replaced
        # the admitted API. Never adopt a PID solely because it owns a port.
        pointer = _read(folder.parent / 'current-api.json')
        previous = _read(_folder(root, pointer['job_id']) / 'state.json')
        need(previous.get('state') == 'succeeded' and _server_identity(pointer['identity']['pid']) == pointer['identity'],
             'Admitted API changed without a verified successful maintenance handoff')
        return {**request, 'server': pointer['identity']}

    def check(self, label, argv, cwd, folder, environment, timeout=300):
        result = run_bounded_check(list(map(str, argv)), cwd=str(cwd), env=environment,
                                   timeout_seconds=timeout, output_limit=1024 * 1024)
        (folder / (label + '.stdout.local.log')).write_text(result.pop('stdout', ''), encoding='utf-8')
        (folder / (label + '.stderr.local.log')).write_text(result.pop('stderr', ''), encoding='utf-8')
        write_json_record(folder / (label + '.json'), result, exclusive=True)
        need(result.get('returncode') == 0 and not result.get('error'), label + ' failed; retained local logs identify the failure')
        return result

    def backup(self, root, job_id, folder):
        destination = _plain(root / '.aibs_backups/project_maintenance' / job_id)
        destination.mkdir(parents=True)
        rows = []
        for name in _DBS:
            source = root / name
            if not source.is_file():
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            _plain(source)
            deadline = time.monotonic() + 60
            def progress(status, remaining, total):
                need(time.monotonic() < deadline, 'Private SQLite recovery snapshot deadline expired')
            connection = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=10)
            snapshot = sqlite3.connect(target)
            try:
                connection.backup(snapshot, pages=4096, progress=progress, sleep=.05)
                need(snapshot.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'Private database snapshot validation failed')
            finally:
                snapshot.close();connection.close()
            rows.append({'relative': name, 'bytes': target.stat().st_size, 'sha256': digest(target)})
        receipt = {'private_recovery_root': str(destination), 'snapshots': rows, 'contents_public': False}
        write_json_record(folder / 'private-recovery.json', receipt, exclusive=True)
        return {'private_recovery_root': str(destination), 'database_count': len(rows)}

    def restart(self, root, request, folder):
        old = request['server']
        identity = _server_identity(old['pid'])
        need(identity == old, 'API restart request identity differs from the current canonical worker')
        process = psutil.Process(old['pid'])
        need(abs(process.create_time() - old['created']) < .001 and process.cmdline() == old['argv']
             and process.cwd() == old['cwd'], 'API identity changed; never stop a reused/unrelated PID')
        environment = process.environ()  # Never serialized, including credentials.
        need(environment.get('AI_BS_BACKEND_MANAGE_DAEMONS', '').lower() != 'true', 'API owns a separate daemon fleet; preserve it')
        children = process.children(recursive=True)
        need(all(child.pid == os.getpid() or child.name().lower() == 'conhost.exe' for child in children),
             'API has active child jobs; preserve them instead of killing their tree')
        for state in (root / 'screenplay_projects').glob('*/adaptation_state.json'):
            need(_read(state).get('status') in {'complete', 'completed', 'error', 'failed', 'reset', 'cancelled', 'idle', 'paused'},
                 'Active/unknown adaptation state must finish before API maintenance')
        key = environment.get('AI_BS_ADMIN_KEY', '')
        need(bool(key), 'Existing private API credential is unavailable')
        with httpx.Client(base_url='http://127.0.0.1:8080', timeout=15, trust_env=False, headers={'X-Admin-Key': key}) as client:
            before = client.get('/api/v1/recdebut/workflow/email/live')
            need(before.status_code == 200, 'Existing mail state cannot be inspected')
            before = before.json()
        forwarding = before.get('reply_forwarding', {})
        need(before.get('sending_enabled') is False, 'Campaign dispatch must remain held during this scoped maintenance')
        need(not forwarding.get('enabled') or forwarding.get('status') == 'scanned',
             'Preserve a paused/unhealthy reply worker; do not reset its retry state')
        original_flags = {name: environment.get(name, '') for name in ('AI_BS_BACKEND_MANAGE_DAEMONS', 'AI_BS_BACKEND_BACKGROUND_ENABLED', 'RECDEBUT_REPLY_FORWARDING_ENABLED')}
        process.terminate()  # Exact verified API only. No taskkill /T or console broadcast.
        process.wait(timeout=20)
        with (folder / 'api.stdout.local.log').open('xb') as output, (folder / 'api.stderr.local.log').open('xb') as errors:
            replacement = subprocess.Popen(old['argv'], cwd=old['cwd'], env=environment, stdin=subprocess.DEVNULL,
                stdout=output, stderr=errors, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)
        created = psutil.Process(replacement.pid).create_time()
        write_json_record(folder / 'replacement.json', {'pid': replacement.pid, 'created': created, 'api_ready': False}, exclusive=True)
        deadline = time.monotonic() + 90
        try:
            with httpx.Client(base_url='http://127.0.0.1:8080', timeout=10, trust_env=False, headers={'X-Admin-Key': key}) as client:
                while time.monotonic() < deadline:
                    need(replacement.poll() is None, 'Replacement API exited; old loaded generation is unavailable for exact rollback')
                    try:
                        response = client.get('/health')
                        health = response.json() if response.status_code == 200 else {}
                        if health.get('service') == 'AI-BS Central Cognitive Engine API' and health.get('process_id') == replacement.pid and health.get('local_maintenance_protocol') == 1:
                            break
                    except (httpx.RequestError, ValueError):
                        pass
                    time.sleep(.25)
                else:
                    raise ValueError('Replacement API readiness deadline expired')
                need(client.get('/api/ai/providers').status_code == 200, 'New API authenticated admission failed')
                anonymous = httpx.get('http://127.0.0.1:8080/api/ai/providers', timeout=10, trust_env=False)
                need(anonymous.status_code in (401, 403), 'Anonymous API boundary changed')
                after = client.get('/api/v1/recdebut/workflow/email/live').json()
                need(after.get('sending_enabled') == before.get('sending_enabled') and after.get('reply_forwarding', {}).get('enabled') == forwarding.get('enabled')
                     and after.get('reply_forwarding', {}).get('configured') == forwarding.get('configured'),
                     'Existing campaign/reply activation changed')
            actual = psutil.Process(replacement.pid)
            need(abs(actual.create_time() - created) < .001 and actual.cmdline() == old['argv'], 'Replacement API identity changed')
            need({name: actual.environ().get(name, '') for name in original_flags} == original_flags, 'API activation flags changed')
            return {'old_pid': old['pid'], 'new_pid': replacement.pid, 'new_created': created, 'api_ready': True,
                    'loopback_only': True, 'activation_flags_preserved': True, 'other_daemons_restarted': False,
                    'generation_verified': False, 'backend_exact_rollback_available': False}
        except BaseException:
            if replacement.poll() is None:
                replacement.terminate();replacement.wait(timeout=20)
            raise


def _run_job(job_id, *, root=ROOT, runtime=None):
    """One worker executes one job. All failed/partial artifacts remain on disk."""
    root = _plain(root);folder = _folder(root, job_id)
    runtime = runtime or Runtime()
    request = _read(folder / 'request.json')
    record = _read(folder / 'state.json')
    if record['state'] in TERMINAL:
        return record
    process = psutil.Process(os.getpid())
    record['worker'] = {'pid': process.pid, 'created': process.create_time()}
    _event(folder, record, 'waiting', message='Waiting for the shared local build/update slot.')
    applied = None
    try:
        deadline = time.monotonic() + 1800
        while True:
            try:
                lock = record_lock(folder.parent / 'execution.lock');lock.__enter__();break
            except ValueError:
                need(time.monotonic() < deadline, 'Local maintenance queue deadline expired')
                time.sleep(.2)
        try:
            lane = request['lane'];operation = request['operation']
            need(lane in {'all', 'frontend', 'backend'} and operation in {'build_update', 'restart'}, 'Invalid fixed maintenance request')
            original_server = request['server']
            request = runtime.resolve_server(root, request, folder)
            if request['server'] != original_server:
                record['server_rebound_from'] = original_server['pid']
                record['server'] = request['server']
            _event(folder, record, 'checking', message='Retaining source identity and running the fixed local checks.')
            manifest = _inputs(root, lane)
            write_json_record(folder / 'inputs-before.json', manifest, exclusive=True)
            _source_preimages(root, folder, manifest)
            environment = os.environ.copy()
            candidate = _plain(root / 't' / ('m' + job_id[:12]) / 'web')
            # Restart-only and frontend-only requests load backend code too.
            # Syntax/curated checks must pass before any activation or stop.
            parsed = 0
            for name in manifest:
                if name.startswith('backend/') and name.endswith('.py'):
                    ast.parse((root / name).read_text(encoding='utf-8-sig'), filename=name);parsed += 1
            need(parsed > 0, 'Backend source set is empty')
            write_json_record(folder / 'backend-syntax.json', {'parsed_files': parsed, 'passed': True}, exclusive=True)
            runtime.check('backend-checks', [sys.executable, '-X', 'utf8', '-B', root / 'scripts/run_takeover_checks.py',
                '--group', 'core', '--output-root', folder / 'checks'], root, folder, environment)
            if operation == 'build_update':
                if lane in {'all', 'frontend'}:
                    need(not candidate.exists(), 'Preserve previous frontend candidate')
                    candidate.parent.mkdir(parents=True)
                    node = shutil.which('node') or 'node'
                    runtime.check('versions', [node, root / 'scripts/release-version.cjs', 'check'], root, folder, environment)
                    runtime.check('frontend-types', [node, root / 'frontend/node_modules/typescript/bin/tsc', '--noEmit', '--pretty', 'false', '-p', 'tsconfig.json'], root / 'frontend', folder, environment)
                    runtime.check('frontend-checks', [node, '--experimental-vm-modules', '--test',
                        *(root / 'scripts/tests' / name for name in FRONTEND_CHECKS)], root, folder, environment)
                    runtime.check('frontend-build', [node, root / 'frontend/node_modules/vite/bin/vite.js', 'build', '--outDir', candidate], root / 'frontend', folder, environment)
                    _validate_web(candidate)
            need(_inputs(root, lane) == manifest, 'Source changed during checks; built candidate remains held and active release is unchanged')
            write_json_record(folder / 'inputs-after.json', manifest, exclusive=True)
            recovery = runtime.backup(root, job_id, folder)
            record.update(recovery=recovery, input_file_count=len(manifest), source_unchanged=True)
            if operation == 'build_update' and lane in {'all', 'frontend'}:
                _event(folder, record, 'applying', message='Applying the verified local web build while retaining previous files and open-tab assets.')
                applied = _apply_web(root, candidate, root / '.aibs_backups/project_maintenance' / job_id / 'dist-before')
                write_json_record(folder / 'frontend-activation.json', applied, exclusive=True)
                record['frontend_applied'] = True
            need(_inputs(root, lane) == manifest, 'Source changed before API restart; do not claim the built source was loaded')
            _event(folder, record, 'restarting', message='Restarting only the verified loopback API; polling will resume when it is ready.')
            restarted = runtime.restart(root, request, folder)
            need(restarted.get('api_ready') is True, 'Restart adapter did not establish API readiness')
            need(_inputs(root, lane) == manifest, 'Source changed during restart; runtime source qualification is unresolved')
            if 'new_pid' in restarted and 'new_created' in restarted:
                identity = {**request['server'], 'pid': restarted['new_pid'], 'created': restarted['new_created']}
                write_json_record(folder.parent / 'current-api.json', {'job_id': job_id, 'identity': identity})
            _event(folder, record, 'succeeded', completed_at=utc(), restart=restarted, api_ready=True,
                   message='Local checks and update completed; loopback API readiness verified. Open drafts were not reloaded.',
                   stdout='Checks and per-stage logs are retained in the local maintenance receipt.', stderr='', exit_code=0)
        finally:
            lock.__exit__(None, None, None)
    except BaseException as error:
        if applied is not None:
            try:
                record['frontend_recovery'] = _restore_web(applied, folder / 'failed-dist')
            except Exception as recovery_error:
                record['frontend_recovery'] = 'held-conflict: ' + str(recovery_error)
        _event(folder, record, 'failed', completed_at=utc(), error_type=type(error).__name__, api_ready=False,
               message=str(error), stderr=str(error), exit_code=1,
               backend_recovery='No exact rollback of an unknown previously loaded backend generation is claimed; retained logs/source/private snapshots support recovery.')
    return record


def run_job(job_id, *, root=ROOT, runtime=None):
    # A duplicate worker cannot execute the same request again after waiting
    # for another job; OS locks are released even if the worker is interrupted.
    with record_lock(_folder(root, job_id) / 'worker.lock'):
        return _run_job(job_id, root=root, runtime=runtime)


def run_dispatched_job(job_id, *, root=ROOT, runtime=None, wait_seconds=15):
    folder = _folder(root, job_id)
    deadline = time.monotonic() + wait_seconds
    while not (folder / 'dispatch-ready.json').is_file():
        if time.monotonic() >= deadline:
            record = _read(folder / 'state.json')
            _event(folder, record, 'interrupted', completed_at=utc(),
                   message='Dispatcher ended before durable worker admission completed; no build/restart was executed.')
            return record
        time.sleep(.05)
    need(_read(folder / 'dispatch-ready.json').get('job_id') == job_id, 'Invalid durable dispatch acknowledgement')
    return run_job(job_id, root=root, runtime=runtime)
