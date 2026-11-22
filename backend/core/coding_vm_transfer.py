"""Adapt admitted project bytes to bounded opaque transfer files.

No I/O, authentication, runtime invocation or authority is provided here. The
caller supplies a previously authenticated host admission and transports every
part through the existing confidential, authenticated, replay-protected boundary.
Original project names remain manifest data; they never select transport paths.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from typing import Mapping

from .coding_vm_inputs import validate_vm_inputs, _hex, _keys, _path, _require
from .coding_vm_artifacts import validate_vm_artifacts

PART_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 262144
MAX_FILES = 20
MAX_FILE_BYTES = 2 * PART_BYTES
MAX_TOTAL_BYTES = 16 * PART_BYTES
DOMAIN = b'AI-BS/task-transfer/v1\x00'
# Preserve the existing codec/native private-store exclusions even though
# physical transport names are opaque. This does not detect secrets in content.
PRIVATE_STORE_SUFFIXES = ('.db', '.sqlite', '.sqlite3', '.db-wal', '.db-shm',
                          '.pem', '.key', '.pfx', '.vdi', '.gguf', '.safetensors')


def _encoded(value):
    try:
        return json.dumps(value, sort_keys=True, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError):
        raise ValueError('Transfer metadata must be plain JSON') from None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'Duplicate transfer metadata field')
        result[key] = value
    return result


def _constant(_):
    raise ValueError('Nonfinite transfer metadata')


def _logical_path(name):
    folded = _path(name)
    _require(not any(part.lower().endswith(PRIVATE_STORE_SUFFIXES) for part in name.split('/')),
             'Private store or model path excluded')
    return folded


def _scope(admission, direction):
    _require(direction in ('host_to_guest', 'guest_to_host'), 'Unsupported transfer direction')
    raw = _encoded(admission)
    _require(len(raw) <= 131072, 'Admission manifest size exceeded')
    _require(type(admission) is dict, 'Host admission required')
    for field in ('task_id', 'request_id', 'attempt_id'):
        _hex(admission.get(field), (32,))
    _hex(admission.get('base_image_sha256'), (64,))
    digest = hashlib.sha256(raw).hexdigest()
    identity = hashlib.sha256(DOMAIN + direction.encode('ascii') + digest.encode('ascii')).hexdigest()[:32]
    prefix = ('inputs/' if direction == 'host_to_guest' else 'outputs/') + identity
    return digest, identity, prefix


def _layout(envelope, admission, direction, prefix):
    """Check all metadata bounds before accepting or concatenating part bytes."""
    _require(type(envelope) is dict, 'Transfer envelope required')
    approved = None
    if direction == 'host_to_guest':
        _require(_encoded(envelope) == _encoded(admission), 'Transfer differs from host admission')
    else:
        _keys(envelope, ('schema_version', 'task_id', 'request_id', 'attempt_id',
                         'base_image_sha256', 'input_manifest_sha256', 'files'))
        _require(type(envelope['schema_version']) is int and envelope['schema_version'] == 1,
                 'Unsupported artifact version')
        for field in ('task_id', 'request_id', 'attempt_id', 'base_image_sha256'):
            _require(envelope[field] == admission[field], 'Artifact belongs to another admission')
        _require(envelope['input_manifest_sha256'] == hashlib.sha256(_encoded(admission)).hexdigest(),
                 'Artifact input binding mismatch')
        admitted_files = admission.get('files')
        _require(type(admitted_files) is list and 1 <= len(admitted_files) <= MAX_FILES,
                 'Previously validated host file admission required')
        approved = {}
        for source in admitted_files:
            _keys(source, ('relative_path', 'length', 'sha256', 'role'))
            name = source['relative_path']
            _logical_path(name)
            _require(name not in approved, 'Duplicate admitted artifact path')
            _require(source['role'] in ('editable', 'verification', 'dependency'), 'Invalid admitted role')
            approved[name] = source
    files = envelope.get('files')
    _require(type(files) is list and 1 <= len(files) <= MAX_FILES, 'Expected 1-20 transfer files')
    seen = set()
    descriptions = []
    total = 0
    for index, entry in enumerate(files):
        fields = ('relative_path', 'length', 'sha256', 'role') if direction == 'host_to_guest' else ('relative_path', 'length', 'sha256')
        _keys(entry, fields)
        folded = _logical_path(entry['relative_path'])
        try:
            entry['relative_path'].encode('utf-8', errors='strict')
        except UnicodeError:
            raise ValueError('Invalid Unicode project path') from None
        _require(folded not in seen, 'Project path alias collision')
        seen.add(folded)
        size = entry['length']
        _require(type(size) is int and 0 <= size <= MAX_FILE_BYTES, 'Project file size exceeded')
        _hex(entry['sha256'], (64,))
        if approved is not None:
            _require(entry['relative_path'] in approved, 'Unexpected artifact path')
            source = approved[entry['relative_path']]
            if source['role'] != 'editable':
                _require(size == source['length'] and entry['sha256'] == source['sha256'],
                         'Immutable verification or dependency metadata was changed')
        total += size
        _require(total <= MAX_TOTAL_BYTES, 'Project total size exceeded')
        count = max(1, (size + PART_BYTES - 1) // PART_BYTES)
        for part in range(count):
            descriptions.append(dict(path=f'{prefix}/file_{index:02d}_{part:02d}.bin',
                                     file_index=index, part_index=part,
                                     length=min(PART_BYTES, max(0, size - part * PART_BYTES))))
    for name in seen:
        parts = name.split('/')
        _require(not any('/'.join(parts[:index]) in seen for index in range(1, len(parts))),
                 'File/directory project path collision')
    if approved is not None:
        _require({entry['relative_path'] for entry in files} == set(approved),
                 'Incomplete artifact file set')
    return descriptions


@dataclass(frozen=True)
class TransferPlan:
    manifest_path: str
    manifest_bytes: bytes
    chunks: Mapping[str, bytes]

    @property
    def transport_files(self):
        return MappingProxyType({self.manifest_path:self.manifest_bytes, **self.chunks})

    @property
    def execution_authorized(self):
        return False

    @property
    def apply_authorized(self):
        return False


@dataclass(frozen=True)
class TransferInspection:
    """Checked metadata for deciding which parts to collect; never a task grant."""
    manifest_path: str
    manifest_bytes: bytes
    parts: tuple

    @property
    def envelope(self):
        # Return a detached view, so consumers cannot alter the checked record.
        return json.loads(self.manifest_bytes)['envelope']

    @property
    def worker_admitted(self):
        return False

    @property
    def execution_authorized(self):
        return False

    @property
    def apply_authorized(self):
        return False

    @property
    def verification_status(self):
        return 'not_run'


@dataclass(frozen=True)
class RestoredTransfer:
    envelope: dict
    contents: Mapping[str, bytes]

    @property
    def execution_authorized(self):
        return False

    @property
    def apply_authorized(self):
        return False

    @property
    def verification_status(self):
        return 'not_run'


def prepare_vm_transfer(envelope, contents, admission, *, direction):
    """Validate the original contract, then split only explicitly supplied bytes."""
    digest, identity, prefix = _scope(admission, direction)
    _require(type(contents) is dict, 'Explicit project byte mapping required')
    contents = dict(contents)
    validate = validate_vm_inputs if direction == 'host_to_guest' else validate_vm_artifacts
    envelope = validate(envelope, contents, admission)
    descriptions = _layout(envelope, admission, direction, prefix)
    chunks = {}
    parts = []
    for description in descriptions:
        file = envelope['files'][description['file_index']]
        start = description['part_index'] * PART_BYTES
        data = contents[file['relative_path']][start:start + description['length']]
        chunks[description['path']] = data
        parts.append(dict(description, sha256=hashlib.sha256(data).hexdigest()))
    manifest = dict(version=1, direction=direction, transfer_id=identity,
                    input_manifest_sha256=digest, envelope=envelope, parts=parts)
    raw = _encoded(manifest)
    _require(len(raw) <= MAX_MANIFEST_BYTES, 'Transport manifest size exceeded')
    return TransferPlan(prefix+'/manifest.json', raw, MappingProxyType(chunks))


def inspect_vm_transfer(manifest_bytes, admission, *, direction):
    """Validate bounded metadata before requesting or materializing any parts.

    The admission is previously authenticated host policy, not a guest copy.
    Authentication, actual bytes, native file identity and execution authorization
    remain separate requirements. This function performs no I/O or byte joins.
    """
    _require(type(manifest_bytes) is bytes and 0 < len(manifest_bytes) <= MAX_MANIFEST_BYTES,
             'Transport manifest byte bound')
    try:
        manifest = json.loads(manifest_bytes.decode('utf-8'), object_pairs_hook=_unique,
                              parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('Transport manifest rejected') from None
    _require(_encoded(manifest) == manifest_bytes, 'Noncanonical transport manifest')
    _keys(manifest, ('version','direction','transfer_id','input_manifest_sha256','envelope','parts'))
    _require(type(manifest['version']) is int and manifest['version'] == 1, 'Unsupported transport version')
    digest, identity, prefix = _scope(admission, direction)
    _require(manifest['direction'] == direction and manifest['transfer_id'] == identity and
             manifest['input_manifest_sha256'] == digest, 'Transfer admission binding mismatch')
    envelope = manifest['envelope']
    descriptions = _layout(envelope, admission, direction, prefix)
    parts = manifest['parts']
    _require(type(parts) is list and len(parts) == len(descriptions) <= 40, 'Transport part count mismatch')
    for expected, part in zip(descriptions, parts):
        _keys(part, ('path','file_index','part_index','length','sha256'))
        for field in ('file_index','part_index','length'):
            _require(type(part[field]) is int, 'Integer part metadata required')
        _require(all(part[field] == value for field, value in expected.items()), 'Transport part layout mismatch')
        _hex(part['sha256'], (64,))
    return TransferInspection(prefix+'/manifest.json', manifest_bytes,
                              tuple(MappingProxyType(dict(part)) for part in parts))


def restore_vm_transfer(manifest_bytes, chunks, admission, *, direction):
    """Accept exactly one complete admitted transfer; never materialize a path.

    Missing/extra/altered parts fail without a completion or execution claim.
    A collector must retain partial bytes and independently enforce native file
    identity, caller/root authority and durable transfer/replay state.
    """
    _require(type(chunks) is dict, 'Explicit transport part mapping required')
    inspected = inspect_vm_transfer(manifest_bytes, admission, direction=direction)
    envelope = inspected.envelope
    _require(set(chunks) == {part['path'] for part in inspected.parts}, 'Missing or unexpected transport part')
    grouped = [[] for _ in envelope['files']]
    for part in inspected.parts:
        data = chunks[part['path']]
        _require(type(data) is bytes and len(data) == part['length'] <= PART_BYTES,
                 'Transport part byte bound')
        _require(hashlib.sha256(data).hexdigest() == part['sha256'], 'Transport part hash mismatch')
        grouped[part['file_index']].append(data)
    contents = {entry['relative_path']:b''.join(grouped[index]) for index, entry in enumerate(envelope['files'])}
    validate = validate_vm_inputs if direction == 'host_to_guest' else validate_vm_artifacts
    validated = validate(envelope, contents, admission)
    return RestoredTransfer(validated, MappingProxyType(contents))
