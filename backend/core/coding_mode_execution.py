"""Retained coding candidates; expanded verification fails closed without a worker.

This bridge never invokes a shell, model, VM, project code or application writer.
Static Python parsing is evidence of syntax only, never project verification.
"""
import ast
from datetime import datetime, timezone
import hashlib
import os
import heapq
import re
import time
from typing import Literal
from contextlib import ExitStack

from pydantic import BaseModel, ConfigDict, Field

from . import coding_preparation as preparation
from . import coding_preparation_proposals as proposals
from .coding_chat import _ACTIVE
from .coding_locks import record_lock
from .coding_vm_inputs import _path
from .coding_vm_staging import _write_new_file
from . import coding_syntax
from . import coding_mode_local as local

BLOCKED_REASON = 'No accepted isolated project-verification worker is connected. Project checks were not run; applying this candidate is unavailable.'


class ExecutionPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    execution_id: str = Field(pattern=preparation.ID_PATTERN)
    request_id: str = Field(pattern=preparation.ID_PATTERN)
    plan_id: str = Field(pattern=preparation.ID_PATTERN)
    proposal_id: str = Field(pattern=preparation.ID_PATTERN)
    execution_backend: Literal['isolated', 'trusted_host'] = 'isolated'
    trusted_local_ack: bool = False


def enabled():
    return os.environ.get('AI_BS_CODING_MODE') == '1'


def capabilities():
    return {'enabled': enabled(), 'languages': ['python', 'javascript', 'jsx'],
            'execution_available': False, 'apply_available': False,
            'blocked_reason': BLOCKED_REASON, 'static_validation': ['python_ast'] + (['javascript_jsx_parser'] if coding_syntax.available() else []),
            'max_active_tasks': 1, 'supported_execution_backends': ['isolated', 'trusted_host'],
            'trusted_local_available': local.available()}


def _folder(owner, execution_id):
    return preparation._job(owner, execution_id).parent/'coding_mode'/execution_id


def _source(owner, payload):
    value = proposals.read_proposal(owner, payload['request_id'], payload['plan_id'], payload['proposal_id'])
    if value['state'] != 'PROPOSAL_READY':
        raise preparation.PreparationConflict('A confirmed saved proposal is required')
    return value


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _candidate_inputs(owner, payload):
    source = _source(owner, payload)
    job = preparation._job(owner, payload['request_id'])
    with preparation._directory(job):
        intent = preparation._intent(job, owner, payload['request_id'])
        preparation._retained(job, intent)
    candidates = {f['path']: f for f in source['proposal']['files']}
    files, contents, static_checks, javascript = [], {}, [], []
    for original in intent['snapshot']['files']:
        name = original['relative_path']
        if name in candidates:
            raw = candidates[name]['content'].encode('utf-8')
            if _digest(raw) != candidates[name]['proposed_sha256']:
                raise preparation.PreparationEvidenceError('Candidate hash changed')
        else:
            path = job/'inputs'/name
            with preparation._directory(path.parent), preparation._source_handle(path) as (handle, length):
                raw = preparation._read_bytes(handle, length)
            if _digest(raw) != original['sha256']:
                raise preparation.PreparationEvidenceError('Immutable selected input changed')
        contents[name] = raw
        files.append({**original, 'length': len(raw), 'sha256': _digest(raw)})
        if original['role'] == 'editable':
            check = {'path': name, 'kind': 'syntax', 'status': 'not_run'}
            if name.lower().endswith(('.py', '.pyw')):
                try:
                    ast.parse(raw, filename=name)
                    check['status'] = 'passed'
                except (SyntaxError, ValueError) as error:
                    check.update(status='failed', message=type(error).__name__)
            else:
                javascript.append({'path': name, 'content': raw.decode('utf-8')})
            static_checks.append(check)
    parsed = {check['path']: check for check in coding_syntax.javascript_checks(javascript)}
    static_checks = [parsed.get(check['path'], check) for check in static_checks]
    return source, intent, files, contents, static_checks


def _response(value, state, checks):
    return {**value['payload'], 'kind': 'coding_mode_execution', 'owner': value['owner'],
            'state': state, 'verification_status': 'not_run', 'execution_authorized': False,
            'apply_authorized': False, 'can_apply': False, 'blocked_reason': BLOCKED_REASON,
            'static_checks': checks, 'checks': value['checks'], 'files': value['files'],
            'review_diff': value['review_diff'], 'source_status': 'retained_candidate',
            'current_sources_rechecked': False, 'created_at_utc': value['created_at_utc']}


def _read(owner, execution_id):
    folder = _folder(owner, execution_id)
    with preparation._directory(folder):
        value = preparation._load(folder/'input.json')
        if (value.get('kind') != 'coding_mode_execution_input' or value.get('owner') != owner
                or value.get('payload', {}).get('execution_id') != execution_id):
            raise preparation.PreparationEvidenceError('Coding candidate owner or identity changed')
        ExecutionPayload.model_validate(value['payload'])
        source, intent, files, contents, static_checks = _candidate_inputs(owner, value['payload'])
        if (set(value) != {'kind', 'owner', 'payload', 'proposal_sha256', 'files', 'checks', 'review_diff', 'created_at_utc'}
                or preparation._hash(source) != value['proposal_sha256']
                or value['files'] != files or value['review_diff'] != source['proposal']['diff']
                or value['checks'] != [{**check, 'status': 'not_run'} for check in intent['checks']]):
            raise preparation.PreparationEvidenceError('Saved proposal binding changed')
        result = preparation._load(folder/'result.json') if (folder/'result.json').exists() else None
        if value['payload'].get('execution_backend') == 'trusted_host':
            return value, local.decorate(folder, value, _response(value, 'RUNNING', []))
        partial = result is None or result.get('state') == 'INTERRUPTED'
        for entry in value['files']:
            _path(entry['relative_path'])
            path = folder/'candidate'/entry['relative_path']
            if partial and not path.exists():
                continue
            with preparation._directory(path.parent), preparation._source_handle(path) as (handle, length):
                raw = preparation._read_bytes(handle, length)
            if length != entry['length'] or _digest(raw) != entry['sha256']:
                raise preparation.PreparationEvidenceError('Retained candidate bytes changed')
        if result is None:
            return value, _response(value, 'INCOMPLETE', [])
        if (set(result) != {'input_sha256', 'state', 'static_checks'}
                or result.get('input_sha256') != preparation._hash(value)
                or result.get('state') not in {'BLOCKED', 'INTERRUPTED'}
                or result['static_checks'] != (static_checks if result['state'] == 'BLOCKED' else [])):
            raise preparation.PreparationEvidenceError('Coding candidate result changed')
        return value, _response(value, result['state'], result['static_checks'])


def read_execution(owner, execution_id):
    return _read(owner, execution_id)[1]


def list_executions(owner, *, limit=20, cursor=None):
    """Owner-bound metadata discovery; never parse source or replay work."""
    owner = preparation._owner(owner)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError('Invalid execution history limit')
    if cursor is not None and (not isinstance(cursor, str) or re.fullmatch(preparation.ID_PATTERN, cursor) is None):
        raise ValueError('Invalid execution cursor')
    namespace = _folder(owner, '0'*32).parent
    response = {'owner': owner, 'items': [], 'next_cursor': None, 'metadata_only': True}
    started = time.monotonic()
    def budget():
        if time.monotonic()-started > 1:
            raise preparation.PreparationEvidenceError('Execution metadata deadline exceeded')
    with ExitStack() as held:
        try:
            held.enter_context(preparation._directory(namespace))
        except preparation.PreparationNotFound:
            return response
        def identifiers():
            with os.scandir(namespace) as entries:
                for entry in entries:
                    budget()
                    if re.fullmatch(preparation.ID_PATTERN, entry.name) and (cursor is None or entry.name > cursor):
                        yield entry.name
        names = heapq.nsmallest(limit+1, identifiers())
        for name in names[:limit]:
            budget()
            with preparation._directory(namespace/name):
                value = preparation._load(namespace/name/'input.json')
                payload = ExecutionPayload.model_validate(value['payload']).model_dump(mode='json')
                if value.get('owner') != owner or payload['execution_id'] != name or value.get('kind') != 'coding_mode_execution_input':
                    raise preparation.PreparationEvidenceError('Execution history identity changed')
                state = 'INCOMPLETE'
                if (namespace/name/'result.json').is_file():
                    result = preparation._load(namespace/name/'result.json')
                    if result.get('input_sha256') != preparation._hash(value):
                        raise preparation.PreparationEvidenceError('Execution history result changed')
                    if payload.get('execution_backend') == 'trusted_host':
                        state = result['state'] if local._valid(result, value) else 'UNCONFIRMED'
                        if state == 'RUNNING' and not local._active(namespace/name): state = 'INCOMPLETE'
                    else:
                        if result.get('state') not in {'BLOCKED', 'INTERRUPTED'}:
                            raise preparation.PreparationEvidenceError('Execution history result changed')
                        state = result['state']
                response['items'].append({**payload, 'state': state, 'verification_status': 'not_run',
                                          'created_at_utc': value['created_at_utc']})
                if state == 'VERIFIED': response['items'][-1]['verification_status'] = 'passed'
                elif state == 'FAILED': response['items'][-1]['verification_status'] = 'failed'
        if len(names) > limit:
            response['next_cursor'] = names[limit-1]
        budget()
    return response


def prepare_execution(owner, payload):
    payload = ExecutionPayload.model_validate(payload).model_dump(mode='json')
    if payload['execution_backend'] == 'trusted_host' and payload['trusted_local_ack'] is not True:
        raise preparation.PreparationScopeError('Trusted local checks require explicit per-task acknowledgement')
    if payload['execution_backend'] == 'isolated' and payload['trusted_local_ack']:
        raise ValueError('Local acknowledgement cannot change an isolated task')
    folder = _folder(owner, payload['execution_id'])
    if folder.exists():
        value, response = _read(owner, payload['execution_id'])
        if value['payload'] != payload:
            raise preparation.PreparationConflict('Execution ID already binds different inputs')
        return response
    if not _ACTIVE.acquire(blocking=False):
        raise preparation.PreparationConflict('Another coding operation is active')
    transferred = False
    try:
        source, intent, files, contents, static_checks = _candidate_inputs(owner, payload)
        value = {'kind': 'coding_mode_execution_input', 'owner': preparation._owner(owner),
                 'payload': payload, 'proposal_sha256': preparation._hash(source), 'files': files,
                 'checks': [{**check, 'status': 'not_run'} for check in intent['checks']],
                 'review_diff': source['proposal']['diff'], 'created_at_utc': datetime.now(timezone.utc).isoformat()}
        with preparation._directory(folder, create=True), record_lock(folder/'state.lock'):
            preparation._save_new(folder/'input.json', value)
            for name, raw in contents.items():
                target = folder/'candidate'/name
                with preparation._directory(target.parent, create=True):
                    _write_new_file(target, raw)
            if payload['execution_backend'] == 'isolated':
                preparation._save_new(folder/'result.json', {'input_sha256': preparation._hash(value),
                                      'state': 'BLOCKED', 'static_checks': static_checks})
        if payload['execution_backend'] == 'trusted_host':
            local.start(folder, value, intent, static_checks, _ACTIVE.release)
            transferred = True
        return read_execution(owner, payload['execution_id'])
    finally:
        if not transferred: _ACTIVE.release()


def recover_execution(owner, execution_id):
    # Inspection cannot replay candidate creation, inference, verification or apply.
    folder = _folder(owner, execution_id)
    value, response = _read(owner, execution_id)
    if value['payload'].get('execution_backend') == 'trusted_host':
        return local.recover(folder, value, response)
    with preparation._directory(folder), record_lock(folder/'state.lock'):
        value, response = _read(owner, execution_id)
        if response['state'] == 'INCOMPLETE':
            preparation._save_new(folder/'result.json', {'input_sha256': preparation._hash(value),
                                  'state': 'INTERRUPTED', 'static_checks': []})
    return {**read_execution(owner, execution_id), 'replayed': False}


def cancel_execution(owner, execution_id):
    value, response = _read(owner, execution_id)
    if value['payload'].get('execution_backend') == 'trusted_host':
        return local.cancel(_folder(owner, execution_id), value, response)
    return {**response, 'cancel_requested': False}


def review_execution(owner, execution_id):
    value, response = _read(owner, execution_id)
    if value['payload'].get('execution_backend') == 'trusted_host':
        _, intent, _, _, _ = _candidate_inputs(owner, value['payload'])
        return local.review(_folder(owner, execution_id), value, intent, response)
    return response


def read_check_log(owner, execution_id, check_id):
    if not isinstance(check_id, str) or re.fullmatch(r'[a-z0-9_-]{1,64}', check_id) is None:
        raise ValueError('Invalid check identity')
    value, _ = _read(owner, execution_id)
    if value['payload'].get('execution_backend') != 'trusted_host':
        raise preparation.PreparationNotFound('No local check log exists')
    return local.read_log(_folder(owner, execution_id), value, check_id)


def apply_execution(owner, execution_id, review_token=None):
    value, response = _read(owner, execution_id)
    if value['payload'].get('execution_backend') == 'trusted_host':
        _, intent, _, _, _ = _candidate_inputs(owner, value['payload'])
        return local.apply(_folder(owner, execution_id), value, intent, response, review_token)
    raise preparation.PreparationConflict(BLOCKED_REASON)
