"""Read-only reconciliation of interrupted coding operations.

Recovery never reruns inference, checks, or file application. It may update only
task/request metadata after comparing immutable evidence with current bytes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
import uuid

import psutil

from .coding_workflow import STORE, _digest, _inside, _relative, _save, get_coding_task, request_cancellation
from .coding_locks import task_lock, repository_lock, record_lock
from .coding_journal import write_json_record

REQUESTS = STORE.parent / 'coding_requests'
TERMINAL = {'VERIFIED', 'FAILED', 'INTERRUPTED', 'CANCELLED'}


def worker_identity():
    process = psutil.Process(os.getpid())
    return {'pid':process.pid,'created':process.create_time()}


def _alive(record):
    worker = record.get('worker') or {}
    try:
        return worker.get('pid', 0) > 0 and abs(psutil.Process(worker['pid']).create_time()-worker['created']) < .01
    except (psutil.Error, KeyError, TypeError):
        return False


def _request_path(request_id):
    if not isinstance(request_id, str) or len(request_id)!=32 or any(ch not in '0123456789abcdef' for ch in request_id):
        raise ValueError('Invalid request ID')
    return REQUESTS/request_id/'request.json'


def _save_request(record):
    path=_request_path(record['request_id'])
    path.parent.mkdir(parents=True,exist_ok=True)
    write_json_record(path, record)


def admit_request(repository, objective, files, checks, source_inputs=None, execution_backend='trusted_host'):
    request_id=uuid.uuid4().hex
    record={'request_id':request_id,'repository':str(Path(repository).resolve()),
            'objective':objective,'files':list(files),'checks':checks,
            'execution_backend':execution_backend,
            'state':'GENERATING','worker':worker_identity(),'attempt_ids':[],
            'created_at':time.time()}
    record['deadline_at']=record['created_at']+300
    record['input_hashes']={}
    for name, model_text in (source_inputs or {}).items():
        relative=_relative(name)
        source=_inside(Path(record['repository']),relative)
        data=source.read_bytes()
        normalized=data.decode('utf-8').replace('\r\n','\n').replace('\r','\n')
        if normalized != model_text:
            raise ValueError('Source changed before generation admission: '+name)
        retained=_inside(REQUESTS/request_id/'inputs',relative)
        retained.parent.mkdir(parents=True,exist_ok=True)
        retained.write_bytes(data)
        record['input_hashes'][name]=_digest(data)
    _save_request(record)
    return record


def assert_request_inputs(record):
    for name,digest in record.get('input_hashes',{}).items():
        relative=_relative(name)
        source=_inside(Path(record['repository']),relative)
        retained=_inside(REQUESTS/record['request_id']/'inputs',relative)
        if (not source.is_file() or not retained.is_file()
                or _digest(source.read_bytes())!=digest or _digest(retained.read_bytes())!=digest):
            raise ValueError('Source input changed since generation admission: '+name)


def is_request_cancelled(record):
    return (_request_path(record['request_id']).parent/'cancel_requested.json').is_file()


def request_coding_cancellation(identifier):
    path=_request_path(identifier)
    if (STORE/identifier/'result.json').is_file():return request_cancellation(identifier)
    if not path.is_file():raise ValueError('Task or request not found')
    with record_lock(path.parent/'state.lock'):
        if not path.is_file():raise ValueError('Task or request not found')
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('state') in TERMINAL:
            return {'request_id':identifier,'state':record['state'],'cancel_requested':False}
        write_json_record(path.parent/'cancel_requested.json', {'requested_at':time.time()})
        if record.get('current_task_id'):request_cancellation(record['current_task_id'])
        return {'request_id':identifier,'state':record['state'],'cancel_requested':True}


def update_request(record, **changes):
    record.update(changes)
    record['updated_at']=time.time()
    _save_request(record)
    return record


def recover_request(request_id):
    with record_lock(_request_path(request_id).parent/'state.lock'):
        return _recover_request(request_id)


def _recover_request(request_id):
    path=_request_path(request_id)
    if not path.is_file():raise ValueError('Request not found')
    record=json.loads(path.read_text(encoding='utf-8'))
    if record['state'] in TERMINAL or _alive(record):
        return record
    record['state']='INTERRUPTED'
    record['recovery_note']='Backend worker ended before a terminal result. Explicit rerun required.'
    return update_request(record)


def recover_task(task_id):
    result=get_coding_task(task_id)
    if result.get('status')=='error':raise ValueError(result['message'])
    with task_lock(STORE/task_id):
        repository=(result.get('review_seal') or {}).get('repository')
        if result.get('application') and repository:
            with repository_lock(STORE,repository):
                return _recover_task(task_id)
        return _recover_task(task_id)


def _recover_task(task_id):
    result=get_coding_task(task_id)
    if result.get('status')=='error':raise ValueError(result['message'])
    folder=STORE/task_id
    app=result.get('application')
    if app and app.get('state') in ('APPLYING','PARTIAL'):
        if _alive(app):return result
        seal=result.get('review_seal') or {}
        backup=Path(app.get('backup',''))
        repo=Path(seal.get('repository','')).resolve()
        names=app.get('files') or []
        expected=set(seal.get('proposal_hashes',{}))
        backup_root=(folder/'application_backups').resolve()
        if (not expected or len(names)!=len(expected) or set(names)!=expected
                or not backup.resolve().is_relative_to(backup_root)
                or str(repo)!=result.get('repository')):
            app['state']='CONFLICT'
            result['recovery']={'note':'Incomplete or inconsistent application journal. No project files were written.'}
            _save(folder,result)
            return result
        states=[]
        for name in names:
            rel=_relative(name)
            original=seal.get('original_hashes',{}).get(name)
            proposed=seal.get('proposal_hashes',{}).get(name)
            backup_path=_inside(backup,rel)
            backup_data=backup_path.read_bytes() if backup_path.is_file() else None
            if not proposed or _digest(backup_data)!=original:
                states.append('unknown');continue
            current=_inside(repo,rel)
            digest=_digest(current.read_bytes() if current.is_file() else None)
            states.append('proposed' if digest==proposed else 'original' if digest==original else 'unknown')
        if not states or 'unknown' in states:
            app['state']='CONFLICT'
        elif all(state=='proposed' for state in states):
            app.update(state='APPLIED',completed=names,reconciled_at=time.time())
        elif all(state=='original' for state in states):
            app['state']='INTERRUPTED'
        else:
            app['state']='PARTIAL'
        result['recovery']={'file_states':dict(zip(names,states)),
                            'note':'No original file was written by recovery.'}
        _save(folder,result)
        return result
    if result.get('state') in TERMINAL or _alive(result):
        return result
    result.update(state='INTERRUPTED',status='interrupted',
                  recovery={'note':'Unfinished task was not rerun. Explicit rerun required.'})
    _save(folder,result)
    return result


def list_coding_records(limit=50):
    items=[]
    for root,kind in ((STORE,'task'),(REQUESTS,'request')):
        if not root.is_dir():continue
        # Preparation namespaces and partial/control directories are not legacy
        # task records and must not displace actual items from the history cap.
        folders = [p for p in root.iterdir() if len(p.name)==32 and all(c in '0123456789abcdef' for c in p.name)
                   and p.is_dir() and not p.is_symlink() and not p.is_junction()]
        for folder in sorted(folders,key=lambda p:p.stat().st_mtime,reverse=True)[:limit]:
            path=folder/('result.json' if kind=='task' else 'request.json')
            if not path.is_file():continue
            try:
                record=json.loads(path.read_text(encoding='utf-8'))
                items.append({'kind':kind,'id':record.get('task_id') or record.get('request_id'),
                              'state':record.get('state'),'status':record.get('status'),
                              'application_state':(record.get('application') or {}).get('state'),
                              'updated':path.stat().st_mtime})
            except (OSError,ValueError):continue
    return sorted(items,key=lambda item:item['updated'],reverse=True)[:limit]
