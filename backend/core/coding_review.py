"""Review and explicitly apply sealed, verified coding proposals.

The model cannot invoke these functions as a tool. HTTP callers must pass the
administrator boundary before reaching apply_task.
"""
from __future__ import annotations

import difflib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import uuid

from .coding_workflow import STORE, _digest, _inside, _relative, _save, get_coding_task
from .coding_recovery import worker_identity
from .coding_locks import task_lock, repository_lock


def _bytes(path):
    return path.read_bytes() if path.is_file() else None


def _task(task_id):
    result = get_coding_task(task_id)
    if result.get('status') == 'error':
        raise ValueError(result['message'])
    return result, STORE / task_id


def _current(result, folder):
    seal = result.get('review_seal')
    if result.get('status') != 'success' or result.get('state') != 'VERIFIED' or not isinstance(seal, dict):
        return 'Task has no sealed successful verification'
    if seal.get('schema_version') != 2:
        return 'Task needs fresh verification with complete review evidence'
    if (not result.get('checks') or any(check.get('returncode') != 0 or check.get('error') for check in result['checks'])
            or _digest(json.dumps(result['checks'],sort_keys=True).encode('utf-8')) != seal.get('checks_hash')):
        return 'Verification evidence changed'
    if set(result.get('changed_files',[])) != set(seal.get('proposal_hashes',{})):
        return 'Reviewed file list changed'
    repo = Path(seal['repository']).resolve()
    work = folder / 'worktree'
    if result.get('repository') != str(repo) or result.get('worktree') != str(work):
        return 'Repository or working-copy identity changed'
    try:
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, capture_output=True, text=True, timeout=10)
        if head.returncode or head.stdout.strip() != seal['base_commit']:
            return 'Repository commit changed'
        diff = folder / 'changes.diff'
        if _digest(_bytes(diff)) != seal['diff_hash']:
            return 'Reviewed diff changed'
        for name, original_hash in seal['original_hashes'].items():
            rel = _relative(name)
            if _digest(_bytes(_inside(repo, rel))) != original_hash:
                return 'Original file changed: ' + name
            if _digest(_bytes(_inside(folder/'originals', rel))) != original_hash:
                return 'Retained original copy changed: ' + name
        for name, proposal_hash in seal['proposal_hashes'].items():
            rel = _relative(name)
            if (_digest(_bytes(_inside(work, rel))) != proposal_hash
                    or _digest(_bytes(_inside(folder/'proposed', rel))) != proposal_hash):
                return 'Proposed file changed: ' + name
        for name, hashes in seal['verification_hashes'].items():
            rel = _relative(name)
            if (_digest(_bytes(_inside(repo, rel))) != hashes['repository']
                    or _digest(_bytes(_inside(work, rel))) != hashes['worktree']):
                return 'Verification input changed: ' + name
    except (OSError, ValueError, subprocess.SubprocessError, KeyError) as exc:
        return 'Cannot revalidate proposal: ' + str(exc)
    return None


def _review_fingerprint(result):
    values={name:result.get(name) for name in ('review_seal','checks','changed_files')}
    return _digest(json.dumps(values,sort_keys=True).encode('utf-8'))


def _submitted_preview(result, folder):
    path=folder/'input.json'
    if not path.is_file():return [],None
    if path.stat().st_size>2097152:
        return [],'Submitted input is retained on disk; preview exceeds 2 MiB'
    raw=path.read_bytes()
    if _digest(raw)!=result.get('input_sha256'):
        return [],'Submitted input no longer matches its recorded hash'
    try:
        data=json.loads(raw)
        files=[]
        for entry in data.get('files',[])[:20]:
            if not isinstance(entry,dict):continue
            content=entry.get('content','')
            if not isinstance(content,str):continue
            files.append({'path':str(entry.get('path','')),'content':content[:16000],
                          'truncated':len(content)>16000})
        return files,None
    except (ValueError,TypeError):
        return [],'Retained submitted input cannot be decoded'


def review_task(task_id):
    _, folder = _task(task_id)
    with task_lock(folder):
        return _review_task(task_id)


def _review_task(task_id):
    result, folder = _task(task_id)
    seal = result.get('review_seal')
    review_diff = ''
    if isinstance(seal, dict):
        for name in seal['proposal_hashes']:
            rel = _relative(name)
            before = _bytes(_inside(folder/'originals', rel))
            after = _bytes(_inside(folder/'proposed', rel))
            if after is None:
                continue
            review_diff += ''.join(difflib.unified_diff(
                (before or b'').decode('utf-8', 'replace').splitlines(keepends=True),
                after.decode('utf-8', 'replace').splitlines(keepends=True),
                fromfile='original/' + name, tofile='proposed/' + name))
    elif result.get('diff') and (folder/'changes.diff').is_file():
        review_diff = (folder/'changes.diff').read_text(encoding='utf-8', errors='replace')
    application = result.get('application')
    reason = 'Already applied' if application and application.get('state') == 'APPLIED' else _current(result, folder)
    if application and application.get('state') != 'APPLIED':
        reason = 'Application needs recovery review'
    if (folder/'apply.lock').exists() and reason is None:
        reason = 'Application lock needs recovery review'
    response = {'task_id':task_id,'state':result.get('state'),'status':result.get('status'),
                'execution_mode':result.get('execution_mode','trusted_host'),
                'requested_execution_backend':result.get('requested_execution_backend'),
                'guest_provider':result.get('guest_provider'),
                'isolation_verified':bool(result.get('isolation_verified')),
                'limits':result.get('limits'),
                'changed_files':result.get('changed_files',[]),'review_diff':review_diff,
                'checks':result.get('checks',[]),'application':application,
                'can_apply':reason is None,'reason':reason}
    response.update(error=result.get('error'),error_stage=result.get('error_stage'))
    if result.get('status')!='success' and not result.get('worktree'):
        response['submitted_files'],response['input_preview_error']=_submitted_preview(result,folder)
    if reason is None:
        token = secrets.token_urlsafe(32)
        result['review_token_hash'] = _digest(token.encode('utf-8'))
        result['review_content_hash'] = _review_fingerprint(result)
        _save(folder, result)
        response['review_token'] = token
    return response


def apply_task(task_id, review_token):
    result, folder = _task(task_id)
    repository=(result.get('review_seal') or {}).get('repository')
    if not repository:
        raise ValueError('Task has no reviewed repository')
    with task_lock(folder), repository_lock(STORE, repository):
        return _apply_task(task_id, review_token)


def _apply_task(task_id, review_token):
    if not isinstance(review_token, str) or not review_token:
        raise ValueError('A review token is required')
    result, folder = _task(task_id)
    token_hash = _digest(review_token.encode('utf-8'))
    if not secrets.compare_digest(token_hash, str(result.get('review_token_hash') or '')):
        raise ValueError('Review token is invalid or outdated')
    if result.get('application', {}).get('state') == 'APPLIED':
        return result
    lock_path = folder/'apply.lock'
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.write(lock_fd, json.dumps(worker_identity()).encode('utf-8'))
    except FileExistsError as exc:
        raise ValueError('Another application is in progress or needs recovery') from exc
    try:
        # Re-read after taking the inter-process lock. A partial application stays blocked.
        result, folder = _task(task_id)
        if not secrets.compare_digest(token_hash, str(result.get('review_token_hash') or '')):
            raise ValueError('Review token changed before application')
        if result.get('review_content_hash') != _review_fingerprint(result):
            raise ValueError('Reviewed proposal or evidence changed before application')
        if result.get('application'):
            if result['application'].get('state') == 'APPLIED':
                return result
            raise ValueError('Application needs recovery review')
        reason = _current(result, folder)
        if reason:
            raise ValueError(reason)
        seal = result['review_seal']
        repo = Path(seal['repository']).resolve()
        backup = folder/'application_backups'/time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        backup.mkdir(parents=True, exist_ok=False)
        names = list(seal['proposal_hashes'])
        for name in names:
            rel = _relative(name)
            data = _bytes(_inside(repo, rel))
            if _digest(data) != seal['original_hashes'][name]:
                raise ValueError('Original file changed: ' + name)
            if data is not None:
                target = _inside(backup, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        application = {'id':uuid.uuid4().hex,'state':'APPLYING','backup':str(backup),
                       'worker':worker_identity(),
                       'files':names,'completed':[],'started_at':time.time()}
        result['application'] = application
        _save(folder, result)  # Durable journal before the first original write.
        try:
            for name in names:
                rel = _relative(name)
                destination = _inside(repo, rel)
                if _digest(_bytes(destination)) != seal['original_hashes'][name]:
                    raise ValueError('Original file changed during application: ' + name)
                proposal = _inside(folder/'proposed', rel).read_bytes()
                if _digest(proposal) != seal['proposal_hashes'][name]:
                    raise ValueError('Proposed file changed during application: ' + name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                staged = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.applytmp')
                try:
                    staged.write_bytes(proposal)
                    os.replace(staged, destination)
                finally:
                    if staged.exists():
                        staged.unlink()
                application['completed'].append(name)
                _save(folder, result)
            application['state'] = 'APPLIED'
            application['completed_at'] = time.time()
            _save(folder, result)
        except Exception as exc:
            application['state'] = 'PARTIAL'
            application['error'] = str(exc)
            _save(folder, result)
            raise
        return result
    finally:
        try:
            application = result.get('application') if isinstance(result, dict) else None
            if application and application.get('state') in ('APPLIED','PARTIAL'):
                application['worker'] = None
                _save(folder, result)
        finally:
            os.close(lock_fd)
            lock_path.unlink(missing_ok=True)
