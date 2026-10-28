"""Isolated VM guest check runners for the AI-BS coding workflow.

Supports two hardware-virtualized guest execution providers with zero host-process
fallback:
1. ``vbox_windows``: Headless VirtualBox Windows VM via ``VBoxManage guestcontrol``
   from a clean offline snapshot with NICs, clipboard, drag-and-drop, and shared
   folders disabled, using DPAPI-protected guest credentials.
2. ``wsl2_isolated``: Hyper-V / WSL2 Linux utility VM executing inside unshared
   mount, network, IPC, UTS, and PID namespaces with ``/mnt``, ``/run``, and
   ``binfmt_misc`` masked by read-only ``tmpfs``, ephemeral RAM ``/tmp``,
   ``nobody:nogroup`` (65534:65534) zero-capability drop, and an ``x86_64``
   ``seccomp-bpf`` syscall filter blocking ``AF_VSOCK``, ``AF_INET``, and ``AF_INET6``.

Neither provider ever falls back to ``coding_process.run_bounded_check`` on the host.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import fnmatch
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import threading
import time
import uuid

import psutil

from .coding_locks import record_lock

CONFIG_DIR = Path(__file__).resolve().parents[2] / 'saved_data' / 'vm_runner_config'
VBOX_CONFIG_FILE = CONFIG_DIR / 'vbox_guest_config.json'
VBOX_PASSWORD_FILE = CONFIG_DIR / 'vbox_guest_password.dpapi'
VBOX_LOCK_FILE = CONFIG_DIR / 'vbox_runner.lock'

SUPPORTED_EXECUTION_BACKENDS = ('trusted_host', 'wsl2_vm', 'windows_vm')

_EXCLUDED_PATTERNS = (
    '.git',
    '.git/*',
    '.env',
    '.env.*',
    '*.env',
    '*.pem',
    '*.key',
    '*.pfx',
    '*.p12',
    '*.dpapi',
    '*.kdbx',
    '*.db',
    '*.sqlite',
    '*.sqlite3',
    '*.sqlite-*',
    'saved_data/*',
    'backups/*',
    'credentials/*',
    'private/*',
    'node_modules/*',
    '__pycache__/*',
    '*.pyc',
)

_MAX_SINGLE_FILE_BYTES = 2 * 1024 * 1024
_MAX_BUNDLE_BYTES = 32 * 1024 * 1024


class CodingExecutionPolicyError(RuntimeError):
    """Raised when an execution backend cannot run under current security policy."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ('true', '1', 'yes', 'on')


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_char)),
    ]


def dpapi_encrypt(plaintext: bytes) -> bytes:
    """Encrypt bytes with Windows DPAPI scoped to the current Windows user."""
    if not isinstance(plaintext, (bytes, bytearray)) or not plaintext:
        raise ValueError('Non-empty bytes required for DPAPI encryption')
    if os.name != 'nt':
        raise RuntimeError('Windows DPAPI is only available on Windows')
    try:
        import win32crypt
        return bytes(win32crypt.CryptProtectData(bytes(plaintext), 'AI-BS-VBoxGuest', None, None, None, 0x01))
    except ImportError:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        buf = ctypes.create_string_buffer(bytes(plaintext), len(plaintext))
        in_blob = _DataBlob(len(plaintext), buf)
        out_blob = _DataBlob()
        if not crypt32.CryptProtectData(ctypes.byref(in_blob), 'AI-BS-VBoxGuest', None, None, None, 0x01, ctypes.byref(out_blob)):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)


def dpapi_decrypt(ciphertext: bytes) -> bytes:
    """Decrypt Windows DPAPI bytes scoped to the current Windows user."""
    if not isinstance(ciphertext, (bytes, bytearray)) or not ciphertext:
        raise ValueError('Non-empty bytes required for DPAPI decryption')
    if os.name != 'nt':
        raise RuntimeError('Windows DPAPI is only available on Windows')
    try:
        import win32crypt
        _, data = win32crypt.CryptUnprotectData(bytes(ciphertext), None, None, None, 0x01)
        return bytes(data)
    except ImportError:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        buf = ctypes.create_string_buffer(bytes(ciphertext), len(ciphertext))
        in_blob = _DataBlob(len(ciphertext), buf)
        out_blob = _DataBlob()
        if not crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0x01, ctypes.byref(out_blob)):
            raise ctypes.WinError()
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)


def _is_excluded_relpath(posix_rel: str) -> bool:
    low = posix_rel.lower()
    parts = low.split('/')
    if any(p in ('.git', '__pycache__', 'node_modules') for p in parts):
        return True
    for pattern in _EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(low, pattern) or fnmatch.fnmatch(parts[-1], pattern):
            return True
    return False


def collect_worktree_files(
    worktree: Path,
    required_paths: tuple[str, ...] | list[str] = (),
) -> list[tuple[str, bytes]]:
    """Collect tracked and required relative files from a detached Git worktree.

    Excludes ``.git``, ``.env``, keys, databases, and unapproved host artifacts.
    """
    work = Path(worktree).resolve()
    required_norm = {p.replace('\\', '/').lstrip('/'): True for p in required_paths if p}
    candidates: list[str] = []
    seen: set[str] = set()

    for rel in sorted(required_norm):
        if rel not in seen:
            seen.add(rel)
            candidates.append(rel)

    proc = subprocess.run(
        ['git', '-C', str(work), 'ls-files', '-z'],
        capture_output=True,
        timeout=20,
    )
    if proc.returncode == 0 and proc.stdout:
        for raw_entry in proc.stdout.split(b'\x00'):
            if not raw_entry:
                continue
            rel = raw_entry.decode('utf-8', 'surrogateescape').replace('\\', '/').lstrip('/')
            if rel not in seen:
                seen.add(rel)
                candidates.append(rel)
    else:
        for path in sorted(work.rglob('*')):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(work).as_posix()
            if rel not in seen:
                seen.add(rel)
                candidates.append(rel)

    collected: list[tuple[str, bytes]] = []
    total_bytes = 0
    for rel in candidates:
        is_required = rel in required_norm
        if not is_required and _is_excluded_relpath(rel):
            continue
        if any(part in ('', '.', '..', '.git') for part in rel.split('/')):
            continue
        full = (work / Path(*rel.split('/'))).resolve()
        if not full.is_relative_to(work):
            raise ValueError(f'Guest bundle file escapes worktree: {rel}')
        if full.is_symlink():
            if is_required:
                raise ValueError(f'Required file cannot be a symlink: {rel}')
            continue
        if not full.is_file():
            continue
        size = full.stat().st_size
        if size > _MAX_SINGLE_FILE_BYTES:
            if is_required:
                raise ValueError(f'Required guest file exceeds 2 MiB cap: {rel}')
            continue
        if total_bytes + size > _MAX_BUNDLE_BYTES:
            if is_required:
                raise ValueError('Guest verification bundle exceeds 32 MiB limit')
            continue
        data = full.read_bytes()
        total_bytes += len(data)
        collected.append((rel, data))
    return collected


def build_guest_tar_bytes(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w') as tf:
        for rel, data in files:
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            info.mode = 0o444
            info.uid = 0
            info.gid = 0
            info.uname = 'root'
            info.gname = 'root'
            info.mtime = 1700000000
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


_LINUX_GUEST_BOOTSTRAP = r"""
import ctypes, io, json, os, struct, subprocess, sys, tarfile

def install_network_seccomp():
    libc = ctypes.CDLL('libc.so.6', use_errno=True)
    PR_SET_NO_NEW_PRIVS = 38
    PR_SET_SECCOMP = 22
    SECCOMP_MODE_FILTER = 2
    AUDIT_ARCH_X86_64 = 0xC000003E
    SYS_socket = 41
    AF_UNIX = 1
    SECCOMP_RET_KILL_PROCESS = 0x80000000
    SECCOMP_RET_ERRNO_EPERM = 0x00050001
    SECCOMP_RET_ALLOW = 0x7FFF0000

    def stmt(code, k):
        return struct.pack('HBBI', code, 0, 0, k)
    def jump(code, k, jt, jf):
        return struct.pack('HBBI', code, jt, jf, k)

    insns = b''.join([
        stmt(0x20, 4),
        jump(0x15, AUDIT_ARCH_X86_64, 1, 0),
        stmt(0x06, SECCOMP_RET_KILL_PROCESS),
        stmt(0x20, 0),
        jump(0x15, SYS_socket, 0, 3),
        stmt(0x20, 16),
        jump(0x15, AF_UNIX, 1, 0),
        stmt(0x06, SECCOMP_RET_ERRNO_EPERM),
        stmt(0x06, SECCOMP_RET_ALLOW),
    ])

    class SockFprog(ctypes.Structure):
        _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.c_char_p)]

    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'prctl(PR_SET_NO_NEW_PRIVS) failed')
    buf = ctypes.create_string_buffer(insns, len(insns))
    prog = SockFprog(len(insns) // 8, ctypes.cast(buf, ctypes.c_char_p))
    if libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(prog), 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'prctl(PR_SET_SECCOMP) failed')

header_line = sys.stdin.buffer.readline()
if not header_line:
    raise RuntimeError('Missing guest bootstrap metadata header')
meta = json.loads(header_line.decode('utf-8'))
tar_size = int(meta['tar_size'])
tar_bytes = bytearray()
while len(tar_bytes) < tar_size:
    chunk = sys.stdin.buffer.read(tar_size - len(tar_bytes))
    if not chunk:
        raise RuntimeError('Truncated guest tar stream')
    tar_bytes.extend(chunk)

for target in ('/mnt', '/run', '/home', '/root', '/media', '/srv', '/opt'):
    if os.path.isdir(target):
        subprocess.check_call([
            '/bin/mount', '-t', 'tmpfs',
            '-o', 'size=1m,mode=0555,ro,nosuid,nodev,noexec',
            'tmpfs', target,
        ])
if os.path.isdir('/proc/sys/fs/binfmt_misc'):
    subprocess.call([
        '/bin/mount', '-t', 'tmpfs',
        '-o', 'size=1m,mode=0555,ro,nosuid,nodev,noexec',
        'tmpfs', '/proc/sys/fs/binfmt_misc',
    ])

subprocess.check_call([
    '/bin/mount', '-t', 'tmpfs',
    '-o', 'size=128m,mode=0755,nosuid,nodev',
    'tmpfs', '/tmp',
])
work = '/tmp/work'
scratch = '/tmp/scratch'
os.makedirs(work, mode=0o1777, exist_ok=True)
os.makedirs(scratch, mode=0o700, exist_ok=True)
os.chown(scratch, 65534, 65534)
os.chmod(scratch, 0o700)

with tarfile.open(fileobj=io.BytesIO(bytes(tar_bytes)), mode='r:') as tf:
    for member in tf.getmembers():
        if not member.isfile():
            raise RuntimeError('Only regular files permitted in guest archive')
        norm = os.path.normpath(member.name).lstrip('/')
        if not norm or norm.startswith('..') or '/..' in norm:
            raise RuntimeError('Unsafe archive member path: ' + member.name)
        dest = os.path.join(work, norm)
        parent = os.path.dirname(dest)
        os.makedirs(parent, mode=0o1777, exist_ok=True)
        extracted = tf.extractfile(member)
        with open(dest, 'wb') as handle:
            handle.write(extracted.read())
        os.chown(dest, 0, 0)
        os.chmod(dest, 0o444)

for root_dir, dirs, _ in os.walk(work):
    os.chown(root_dir, 0, 0)
    os.chmod(root_dir, 0o1777)
    for d in dirs:
        dp = os.path.join(root_dir, d)
        os.chown(dp, 0, 0)
        os.chmod(dp, 0o1777)

os.chdir(work)
devnull = os.open('/dev/null', os.O_RDONLY)
os.dup2(devnull, 0)
os.close(devnull)

install_network_seccomp()

wall_seconds = max(2, int(meta.get('wall_seconds', 31)))
cpu_seconds = max(1, int(meta.get('cpu_seconds', 30)))
clean_env = {
    'PATH': '/usr/bin:/bin',
    'HOME': scratch,
    'TMPDIR': scratch,
    'TEMP': scratch,
    'TMP': scratch,
    'LANG': 'C.UTF-8',
    'PYTHONDONTWRITEBYTECODE': '1',
    'PYTHONUNBUFFERED': '1',
    'PYTHONNOUSERSITE': '1',
}
exec_argv = [
    '/usr/bin/timeout',
    '-s', 'KILL',
    f'{wall_seconds}s',
    '/usr/bin/prlimit',
    '--nproc=64',
    '--nofile=256',
    '--fsize=33554432',
    f'--cpu={cpu_seconds}',
    '--as=1073741824',
    '--',
    '/usr/bin/setpriv',
    '--reuid=65534',
    '--regid=65534',
    '--clear-groups',
    '--inh-caps=-all',
    '--bounding-set=-all',
    '--no-new-privs',
    '--',
    '/usr/bin/python3',
    '-s',
    '-B',
    *meta['argv'][1:],
]
os.execvpe(exec_argv[0], exec_argv, clean_env)
"""


def _wsl_exe() -> Path:
    system_root = Path(os.environ.get('SYSTEMROOT', r'C:\Windows'))
    return system_root / 'System32' / 'wsl.exe'


def _wsl_distro() -> str:
    return (os.environ.get('AI_BS_WSL2_DISTRO') or 'Ubuntu-24.04').strip()


def inspect_wsl2_provider() -> dict:
    """Inspect whether the Hyper-V/WSL2 isolated Linux VM runner is operational."""
    distro = _wsl_distro()
    info = {
        'provider': 'wsl2_isolated',
        'distro': distro,
        'hypervisor': 'Hyper-V/WSL2',
        'available': False,
        'reason': None,
    }
    if os.name != 'nt':
        info['reason'] = 'WSL2 guest runner requires a Windows host'
        return info
    wsl = _wsl_exe()
    if not wsl.is_file():
        info['reason'] = f'wsl.exe not found at {wsl}'
        return info
    try:
        listed = subprocess.run(
            [str(wsl), '--list', '--quiet'],
            capture_output=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        raw = listed.stdout.decode('utf-16-le', errors='ignore') if b'\x00' in listed.stdout else listed.stdout.decode('utf-8', errors='ignore')
        distros = [line.strip().lstrip('\ufeff') for line in raw.splitlines() if line.strip()]
        if distro not in distros:
            info['reason'] = f'WSL2 distribution {distro!r} is not registered (found: {distros})'
            return info
        probe = subprocess.run(
            [
                str(wsl), '-d', distro, '-u', 'root', '--exec',
                '/usr/bin/python3', '-c',
                "import os, sys; req=['/usr/bin/unshare','/usr/bin/setpriv','/usr/bin/prlimit','/usr/bin/timeout','/bin/mount']; "
                "missing=[p for p in req if not os.path.isfile(p)]; "
                "print(sys.version.split()[0] if not missing else 'MISSING:'+','.join(missing)); "
                "sys.exit(0 if not missing else 2)",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if probe.returncode != 0:
            info['reason'] = f'WSL2 sandbox prerequisites failed: {(probe.stdout + probe.stderr).strip()[:300]}'
            return info
        info['guest_python_version'] = probe.stdout.strip()
        info['available'] = True
        return info
    except Exception as exc:
        info['reason'] = f'WSL2 inspection failed: {exc}'
        return info


def _vbox_manage_path() -> Path:
    configured = os.environ.get('AI_BS_VBOX_MANAGE')
    if configured:
        return Path(configured)
    return Path(r'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe')


def _wait_for_compatible_vboxsvc(vbox_user_home: str | None, timeout_seconds: float = 8.0) -> None:
    """Avoid VBoxSVC COM server caching a stale VBOX_USER_HOME across rapid calls."""
    if not vbox_user_home:
        return
    desired = str(Path(vbox_user_home).resolve()).casefold()
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        conflict = False
        active_vm = False
        for proc in psutil.process_iter(['name']):
            try:
                name = (proc.info.get('name') or '').lower()
                if name in ('virtualboxvm.exe', 'vboxheadless.exe'):
                    active_vm = True
                elif name == 'vboxsvc.exe':
                    env = proc.environ()
                    current = env.get('VBOX_USER_HOME')
                    current_norm = str(Path(current).resolve()).casefold() if current else ''
                    if current_norm != desired:
                        conflict = True
            except (psutil.Error, OSError):
                continue
        if not conflict or active_vm:
            return
        time.sleep(0.25)


def _vbox_env(vbox_user_home: str | None) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if k.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA', 'HOMEDRIVE', 'HOMEPATH'}
    }
    if vbox_user_home:
        _wait_for_compatible_vboxsvc(vbox_user_home)
        env['VBOX_USER_HOME'] = str(Path(vbox_user_home).resolve())
    return env


def _parse_machinereadable(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if '=' not in line:
            continue
        key, val = line.split('=', 1)
        key = key.strip().strip('"')
        val = val.strip()
        if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        parsed[key] = val
    return parsed


def inspect_vbox_provider() -> dict:
    """Inspect whether an enrolled, containment-sanitized VirtualBox Windows VM is ready."""
    info = {
        'provider': 'vbox_windows',
        'hypervisor': 'VirtualBox',
        'available': False,
        'enrolled': False,
        'isolated': False,
        'config_path': str(VBOX_CONFIG_FILE),
        'reason': None,
    }
    if os.name != 'nt':
        info['reason'] = 'VirtualBox Windows runner requires a Windows host'
        return info
    vbox = _vbox_manage_path()
    if not vbox.is_file():
        info['reason'] = f'VBoxManage.exe not found at {vbox}'
        return info
    if not VBOX_CONFIG_FILE.is_file() or not VBOX_PASSWORD_FILE.is_file():
        info['reason'] = (
            'No independent, licensed, containment-sanitized Windows VM guest is enrolled yet. '
            'Explicit windows_vm requests fail closed (ISOLATION_UNAVAILABLE) without host or WSL2 substitution.'
        )
        return info
    try:
        cfg = json.loads(VBOX_CONFIG_FILE.read_text(encoding='utf-8'))
        secret = dpapi_decrypt(VBOX_PASSWORD_FILE.read_bytes())
        if not secret:
            raise ValueError('Decrypted guest credential is empty')
        del secret
        info['enrolled'] = True
        vm_uuid = cfg['vm_uuid']
        snapshot_uuid = cfg['snapshot_uuid']
        vbox_home = cfg.get('vbox_user_home')
        licensing_verified = bool(cfg.get('licensing_verified'))
        info.update(
            vm_name=cfg.get('vm_name'),
            vm_uuid=vm_uuid,
            snapshot_name=cfg.get('snapshot_name'),
            snapshot_uuid=snapshot_uuid,
            vbox_user_home=vbox_home,
            guest_username=cfg.get('guest_username'),
            guest_python_exe=cfg.get('guest_python_exe'),
            licensing_verified=licensing_verified,
        )
        if vm_uuid.lower() == '6c5a53da-ab80-4ecb-8be6-4059266f736e' and not cfg.get('integration_vm_override_authorized'):
            info['reason'] = (
                'Integration guest 6c5a53da-ab80-4ecb-8be6-4059266f736e is excluded from disposable '
                'candidate execution per Record 126; enroll a dedicated clean licensed Windows guest.'
            )
            return info
        if not licensing_verified:
            info['reason'] = (
                'Windows guest licensing is unverified (expired/unactivated evaluation images are '
                'blocked per docs/phase4/WINDOWS_EVALUATION_REVIEW.md).'
            )
            return info
        proc = subprocess.run(
            [str(vbox), 'showvminfo', vm_uuid, '--machinereadable'],
            env=_vbox_env(vbox_home),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if proc.returncode != 0:
            info['reason'] = f'VBoxManage showvminfo failed: {proc.stderr.strip()[:300]}'
            return info
        mr = _parse_machinereadable(proc.stdout)
        nics_enabled = [f'nic{i}={mr.get(f"nic{i}")}' for i in range(1, 9) if mr.get(f'nic{i}', 'none') != 'none']
        clipboard = mr.get('clipboard', 'disabled')
        draganddrop = mr.get('draganddrop', 'disabled')
        vrde = mr.get('vrde', 'off').lower()
        shared_folders = [k for k in mr if k.startswith(('SharedFolderNameMachineMapping', 'SharedFolderNameTransientMapping'))]
        violations = []
        if nics_enabled:
            violations.append('NICs active: ' + ', '.join(nics_enabled))
        if clipboard != 'disabled':
            violations.append(f'clipboard={clipboard}')
        if draganddrop != 'disabled':
            violations.append(f'draganddrop={draganddrop}')
        if vrde not in ('off', 'disabled'):
            violations.append(f'vrde={vrde}')
        if shared_folders:
            violations.append(f'shared_folders={len(shared_folders)}')
        if snapshot_uuid not in proc.stdout:
            violations.append(f'snapshot {snapshot_uuid} not found on VM')
        if violations:
            info['reason'] = 'VirtualBox VM failed isolation preflight: ' + '; '.join(violations)
            return info
        info['isolated'] = True
        info['available'] = True
        return info
    except Exception as exc:
        info['reason'] = f'VirtualBox provider inspection error: {exc}'
        return info


def resolve_coding_execution_plan(requested_backend: str | None) -> dict:
    """Resolve and authorize a coding execution backend with zero host or cross-OS fallback."""
    effective_request = requested_backend
    if effective_request is None or (isinstance(effective_request, str) and not effective_request.strip()):
        effective_request = os.environ.get('AI_BS_EXECUTION_BACKEND', 'trusted_host').strip() or 'trusted_host'

    if not isinstance(effective_request, str) or effective_request not in SUPPORTED_EXECUTION_BACKENDS:
        raise CodingExecutionPolicyError('INVALID_EXECUTION_BACKEND', 'Unsupported coding execution backend')

    if effective_request == 'trusted_host':
        if not _env_flag('AI_BS_ALLOW_TRUSTED_HOST_EXECUTION', default=False):
            raise CodingExecutionPolicyError(
                'TRUSTED_HOST_UNAUTHORIZED',
                'Trusted host execution is not authorized by administrator policy.',
            )
        return {
            'requested_backend': 'trusted_host',
            'execution_mode': 'trusted_host',
            'guest_provider': None,
            'isolation_verified': False,
        }

    if effective_request == 'wsl2_vm':
        if not _env_flag('AI_BS_ALLOW_WSL2_ISOLATED_VM', default=False):
            raise CodingExecutionPolicyError(
                'ISOLATION_UNAVAILABLE',
                'WSL2 isolated VM execution is not enabled by administrator policy (set AI_BS_ALLOW_WSL2_ISOLATED_VM=true). Host fallback is forbidden.',
            )
        wsl_info = inspect_wsl2_provider()
        if not wsl_info['available']:
            raise CodingExecutionPolicyError(
                'ISOLATION_UNAVAILABLE',
                f"WSL2 isolated VM is unavailable ({wsl_info.get('reason')}). Host fallback is forbidden.",
            )
        return {
            'requested_backend': 'wsl2_vm',
            'execution_mode': 'wsl2_vm',
            'guest_provider': 'wsl2_isolated',
            'isolation_verified': True,
            'provider_info': wsl_info,
        }

    # effective_request == 'windows_vm'
    # Strict fail-closed invariant (ADR-107 / ADR-109 / WINDOWS_EVALUATION_REVIEW.md):
    # Explicit windows_vm requests NEVER fall back to trusted_host and NEVER substitute wsl2_vm.
    vbox_reason = 'VirtualBox Windows VM disabled by policy'
    if _env_flag('AI_BS_ALLOW_VBOX_WINDOWS_VM', default=True):
        vbox_info = inspect_vbox_provider()
        if vbox_info['available']:
            return {
                'requested_backend': 'windows_vm',
                'execution_mode': 'windows_vm',
                'guest_provider': 'vbox_windows',
                'isolation_verified': True,
                'provider_info': vbox_info,
            }
        vbox_reason = vbox_info.get('reason') or 'VirtualBox Windows VM not ready'

    raise CodingExecutionPolicyError(
        'ISOLATION_UNAVAILABLE',
        f'Windows VM execution is unavailable ({vbox_reason}). Host fallback and Linux/WSL2 substitution are forbidden.',
    )


def run_wsl2_isolated_check(
    argv: list[str],
    worktree: Path,
    required_paths: tuple[str, ...] | list[str] = (),
    timeout_seconds: float = 30.0,
    output_limit: int = 262144,
    cancelled=None,
    distro: str | None = None,
) -> dict:
    """Run one Python check inside an isolated Hyper-V/WSL2 namespace & seccomp guest."""
    started = time.monotonic()
    target_distro = distro or _wsl_distro()
    guest_argv = ['/usr/bin/python3', '-s', '-B', *argv[1:]]
    result: dict = {
        'argv': guest_argv,
        'requested_argv': list(argv),
        'returncode': None,
        'stdout': '',
        'stderr': '',
        'isolated': True,
        'guest_provider': 'wsl2_isolated',
        'guest_distro': target_distro,
    }
    if os.name != 'nt':
        return {**result, 'error': 'WSL2 guest isolation unavailable on non-Windows host'}
    if cancelled and cancelled():
        return {**result, 'error': 'cancelled'}

    output_limit = min(max(int(output_limit), 1024), 1048576)
    wall_timeout = max(float(timeout_seconds), 0.25)
    deadline = started + wall_timeout

    try:
        bundled_files = collect_worktree_files(worktree, required_paths=required_paths)
        tar_data = build_guest_tar_bytes(bundled_files)
    except Exception as exc:
        result['error'] = f'guest_bundle_error: {exc}'
        result['execution_time_ms'] = round((time.monotonic() - started) * 1000)
        return result

    header = json.dumps({
        'tar_size': len(tar_data),
        'argv': list(argv),
        'cpu_seconds': max(1, int(wall_timeout) + 1),
        'wall_seconds': max(2, int(wall_timeout) + 2),
    }).encode('utf-8') + b'\n'
    payload = header + tar_data
    b64_script = base64.b64encode(_LINUX_GUEST_BOOTSTRAP.encode('utf-8')).decode('ascii')

    cmd = [
        str(_wsl_exe()), '-d', target_distro, '-u', 'root', '--exec',
        '/usr/bin/unshare',
        '--mount', '--net', '--ipc', '--uts', '--pid', '--fork', '--mount-proc', '--propagation', 'private',
        '/usr/bin/python3', '-I', '-B', '-c', f"import base64;exec(base64.b64decode('{b64_script}'))",
    ]

    chunks = {'stdout': bytearray(), 'stderr': bytearray()}
    limit_hit = threading.Event()
    buffer_lock = threading.Lock()
    process = None
    job = None
    readers: list[threading.Thread] = []

    def consume(pipe, name: str):
        try:
            while True:
                block = pipe.read(4096)
                if not block:
                    break
                with buffer_lock:
                    used = sum(map(len, chunks.values()))
                    remaining = output_limit - used
                    chunks[name].extend(block[:max(remaining, 0)])
                    if len(block) > remaining:
                        limit_hit.set()
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    def feed_stdin(pipe, data: bytes):
        try:
            pipe.write(data)
            pipe.flush()
        except OSError:
            pass
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    try:
        import win32api
        import win32job
        import win32process

        host_env = {
            k: v for k, v in os.environ.items()
            if k.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA', 'USERPROFILE'}
        }
        job = win32job.CreateJobObject(None, '')
        limits = win32job.QueryInformationJobObject(job, win32job.JobObjectExtendedLimitInformation)
        limits['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        win32job.SetInformationJobObject(job, win32job.JobObjectExtendedLimitInformation, limits)

        process = subprocess.Popen(
            cmd,
            env=host_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=win32process.CREATE_SUSPENDED | subprocess.CREATE_NO_WINDOW,
        )
        handle = win32api.OpenProcess(0x0100 | 0x0001 | 0x0400, False, process.pid)
        try:
            win32job.AssignProcessToJobObject(job, handle)
            if not win32job.IsProcessInJob(handle, job):
                raise RuntimeError('WSL2 client process was not assigned to its process job')
        finally:
            handle.Close()

        writer = threading.Thread(target=feed_stdin, args=(process.stdin, payload), daemon=True)
        for stream_name in ('stdout', 'stderr'):
            thread = threading.Thread(target=consume, args=(getattr(process, stream_name), stream_name), daemon=True)
            thread.start()
            readers.append(thread)

        psutil.Process(process.pid).resume()
        writer.start()

        while process.poll() is None:
            if cancelled and cancelled():
                result['error'] = 'cancelled'
                break
            if limit_hit.is_set():
                result['error'] = 'output_limit'
                break
            if time.monotonic() >= deadline:
                result['error'] = 'timeout'
                break
            time.sleep(0.02)

        job.Close()
        job = None
        process.wait(timeout=5)
        writer.join(timeout=2)
        for thread in readers:
            thread.join(timeout=5)
        if any(thread.is_alive() for thread in readers) and 'error' not in result:
            result['error'] = 'output_reader_did_not_finish'
        if limit_hit.is_set() and 'error' not in result:
            result['error'] = 'output_limit'
        if process.returncode in (124, 137) and 'error' not in result and time.monotonic() >= deadline - 0.1:
            result['error'] = 'timeout'
        result['returncode'] = process.returncode
    except Exception as exc:
        result['error'] = f'guest_control: {exc}'
    finally:
        if job is not None:
            try:
                job.Close()
            except Exception:
                pass
        if process is not None:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=5)
            except Exception:
                pass
            if result['returncode'] is None:
                result['returncode'] = process.returncode
            for stream_name in ('stdin', 'stdout', 'stderr'):
                pipe = getattr(process, stream_name, None)
                if pipe and not pipe.closed:
                    try:
                        pipe.close()
                    except Exception:
                        pass
            for thread in readers:
                thread.join(timeout=2)
        with buffer_lock:
            result.update({name: bytes(value).decode('utf-8', 'replace') for name, value in chunks.items()})
        result['execution_time_ms'] = round((time.monotonic() - started) * 1000)
    return result


def run_vbox_windows_check(
    argv: list[str],
    worktree: Path,
    required_paths: tuple[str, ...] | list[str] = (),
    timeout_seconds: float = 60.0,
    output_limit: int = 262144,
    cancelled=None,
) -> dict:
    """Run one Python check inside an isolated snapshot-backed VirtualBox Windows VM."""
    started = time.monotonic()
    result: dict = {
        'argv': list(argv),
        'requested_argv': list(argv),
        'returncode': None,
        'stdout': '',
        'stderr': '',
        'isolated': True,
        'guest_provider': 'vbox_windows',
    }
    if cancelled and cancelled():
        return {**result, 'error': 'cancelled'}

    preflight = inspect_vbox_provider()
    if not preflight['available']:
        return {**result, 'error': 'isolation_unavailable: ' + str(preflight.get('reason'))}

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(VBOX_CONFIG_FILE.read_text(encoding='utf-8'))
    vm_uuid = cfg['vm_uuid']
    snapshot_uuid = cfg['snapshot_uuid']
    vbox_home = cfg.get('vbox_user_home')
    guest_user = cfg['guest_username']
    guest_python = cfg['guest_python_exe']
    guest_temp_root = cfg.get('guest_temp_root') or r'C:\Windows\Temp'
    vbox = str(_vbox_manage_path())
    env = _vbox_env(vbox_home)
    output_limit = min(max(int(output_limit), 1024), 1048576)
    guest_argv = [guest_python, '-s', '-B', *argv[1:]]
    result['argv'] = guest_argv
    result['vm_uuid'] = vm_uuid
    result['snapshot_uuid'] = snapshot_uuid

    try:
        bundled_files = collect_worktree_files(worktree, required_paths=required_paths)
    except Exception as exc:
        result['error'] = f'guest_bundle_error: {exc}'
        result['execution_time_ms'] = round((time.monotonic() - started) * 1000)
        return result

    pw_file: Path | None = None
    with record_lock(VBOX_LOCK_FILE):
        try:
            secret = dpapi_decrypt(VBOX_PASSWORD_FILE.read_bytes()).decode('utf-8')
            fd, raw_pw_path = tempfile.mkstemp(prefix='aibs_vbox_pw_', suffix='.tmp')
            pw_file = Path(raw_pw_path)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(secret)
            del secret

            def vbox_cmd(*args: str, timeout: float = 45.0, check: bool = True) -> subprocess.CompletedProcess:
                proc = subprocess.run(
                    [vbox, *args],
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=timeout,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                if check and proc.returncode != 0:
                    raise RuntimeError(f"VBoxManage {' '.join(args[:2])} failed: {proc.stderr.strip()[:400]}")
                return proc

            vbox_cmd('controlvm', vm_uuid, 'poweroff', timeout=20, check=False)
            time.sleep(0.5)
            vbox_cmd('snapshot', vm_uuid, 'restore', snapshot_uuid, timeout=60)
            vbox_cmd('startvm', vm_uuid, '--type', 'headless', timeout=45)

            boot_deadline = time.monotonic() + 90.0
            ready = False
            while time.monotonic() < boot_deadline:
                if cancelled and cancelled():
                    result['error'] = 'cancelled'
                    return result
                gp = vbox_cmd('guestproperty', 'get', vm_uuid, '/VirtualBox/GuestAdd/RunLevel', timeout=10, check=False)
                if 'Value: 2' in gp.stdout or 'Value: 3' in gp.stdout:
                    ready = True
                    break
                time.sleep(1.0)
            if not ready:
                raise TimeoutError('VirtualBox Guest Additions did not reach RunLevel 2 within 90s')

            guest_work = f"{guest_temp_root.rstrip('\\')}\\aibs_check_{uuid.uuid4().hex[:12]}"
            vbox_cmd(
                'guestcontrol', vm_uuid, 'mkdir', '--parents', guest_work,
                '--username', guest_user, '--passwordfile', str(pw_file),
                timeout=20,
            )

            with tempfile.TemporaryDirectory(prefix='aibs_vbox_stage_') as stage_dir:
                stage_root = Path(stage_dir)
                created_dirs: set[str] = set()
                for rel, data in bundled_files:
                    local_file = stage_root / Path(*rel.split('/'))
                    local_file.parent.mkdir(parents=True, exist_ok=True)
                    local_file.write_bytes(data)
                    rel_win = rel.replace('/', '\\')
                    parent_win = os.path.dirname(rel_win)
                    if parent_win and parent_win not in created_dirs:
                        created_dirs.add(parent_win)
                        vbox_cmd(
                            'guestcontrol', vm_uuid, 'mkdir', '--parents', f'{guest_work}\\{parent_win}',
                            '--username', guest_user, '--passwordfile', str(pw_file),
                            timeout=15,
                        )
                    vbox_cmd(
                        'guestcontrol', vm_uuid, 'copyto', str(local_file), f'{guest_work}\\{rel_win}',
                        '--username', guest_user, '--passwordfile', str(pw_file),
                        timeout=20,
                    )

            run_args = [
                vbox, 'guestcontrol', vm_uuid, 'run',
                '--exe', guest_python,
                '--cwd', guest_work,
                '--username', guest_user,
                '--passwordfile', str(pw_file),
                '--putenv', 'PYTHONDONTWRITEBYTECODE=1',
                '--putenv', 'PYTHONUNBUFFERED=1',
                '--putenv', 'PYTHONNOUSERSITE=1',
                '--wait-stdout', '--wait-stderr',
                '--', guest_python, '-s', '-B', *argv[1:],
            ]
            proc = subprocess.Popen(
                run_args,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            check_deadline = time.monotonic() + max(float(timeout_seconds), 1.0)
            while proc.poll() is None:
                if cancelled and cancelled():
                    result['error'] = 'cancelled'
                    proc.kill()
                    break
                if time.monotonic() >= check_deadline:
                    result['error'] = 'timeout'
                    proc.kill()
                    break
                time.sleep(0.05)
            out_bytes, err_bytes = proc.communicate(timeout=10)
            if len(out_bytes) + len(err_bytes) > output_limit and 'error' not in result:
                result['error'] = 'output_limit'
            result['stdout'] = out_bytes[:output_limit].decode('utf-8', 'replace')
            rem = max(0, output_limit - len(out_bytes))
            result['stderr'] = err_bytes[:rem].decode('utf-8', 'replace')
            result['returncode'] = proc.returncode
        except Exception as exc:
            result['error'] = f'vbox_guest_control: {exc}'
        finally:
            if pw_file is not None:
                pw_file.unlink(missing_ok=True)
            subprocess.run(
                [vbox, 'controlvm', vm_uuid, 'poweroff'],
                env=env, capture_output=True, timeout=25, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time.sleep(0.5)
            subprocess.run(
                [vbox, 'snapshot', vm_uuid, 'restore', snapshot_uuid],
                env=env, capture_output=True, timeout=60, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            result['execution_time_ms'] = round((time.monotonic() - started) * 1000)
    return result


def run_guest_check(
    plan: dict,
    argv: list[str],
    worktree: Path,
    required_paths: tuple[str, ...] | list[str] = (),
    timeout_seconds: float = 30.0,
    output_limit: int = 262144,
    cancelled=None,
) -> dict:
    """Dispatch a check strictly to an isolated VM guest runner (never host)."""
    provider = plan.get('guest_provider')
    if provider == 'vbox_windows':
        return run_vbox_windows_check(
            argv=argv,
            worktree=worktree,
            required_paths=required_paths,
            timeout_seconds=timeout_seconds,
            output_limit=output_limit,
            cancelled=cancelled,
        )
    if provider == 'wsl2_isolated':
        distro = (plan.get('provider_info') or {}).get('distro')
        return run_wsl2_isolated_check(
            argv=argv,
            worktree=worktree,
            required_paths=required_paths,
            timeout_seconds=timeout_seconds,
            output_limit=output_limit,
            cancelled=cancelled,
            distro=distro,
        )
    raise RuntimeError(f'Refusing to execute check: unsupported guest provider {provider!r}')
