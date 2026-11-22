"""Owner-scoped, prepare-only project records in the existing request journal."""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import threading
import time
from types import MappingProxyType
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .coding_recovery import REQUESTS, worker_identity, _alive
from .coding_journal import write_json_record
from .coding_locks import record_lock
from .coding_repository_snapshot import capture_repository_snapshot, _source_handle, _read_bytes
from .coding_vm_inputs import _path, _validate_project_inputs
from .coding_vm_staging import _locked_directory, _write_new_file
from .personal_memory_scope import is_sensitive_memory_text

REPOSITORIES = MappingProxyType({'ai-bs':Path(__file__).resolve().parents[2]})
_ACTIVE = threading.Lock()
ID_PATTERN = r'^[a-f0-9]{32}$'


class PreparationConflict(ValueError): pass
class PreparationNotFound(LookupError): pass
class PreparationEvidenceError(RuntimeError): pass
class PreparationScopeError(PermissionError): pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra='forbid',strict=True)


class SelectedFile(_Strict):
    relative_path: str = Field(min_length=1,max_length=240)
    role: Literal['editable','verification','dependency']


class SelectedCheck(_Strict):
    check_id: str = Field(pattern=r'^[a-z0-9_-]{1,64}$')
    profile: Literal['python_unittest','node_test','npm_script']
    targets: list[Annotated[str,Field(min_length=1,max_length=1024)]] = Field(min_length=1,max_length=61)


class PreparationLimits(_Strict):
    check_seconds: StrictInt = Field(default=30,ge=1,le=120)
    total_seconds: StrictInt = Field(default=180,ge=1,le=600)
    output_bytes: StrictInt = Field(default=262144,ge=1024,le=1048576)


class PreparationPlan(_Strict):
    request_id: str = Field(pattern=ID_PATTERN)
    repository_id: str = Field(min_length=1,max_length=64)
    objective: str = Field(min_length=1,max_length=8000)
    files: list[SelectedFile] = Field(min_length=1,max_length=20)
    checks: list[SelectedCheck] = Field(min_length=1,max_length=10)
    limits: PreparationLimits = Field(default_factory=PreparationLimits)


class PreparePayload(PreparationPlan):
    review_digest: str = Field(pattern=r'^[a-f0-9]{64}$')


def _encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def _hash(value): return hashlib.sha256(_encoded(value)).hexdigest()


def _owner(owner):
    valid = owner == 'local_admin'
    if isinstance(owner,str) and owner.startswith('firebase:'):
        parts = owner.split(':',2); valid = len(parts) == 3 and bool(parts[1]) and bool(parts[2])
    if not valid or not isinstance(owner,str) or len(owner) > 512 or any(ord(c)<32 or ord(c)==127 for c in owner):
        raise PreparationScopeError('Verified administrator ownership is required')
    return owner


@contextmanager
def _single_operation():
    if not _ACTIVE.acquire(blocking=False): raise PreparationConflict('Another project preparation is active')
    try: yield
    finally: _ACTIVE.release()


def _plan(value):
    plan = PreparationPlan.model_validate(value).model_dump(mode='json')
    if plan['repository_id'] not in REPOSITORIES: raise PreparationScopeError('Repository is outside the configured preparation policy')
    if plan['limits']['check_seconds'] > plan['limits']['total_seconds']: raise ValueError('Check exceeds total deadline')
    if len(_encoded(plan)) > 65536: raise ValueError('Preparation plan exceeds the metadata limit')
    if is_sensitive_memory_text(plan['objective']): raise ValueError('Recognized credentials must be removed from the objective')
    return plan


def _checks(plan):
    result = []
    for item in plan['checks']:
        profile,targets = item['profile'],item['targets']
        if profile == 'python_unittest': argv = ['python','-m','unittest',*targets]
        elif profile == 'node_test': argv = ['node','--test',*targets]
        else:
            if len(targets) != 1: raise ValueError('Select exactly one existing npm script')
            argv = ['npm','run',targets[0]]
        if any(c['check_id'] == item['check_id'] for c in result): raise ValueError('Duplicate check identity')
        result.append({'check_id':item['check_id'],'argv':argv})
    return result


def _repository_policy(plan):
    return hashlib.sha256(os.path.normcase(os.path.abspath(REPOSITORIES[plan['repository_id']])).encode('utf-8')).hexdigest()


def _review(owner,plan,snapshot):
    return _hash({'owner':owner,'plan':plan,'repository_policy_sha256':_repository_policy(plan),
                  'commit':snapshot['commit'],'files':snapshot['files'],'byte_count':snapshot['byte_count']})


def _capture(owner,plan):
    repo = REPOSITORIES[plan['repository_id']]
    snapshot,contents = capture_repository_snapshot(repo,plan['files'],allowed_roots=[repo])
    checks = _checks(plan)
    # Reuse actual schema2 project rules without inventing a VM/image identity.
    _validate_project_inputs(snapshot['files'],contents,checks)
    return snapshot,contents,checks,_review(owner,plan,snapshot)


def preview_preparation(owner,value):
    owner,plan = _owner(owner),_plan(value)
    with _single_operation():
        snapshot,_,checks,review = _capture(owner,plan)
    return {'state':'PREVIEW','request_id':plan['request_id'],'owner':owner,'repository_id':plan['repository_id'],
            'files':snapshot['files'],'checks':checks,'review_digest':review,
            'execution_authorized':False,'verification_status':'not_run','durable':False}


def _job(owner,request_id):
    if not isinstance(request_id,str) or re.fullmatch(ID_PATTERN,request_id) is None: raise ValueError('Invalid preparation ID')
    return REQUESTS / 'preparations' / hashlib.sha256(_owner(owner).encode('utf-8')).hexdigest() / request_id


@contextmanager
def _directory(path,create=False):
    with ExitStack() as locks:
        for item in reversed((path,*path.parents)):
            if create and not item.exists():
                try: os.mkdir(item)
                except FileExistsError: pass
            try: locks.enter_context(_locked_directory(item))
            except FileNotFoundError: raise PreparationNotFound('Preparation not found') from None
            except ValueError: raise PreparationEvidenceError('Journal directory could not be confirmed') from None
        yield


def _sealed(value):
    result = dict(value); result['entry_sha256'] = _hash(value)
    if len(json.dumps(result,indent=2,allow_nan=False).encode('utf-8')) > 131072: raise ValueError('Preparation evidence exceeds the metadata limit')
    return result


def _save_new(path,value):
    if path.exists(): raise PreparationConflict('Preparation evidence already exists')
    write_json_record(path,_sealed(value),exclusive=True)


def _load(path):
    try:
        with _source_handle(path) as (handle,length):
            if length > 131072: raise PreparationEvidenceError('Preparation metadata limit exceeded')
            value = json.loads(_read_bytes(handle,length).decode('utf-8'))
        if type(value) is not dict: raise PreparationEvidenceError('Invalid preparation evidence')
        digest = value.pop('entry_sha256',None)
        if digest != _hash(value): raise PreparationEvidenceError('Preparation evidence has changed')
        return value
    except (UnicodeError,ValueError,RecursionError):
        raise PreparationEvidenceError('Preparation metadata could not be confirmed') from None


def _intent(job,owner,request_id):
    try: value = _load(job / 'intent.json')
    except FileNotFoundError: raise PreparationNotFound('Preparation not found') from None
    if value.get('owner') != owner or value.get('request_id') != request_id: raise PreparationNotFound('Preparation not found')
    try:
        plan = _plan(value['plan']); snapshot = value['snapshot']
        actual = dict(snapshot); digest = actual.pop('snapshot_sha256')
        valid = (value['plan_sha256'] == _hash(plan) and digest == _hash(actual)
            and value['repository_policy_sha256'] == _repository_policy(plan)
            and value['review_digest'] == _review(owner,plan,snapshot)
            and value['checks'] == _checks(plan)
            and [{'relative_path':e['relative_path'],'role':e['role']} for e in snapshot['files']] == plan['files'])
        if not valid: raise PreparationEvidenceError('Preparation bindings changed')
    except (KeyError,TypeError,ValueError): raise PreparationEvidenceError('Preparation bindings are unavailable') from None
    return value


def _retained(job,intent):
    with ExitStack() as locks:
        handles,total = [],0
        for entry in intent['snapshot']['files']:
            _path(entry['relative_path'])
            target = job / 'inputs' / entry['relative_path']
            locks.enter_context(_directory(target.parent))
            handle,length = locks.enter_context(_source_handle(target))
            total += length
            if length != entry['length'] or total > 16777216: raise PreparationEvidenceError('Retained source length changed')
            handles.append((entry,handle,length))
        for entry,handle,length in handles:
            if hashlib.sha256(_read_bytes(handle,length)).hexdigest() != entry['sha256']:
                raise PreparationEvidenceError('Retained source hash changed')
        if total != intent['snapshot']['byte_count']: raise PreparationEvidenceError('Retained source count changed')


def _summary(intent,state,durable=False):
    plan = intent['plan']
    return {'kind':'project_preparation','request_id':intent['request_id'],'owner':intent['owner'],
            'repository_id':plan['repository_id'],'objective':plan['objective'],'files':intent['snapshot']['files'],
            'checks':intent['checks'],'limits':plan['limits'],'review_digest':intent['review_digest'],
            'snapshot_sha256':intent['snapshot']['snapshot_sha256'],'captured_at_utc':intent['snapshot']['captured_at_utc'],
            'state':state,'durable':durable,'execution_mode':'windows_vm','execution_authorized':False,
            'vm_admission_status':'pending_accepted_worker','verification_status':'not_run','current_sources_rechecked':False}


def _confirm(job,owner,request_id):
    intent = _intent(job,owner,request_id)
    receipt = _load(job / 'preparation.json')
    if receipt != {'state':'PREPARED','intent_sha256':_hash(intent),'review_digest':intent['review_digest']}:
        raise PreparationEvidenceError('Preparation receipt changed')
    _retained(job,intent)
    return _summary(intent,'PREPARED',True)


def _read(job,owner,request_id):
    if (job / 'preparation.json').is_file(): return _confirm(job,owner,request_id)
    intent = _intent(job,owner,request_id)
    state = 'PREPARING'
    for name,expected in [('failure.json','FAILED'),('recovery.json','INTERRUPTED')]:
        if (job / name).is_file():
            evidence = _load(job / name)
            if evidence.get('state') != expected or evidence.get('intent_sha256') != _hash(intent): raise PreparationEvidenceError('Partial preparation evidence changed')
            state = expected
    return _summary(intent,state)


def read_preparation(owner,request_id):
    owner = _owner(owner); job = _job(owner,request_id)
    with _directory(job): return _read(job,owner,request_id)


def prepare_request(owner,value):
    owner = _owner(owner)
    request = PreparePayload.model_validate(value).model_dump(mode='json')
    expected = request.pop('review_digest'); plan = _plan(request)
    job = _job(owner,plan['request_id'])
    with _single_operation():
        if job.exists():
            with _directory(job),record_lock(job / 'state.lock'):
                intent = _intent(job,owner,plan['request_id'])
                if intent['plan_sha256'] != _hash(plan) or intent['review_digest'] != expected: raise PreparationConflict('Request inputs changed')
                if not (job / 'preparation.json').is_file(): raise PreparationConflict('Incomplete preparation requires inspection and a new request ID')
                return _confirm(job,owner,plan['request_id'])
        snapshot,contents,checks,review = _capture(owner,plan)
        if review != expected: raise PreparationConflict('Source or plan changed; preview the current inputs again')
        intent = dict(kind='project_preparation',request_id=plan['request_id'],owner=owner,plan=plan,plan_sha256=_hash(plan),
            repository_policy_sha256=_repository_policy(plan),snapshot=snapshot,checks=checks,review_digest=review,
            state='PREPARING',worker=worker_identity(),created_at_utc=datetime.now(timezone.utc).isoformat())
        _sealed(intent)  # Reject oversized metadata before any journal mutation.
        with _directory(job.parent,True):
            try: os.mkdir(job)
            except FileExistsError: raise PreparationConflict('Another writer retained this request; inspect it') from None
            with _directory(job),record_lock(job / 'state.lock'):
                _save_new(job / 'intent.json',intent)
                try:
                    for entry in snapshot['files']:
                        target = job / 'inputs' / entry['relative_path']
                        with _directory(target.parent,True): _write_new_file(target,contents[entry['relative_path']])
                    _retained(job,intent)
                    _save_new(job / 'preparation.json',{'state':'PREPARED','intent_sha256':_hash(intent),'review_digest':review})
                    return _confirm(job,owner,plan['request_id'])
                except Exception:
                    if not (job / 'preparation.json').exists():
                        _save_new(job / 'failure.json',{'state':'FAILED','intent_sha256':_hash(intent),'reason':'retained_copy_or_confirmation_failed'})
                    raise


def recover_preparation(owner,request_id):
    owner = _owner(owner); job = _job(owner,request_id)
    with _directory(job),record_lock(job / 'state.lock'):
        result = _read(job,owner,request_id)
        if result['state'] == 'PREPARING':
            intent = _intent(job,owner,request_id)
            if not _alive(intent):
                _save_new(job / 'recovery.json',{'state':'INTERRUPTED','intent_sha256':_hash(intent),'reason':'worker_ended_no_actions_replayed'})
                result = _summary(intent,'INTERRUPTED')
        return result


def _listing_clock(): return time.monotonic()


def list_preparations(owner,*,limit=20,cursor=None):
    """Bounded metadata page only; inspection separately rechecks input bytes."""
    owner=_owner(owner)
    if type(limit) is not int or not 1<=limit<=50: raise ValueError('History limit must be between1 and50')
    if cursor is not None and (not isinstance(cursor,str) or re.fullmatch(ID_PATTERN,cursor) is None): raise ValueError('Invalid history cursor')
    namespace=_job(owner,'0'*32).parent
    result={'owner':owner,'items':[],'next_cursor':None,'metadata_only':True}
    started=_listing_clock()
    def budget():
        if _listing_clock()-started>0.5: raise PreparationEvidenceError('Preparation history deadline exceeded')
    with ExitStack() as locks:
        try: locks.enter_context(_directory(namespace))
        except PreparationNotFound: return result
        def entries():
            with os.scandir(namespace) as stream:
                for entry in stream:
                    budget()
                    if re.fullmatch(ID_PATTERN,entry.name) and (cursor is None or entry.name>cursor): yield entry.name
        names=heapq.nsmallest(limit+1,entries())
        for identifier in names[:limit]:
            budget(); job=namespace/identifier
            try:
                with _directory(job):
                    intent=_intent(job,owner,identifier)
                    if (job/'preparation.json').is_file():
                        receipt=_load(job/'preparation.json')
                        if receipt!={'state':'PREPARED','intent_sha256':_hash(intent),'review_digest':intent['review_digest']}: raise PreparationEvidenceError('History receipt changed')
                        state='PREPARED'
                    else:
                        # A receipt can appear after the first existence check.
                        # Keep this page a metadata snapshot; never enter _read's
                        # full input verification branch during listing.
                        state='PREPARING'
                        for marker,expected in [('failure.json','FAILED'),('recovery.json','INTERRUPTED')]:
                            if (job/marker).is_file():
                                evidence=_load(job/marker)
                                if evidence.get('state')!=expected or evidence.get('intent_sha256')!=_hash(intent): raise PreparationEvidenceError('History progress evidence changed')
                                state=expected
            except PreparationNotFound: raise PreparationEvidenceError('History record could not be confirmed') from None
            result['items'].append({'request_id':identifier,'title':intent['plan']['objective'][:200],
                'state':state,'captured_at_utc':intent['snapshot']['captured_at_utc'],'retained_inputs_revalidated':False,
                'execution_authorized':False,'verification_status':'not_run'})
        if len(names)>limit: result['next_cursor']=names[limit-1]
        budget()
    return result
