#!/usr/bin/env python3
"""Setup, enrollment, and end-to-end verification CLI for AI-BS Isolated Guest Runners.

Subcommands:
  status        Inspect policy flags, Hyper-V/WSL2 isolated VM, and VirtualBox Windows VM.
  verify        Run 6 guest containment/escape-denial probes + 7-test Number Summary canary
                end-to-end through the isolated VM workflow (review + apply verified).
  enroll-vbox   Interactive DPAPI credential enrollment & containment sanitization for
                VirtualBox Windows 11 guest (AI-BS-Eval-Base-20261023).
  verify-vbox   Run 7-test Number Summary canary strictly inside VirtualBox Windows guest.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_VBOX_HOME = REPO_ROOT / 'isolated_workers' / 'windows' / 'runtime' / 'base_preparation_v2' / 'vbox_config'
DEFAULT_VBOX_VM_UUID = '6c5a53da-ab80-4ecb-8be6-4059266f736e'
DEFAULT_VBOX_BASE_SNAPSHOT = '5f014291-52f1-4b18-83c9-37110083b3a0'
CANARY_FIXTURE_DIR = REPO_ROOT / 'backups' / 'durable_packet_inbox_20261026_record122' / 'guest_test_fixture'

POLICY_KEYS = (
    'AI_BS_EXECUTION_BACKEND',
    'AI_BS_ALLOW_TRUSTED_HOST_EXECUTION',
    'AI_BS_ALLOW_WSL2_ISOLATED_VM',
    'AI_BS_ALLOW_VBOX_WINDOWS_VM',
    'AI_BS_ALLOW_WSL2_GUEST_FOR_WINDOWS_VM',
    'AI_BS_REQUIRE_STRICT_WINDOWS_KERNEL_FOR_WINDOWS_VM',
    'AI_BS_WSL2_DISTRO',
)

FALLBACK_STUB_SOURCE = '''"""Initial stub prior to candidate verification."""


def summarize(values):
    raise NotImplementedError("stub")
'''

FALLBACK_IMPL_SOURCE = '''"""Disposable AI-BS round-trip canary. Standard library only; no external I/O."""


def summarize(values):
    if type(values) is not list:
        raise TypeError('values must be a list')
    if any(type(value) is not int for value in values):
        raise TypeError('values must contain integers only')
    return {
        'count': len(values),
        'sum': sum(values),
        'min': min(values) if values else None,
        'max': max(values) if values else None,
    }
'''

FALLBACK_TEST_SOURCE = '''"""Immutable trusted test specification for the disposable execution guest."""
import unittest
from number_summary import summarize


class NumberSummaryTests(unittest.TestCase):
    def test_mixed_signs(self):
        self.assertEqual(summarize([3, -1, 4]), {'count': 3, 'sum': 6, 'min': -1, 'max': 4})

    def test_empty_list(self):
        self.assertEqual(summarize([]), {'count': 0, 'sum': 0, 'min': None, 'max': None})

    def test_duplicates(self):
        self.assertEqual(summarize([2, 2]), {'count': 2, 'sum': 4, 'min': 2, 'max': 2})

    def test_large_integers(self):
        self.assertEqual(summarize([2**100, -(2**100)])['sum'], 0)

    def test_boolean_rejected(self):
        with self.assertRaises(TypeError):
            summarize([True])

    def test_noninteger_rejected(self):
        with self.assertRaises(TypeError):
            summarize([1, '2'])

    def test_nonlist_rejected(self):
        with self.assertRaises(TypeError):
            summarize((1, 2))


if __name__ == '__main__':
    unittest.main()
'''


def load_policy_env() -> dict[str, str]:
    """Load only safe execution-policy keys from .env files into os.environ."""
    loaded: dict[str, str] = {}
    for env_path in (REPO_ROOT / '.env', BACKEND_DIR / '.env'):
        if not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding='utf-8', errors='replace').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, val = line.split('=', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in POLICY_KEYS:
                os.environ.setdefault(key, val)
                loaded[key] = os.environ[key]
    for key in POLICY_KEYS:
        if key in os.environ:
            loaded[key] = os.environ[key]
    return loaded


def load_canary_sources() -> tuple[str, str]:
    impl_file = CANARY_FIXTURE_DIR / 'number_summary.py'
    test_file = CANARY_FIXTURE_DIR / 'test_number_summary.py'
    if impl_file.is_file() and test_file.is_file():
        return impl_file.read_text(encoding='utf-8'), test_file.read_text(encoding='utf-8')
    return FALLBACK_IMPL_SOURCE, FALLBACK_TEST_SOURCE


def init_disposable_canary_repo(root: Path, test_source: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    env = {
        k: v for k, v in os.environ.items()
        if k.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA'}
    }
    env['GIT_TERMINAL_PROMPT'] = '0'
    subprocess.run(['git', 'init'], cwd=root, env=env, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'canary@aibs.local'], cwd=root, env=env, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'AI-BS Canary'], cwd=root, env=env, check=True, capture_output=True)
    (root / 'number_summary.py').write_text(FALLBACK_STUB_SOURCE, encoding='utf-8')
    (root / 'test_number_summary.py').write_text(test_source, encoding='utf-8')
    subprocess.run(['git', 'add', 'number_summary.py', 'test_number_summary.py'], cwd=root, env=env, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial canary stub and 7-test specification'], cwd=root, env=env, check=True, capture_output=True)


def inspect_unregistered_vbox_candidate() -> dict:
    from core.coding_guest_runner import _parse_machinereadable, _vbox_env, _vbox_manage_path
    vbox = _vbox_manage_path()
    if not vbox.is_file() or not DEFAULT_VBOX_HOME.is_dir():
        return {'detected': False}
    try:
        proc = subprocess.run(
            [str(vbox), 'showvminfo', DEFAULT_VBOX_VM_UUID, '--machinereadable'],
            env=_vbox_env(str(DEFAULT_VBOX_HOME)),
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if proc.returncode != 0:
            return {'detected': False, 'error': proc.stderr.strip()[:200]}
        mr = _parse_machinereadable(proc.stdout)
        return {
            'detected': True,
            'vm_name': mr.get('name'),
            'vm_uuid': DEFAULT_VBOX_VM_UUID,
            'vm_state': mr.get('VMState'),
            'current_snapshot': mr.get('CurrentSnapshotName'),
            'current_snapshot_uuid': mr.get('CurrentSnapshotUUID'),
            'nic1': mr.get('nic1'),
            'clipboard': mr.get('clipboard'),
            'draganddrop': mr.get('draganddrop'),
            'vbox_user_home': str(DEFAULT_VBOX_HOME),
        }
    except Exception as exc:
        return {'detected': False, 'error': str(exc)}


def cmd_status(_args: argparse.Namespace) -> int:
    from core.coding_guest_runner import (
        CodingExecutionPolicyError,
        inspect_vbox_provider,
        inspect_wsl2_provider,
        resolve_coding_execution_plan,
    )
    policy = load_policy_env()
    wsl_info = inspect_wsl2_provider()
    vbox_info = inspect_vbox_provider()
    vbox_candidate = inspect_unregistered_vbox_candidate() if not vbox_info.get('enrolled') else None

    resolutions = {}
    for target in (None, 'wsl2_vm', 'windows_vm', 'trusted_host'):
        label = 'default (None)' if target is None else target
        try:
            plan = resolve_coding_execution_plan(target)
            resolutions[label] = {
                'status': 'READY',
                'execution_mode': plan['execution_mode'],
                'guest_provider': plan['guest_provider'],
                'isolation_verified': plan['isolation_verified'],
            }
        except CodingExecutionPolicyError as exc:
            resolutions[label] = {
                'status': 'BLOCKED',
                'error_code': exc.error_code,
                'reason': str(exc),
            }

    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'policy_flags': policy,
        'providers': {
            'wsl2_isolated': wsl_info,
            'vbox_windows': vbox_info,
            **({'vbox_candidate_inventory': vbox_candidate} if vbox_candidate else {}),
        },
        'backend_resolutions': resolutions,
    }
    print(json.dumps(report, indent=2))
    return 0


def run_wsl2_containment_and_canary() -> dict:
    from core.coding_guest_runner import (
        CONFIG_DIR,
        inspect_wsl2_provider,
        run_wsl2_isolated_check,
    )
    from core.coding_review import apply_task, review_task
    from core.coding_workflow import STORE, run_coding_task

    load_policy_env()
    wsl_info = inspect_wsl2_provider()
    if not wsl_info['available']:
        raise RuntimeError(f"WSL2 isolated VM provider is not available: {wsl_info.get('reason')}")

    probes: dict[str, dict] = {}
    created_task_dirs: list[Path] = []

    with tempfile.TemporaryDirectory(prefix='aibs_guest_verify_') as tmp:
        try:
            tmp_root = Path(tmp)

            # Probe 1-4: Namespace, Host Drive/Interop Masking, Seccomp Socket Denial, Test File Immutability
            probe_dir = tmp_root / 'containment_probe'
            probe_dir.mkdir(parents=True)
            (probe_dir / 'test_immutable.py').write_text('# immutable verification file\n', encoding='utf-8')
            (probe_dir / 'run_probe.py').write_text(
                """import json, os, socket, subprocess

def check_socket(family):
    try:
        s = socket.socket(family, socket.SOCK_STREAM)
        s.close()
        return 'ALLOWED'
    except OSError as exc:
        return f'{type(exc).__name__}:{exc.errno}'

a, b = socket.socketpair()
a.send(b'ping')
unix_ok = (b.recv(4) == b'ping')
a.close(); b.close()

cmd_err = None
try:
    subprocess.run(['/mnt/c/Windows/System32/cmd.exe', '/c', 'ver'], timeout=2)
except OSError as exc:
    cmd_err = type(exc).__name__

overwrite_err = None
try:
    with open('test_immutable.py', 'w', encoding='utf-8') as f:
        f.write('tampered')
except OSError as exc:
    overwrite_err = type(exc).__name__

unlink_err = None
try:
    os.unlink('test_immutable.py')
except OSError as exc:
    unlink_err = type(exc).__name__

print(json.dumps({
    'uid': os.getuid(),
    'gid': os.getgid(),
    'pid': os.getpid(),
    'ppid': os.getppid(),
    'proc_pids': sorted(int(e) for e in os.listdir('/proc') if e.isdigit()),
    'mnt_entries': os.listdir('/mnt'),
    'run_entries': os.listdir('/run'),
    'home_entries': os.listdir('/home'),
    'af_inet': check_socket(socket.AF_INET),
    'af_inet6': check_socket(socket.AF_INET6),
    'af_vsock': check_socket(socket.AF_VSOCK),
    'af_unix_socketpair': unix_ok,
    'windows_interop_cmd': cmd_err,
    'overwrite_verification_file': overwrite_err,
    'unlink_verification_file': unlink_err,
}))
""",
                encoding='utf-8',
            )

            ev = run_wsl2_isolated_check(
                ['python', 'run_probe.py'],
                probe_dir,
                required_paths=('run_probe.py', 'test_immutable.py'),
                timeout_seconds=20,
            )
            if ev.get('returncode') != 0 or ev.get('error'):
                raise RuntimeError(f'Containment probe failed: {ev}')
            attestation = json.loads(ev['stdout'].strip())
            assert attestation['uid'] == 65534 and attestation['gid'] == 65534, f'Unexpected UID/GID: {attestation}'
            assert attestation['ppid'] == 1 and attestation['proc_pids'] == [1, attestation['pid']], f'Expected isolated PID namespace: {attestation}'
            assert attestation['mnt_entries'] == [] and attestation['run_entries'] == [], f'Host mounts leaked: {attestation}'
            assert attestation['af_inet'].startswith('PermissionError:'), f'AF_INET not blocked: {attestation}'
            assert attestation['af_inet6'].startswith('PermissionError:'), f'AF_INET6 not blocked: {attestation}'
            assert attestation['af_vsock'].startswith('PermissionError:'), f'AF_VSOCK not blocked: {attestation}'
            assert attestation['af_unix_socketpair'] is True
            assert attestation['windows_interop_cmd'] == 'FileNotFoundError'
            assert attestation['overwrite_verification_file'] == 'PermissionError'
            assert attestation['unlink_verification_file'] == 'PermissionError'
            probes['namespace_and_seccomp_attestation'] = {'passed': True, 'details': attestation}

            # Probe 5: Timeout enforcement inside isolated guest
            (probe_dir / 'hang_probe.py').write_text('import time\ntime.sleep(30)\n', encoding='utf-8')
            hang_ev = run_wsl2_isolated_check(
                ['python', 'hang_probe.py'],
                probe_dir,
                required_paths=('hang_probe.py',),
                timeout_seconds=1.2,
            )
            assert hang_ev.get('error') == 'timeout', f'Expected timeout error, got: {hang_ev}'
            probes['timeout_containment'] = {
                'passed': True,
                'error': hang_ev.get('error'),
                'execution_time_ms': hang_ev.get('execution_time_ms'),
            }

            impl_source, test_source = load_canary_sources()

            # End-to-End Canary 1: explicit wsl2_vm -> VERIFIED -> review_task -> apply_task
            repo_wsl = tmp_root / 'canary_repo_wsl2'
            init_disposable_canary_repo(repo_wsl, test_source)
            res_wsl = run_coding_task(
                repository=str(repo_wsl),
                objective='Implement number_summary.summarize and pass the 7-test Number Summary canary in isolated VM.',
                files=[{'path': 'number_summary.py', 'content': impl_source}],
                checks=[['python', '-m', 'unittest', 'test_number_summary']],
                timeout_seconds=30,
                execution_backend='wsl2_vm',
            )
            created_task_dirs.append(STORE / res_wsl['task_id'])
            assert res_wsl['status'] == 'success' and res_wsl['state'] == 'VERIFIED', f'wsl2_vm canary failed: {res_wsl}'
            assert res_wsl['execution_mode'] == 'wsl2_vm'
            assert res_wsl['guest_provider'] == 'wsl2_isolated'
            assert res_wsl['isolation_verified'] is True
            assert 'Ran 7 tests' in (res_wsl['checks'][0]['stderr'] + res_wsl['checks'][0]['stdout'])

            rev = review_task(res_wsl['task_id'])
            assert rev['can_apply'] is True and rev.get('review_token'), f'Review not applicable: {rev}'
            applied = apply_task(res_wsl['task_id'], rev['review_token'])
            assert applied['application']['state'] == 'APPLIED'
            assert (repo_wsl / 'number_summary.py').read_text(encoding='utf-8').strip() == impl_source.strip()
            probes['canary_wsl2_vm_roundtrip'] = {
                'passed': True,
                'task_id': res_wsl['task_id'],
                'execution_mode': res_wsl['execution_mode'],
                'guest_provider': res_wsl['guest_provider'],
                'diff_hash': res_wsl['review_seal']['diff_hash'],
                'checks_hash': res_wsl['review_seal']['checks_hash'],
                'application_state': applied['application']['state'],
            }

            # End-to-End Canary 2: windows_vm request under operator policy -> isolated VM execution (zero host fallback)
            repo_vm = tmp_root / 'canary_repo_vm'
            init_disposable_canary_repo(repo_vm, test_source)
            res_vm = run_coding_task(
                repository=str(repo_vm),
                objective='Verify windows_vm executes inside isolated VM guest without failing closed or touching host.',
                files=[{'path': 'number_summary.py', 'content': impl_source}],
                checks=[['python', '-m', 'unittest', 'test_number_summary']],
                timeout_seconds=30,
                execution_backend='windows_vm',
            )
            created_task_dirs.append(STORE / res_vm['task_id'])
            assert res_vm['status'] == 'success' and res_vm['state'] == 'VERIFIED', f'windows_vm canary failed: {res_vm}'
            assert res_vm['isolation_verified'] is True
            assert res_vm['guest_provider'] in ('vbox_windows', 'wsl2_isolated')
            assert res_vm['execution_mode'] in ('windows_vm', 'wsl2_vm')
            probes['canary_windows_vm_roundtrip'] = {
                'passed': True,
                'task_id': res_vm['task_id'],
                'requested_execution_backend': res_vm['requested_execution_backend'],
                'execution_mode': res_vm['execution_mode'],
                'guest_provider': res_vm['guest_provider'],
                'diff_hash': res_vm['review_seal']['diff_hash'],
            }
        finally:
            for task_folder in created_task_dirs:
                shutil.rmtree(task_folder, ignore_errors=True)

    receipt = {
        'status': 'VERIFIED',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'wsl2_provider': wsl_info,
        'probes': probes,
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    receipt_path = CONFIG_DIR / 'last_verification_receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    receipt['receipt_path'] = str(receipt_path)
    return receipt


def cmd_verify(_args: argparse.Namespace) -> int:
    receipt = run_wsl2_containment_and_canary()
    print(json.dumps(receipt, indent=2))
    return 0


def cmd_enroll_vbox(args: argparse.Namespace) -> int:
    from core.coding_guest_runner import (
        CONFIG_DIR,
        VBOX_CONFIG_FILE,
        VBOX_PASSWORD_FILE,
        _parse_machinereadable,
        _vbox_env,
        _vbox_manage_path,
        dpapi_encrypt,
    )
    vbox = _vbox_manage_path()
    if not vbox.is_file():
        print(f'ERROR: VBoxManage.exe not found at {vbox}', file=sys.stderr)
        return 1

    vbox_home = args.vbox_user_home or (str(DEFAULT_VBOX_HOME) if DEFAULT_VBOX_HOME.is_dir() else None)
    vm_uuid = args.vm_uuid
    username = args.username or input('Enter Windows 11 Guest local username: ').strip()
    if not username:
        print('ERROR: Guest username is required.', file=sys.stderr)
        return 1
    password = getpass.getpass(f'Enter Windows 11 Guest password for {username} (hidden): ')
    if not password:
        print('ERROR: Guest password is required.', file=sys.stderr)
        return 1

    guest_python = args.guest_python or rf'C:\Users\{username}\AppData\Local\Programs\Python\Python313\python.exe'
    env = _vbox_env(vbox_home)

    def run_vb(*vb_args: str, check: bool = True, timeout: float = 60.0) -> subprocess.CompletedProcess:
        p = subprocess.run(
            [str(vbox), *vb_args],
            env=env, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if check and p.returncode != 0:
            raise RuntimeError(f"VBoxManage {' '.join(vb_args[:2])} failed: {p.stderr.strip()[:400]}")
        return p

    info_proc = run_vb('showvminfo', vm_uuid, '--machinereadable')
    mr = _parse_machinereadable(info_proc.stdout)
    vm_name = mr.get('name', vm_uuid)
    vm_state = mr.get('VMState', '')

    snapshot_uuid = args.snapshot_uuid
    snapshot_name = 'AIBS_IsolatedRunner_Ready'

    if not args.no_sanitize:
        print(f'Sanitizing {vm_name} ({vm_uuid}) for strict isolated guest execution...')
        if vm_state == 'running':
            run_vb('controlvm', vm_uuid, 'poweroff', check=False)
        base_snap = args.base_snapshot_uuid or mr.get('CurrentSnapshotUUID') or DEFAULT_VBOX_BASE_SNAPSHOT
        run_vb('snapshot', vm_uuid, 'restore', base_snap, timeout=90)
        info_after = _parse_machinereadable(run_vb('showvminfo', vm_uuid, '--machinereadable').stdout)
        if info_after.get('VMState') == 'saved':
            run_vb('discardstate', vm_uuid, timeout=30)
        modify = ['modifyvm', vm_uuid, '--clipboard-mode', 'disabled', '--drag-and-drop', 'disabled']
        for idx in range(1, 9):
            modify.extend([f'--nic{idx}', 'none'])
        run_vb(*modify, timeout=30)
        for key, val in info_after.items():
            if key.startswith('SharedFolderNameMachineMapping'):
                run_vb('sharedfolder', 'remove', vm_uuid, '--name', val, check=False)
        snap_proc = run_vb(
            'snapshot', vm_uuid, 'take', snapshot_name,
            '--description', 'Sanitized offline snapshot for AI-BS isolated guest runner (NICs/clipboard/DnD disabled)',
            timeout=90,
        )
        m = re.search(r'UUID:\s*([0-9a-fA-F-]{36})', snap_proc.stdout + '\n' + snap_proc.stderr)
        if m:
            snapshot_uuid = m.group(1)
        else:
            refreshed = _parse_machinereadable(run_vb('showvminfo', vm_uuid, '--machinereadable').stdout)
            snapshot_uuid = refreshed['CurrentSnapshotUUID']

    if not snapshot_uuid:
        snapshot_uuid = mr.get('CurrentSnapshotUUID') or DEFAULT_VBOX_BASE_SNAPSHOT

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    VBOX_PASSWORD_FILE.write_bytes(dpapi_encrypt(password.encode('utf-8')))
    del password

    cfg = {
        'vm_name': vm_name,
        'vm_uuid': vm_uuid,
        'snapshot_name': snapshot_name,
        'snapshot_uuid': snapshot_uuid,
        'vbox_user_home': vbox_home,
        'guest_username': username,
        'guest_python_exe': guest_python,
        'guest_temp_root': r'C:\Windows\Temp',
        'enrolled_at_utc': datetime.now(timezone.utc).isoformat(),
    }
    VBOX_CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    print(f'Enrolled DPAPI credentials and VirtualBox config at {VBOX_CONFIG_FILE}')
    return cmd_verify_vbox(args)


def cmd_verify_vbox(_args: argparse.Namespace) -> int:
    from core.coding_guest_runner import inspect_vbox_provider
    from core.coding_workflow import STORE, run_coding_task

    load_policy_env()
    info = inspect_vbox_provider()
    if not info['available']:
        print(json.dumps({'status': 'UNAVAILABLE', 'vbox_provider': info}, indent=2))
        return 1

    impl_source, test_source = load_canary_sources()
    old_strict = os.environ.get('AI_BS_REQUIRE_STRICT_WINDOWS_KERNEL_FOR_WINDOWS_VM')
    os.environ['AI_BS_REQUIRE_STRICT_WINDOWS_KERNEL_FOR_WINDOWS_VM'] = 'true'
    try:
        with tempfile.TemporaryDirectory(prefix='aibs_vbox_canary_') as tmp:
            repo_dir = Path(tmp) / 'vbox_canary_repo'
            init_disposable_canary_repo(repo_dir, test_source)
            res = run_coding_task(
                repository=str(repo_dir),
                objective='Verify 7-test Number Summary canary inside VirtualBox Windows 11 guest.',
                files=[{'path': 'number_summary.py', 'content': impl_source}],
                checks=[['python', '-m', 'unittest', 'test_number_summary']],
                timeout_seconds=60,
                overall_timeout_seconds=300,
                execution_backend='windows_vm',
            )
            shutil.rmtree(STORE / res['task_id'], ignore_errors=True)
        ok = res['status'] == 'success' and res['state'] == 'VERIFIED' and res.get('guest_provider') == 'vbox_windows'
        print(json.dumps({
            'status': 'VERIFIED' if ok else 'FAILED',
            'execution_mode': res.get('execution_mode'),
            'guest_provider': res.get('guest_provider'),
            'checks': res.get('checks'),
            'error': res.get('error'),
        }, indent=2))
        return 0 if ok else 1
    finally:
        if old_strict is None:
            os.environ.pop('AI_BS_REQUIRE_STRICT_WINDOWS_KERNEL_FOR_WINDOWS_VM', None)
        else:
            os.environ['AI_BS_REQUIRE_STRICT_WINDOWS_KERNEL_FOR_WINDOWS_VM'] = old_strict


def cmd_test_all(_args: argparse.Namespace) -> int:
    """Run guest runner tests, baseline regression tests, and preparation snapshot suites."""
    load_policy_env()
    suites = []

    p1 = subprocess.run(
        [
            sys.executable, '-X', 'utf8', '-m', 'unittest',
            'scripts.tests.test_coding_guest_runner',
            'scripts.tests.test_chat_attachment_upload',
            'scripts.tests.test_router_mount_integrity',
            'scripts.tests.test_audio_router_trace',
            'scripts.tests.test_mobile_media_delivery',
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    suites.append({
        'name': 'guest_runner_and_core_regressions',
        'passed': p1.returncode == 0,
        'returncode': p1.returncode,
        'summary': (p1.stderr or p1.stdout).strip().splitlines()[-3:],
    })

    for cls_name, mod_name in (
        ('RepositorySnapshotTests', 'test_repository_snapshot.RepositorySnapshotTests'),
        ('PreparationTests', 'test_coding_preparation.PreparationTests'),
    ):
        with tempfile.TemporaryDirectory(prefix=f'aibs_{cls_name.lower()}_') as tmp_parent:
            snap_root = Path(tmp_parent) / 'snapshot_root'
            env = dict(os.environ)
            env['PYTHONPATH'] = f"{BACKEND_DIR};{BACKEND_DIR / 'tests'};{REPO_ROOT}"
            env['AIBS_SNAPSHOT_TEST_ROOT'] = str(snap_root)
            proc = subprocess.run(
                [sys.executable, '-X', 'utf8', '-m', 'unittest', mod_name],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
            suites.append({
                'name': cls_name,
                'passed': proc.returncode == 0,
                'returncode': proc.returncode,
                'summary': (proc.stderr or proc.stdout).strip().splitlines()[-3:],
            })

    all_passed = all(s['passed'] for s in suites)
    print(json.dumps({
        'status': 'PASSED' if all_passed else 'FAILED',
        'suites': suites,
    }, indent=2))
    return 0 if all_passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Verify and connect AI-BS isolated VM guest runners.')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('status', help='Show guest runner readiness and execution policy status.')
    sub.add_parser('verify', help='Run live guest containment probes and 7-test Number Summary VM canary.')
    sub.add_parser('verify-wsl2', help='Alias for verify (Hyper-V/WSL2 isolated VM containment + canary).')
    sub.add_parser('verify-vbox', help='Verify native VirtualBox Windows 11 guest execution.')
    sub.add_parser('test-all', help='Run all 105 guest runner, core regression, and preparation snapshot tests.')

    enroll = sub.add_parser('enroll-vbox', help='Enroll DPAPI credentials and sanitize VirtualBox Windows 11 guest.')
    enroll.add_argument('--vm-uuid', default=DEFAULT_VBOX_VM_UUID)
    enroll.add_argument('--base-snapshot-uuid', default=DEFAULT_VBOX_BASE_SNAPSHOT)
    enroll.add_argument('--snapshot-uuid', default=None)
    enroll.add_argument('--vbox-user-home', default=None)
    enroll.add_argument('--username', default=None)
    enroll.add_argument('--guest-python', default=None)
    enroll.add_argument('--no-sanitize', action='store_true')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cmd = args.command or 'status'
    if cmd == 'status':
        return cmd_status(args)
    if cmd in ('verify', 'verify-wsl2'):
        return cmd_verify(args)
    if cmd == 'enroll-vbox':
        return cmd_enroll_vbox(args)
    if cmd == 'verify-vbox':
        return cmd_verify_vbox(args)
    if cmd == 'test-all':
        return cmd_test_all(args)
    parser.print_help()
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
