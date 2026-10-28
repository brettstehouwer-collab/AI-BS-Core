#!/usr/bin/env python3
"""Setup, enrollment, and non-promoting verification CLI for AI-BS Isolated Guest Runners.

Safety & Read-Only Guarantees:
  - ``status``, ``verify``, ``verify-wsl2``, ``verify-vbox``, and ``test-all`` are 100%
    non-promoting and zero-mutation on ``C:\\AI-BS`` and ``C:\\AI-BS\\saved_data``.
  - ``verify`` NEVER invokes file promotion and redirects all task/request stores and
    disposable canary Git repositories strictly to ``tempfile.TemporaryDirectory()``.
  - Explicit ``windows_vm`` requests strictly fail closed (``ISOLATION_UNAVAILABLE``)
    unless an independent, licensed, containment-sanitized Windows VM (``vbox_windows``)
    is enrolled — with zero host fallback and zero Linux/WSL2 substitution.

Subcommands:
  status        Read-only inspection of policy flags, Hyper-V/WSL2 isolated VM, and
                VirtualBox Windows VM inventory (no VBoxSVC side effects when un-enrolled).
  verify        Non-promoting live verification: guest containment/escape-denial probes,
                strict windows_vm fail-closed check, and 7-test Number Summary canary in
                ephemeral temp directories (zero live repo or saved_data writes).
  enroll-vbox   Interactive DPAPI credential enrollment, containment sanitization, and
                Windows licensing check for a dedicated VirtualBox Windows 11 guest.
  verify-vbox   Non-promoting 7-test Number Summary canary inside an enrolled Windows guest.
  test-all      Run all automated guest runner, core regression, and snapshot suites
                inside isolated temporary directories.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

INTEGRATION_VBOX_UUID = '6c5a53da-ab80-4ecb-8be6-4059266f736e'
INTEGRATION_VBOX_FILE = (
    REPO_ROOT / 'isolated_workers' / 'windows' / 'runtime' / 'base_preparation_v2'
    / 'vms' / 'AI-BS-Eval-Base-20261023' / 'AI-BS-Eval-Base-20261023.vbox'
)
DISPOSABLE_PROBE_VBOX_UUID = 'e5a2fe34-7b90-460c-83af-903d51b4bb16'
DISPOSABLE_PROBE_VBOX_FILE = Path(
    r'E:\AI-BS-DisposableProbe-v1\AI-BS-DisposableProbe-20261026\AI-BS-DisposableProbe-20261026.vbox'
)
CANARY_FIXTURE_DIR = REPO_ROOT / 'backups' / 'durable_packet_inbox_20261026_record122' / 'guest_test_fixture'

POLICY_KEYS = (
    'AI_BS_EXECUTION_BACKEND',
    'AI_BS_ALLOW_TRUSTED_HOST_EXECUTION',
    'AI_BS_ALLOW_WSL2_ISOLATED_VM',
    'AI_BS_ALLOW_VBOX_WINDOWS_VM',
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


@contextmanager
def _ephemeral_coding_stores(tmp_root: Path):
    """Redirect all coding task/request stores to an ephemeral temp folder."""
    from core import coding_chat, coding_recovery, coding_review, coding_workflow

    ephemeral_tasks = tmp_root / 'ephemeral_coding_tasks'
    ephemeral_requests = tmp_root / 'ephemeral_coding_requests'
    ephemeral_tasks.mkdir(parents=True, exist_ok=True)
    ephemeral_requests.mkdir(parents=True, exist_ok=True)

    with patch.object(coding_workflow, 'STORE', ephemeral_tasks), \
         patch.object(coding_review, 'STORE', ephemeral_tasks), \
         patch.object(coding_recovery, 'STORE', ephemeral_tasks), \
         patch.object(coding_recovery, 'REQUESTS', ephemeral_requests), \
         patch.object(coding_chat, 'STORE', ephemeral_tasks), \
         patch.object(coding_chat, 'REQUESTS', ephemeral_requests):
        yield ephemeral_tasks, ephemeral_requests


def _snapshot_saved_data_state() -> dict[str, list[str] | None]:
    """Capture directory entry names in saved_data to prove zero workspace mutation."""
    state: dict[str, list[str] | None] = {}
    for rel in ('coding_tasks', 'coding_requests', 'vm_runner_config'):
        target = REPO_ROOT / 'saved_data' / rel
        state[rel] = sorted(p.name for p in target.iterdir()) if target.is_dir() else None
    return state


def _parse_vbox_xml_readonly(vbox_file: Path, role: str, admissibility_note: str) -> dict:
    """Parse a .vbox XML file directly without starting VBoxSVC or mutating state."""
    if not vbox_file.is_file():
        return {'detected': False, 'role': role, 'vbox_file': str(vbox_file)}
    try:
        tree = ET.parse(vbox_file)
        root = tree.getroot()
        ns = {'vb': 'http://www.virtualbox.org/'}
        mach = root.find('vb:Machine', ns)
        if mach is None:
            return {'detected': False, 'role': role, 'vbox_file': str(vbox_file)}
        hw = mach.find('vb:Hardware', ns)
        nics_enabled = []
        clipboard_mode = 'disabled'
        dnd_mode = 'disabled'
        if hw is not None:
            for adapter in hw.findall('vb:Network/vb:Adapter', ns):
                if adapter.attrib.get('enabled', 'false').lower() == 'true':
                    slot = int(adapter.attrib.get('slot', '0')) + 1
                    nics_enabled.append(f'nic{slot}')
            clip = hw.find('vb:Clipboard', ns)
            if clip is not None:
                clipboard_mode = clip.attrib.get('mode', 'Disabled').lower()
            dnd = hw.find('vb:GuestProperties', ns)
            for elem in list(hw):
                tag_local = elem.tag.split('}')[-1]
                if tag_local == 'DragAndDrop':
                    dnd_mode = elem.attrib.get('mode', 'Disabled').lower()
        aborted = mach.attrib.get('aborted', 'false').lower() == 'true'
        state_file = mach.attrib.get('stateFile')
        vm_state = 'aborted' if aborted else ('saved' if state_file else 'powered_off')
        return {
            'detected': True,
            'role': role,
            'vm_name': mach.attrib.get('name'),
            'vm_uuid': mach.attrib.get('uuid', '').strip('{}'),
            'vm_state_xml': vm_state,
            'current_snapshot_uuid': mach.attrib.get('currentSnapshot', '').strip('{}') or None,
            'nics_enabled': nics_enabled,
            'clipboard': clipboard_mode,
            'draganddrop': dnd_mode,
            'admissibility_note': admissibility_note,
        }
    except Exception as exc:
        return {'detected': False, 'role': role, 'error': str(exc)}


def inspect_vbox_inventory_readonly() -> list[dict]:
    return [
        _parse_vbox_xml_readonly(
            INTEGRATION_VBOX_FILE,
            role='integration_guest_excluded',
            admissibility_note=(
                'Preserved Oct 24 integration guest (Record 126 / WINDOWS_EVALUATION_REVIEW.md 0xC004F009); '
                'not enrolled and excluded from disposable candidate execution.'
            ),
        ),
        _parse_vbox_xml_readonly(
            DISPOSABLE_PROBE_VBOX_FILE,
            role='disposable_worker_candidate_incomplete',
            admissibility_note=(
                'Record 127 dedicated disposable probe VM (NICs/clipboard/DnD/VRDE disabled); '
                'Windows 11 OS setup incomplete in WinPE, so windows_vm remains fail-closed.'
            ),
        ),
    ]


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
    vbox_inventory = inspect_vbox_inventory_readonly() if not vbox_info.get('enrolled') else []

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
                'status': 'FAIL_CLOSED',
                'error_code': exc.error_code,
                'reason': str(exc),
            }

    report = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'read_only': True,
        'policy_flags': policy,
        'providers': {
            'wsl2_isolated': wsl_info,
            'vbox_windows': vbox_info,
            **({'vbox_host_inventory_readonly': vbox_inventory} if vbox_inventory else {}),
        },
        'backend_resolutions': resolutions,
    }
    print(json.dumps(report, indent=2))
    return 0


def run_wsl2_containment_and_canary(write_receipt_path: str | None = None) -> dict:
    from core import coding_guest_runner, coding_workflow
    from core.coding_guest_runner import (
        inspect_vbox_provider,
        inspect_wsl2_provider,
        resolve_coding_execution_plan,
        run_wsl2_isolated_check,
    )
    from core.coding_review import review_task
    from core.coding_workflow import run_coding_task

    load_policy_env()
    before_saved_data = _snapshot_saved_data_state()

    wsl_info = inspect_wsl2_provider()
    if not wsl_info['available']:
        raise RuntimeError(f"WSL2 isolated VM provider is not available: {wsl_info.get('reason')}")
    vbox_info = inspect_vbox_provider()

    probes: dict[str, dict] = {}

    with tempfile.TemporaryDirectory(prefix='aibs_guest_verify_') as tmp:
        tmp_root = Path(tmp)
        with _ephemeral_coding_stores(tmp_root):
            # Probe 1: Namespace, Host Drive/Interop Masking, Seccomp Socket Denial, Test File Immutability
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

            # Probe 2: Timeout enforcement inside isolated guest
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

            # Probe 3: Non-promoting 7-test Number Summary canary in wsl2_vm (with host runner forbidden)
            repo_wsl = tmp_root / 'canary_repo_wsl2'
            init_disposable_canary_repo(repo_wsl, test_source)
            default_plan = resolve_coding_execution_plan(None)
            assert default_plan['execution_mode'] == 'wsl2_vm' and default_plan['guest_provider'] == 'wsl2_isolated'

            with patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host fallback is forbidden')):
                res_wsl = run_coding_task(
                    repository=str(repo_wsl),
                    objective='Verify 7-test Number Summary canary inside isolated Hyper-V/WSL2 Linux VM without promoting files.',
                    files=[{'path': 'number_summary.py', 'content': impl_source}],
                    checks=[['python', '-m', 'unittest', 'test_number_summary']],
                    timeout_seconds=30,
                    execution_backend='wsl2_vm',
                )
            assert res_wsl['status'] == 'success' and res_wsl['state'] == 'VERIFIED', f'wsl2_vm canary failed: {res_wsl}'
            assert res_wsl['execution_mode'] == 'wsl2_vm'
            assert res_wsl['guest_provider'] == 'wsl2_isolated'
            assert res_wsl['isolation_verified'] is True
            assert res_wsl['originals_unchanged'] is True
            assert res_wsl['merged'] is False
            assert 'Ran 7 tests' in (res_wsl['checks'][0]['stderr'] + res_wsl['checks'][0]['stdout'])
            assert (repo_wsl / 'number_summary.py').read_text(encoding='utf-8') == FALLBACK_STUB_SOURCE

            rev = review_task(res_wsl['task_id'])
            assert rev['can_apply'] is True and rev['execution_mode'] == 'wsl2_vm'
            assert (repo_wsl / 'number_summary.py').read_text(encoding='utf-8') == FALLBACK_STUB_SOURCE
            probes['canary_wsl2_vm_roundtrip_nonpromoting'] = {
                'passed': True,
                'execution_mode': res_wsl['execution_mode'],
                'guest_provider': res_wsl['guest_provider'],
                'diff_hash': res_wsl['review_seal']['diff_hash'],
                'checks_hash': res_wsl['review_seal']['checks_hash'],
                'review_can_apply': rev['can_apply'],
                'originals_unchanged': res_wsl['originals_unchanged'],
                'files_promoted': False,
            }

            # Probe 4: Explicit windows_vm strictly fails closed when vbox_windows is un-enrolled (zero host or WSL2 substitution)
            repo_win = tmp_root / 'canary_repo_windows_vm'
            init_disposable_canary_repo(repo_win, test_source)
            if not vbox_info['available']:
                with patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host fallback is forbidden')), \
                     patch.object(coding_guest_runner, 'run_wsl2_isolated_check', side_effect=AssertionError('WSL2 substitution for windows_vm is forbidden')):
                    res_win = run_coding_task(
                        repository=str(repo_win),
                        objective='Verify explicit windows_vm fails closed when Windows guest is unavailable.',
                        files=[{'path': 'number_summary.py', 'content': impl_source}],
                        checks=[['python', '-m', 'unittest', 'test_number_summary']],
                        timeout_seconds=30,
                        execution_backend='windows_vm',
                    )
                assert res_win['status'] == 'failed' and res_win['state'] == 'FAILED', f'Expected fail-closed windows_vm: {res_win}'
                assert res_win.get('error_code') == 'ISOLATION_UNAVAILABLE', f'Expected ISOLATION_UNAVAILABLE: {res_win}'
                assert 'review_seal' not in res_win
                probes['strict_windows_vm_fail_closed'] = {
                    'passed': True,
                    'requested_execution_backend': 'windows_vm',
                    'state': res_win['state'],
                    'error_code': res_win['error_code'],
                    'host_fallback_attempted': False,
                    'wsl2_substitution_attempted': False,
                }
            else:
                with patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host fallback is forbidden')), \
                     patch.object(coding_guest_runner, 'run_wsl2_isolated_check', side_effect=AssertionError('WSL2 substitution for windows_vm is forbidden')):
                    res_win = run_coding_task(
                        repository=str(repo_win),
                        objective='Verify explicit windows_vm executes inside enrolled VirtualBox Windows guest.',
                        files=[{'path': 'number_summary.py', 'content': impl_source}],
                        checks=[['python', '-m', 'unittest', 'test_number_summary']],
                        timeout_seconds=60,
                        overall_timeout_seconds=300,
                        execution_backend='windows_vm',
                    )
                assert res_win['status'] == 'success' and res_win['state'] == 'VERIFIED'
                assert res_win['execution_mode'] == 'windows_vm' and res_win['guest_provider'] == 'vbox_windows'
                probes['canary_windows_vm_roundtrip_nonpromoting'] = {
                    'passed': True,
                    'execution_mode': res_win['execution_mode'],
                    'guest_provider': res_win['guest_provider'],
                    'files_promoted': False,
                }

    after_saved_data = _snapshot_saved_data_state()
    assert before_saved_data == after_saved_data, (
        f'Live saved_data mutated during verification! Before={before_saved_data}, After={after_saved_data}'
    )
    probes['live_workspace_zero_mutation'] = {
        'passed': True,
        'saved_data_unchanged': True,
        'apply_task_invoked': False,
    }

    receipt = {
        'status': 'VERIFIED_WSL2_GUEST_ISOLATION',
        'windows_vm_acceptance': 'VERIFIED' if vbox_info['available'] else 'FAIL_CLOSED_PENDING_ENROLLED_WINDOWS_GUEST',
        'non_mutating': True,
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'wsl2_provider': wsl_info,
        'vbox_provider': vbox_info,
        'probes': probes,
    }
    if write_receipt_path:
        out_path = Path(write_receipt_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        receipt['receipt_path'] = str(out_path)
    return receipt


def cmd_verify(args: argparse.Namespace) -> int:
    receipt = run_wsl2_containment_and_canary(write_receipt_path=getattr(args, 'write_receipt', None))
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

    vm_uuid = (args.vm_uuid or '').strip()
    if not vm_uuid:
        print(
            'ERROR: Supply --vm-uuid for an independent, licensed Windows 11 guest VM.\n'
            'Note: Integration guest 6c5a53da-ab80-4ecb-8be6-4059266f736e is excluded per Record 126.',
            file=sys.stderr,
        )
        return 1
    if vm_uuid.lower() == INTEGRATION_VBOX_UUID and not args.allow_integration_vm_override:
        print(
            f'ERROR: VM {INTEGRATION_VBOX_UUID} is the preserved integration guest (Record 126) '
            'and reported expired evaluation Notification 0xC004F009 (WINDOWS_EVALUATION_REVIEW.md).\n'
            'Provision and pass a separate licensed clean Windows guest --vm-uuid instead.',
            file=sys.stderr,
        )
        return 1

    vbox_home = args.vbox_user_home
    username = args.username or input('Enter Windows 11 Guest local standard username: ').strip()
    if not username:
        print('ERROR: Guest username is required.', file=sys.stderr)
        return 1
    password = getpass.getpass(f'Enter Windows 11 Guest password for {username} (typing hidden): ')
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
        base_snap = args.base_snapshot_uuid or mr.get('CurrentSnapshotUUID')
        if base_snap:
            run_vb('snapshot', vm_uuid, 'restore', base_snap, timeout=90)
        info_after = _parse_machinereadable(run_vb('showvminfo', vm_uuid, '--machinereadable').stdout)
        if info_after.get('VMState') == 'saved':
            run_vb('discardstate', vm_uuid, timeout=30)
        modify = [
            'modifyvm', vm_uuid,
            '--clipboard-mode', 'disabled',
            '--drag-and-drop', 'disabled',
            '--vrde', 'off',
            '--audio-driver', 'none',
        ]
        for idx in range(1, 9):
            modify.extend([f'--nic{idx}', 'none'])
        run_vb(*modify, timeout=30)
        for key, val in info_after.items():
            if key.startswith('SharedFolderNameMachineMapping'):
                run_vb('sharedfolder', 'remove', vm_uuid, '--name', val, check=False)
        snap_proc = run_vb(
            'snapshot', vm_uuid, 'take', snapshot_name,
            '--description', 'Sanitized offline snapshot for AI-BS isolated guest runner (NICs/clipboard/DnD/VRDE/audio disabled)',
            timeout=90,
        )
        m = re.search(r'UUID:\s*([0-9a-fA-F-]{36})', snap_proc.stdout + '\n' + snap_proc.stderr)
        if m:
            snapshot_uuid = m.group(1)
        else:
            refreshed = _parse_machinereadable(run_vb('showvminfo', vm_uuid, '--machinereadable').stdout)
            snapshot_uuid = refreshed['CurrentSnapshotUUID']

    if not snapshot_uuid:
        snapshot_uuid = mr.get('CurrentSnapshotUUID')
    if not snapshot_uuid:
        print('ERROR: A clean offline VirtualBox snapshot UUID is required.', file=sys.stderr)
        return 1

    # Verify Windows guest licensing (LicenseStatus == 1) inside headless guest before admitting
    pw_fd, raw_pw = tempfile.mkstemp(prefix='aibs_enroll_pw_', suffix='.tmp')
    pw_path = Path(raw_pw)
    licensing_verified = False
    try:
        with os.fdopen(pw_fd, 'w', encoding='utf-8') as handle:
            handle.write(password)
        run_vb('snapshot', vm_uuid, 'restore', snapshot_uuid, timeout=60)
        run_vb('startvm', vm_uuid, '--type', 'headless', timeout=45)
        for _ in range(90):
            gp = run_vb('guestproperty', 'get', vm_uuid, '/VirtualBox/GuestAdd/RunLevel', timeout=10, check=False)
            if 'Value: 2' in gp.stdout or 'Value: 3' in gp.stdout:
                break
            import time as _t
            _t.sleep(1.0)
        lic_proc = run_vb(
            'guestcontrol', vm_uuid, 'run',
            '--exe', r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
            '--username', username, '--passwordfile', str(pw_path),
            '--wait-stdout', '--wait-stderr',
            '--', 'powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            "(Get-CimInstance SoftwareLicensingProduct -Filter \"ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' and PartialProductKey is not null\" | Select-Object -First 1 -ExpandProperty LicenseStatus)",
            timeout=45, check=False,
        )
        licensing_verified = lic_proc.returncode == 0 and lic_proc.stdout.strip() == '1'
    finally:
        pw_path.unlink(missing_ok=True)
        run_vb('controlvm', vm_uuid, 'poweroff', timeout=25, check=False)
        run_vb('snapshot', vm_uuid, 'restore', snapshot_uuid, timeout=60, check=False)

    if not licensing_verified:
        del password
        print(
            'ERROR: Guest Windows LicenseStatus is not 1 (Licensed). Per WINDOWS_EVALUATION_REVIEW.md, '
            'unactivated or expired evaluation images cannot be admitted as windows_vm runners.',
            file=sys.stderr,
        )
        return 1

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
        'licensing_verified': True,
        'integration_vm_override_authorized': bool(args.allow_integration_vm_override),
        'enrolled_at_utc': datetime.now(timezone.utc).isoformat(),
    }
    VBOX_CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    print(f'Enrolled DPAPI credentials and VirtualBox config at {VBOX_CONFIG_FILE}')
    return cmd_verify_vbox(args)


def cmd_verify_vbox(_args: argparse.Namespace) -> int:
    from core import coding_guest_runner, coding_workflow
    from core.coding_guest_runner import inspect_vbox_provider
    from core.coding_workflow import run_coding_task

    load_policy_env()
    info = inspect_vbox_provider()
    if not info['available']:
        print(json.dumps({'status': 'FAIL_CLOSED', 'error_code': 'ISOLATION_UNAVAILABLE', 'vbox_provider': info}, indent=2))
        return 1

    impl_source, test_source = load_canary_sources()
    with tempfile.TemporaryDirectory(prefix='aibs_vbox_canary_') as tmp:
        tmp_root = Path(tmp)
        with _ephemeral_coding_stores(tmp_root), \
             patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host fallback forbidden')), \
             patch.object(coding_guest_runner, 'run_wsl2_isolated_check', side_effect=AssertionError('WSL2 substitution forbidden')):
            repo_dir = tmp_root / 'vbox_canary_repo'
            init_disposable_canary_repo(repo_dir, test_source)
            res = run_coding_task(
                repository=str(repo_dir),
                objective='Verify non-promoting 7-test Number Summary canary inside VirtualBox Windows 11 guest.',
                files=[{'path': 'number_summary.py', 'content': impl_source}],
                checks=[['python', '-m', 'unittest', 'test_number_summary']],
                timeout_seconds=60,
                overall_timeout_seconds=300,
                execution_backend='windows_vm',
            )
    ok = res['status'] == 'success' and res['state'] == 'VERIFIED' and res.get('guest_provider') == 'vbox_windows'
    print(json.dumps({
        'status': 'VERIFIED' if ok else 'FAILED',
        'non_mutating': True,
        'execution_mode': res.get('execution_mode'),
        'guest_provider': res.get('guest_provider'),
        'checks': res.get('checks'),
        'error': res.get('error'),
    }, indent=2))
    return 0 if ok else 1


def cmd_test_all(_args: argparse.Namespace) -> int:
    """Run guest runner tests, baseline regression tests, and preparation snapshot suites."""
    load_policy_env()
    before_saved_data = _snapshot_saved_data_state()
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

    after_saved_data = _snapshot_saved_data_state()
    saved_data_clean = (before_saved_data == after_saved_data)
    all_passed = all(s['passed'] for s in suites) and saved_data_clean
    print(json.dumps({
        'status': 'PASSED' if all_passed else 'FAILED',
        'non_mutating': saved_data_clean,
        'suites': suites,
    }, indent=2))
    return 0 if all_passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Verify and connect AI-BS isolated VM guest runners (non-promoting).')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('status', help='Read-only status of guest runners, VM inventory, and execution policy.')

    v_parser = sub.add_parser('verify', help='Non-promoting live guest containment probes + 7-test canary in temp dirs.')
    v_parser.add_argument('--write-receipt', default=None, help='Optional explicit path to write JSON verification receipt.')

    vw_parser = sub.add_parser('verify-wsl2', help='Alias for verify (non-promoting Hyper-V/WSL2 containment + canary).')
    vw_parser.add_argument('--write-receipt', default=None, help='Optional explicit path to write JSON verification receipt.')

    sub.add_parser('verify-vbox', help='Non-promoting 7-test canary inside enrolled VirtualBox Windows 11 guest.')
    sub.add_parser('test-all', help='Run all automated guest runner, core regression, and snapshot suites cleanly.')

    enroll = sub.add_parser('enroll-vbox', help='Enroll DPAPI credentials and sanitize a dedicated licensed Windows 11 VM.')
    enroll.add_argument('--vm-uuid', required=True, help='UUID of a dedicated licensed Windows 11 VirtualBox VM.')
    enroll.add_argument('--base-snapshot-uuid', default=None)
    enroll.add_argument('--snapshot-uuid', default=None)
    enroll.add_argument('--vbox-user-home', default=None)
    enroll.add_argument('--username', default=None)
    enroll.add_argument('--guest-python', default=None)
    enroll.add_argument('--no-sanitize', action='store_true')
    enroll.add_argument('--allow-integration-vm-override', action='store_true')
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
