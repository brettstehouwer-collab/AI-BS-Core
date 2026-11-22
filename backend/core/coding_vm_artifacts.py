"""Pure validation of returned file bytes, never proof of successful execution.

The admission must be a previously validated, trusted host manifest. Transport
must enforce wire limits and regular-file/reparse rules before collecting bytes.
This function performs no I/O and grants no review seal or apply permission.
"""
from __future__ import annotations

import hashlib
import json

from .coding_vm_inputs import _hex, _keys, _path, _require


def validate_vm_artifacts(envelope, contents, admission):
    """Bind output files to one admitted attempt and preserve protected inputs."""
    _keys(envelope, ('schema_version', 'task_id', 'request_id', 'attempt_id',
                     'base_image_sha256', 'input_manifest_sha256', 'files'))
    try:
        raw = json.dumps(envelope, sort_keys=True, allow_nan=False).encode('utf-8')
        admitted = json.dumps(admission, sort_keys=True, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError('Artifact manifest must be plain JSON') from exc
    _require(len(raw) <= 131072 and len(admitted) <= 131072, 'Manifest size exceeded')
    _require(type(envelope['schema_version']) is int and envelope['schema_version'] == 1,
             'Unsupported artifact version')
    for name, sizes in [('task_id', (32,)), ('request_id', (32,)), ('attempt_id', (32,)),
                        ('base_image_sha256', (64,))]:
        _hex(envelope[name], sizes)
        _require(envelope[name] == admission[name], 'Artifact belongs to another admission')
    _hex(envelope['input_manifest_sha256'], (64,))
    _require(envelope['input_manifest_sha256'] == hashlib.sha256(admitted).hexdigest(),
             'Artifact input manifest differs from admission')
    approved = {entry['relative_path']: entry for entry in admission['files']}
    files = envelope['files']
    _require(type(files) is list and 1 <= len(files) <= 20 and type(contents) is dict,
             'Expected bounded artifact records and bytes')
    seen, paths, total = set(), set(), 0
    for entry in files:
        _keys(entry, ('relative_path', 'length', 'sha256'))
        name = entry['relative_path']
        normalized = _path(name)
        _require(normalized not in seen and name in approved, 'Unexpected or duplicate artifact')
        seen.add(normalized)
        paths.add(name)
        _hex(entry['sha256'], (64,))
        _require(type(entry['length']) is int and 0 <= entry['length'] <= 2097152,
                 'Invalid artifact length')
        data = contents.get(name)
        _require(type(data) is bytes and len(data) == entry['length'], 'Missing or altered artifact bytes')
        _require(hashlib.sha256(data).hexdigest() == entry['sha256'], 'Artifact digest mismatch')
        source = approved[name]
        _require(source['role'] in ('editable', 'verification', 'dependency'), 'Invalid admitted role')
        if source['role'] != 'editable':
            _require(entry['sha256'] == source['sha256'] and entry['length'] == source['length'],
                     'Immutable verification or dependency input was changed')
        total += len(data)
        _require(total <= 16777216, 'Total artifact size exceeded')
    _require(paths == set(approved) == set(contents), 'Incomplete or unexpected artifact set')
    return json.loads(raw)
