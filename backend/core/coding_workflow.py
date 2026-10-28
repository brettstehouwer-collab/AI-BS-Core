"""Administrator-authorized code changes in retained Git worktrees.

A worktree protects the original checkout from file writes. Candidate checks run
either inside an isolated VM guest runner (``wsl2_vm`` / ``windows_vm``) or, when
explicitly authorized, inside bounded host job containment (``trusted_host``).
No automatic merge or publish occurs, and VM requests never fall back to the host.
"""
from __future__ import annotations
import hashlib
import json
import ntpath
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import psutil
from .code_quality_gate import sanitize_and_validate_llm_code
from .coding_guest_runner import (
    CodingExecutionPolicyError,
    resolve_coding_execution_plan,
    run_guest_check,
)
from .coding_process import run_bounded_check
from .coding_journal import write_json_record

STORE = Path(__file__).resolve().parents[2] / 'saved_data' / 'coding_tasks'


class _TaskCancelled(RuntimeError):
    pass


def _relative(name):
    if not isinstance(name, str) or not name or ntpath.isabs(name) or ntpath.splitdrive(name)[0]:
        raise ValueError('Expected a relative file path')
    parts = name.replace('\\', '/').split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1,10)), *('LPT'+str(i) for i in range(1,10))}
    if any(not p or p in ('.','..') or p.lower()=='.git' or p.endswith((' ','.')) or p.split('.')[0].upper() in reserved or any(ord(c)<32 or c in '<>:"|?*' for c in p) for p in parts):
        raise ValueError('Unsafe file path')
    return Path(*parts)


def _inside(root, relative):
    target = root / relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('File resolves outside working directory')
    return target


def _save(folder, result):
    write_json_record(folder/'result.json', result)


def _digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def _verification_files(checks):
    """Identify the fixed unittest sources required for a reviewable task."""
    names = set()
    for argv in checks:
        if len(argv) < 4 or argv[:3] != ['python', '-m', 'unittest']:
            return None
        for module in argv[3:]:
            parts = module.split('.')
            if not all(part.isidentifier() for part in parts):
                return None
            names.add(str(_relative('/'.join(parts) + '.py')))
            for index in range(1, len(parts)):
                names.add(str(_relative('/'.join(parts[:index]) + '/__init__.py')))
    return sorted(names)


def get_coding_task(task_id):
    if not isinstance(task_id,str) or len(task_id)!=32 or any(c not in '0123456789abcdef' for c in task_id):
        return {'status':'error','message':'Invalid task ID'}
    path = STORE / task_id / 'result.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'status':'error','message':'Task not found'}


def request_cancellation(task_id):
    result=get_coding_task(task_id)
    if result.get('status')=='error':raise ValueError(result['message'])
    if result.get('state') not in {'VALIDATING','CREATING_WORKTREE','WRITING','CHECKING'}:
        return {'task_id':task_id,'cancel_requested':False,'state':result.get('state')}
    folder=STORE/task_id
    write_json_record(folder/'cancel_requested.json', {'requested_at':time.time()})
    return {'task_id':task_id,'cancel_requested':True,'state':result['state']}


def run_coding_task(repository, objective, files, checks, timeout_seconds=30, overall_timeout_seconds=180, output_limit=262144, on_created=None, execution_backend=None):
    """Apply supplied text changes, then run required Python checks exactly once."""
    process=psutil.Process(os.getpid())
    result = {'status':'failed','state':'VALIDATING','task_id':uuid.uuid4().hex,
              'objective':objective,'checks':[],'events':[], 'merged':False,
              'worker':{'pid':process.pid,'created':process.create_time()},
              'scope':'Supplied changes and explicit Python checks; no automatic code generation or repair.'}
    folder = None
    started=time.monotonic()
    try:
        repo = Path(repository).resolve()
        if not repo.is_dir() or not isinstance(objective,str) or not objective.strip():
            raise ValueError('Existing repository and objective required')
        if not isinstance(files,list) or not 1<=len(files)<=20 or not isinstance(checks,list) or not 1<=len(checks)<=10:
            raise ValueError('Supply 1-20 files and 1-10 explicit check argument lists')
        timeout = min(max(int(timeout_seconds),1),120)
        deadline=started+min(max(int(overall_timeout_seconds),1),600)
        output_limit=min(max(int(output_limit),1024),1048576)
        requested_backend = execution_backend if execution_backend is not None else (os.environ.get('AI_BS_EXECUTION_BACKEND', 'trusted_host').strip() or 'trusted_host')
        result['requested_execution_backend'] = requested_backend
        result['execution_mode'] = requested_backend if isinstance(requested_backend, str) else 'unknown'
        result['limits']={'check_timeout_seconds':timeout,'overall_timeout_seconds':deadline-started,'output_bytes_per_check':output_limit}
        raw=json.dumps({'repository':str(repo),'objective':objective,'files':files,'checks':checks,
                        'limits':result['limits'],'execution_backend':requested_backend},indent=2).encode('utf-8')
        folder=STORE/result['task_id'];folder.mkdir(parents=True,exist_ok=False)
        result.update(repository=str(repo),input_path=str(folder/'input.json'),input_sha256=_digest(raw),input_ready=False)
        def state(name):
            result['state']=name;result['events'].append({'state':name,'time':time.time()});_save(folder,result)
        def check_cancelled():
            if (folder/'cancel_requested.json').is_file():
                raise _TaskCancelled('Coding task cancelled before execution')
        state('VALIDATING')
        staged_input=folder/('input.'+uuid.uuid4().hex+'.tmp')
        staged_input.write_bytes(raw)
        os.replace(staged_input,folder/'input.json')
        result['input_ready']=True
        _save(folder,result)
        if on_created is not None:on_created(result['task_id'])
        check_cancelled()
        try:
            plan = resolve_coding_execution_plan(requested_backend)
        except CodingExecutionPolicyError as exc:
            result['error_code'] = exc.error_code
            if exc.error_code == 'INVALID_EXECUTION_BACKEND':
                raise ValueError(str(exc)) from exc
            raise RuntimeError(str(exc)) from exc
        result['execution_mode'] = plan['execution_mode']
        result['guest_provider'] = plan['guest_provider']
        result['isolation_verified'] = bool(plan['isolation_verified'])
        if plan.get('delegation_note'):
            result['delegation_note'] = plan['delegation_note']
        _save(folder, result)
        def remaining(maximum):
            available=deadline-time.monotonic()
            if available<=0:raise TimeoutError('Overall coding task deadline exceeded')
            return min(maximum,available)
        prepared = {}
        originals = {}
        for entry in files:
            check_cancelled()
            rel = _relative(entry['path']); content = entry['content']
            if not isinstance(content,str) or len(content)>1_000_000:
                raise ValueError('File content must be text up to 1M characters')
            key = str(rel).casefold()
            if key in prepared: raise ValueError('Duplicate file path')
            if rel.suffix.lower() in ('.py','.pyw'):
                validation = sanitize_and_validate_llm_code(content)
                check_cancelled()
                if not validation['valid']: raise ValueError('Python validation failed: '+ '; '.join(validation['errors']))
                content = validation['sanitized_code']
            source = _inside(repo,rel)
            originals[str(rel)] = source.read_bytes() if source.is_file() else None
            prepared[key]=(rel,content)
        check_cancelled()
        commands=[]
        raw_checks=[]
        verification_names=_verification_files(checks)
        if verification_names is not None and any(name.casefold() in prepared for name in verification_names):
            raise ValueError('Verification files cannot be replaced by a coding proposal')
        for argv in checks:
            if not isinstance(argv,list) or len(argv)<2 or not all(isinstance(a,str) and '\x00' not in a for a in argv) or argv[0]!='python':
                raise ValueError('Checks must be argument lists beginning with python')
            raw_checks.append(list(argv))
            commands.append([sys.executable,*argv[1:]])
        # No shell interpolation, hooks, or inherited application credentials.
        env={k:v for k,v in os.environ.items() if k.upper() in {'PATH','SYSTEMROOT','WINDIR','TEMP','TMP','LOCALAPPDATA'}}
        env.update(PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1',GIT_TERMINAL_PROMPT='0')
        def git(*args):
            p=subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=remaining(60))
            if p.returncode: raise RuntimeError('Git operation failed: '+p.stderr[:2000])
            return p.stdout.strip()
        if Path(git('rev-parse','--show-toplevel')).resolve()!=repo:
            raise ValueError('repository must be the Git checkout root')
        result['base_commit']=git('rev-parse','HEAD')
        work=folder/'worktree';hooks=folder/'empty_hooks';hooks.mkdir()
        result.update(worktree=str(work),repository=str(repo),input_hashes={k:_digest(v) for k,v in originals.items()})
        state('CREATING_WORKTREE')
        if (folder/'cancel_requested.json').is_file():
            result['status']='cancelled';state('CANCELLED');return result
        git('-c','core.hooksPath='+str(hooks),'worktree','add','--detach',str(work),result['base_commit'])
        state('WRITING')
        for rel,content in prepared.values():
            target=_inside(work,rel);target.parent.mkdir(parents=True,exist_ok=True)
            # Retain the current checkout's original separately, including dirty inputs.
            old=originals[str(rel)]
            if old is not None:
                backup=folder/'originals'/rel;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(old)
            target.write_text(content,encoding='utf-8')
        # The immutable copies also bind review to the exact bytes submitted to tests.
        proposal_hashes = {}
        for rel,_ in prepared.values():
            name = str(rel)
            proposal = _inside(work, rel).read_bytes()
            frozen = folder/'proposed'/rel
            frozen.parent.mkdir(parents=True,exist_ok=True)
            frozen.write_bytes(proposal)
            proposal_hashes[name] = _digest(proposal)
        verification_names = _verification_files(checks)
        verification_hashes = {}
        if verification_names is not None:
            for name in verification_names:
                target = _inside(work, _relative(name))
                original = _inside(repo, _relative(name))
                # A missing package initializer is normal; a missing test module is not.
                if not target.is_file() and not name.endswith('__init__.py'):
                    verification_names = None
                    break
                verification_hashes[name] = {
                    'worktree': _digest(target.read_bytes()) if target.is_file() else None,
                    'repository': _digest(original.read_bytes()) if original.is_file() else None,
                }
                if verification_hashes[name]['worktree'] != verification_hashes[name]['repository']:
                    raise ValueError('Verification source differs from the selected repository: '+name)
        state('CHECKING')
        required_guest_paths = sorted({
            *(str(rel) for rel, _ in prepared.values()),
            *(verification_names or []),
        })
        for raw_argv, host_argv in zip(raw_checks, commands):
            cancel_fn = lambda: (folder/'cancel_requested.json').is_file()
            if plan['execution_mode'] == 'trusted_host' and plan['guest_provider'] is None:
                evidence = run_bounded_check(
                    host_argv, work, env,
                    timeout_seconds=remaining(timeout),
                    output_limit=output_limit,
                    cancelled=cancel_fn,
                )
            else:
                evidence = run_guest_check(
                    plan, raw_argv, work,
                    required_paths=required_guest_paths,
                    timeout_seconds=remaining(timeout),
                    output_limit=output_limit,
                    cancelled=cancel_fn,
                )
            result['checks'].append(evidence);_save(folder,result)
            if evidence['returncode']!=0 or evidence.get('error'): break
        staged=subprocess.run(['git','-C',str(work),'add','--intent-to-add','--',*[str(rel) for rel,_ in prepared.values()]],env=env,capture_output=True,timeout=remaining(30))
        if staged.returncode: raise RuntimeError('Could not prepare review diff')
        diff=subprocess.run(['git','-C',str(work),'diff','--binary','HEAD'],env=env,capture_output=True,timeout=remaining(30))
        if diff.returncode: raise RuntimeError('Could not capture tracked diff')
        (folder/'changes.diff').write_bytes(diff.stdout)
        result['diff']=str(folder/'changes.diff')
        result['changed_files']=[str(rel) for rel,_ in prepared.values()]
        result['originals_unchanged']=all((_inside(repo,Path(name)).read_bytes() if _inside(repo,Path(name)).is_file() else None)==old for name,old in originals.items())
        result['proposal_unchanged']=all(_digest(_inside(work,_relative(name)).read_bytes())==digest for name,digest in proposal_hashes.items())
        result['verification_unchanged']=verification_names is not None and all(
            (_digest(_inside(work,_relative(name)).read_bytes()) if _inside(work,_relative(name)).is_file() else None)==record['worktree']
            and (_digest(_inside(repo,_relative(name)).read_bytes()) if _inside(repo,_relative(name)).is_file() else None)==record['repository']
            for name,record in verification_hashes.items())
        result['has_changes']=bool(diff.stdout)
        checks_unchanged = verification_names is None or result['verification_unchanged']
        result['status']='success' if result['has_changes'] and len(result['checks'])==len(commands) and all(c['returncode']==0 and not c.get('error') for c in result['checks']) and result['originals_unchanged'] and result['proposal_unchanged'] and checks_unchanged else 'failed'
        if result['status']=='success' and result['verification_unchanged']:
            result['review_seal']={'schema_version':2,'repository':str(repo),'base_commit':result['base_commit'],
                'execution_mode':result['execution_mode'],'guest_provider':result.get('guest_provider'),
                'original_hashes':result['input_hashes'],'proposal_hashes':proposal_hashes,
                'verification_hashes':verification_hashes,'diff_hash':_digest(diff.stdout),
                'checks_hash':_digest(json.dumps(result['checks'],sort_keys=True).encode('utf-8')),
                'check_arguments':checks}
        if any(c.get('error')=='cancelled' for c in result['checks']):
            result['status']='cancelled';state('CANCELLED')
        else:state('VERIFIED' if result['status']=='success' else 'FAILED')
    except _TaskCancelled as exc:
        result.update(status='cancelled',state='CANCELLED',error=str(exc))
        if folder:state('CANCELLED')
    except Exception as exc:
        result.update(status='failed',error_stage=result['state'],state='FAILED',
                      error_type=type(exc).__name__,error=str(exc))
        if folder:
            result['events'].append({'state':'FAILED','time':time.time()})
            _save(folder,result)
    return result
