"""Explicit read-only private generation admission; inert until called.

No environment lookup, legacy fallback, key generation, decryption, publication
or consumer hookup. The root is supplied by trusted host configuration.
"""
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

_GENERATION = re.compile(r'[0-9a-f]{32}')
_HASH = re.compile(r'[0-9a-f]{64}')
_LIMITS = {'key.bin': 44, 'root.env': 2*1024*1024, 'backend.env': 2*1024*1024}


class VaultBundleError(ValueError):
    """Safe admission failure; never includes private paths or contents."""


@dataclass(frozen=True)
class VaultGeneration:
    generation: str
    key: bytes = field(repr=False)
    root_config: bytes = field(repr=False)
    backend_config: bytes = field(repr=False)


def _object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise VaultBundleError('Duplicate bundle metadata is unsupported.')
        result[name] = value
    return result


def _json(raw):
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=_object)
    if not isinstance(value, dict):
        raise VaultBundleError('Bundle metadata must be an object.')
    return value


def _private_directory(path):
    from native_studio.screenplay_client import _private_recovery_directory
    # The existing helper may create a missing folder; this reader never asks it
    # to do so. Directory handles remain pinned by the caller during validation.
    if not path.is_dir():
        raise VaultBundleError('The configured private bundle is unavailable.')
    _private_recovery_directory(path, path.parent)


@contextmanager
def _read_member(directory, name, limit):
    from security.contained_file_access import _windows_io, _normal_handle_path, _file_from_handle
    import win32security
    from native_studio.local_connection import _current_identity
    _, _, flags, native = _windows_io()
    path = directory/name
    handle = native.CreateFile(str(path), flags.GENERIC_READ | 0x00020000,
        flags.FILE_SHARE_READ, None, flags.OPEN_EXISTING, 0x00200000, None)
    try:
        info = native.GetFileInformationByHandle(handle)
        if info[0] & (0x400 | 0x10) or info[7] != 1:
            raise VaultBundleError('Bundle members must be regular, unlinked files.')
        if _normal_handle_path(native.GetFinalPathNameByHandle(handle, 0)) != _normal_handle_path(str(path)):
            raise VaultBundleError('Bundle file identity changed.')
        allowed = {_current_identity().owner_sid, 'S-1-5-18', 'S-1-5-32-544'}
        descriptor = win32security.GetSecurityInfo(handle, win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION)
        acl = descriptor.GetSecurityDescriptorDacl()
        if acl is None or not acl.GetAceCount():
            raise VaultBundleError('Private bundle file permissions are required.')
        for index in range(acl.GetAceCount()):
            ace = acl.GetAce(index)
            if ace[0][0] != win32security.ACCESS_ALLOWED_ACE_TYPE or win32security.ConvertSidToStringSid(ace[2]) not in allowed:
                raise VaultBundleError('Bundle file permissions exceed the private allowlist.')
        # Keep this exact immutable read handle alive until the entire generation
        # is admitted. No write/delete sharing; selector cannot change mid-load.
        with _file_from_handle(handle, 'rb') as stream:
            raw = stream.read(limit+1)
            if len(raw) > limit:
                raise VaultBundleError('A bundle member exceeds its bound.')
            yield raw
    finally:
        if int(handle):
            handle.Close()


def _generation_snapshot(stack, directory, generation):
    """Validate a caller-bound generation while retaining all member handles."""
    from security.contained_file_access import _pinned_directory
    selected = stack.enter_context(_pinned_directory(directory/generation))
    _private_directory(selected)
    raw_manifest = stack.enter_context(_read_member(selected, 'manifest.json', 4096))
    manifest = _json(raw_manifest)
    if (set(manifest) != {'schema', 'generation', 'files'} or type(manifest['schema']) is not int
            or manifest['schema'] != 1 or manifest['generation'] != generation
            or not isinstance(manifest['files'], dict) or set(manifest['files']) != set(_LIMITS)):
        raise VaultBundleError('Incomplete or mixed-generation manifest.')
    values = {}
    for name, limit in _LIMITS.items():
        row = manifest['files'][name]
        if (not isinstance(row, dict) or set(row) != {'bytes', 'sha256'}
                or type(row['bytes']) is not int or not 0 <= row['bytes'] <= limit
                or not isinstance(row['sha256'], str) or not _HASH.fullmatch(row['sha256'])):
            raise VaultBundleError('Invalid member fingerprint.')
        raw = stack.enter_context(_read_member(selected, name, limit))
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise VaultBundleError('Bundle member integrity failed.')
        values[name] = raw
    from cryptography.fernet import Fernet
    Fernet(values['key.bin'])
    return VaultGeneration(generation, values['key.bin'], values['root.env'], values['backend.env']), hashlib.sha256(raw_manifest).hexdigest()


def load_private_generation(root, *, expected_generation=None):
    """Return one immutable raw snapshot, or fail without fallback or writes.

    Secrets are excluded from repr. Callers must keep the returned snapshot
    private; this function grants no execution, publication or migration rights.
    """
    try:
        if expected_generation is not None and (not isinstance(expected_generation, str)
                or not _GENERATION.fullmatch(expected_generation)):
            raise VaultBundleError('Invalid expected generation.')
        path = Path(root)
        if not path.is_absolute() or '..' in path.parts or str(path).startswith(('\\\\', '//')):
            raise VaultBundleError('An explicit local private root is required.')
        from security.contained_file_access import _pinned_directory
        with ExitStack() as stack:
            directory = stack.enter_context(_pinned_directory(path))
            _private_directory(directory)
            selector = _json(stack.enter_context(_read_member(directory, 'current.json', 4096)))
            if set(selector) != {'schema', 'generation'} or type(selector['schema']) is not int or selector['schema'] != 1:
                raise VaultBundleError('Unsupported selector schema.')
            generation = selector['generation']
            if not isinstance(generation, str) or not _GENERATION.fullmatch(generation):
                raise VaultBundleError('Invalid selected generation.')
            if expected_generation is not None and generation != expected_generation:
                raise VaultBundleError('The selected generation changed.')
            return _generation_snapshot(stack, directory, generation)[0]
    except VaultBundleError:
        raise
    except Exception:
        raise VaultBundleError('The private bundle is unavailable or invalid.') from None
