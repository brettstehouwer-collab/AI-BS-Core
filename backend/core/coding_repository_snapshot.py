"""Capture selected Windows repository bytes before future host admission.

No API, model call, staging write or project execution. The trusted caller owns
authentication and the repository allowlist; this helper grants no authority.
"""
from contextlib import ExitStack, contextmanager
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from .coding_vm_inputs import _path
from .coding_vm_staging import _FileInformation, _locked_directory
from .personal_memory_scope import is_sensitive_memory_text

MAX_FILE_BYTES = 2097152
MAX_TOTAL_BYTES = 16777216
GIT_EXE = r'C:\Program Files\Git\cmd\git.exe'


def _root(value):
    if not isinstance(value,(str,os.PathLike)):
        raise ValueError('An absolute local repository scope is required')
    path = Path(value)
    if not path.is_absolute() or len(path.drive) != 2 or path.drive[1] != ':':
        raise ValueError('An absolute local repository scope is required')
    path = Path(os.path.abspath(path))
    if path.parts[1:]:
        _path('/'.join(path.parts[1:]))
    return path


def _selection(value):
    if type(value) is not list or not 1 <= len(value) <= 20:
        raise ValueError('Select between 1 and 20 source files')
    entries, names = [], set()
    for entry in value:
        if type(entry) is not dict or set(entry) != {'relative_path','role'}:
            raise ValueError('Unexpected source selection fields')
        name = entry['relative_path']
        canonical = _path(name)
        if canonical in names:
            raise ValueError('Duplicate or case-colliding source selection')
        names.add(canonical)
        if type(entry['role']) is not str or entry['role'] not in {'editable','verification','dependency'}:
            raise ValueError('Unsupported source role')
        if any(part in {'node_modules','.venv','venv','__pycache__','.npm','.npmrc','.pypirc','.netrc'} for part in canonical.split('/')):
            raise ValueError('Runtime, cache and credential paths are excluded')
        entries.append(dict(relative_path=name,role=entry['role']))
    if any('/'.join(name.split('/')[:i]) in names for name in names for i in range(1,len(name.split('/')))):
        raise ValueError('Source file/directory path collision')
    return entries


def _git_head(repository):
    # Fixed installed Git, explicit directories and no user/project commands.
    environment = {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP','PATH','PATHEXT'}}
    environment.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_SYSTEM=os.devnull)
    try:
        result = subprocess.run([GIT_EXE,'--no-optional-locks','--no-pager','--no-replace-objects',
            '-c','core.hooksPath=NUL','-c','core.fsmonitor=false','--git-dir=' + str(repository / '.git'),
            '--work-tree=' + str(repository),'rev-parse','--verify','HEAD^{commit}'],
            cwd=repository,env=environment,stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError,subprocess.TimeoutExpired):
        raise ValueError('Repository commit could not be confirmed') from None
    if result.returncode or len(result.stdout) > 66:
        raise ValueError('Repository commit could not be confirmed')
    try:
        commit = result.stdout.decode('ascii').strip()
    except UnicodeError:
        raise ValueError('Repository commit is invalid') from None
    if re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})',commit) is None:
        raise ValueError('Repository commit is invalid')
    return commit


@contextmanager
def _source_handle(path):
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    info_call = kernel.GetFileInformationByHandle
    info_call.argtypes = [wintypes.HANDLE,ctypes.POINTER(_FileInformation)]
    info_call.restype = wintypes.BOOL
    file_type = kernel.GetFileType
    file_type.argtypes = [wintypes.HANDLE]
    file_type.restype = wintypes.DWORD
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    # Read only; deny write/delete sharing; open final reparse point itself.
    handle = create('\\\\?\\' + str(path),0x80000000,1,None,3,0x00200000,None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = _FileInformation()
        if not info_call(handle,ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if file_type(handle) != 1 or info.attributes & 0x410 or info.links != 1:
            raise ValueError('Expected a singly linked regular source file')
        length = (info.size_high << 32) | info.size_low
        if length > MAX_FILE_BYTES:
            raise ValueError('Selected source exceeds the 2 MiB limit')
        yield handle,length
    finally:
        close(handle)


def _read_bytes(handle,length):
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    read = kernel.ReadFile
    read.argtypes = [wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID]
    read.restype = wintypes.BOOL
    buffer = ctypes.create_string_buffer(length + 1)
    count = wintypes.DWORD()
    if not read(handle,buffer,length + 1,ctypes.byref(count),None):
        raise ctypes.WinError(ctypes.get_last_error())
    if count.value != length:
        raise ValueError('Selected source changed during capture')
    return buffer.raw[:length]


def capture_repository_snapshot(repository,selected_files,*,allowed_roots):
    """Return (snapshot, bytes) without authorizing, staging or executing them.

    `allowed_roots` MUST come from authenticated server policy, never a model
    or HTTP body. A later controller must bind this capture to exact admitted
    identities/checks/image/limits and apply the existing schema2 validator.
    """
    if os.name != 'nt':
        raise NotImplementedError('Windows held-file protection is required')
    repo = _root(repository)
    if type(allowed_roots) not in (list,tuple) or not 1 <= len(allowed_roots) <= 32:
        raise ValueError('A trusted repository allowlist is required')
    roots = [_root(p) for p in allowed_roots]
    if not any(repo.is_relative_to(p) for p in roots):
        raise ValueError('Repository is outside the admitted host scope')
    entries = _selection(selected_files)
    contents,files = {},[]
    with ExitStack() as locks:
        opened = set()
        def lock_directory(path):
            for directory in reversed((path,*path.parents)):
                if directory not in opened:
                    locks.enter_context(_locked_directory(directory))
                    opened.add(directory)
        lock_directory(repo)
        # Primary repositories only. Do not follow linked metadata elsewhere.
        lock_directory(repo / '.git')
        head = _git_head(repo)
        handles,total = [],0
        for entry in entries:
            source = repo.joinpath(*entry['relative_path'].split('/'))
            lock_directory(source.parent)
            handle,length = locks.enter_context(_source_handle(source))
            total += length
            if total > MAX_TOTAL_BYTES:
                raise ValueError('Selected sources exceed the 16 MiB total limit')
            handles.append((entry,handle,length))
        # All selected read handles are held together before reading any bytes.
        for entry,handle,length in handles:
            data = _read_bytes(handle,length)
            try:
                text = data.decode('utf-8')
            except UnicodeError:
                raise ValueError('Only reviewed UTF8 source text can be captured') from None
            if '\x00' in text or is_sensitive_memory_text(text):
                raise ValueError('Binary or recognized credential-bearing source was excluded; original retained')
            contents[entry['relative_path']] = data
            files.append(dict(entry,length=length,sha256=hashlib.sha256(data).hexdigest()))
        if _git_head(repo) != head:
            raise ValueError('Repository HEAD changed during source capture')
    record = dict(schema_version=1,state='SNAPSHOT_ONLY',authorized=False,executed=False,
                  commit=head,files=files,byte_count=total,captured_at_utc=datetime.now(timezone.utc).isoformat())
    record['snapshot_sha256'] = hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
    return record,contents
