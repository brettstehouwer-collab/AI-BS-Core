"""Stage an admitted byte set without scanning or modifying source repositories.

Windows only. The controller must supply an authenticated, host-approved
admission and an existing private transfer root with suitable ACLs. This module
does not establish that authorization, scan arbitrary source text for secrets,
decode untrusted wire messages, launch a guest, or issue verification seals.
"""
from __future__ import annotations

from contextlib import contextmanager, ExitStack
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

from .coding_vm_inputs import validate_vm_inputs


class _FileInformation(ctypes.Structure):
    _fields_ = [
        ('attributes', wintypes.DWORD), ('creation', wintypes.FILETIME),
        ('access', wintypes.FILETIME), ('write', wintypes.FILETIME),
        ('volume', wintypes.DWORD), ('size_high', wintypes.DWORD),
        ('size_low', wintypes.DWORD), ('links', wintypes.DWORD),
        ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD),
    ]


@contextmanager
def _locked_directory(path):
    """Open the directory itself and deny write/delete sharing while in use.

    OPEN_REPARSE_POINT prevents following the final path component. Every
    ancestor is opened in order and held too, preventing rename/reparse swaps.
    The transfer root must additionally be protected by controller-owned ACLs.
    """
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    get_info = kernel.GetFileInformationByHandle
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(_FileInformation)]
    get_info.restype = wintypes.BOOL
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    # GENERIC_READ, FILE_SHARE_READ, OPEN_EXISTING,
    # FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT.
    handle = create('\\\\?\\' + str(path), 0x80000000, 1, None, 3, 0x02200000, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()
        if error in (2, 3):
            raise FileNotFoundError(str(path))
        raise ctypes.WinError(error)
    try:
        info = _FileInformation()
        if not get_info(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if info.attributes & 0x400:
            raise ValueError('Reparse-point staging directory rejected')
        if not info.attributes & 0x10:
            raise NotADirectoryError(str(path))
        yield handle
    finally:
        close(handle)


def _write_new_file(path, data):
    """Exclusive creation: an existing file/link is never opened or replaced."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_BINARY | os.O_NOINHERIT
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Expected a newly created regular staging file')
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode('utf-8')


def stage_vm_inputs(transfer_root, envelope, contents, admission):
    """Write only validated bytes into a fresh retained task/attempt directory.

    Validation happens before mutation. Failed/partial attempts remain present
    without a staged.json completion record, and repeated attempts are rejected.
    No source paths are opened. A future guest adapter must rehash the payload
    before consuming it; STAGED is not evidence of execution or VM isolation.
    """
    if os.name != 'nt':
        raise NotImplementedError('Windows handle protection is required')
    frozen = dict(contents)
    manifest = validate_vm_inputs(envelope, frozen, admission)
    names = {entry['relative_path'].casefold() for entry in manifest['files']}
    for name in names:
        parts = name.split('/')
        if any('/'.join(parts[:index]) in names for index in range(1, len(parts))):
            raise ValueError('File/directory path collision')
    root = Path(transfer_root)
    if not root.is_absolute() or len(root.drive) != 2 or root.drive[1] != ':':
        raise ValueError('Expected an absolute local transfer directory')
    # Lexical normalization only; never resolve a junction before checking it.
    root = Path(os.path.abspath(root))
    job = root / (manifest['task_id'] + '_' + manifest['attempt_id'])
    encoded = _json_bytes(manifest)
    identity = {
        'schema_version': 1, 'task_id': manifest['task_id'],
        'request_id': manifest['request_id'], 'attempt_id': manifest['attempt_id'],
        'input_manifest_sha256': hashlib.sha256(encoded).hexdigest(),
    }
    with ExitStack() as locks:
        for parent in reversed((root, *root.parents)):
            locks.enter_context(_locked_directory(parent))
        # Atomic admission to a new attempt; no overwrite or automatic retry.
        os.mkdir(job)
        locks.enter_context(_locked_directory(job))
        _write_new_file(job / 'staging.json', _json_bytes(dict(identity, state='STAGING',
                        created_at=datetime.now(timezone.utc).isoformat())))
        _write_new_file(job / 'admission.json', encoded)
        payload = job / 'payload'
        os.mkdir(payload)
        locks.enter_context(_locked_directory(payload))
        opened = {payload}
        for entry in manifest['files']:
            parts = entry['relative_path'].split('/')
            directory = payload
            for part in parts[:-1]:
                directory = directory / part
                if directory not in opened:
                    os.mkdir(directory)
                    locks.enter_context(_locked_directory(directory))
                    opened.add(directory)
            _write_new_file(directory / parts[-1], frozen[entry['relative_path']])
        ready = dict(identity, state='STAGED', file_count=len(manifest['files']),
                     byte_count=sum(len(data) for data in frozen.values()),
                     completed_at=datetime.now(timezone.utc).isoformat())
        _write_new_file(job / 'staged.json', _json_bytes(ready))
    return dict(ready, directory=str(job))
