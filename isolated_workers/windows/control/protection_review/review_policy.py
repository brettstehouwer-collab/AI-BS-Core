"""Dormant review of supplied metadata. No I/O, ACL edits or admission authority.

This is not an effective-access evaluator or authenticated Windows collector.
Even a clean synthetic report requires native token, ancestor and held-object
checks. Do not wire this review result to worker/execution/apply activation.
"""
import json
import ntpath
import re

ROOT = r'C:\ProgramData\AI-BS-WorkerControl'
ROLES = {'deployment', 'state', 'sealed_inputs', 'incoming_outputs', 'receipts'}
ADMIN, SYSTEM = 'S-1-5-32-544', 'S-1-5-18'
BROAD = {'S-1-1-0', 'S-1-5-11', 'S-1-5-32-545', 'S-1-5-7'}
READ = {'Read', 'ReadAndExecute', 'ReadData', 'ListDirectory', 'ReadAttributes',
        'ReadExtendedAttributes', 'ReadPermissions', 'ReadControl', 'ExecuteFile',
        'Traverse', 'Synchronize'}
WRITE = {'FullControl', 'Modify', 'Write', 'WriteData', 'AppendData', 'CreateFiles',
         'CreateDirectories', 'Delete', 'DeleteSubdirectoriesAndFiles',
         'ChangePermissions', 'TakeOwnership', 'WriteDac', 'WriteOwner',
         'WriteAttributes', 'WriteExtendedAttributes'}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def shape(value, fields):
    require(type(value) is dict and set(value) == set(fields), 'UNEXPECTED_FIELDS')


def path(value):
    require(type(value) is str and len(value) <= 1024 and
            re.match(r'^[A-Z]:\\', value) is not None and '/' not in value and
            ntpath.normpath(value) == value, 'CANONICAL_LOCAL_PATH_REQUIRED')
    for part in value[3:].split('\\'):
        require(part not in {'', '.', '..'} and not part.endswith((' ', '.')) and
                not any(ord(c) < 32 or c in '<>:"|?*' for c in part), 'UNSAFE_PATH')
        require(part.split('.')[0].upper() not in
                {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(10)),
                 *(f'LPT{i}' for i in range(10))}, 'DEVICE_PATH_REFUSED')
    return value.casefold()


def sid(value):
    require(type(value) is str and len(value) <= 184 and
            re.fullmatch(r'S-1-(?:[0-9]+-)*[0-9]+', value) is not None, 'SID_REQUIRED')
    return value


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('NON_JSON_CONSTANT')


def parse_json(text):
    require(type(text) is str and len(text.encode('utf-8')) <= 1048576,
            'REVIEW_DOCUMENT_BOUND')
    return json.loads(text, object_pairs_hook=_unique, parse_constant=_constant)


def review(policy, snapshot):
    shape(policy, {'schema_version', 'mode', 'root', 'controller_sid',
                   'vm_worker_sid', 'roots', 'files'})
    require(type(policy['schema_version']) is int and policy['schema_version'] == 1
            and policy['mode'] == 'review_only', 'REVIEW_ONLY_REQUIRED')
    root = path(policy['root'])
    require(root == ROOT.casefold(), 'FIXED_PROPOSED_ROOT_REQUIRED')
    controller, worker = sid(policy['controller_sid']), sid(policy['vm_worker_sid'])
    require(controller != worker and all(s not in BROAD | {ADMIN, SYSTEM}
            and s.startswith('S-1-5-21-') for s in [controller, worker]),
            'DISTINCT_EXACT_HOST_ACCOUNT_SIDS_REQUIRED')
    shape(policy['roots'], ROLES)
    purpose = {root: 'root'}
    for role, name in policy['roots'].items():
        key = path(name)
        require(key == root + '\\' + role, 'FIXED_NONOVERLAPPING_ROOTS_REQUIRED')
        require(key not in purpose, 'ROOT_ALIAS_COLLISION')
        purpose[key] = role
    files = policy['files']
    require(type(files) is list and 1 <= len(files) <= 64, 'BOUNDED_LOAD_FILES_REQUIRED')
    expected_files = {}
    for item in files:
        shape(item, {'path', 'sha256', 'kind', 'signer'})
        key = path(item['path'])
        require(key.startswith(path(policy['roots']['deployment']) + '\\')
                and key not in purpose, 'DEPLOYMENT_FILE_SCOPE_REQUIRED')
        require(type(item['sha256']) is str and re.fullmatch('[a-f0-9]{64}', item['sha256'])
                and item['kind'] in {'controller', 'runtime', 'dependency'}, 'LOAD_IDENTITY_REQUIRED')
        require(type(item['signer']) is str and len(item['signer']) <= 256 and
                (bool(item['signer']) if item['kind'] == 'runtime' else item['signer'] == ''),
                'RUNTIME_SIGNER_POLICY_REQUIRED')
        purpose[key] = 'load_file'
        expected_files[key] = item
    require(any(f['kind'] == 'runtime' for f in files), 'RUNTIME_IDENTITY_REQUIRED')
    shape(snapshot, {'schema_version', 'nodes'})
    require(type(snapshot['schema_version']) is int and snapshot['schema_version'] == 1
            and type(snapshot['nodes']) is list and len(snapshot['nodes']) <= 128,
            'BOUNDED_METADATA_REQUIRED')
    nodes = {}
    for node in snapshot['nodes']:
        require(type(node) is dict and 'path' in node and type(node.get('exists')) is bool,
                'PATH_OBSERVATION_REQUIRED')
        key = path(node['path'])
        require(key in purpose and key not in nodes, 'UNEXPECTED_OR_DUPLICATE_OBSERVATION')
        if node['exists'] is False:
            shape(node, {'path', 'exists'})
        nodes[key] = node
    findings = []
    def finding(code, key):
        findings.append({'code': code, 'path': key})
    for key, role in purpose.items():
        node = nodes.get(key)
        if node is None or node['exists'] is not True:
            finding('MISSING_PATH', key)
            continue
        base_fields = {'path', 'exists', 'owner_sid', 'protected_dacl', 'reparse', 'grants'}
        shape(node, base_fields | ({'sha256', 'signature_valid', 'signer'} if role == 'load_file' else set()))
        if node['owner_sid'] not in {ADMIN, SYSTEM}:
            finding('UNAPPROVED_OWNER', key)
        if node['protected_dacl'] is not True:
            finding('DACL_NOT_PROTECTED', key)
        if node['reparse'] is not False:
            finding('REPARSE_REFUSED', key)
        grants = node['grants']
        require(type(grants) is list and len(grants) <= 64, 'BOUNDED_ACES_REQUIRED')
        writers = {ADMIN, SYSTEM}
        if role in {'state', 'sealed_inputs', 'incoming_outputs', 'receipts'}:
            writers.add(controller)
        if role == 'incoming_outputs':
            writers.add(worker)
        readers = writers | {controller}
        if role in {'root', 'deployment', 'load_file', 'sealed_inputs', 'incoming_outputs'}:
            readers.add(worker)
        for ace in grants:
            shape(ace, {'sid', 'rights', 'type'})
            principal = sid(ace['sid'])
            rights = set(ace['rights'].split(', ')) if type(ace['rights']) is str else set()
            if ace['type'] != 'Allow' or not rights or not rights <= READ | WRITE:
                finding('UNSUPPORTED_ACE', key)
            elif rights & WRITE and principal not in writers:
                finding('UNAPPROVED_WRITER', key)
            elif rights & (READ | WRITE) and principal not in readers:
                finding('UNAPPROVED_READER', key)
        if role == 'load_file':
            expected = expected_files[key]
            if node['sha256'] != expected['sha256']:
                finding('FILE_HASH_MISMATCH', key)
            if expected['kind'] == 'runtime' and (node['signature_valid'] is not True
                    or node['signer'] != expected['signer']):
                finding('RUNTIME_SIGNATURE_MISMATCH', key)
    return {'state': 'REVIEW_ONLY', 'findings': findings,
            'required_native_checks': [
                'Authenticated caller token, effective groups and privileges',
                'All ancestor ownership/delete-child/replacement rights',
                'Held volume/file identities, regular files and hardlink exclusion',
                'Complete protected dependency/cache/DLL/import tree before loading',
                'Effective ACL and OWNER RIGHTS semantics for task-created content',
                'Immutable-input lifecycle and durable exchange receipts/recovery'],
            'worker_admitted': False, 'execution_authorized': False,
            'apply_authorized': False, 'verification_status': 'not_run'}
