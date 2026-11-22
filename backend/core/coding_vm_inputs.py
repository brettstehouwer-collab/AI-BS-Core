"""Validate bounded VM input bytes against a trusted host admission.

Pure validation only: no filesystem access, execution, authentication or VM
configuration. Callers must obtain admission from authenticated host policy,
never from the model/guest, and reject reparse points during actual transfer.
"""
from __future__ import annotations

import hashlib
import json
import re


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _keys(value, expected):
    _require(type(value) is dict and set(value) == set(expected), 'Unexpected record fields')


def _hex(value, lengths):
    _require(type(value) is str and len(value) in lengths and
             re.fullmatch('[0-9a-f]+', value) is not None, 'Invalid opaque identity or hash')


def _path(value):
    _require(type(value) is str and 0 < len(value) <= 240 and '\\' not in value,
             'Expected a canonical relative path')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$',
                *('COM'+n for n in '123456789¹²³'), *('LPT'+n for n in '123456789¹²³')}
    for part in value.split('/'):
        _require(part not in ('', '.', '..') and not part.endswith((' ', '.')) and
                 not any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*' for c in part) and
                 part.split('.')[0].upper() not in reserved, 'Unsafe transfer path')
        lower = part.lower()
        _require(lower not in {'.git', '.ssh', '.aws', '.azure', '.gnupg'} and
                 lower != '.env' and not lower.startswith('.env.') and
                 not lower.endswith(('.pem', '.key', '.pfx', '.p12')), 'Credential path excluded')
    return value.casefold()


def _protected_project_path(name):
    parts = name.casefold().split('/')
    base = parts[-1]
    return (any(part in {'test', 'tests', '__tests__'} for part in parts[:-1]) or
            re.search(r'(^test_.*\.py$|_test\.py$|\.(test|spec)\.(py|js|jsx|mjs|cjs)$)', base) is not None or
            base in {'package.json', 'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock',
                     'pnpm-lock.yaml', 'pyproject.toml', 'poetry.lock', 'uv.lock'} or
            (base.startswith('requirements') and base.endswith('.txt')) or
            base.startswith(('.eslintrc', '.babelrc', 'eslint.config.', 'babel.config.',
                             'vite.config.', 'vitest.config.', 'jest.config.')) or
            (base.startswith('tsconfig') and base.endswith('.json')))


def _unique_package_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'Duplicate package JSON key')
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError('Non-JSON package constant')


def _validate_project_inputs(files, contents, checks):
    """Schema2 plan validation only; none of these check commands are executed."""
    entries = {entry['relative_path']: entry for entry in files}
    names = {name.casefold() for name in entries}
    languages = set()
    for name, entry in entries.items():
        parts = name.casefold().split('/')
        _require(not any(part in {'node_modules', '.venv', 'venv', '__pycache__', '.npm'} for part in parts),
                 'Runtime and cache directories are excluded')
        _require(not any(part in {'.npmrc', '.pypirc', '.netrc'} for part in parts), 'Credential path excluded')
        _require(not any('/'.join(parts[:index]) in names for index in range(1, len(parts))),
                 'File/directory path collision')
        if entry['role'] == 'editable':
            _require(not _protected_project_path(name), 'Protected tests, configuration and dependencies cannot be editable')
            suffix = name.rsplit('.', 1)[-1].casefold() if '.' in name else ''
            _require(suffix in {'py', 'pyw', 'js', 'mjs', 'cjs', 'jsx'}, 'Unsupported editable source language')
            languages.add('python' if suffix in {'py', 'pyw'} else 'jsx' if suffix == 'jsx' else 'javascript')
    _require(bool(languages), 'Select at least one editable implementation file')

    def verification(name):
        _path(name)
        _require(name in entries and entries[name]['role'] == 'verification',
                 'Check must reference a selected verification file')

    profiles = set()
    for check in checks:
        argv = check['argv']
        if argv[:3] == ['python', '-m', 'unittest'] and len(argv) >= 4:
            for module in argv[3:]:
                _require(re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', module) is not None,
                         'Unsupported Python verification module')
                verification(module.replace('.', '/') + '.py')
            profiles.add('python')
        elif argv[:2] == ['node', '--test'] and len(argv) >= 3:
            for name in argv[2:]:
                _require(not name.startswith('-') and not any(c in name for c in '[]{}'),
                         'Node verification requires literal file arguments')
                _require(name.casefold().endswith(('.js', '.mjs', '.cjs')), 'Unsupported Node verification file')
                verification(name)
            profiles.add('javascript')
        elif argv[:2] == ['npm', 'run'] and len(argv) == 3:
            script = argv[2]
            _require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9:_-]{0,63}', script) is not None,
                     'Unsupported npm script name')
            _require(entries.get('package.json', {}).get('role') == 'dependency',
                     'npm package.json must be a selected immutable dependency')
            _require(any(entries.get(name, {}).get('role') == 'dependency'
                         for name in ('package-lock.json', 'npm-shrinkwrap.json')),
                     'npm requires a selected immutable root lockfile')
            try:
                package = json.loads(contents['package.json'].decode('utf-8'),
                                     object_pairs_hook=_unique_package_object,
                                     parse_constant=_reject_json_constant)
            except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
                raise ValueError('Invalid package.json JSON') from exc
            scripts = package.get('scripts') if type(package) is dict else None
            _require(type(scripts) is dict and type(scripts.get(script)) is str and bool(scripts[script].strip()),
                     'Selected package.json does not define the requested script')
            _require(not re.search(r'no test specified|no tests? (?:found|configured|available)',
                                   scripts[script], re.IGNORECASE),
                     'Selected npm script is a placeholder, not a verification check')
            profiles.update(('javascript', 'jsx'))
        else:
            raise ValueError('Unsupported project verification command')
    for language, message in [('python', 'Python verification is required'),
                              ('javascript', 'JavaScript verification is required'),
                              ('jsx', 'JSX verification requires an existing npm-project check')]:
        _require(language not in languages or language in profiles, message)


def validate_vm_inputs(envelope, contents, admission):
    """Return a detached validated manifest; raise before any transfer on error.

    `admission` is the exact immutable, host-approved manifest. This function
    cannot establish its provenance or detect arbitrary secrets in source text.
    """
    fields = ('schema_version', 'task_id', 'request_id', 'attempt_id', 'repository_id',
              'commit', 'authorization_ref', 'base_image_sha256', 'files', 'checks', 'limits')
    _keys(envelope, fields)
    _keys(admission, fields)
    try:
        encoded = json.dumps(envelope, sort_keys=True, allow_nan=False).encode('utf-8')
        approved = json.dumps(admission, sort_keys=True, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError('Manifest must be plain JSON') from exc
    _require(len(encoded) <= 131072 and len(approved) <= 131072, 'Manifest size exceeded')
    _require(encoded == approved, 'Manifest differs from host admission')
    # Validate the detached JSON we compared, not a caller-mutable structure.
    envelope = json.loads(encoded)
    _require(type(envelope['schema_version']) is int and envelope['schema_version'] in (1, 2),
             'Unsupported envelope version')
    for name in ('task_id', 'request_id', 'attempt_id', 'repository_id', 'authorization_ref'):
        _hex(envelope[name], (32,))
    _hex(envelope['commit'], (40, 64))
    _hex(envelope['base_image_sha256'], (64,))
    files = envelope['files']
    _require(type(files) is list and 1 <= len(files) <= 20 and type(contents) is dict,
             'Expected 1-20 files and a byte mapping')
    names = set()
    paths = set()
    total = 0
    for entry in files:
        _keys(entry, ('relative_path', 'length', 'sha256', 'role'))
        name = entry['relative_path']
        normalized = _path(name)
        _require(normalized not in names, 'Duplicate or case-colliding file path')
        names.add(normalized)
        paths.add(name)
        _require(entry['role'] in ('editable', 'verification', 'dependency'), 'Invalid file role')
        _hex(entry['sha256'], (64,))
        _require(type(entry['length']) is int and 0 <= entry['length'] <= 2097152,
                 'Invalid file length')
        data = contents.get(name)
        _require(type(data) is bytes and len(data) == entry['length'], 'Missing or altered input bytes')
        _require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'Input digest mismatch')
        total += len(data)
        _require(total <= 16777216, 'Total input size exceeded')
    _require(set(contents) == paths, 'Unexpected input files')
    checks = envelope['checks']
    _require(type(checks) is list and 1 <= len(checks) <= 10, 'Expected 1-10 fixed checks')
    check_ids = set()
    for check in checks:
        _keys(check, ('check_id', 'argv'))
        name = check['check_id']
        _require(type(name) is str and re.fullmatch('[a-z0-9_-]{1,64}', name) is not None
                 and name not in check_ids, 'Invalid or duplicate check identity')
        check_ids.add(name)
        argv = check['argv']
        _require(type(argv) is list and 3 <= len(argv) <= 64 and
                 all(type(a) is str and len(a) <= 1024 and '\x00' not in a for a in argv),
                 'Unsupported verification command')
        if envelope['schema_version'] == 1:
            _require(argv[:3] == ['python', '-m', 'unittest'], 'Unsupported verification command')
    limits = envelope['limits']
    _keys(limits, ('check_seconds', 'total_seconds', 'output_bytes'))
    for name, low, high in [('check_seconds', 1, 120), ('total_seconds', 1, 600),
                            ('output_bytes', 1024, 1048576)]:
        _require(type(limits[name]) is int and low <= limits[name] <= high, 'Invalid execution limit')
    _require(limits['check_seconds'] <= limits['total_seconds'], 'Check exceeds task deadline')
    if envelope['schema_version'] == 2:
        _validate_project_inputs(files, contents, checks)
    return json.loads(encoded)
