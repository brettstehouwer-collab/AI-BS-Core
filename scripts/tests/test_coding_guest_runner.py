"""Automated security, containment, and non-promoting round-trip tests for coding_guest_runner.

All task/request stores and fixture Git repositories are strictly isolated inside
``tempfile.TemporaryDirectory()`` — zero files are written to ``C:\\AI-BS\\saved_data``,
and ``apply_task`` is never invoked.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / 'backend'
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core import coding_chat, coding_guest_runner, coding_recovery, coding_review, coding_workflow  # noqa: E402


STUB_SUMMARY = '''"""Stub implementation."""


def summarize(values):
    return {}
'''

GOOD_SUMMARY = '''"""Disposable AI-BS round-trip canary. Standard library only; no external I/O."""


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

SEVEN_TESTS = '''"""Immutable trusted test specification for the disposable execution guest."""
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


def _create_git_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    env = {
        k: v for k, v in os.environ.items()
        if k.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LOCALAPPDATA'}
    }
    env['GIT_TERMINAL_PROMPT'] = '0'
    subprocess.run(['git', 'init'], cwd=root, env=env, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@aibs.local'], cwd=root, env=env, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'AI-BS Test'], cwd=root, env=env, check=True, capture_output=True)
    (root / 'number_summary.py').write_text(STUB_SUMMARY, encoding='utf-8')
    (root / 'test_number_summary.py').write_text(SEVEN_TESTS, encoding='utf-8')
    subprocess.run(['git', 'add', 'number_summary.py', 'test_number_summary.py'], cwd=root, env=env, check=True, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial canary fixture'], cwd=root, env=env, check=True, capture_output=True)


class CodingGuestRunnerTests(unittest.TestCase):
    def setUp(self):
        self._store_tmp = tempfile.TemporaryDirectory(prefix='aibs_guest_runner_unit_')
        self.addCleanup(self._store_tmp.cleanup)
        tmp_base = Path(self._store_tmp.name)
        ephemeral_tasks = tmp_base / 'coding_tasks'
        ephemeral_requests = tmp_base / 'coding_requests'
        ephemeral_tasks.mkdir(parents=True, exist_ok=True)
        ephemeral_requests.mkdir(parents=True, exist_ok=True)

        for target_mod, attr, val in (
            (coding_workflow, 'STORE', ephemeral_tasks),
            (coding_review, 'STORE', ephemeral_tasks),
            (coding_recovery, 'STORE', ephemeral_tasks),
            (coding_recovery, 'REQUESTS', ephemeral_requests),
            (coding_chat, 'STORE', ephemeral_tasks),
            (coding_chat, 'REQUESTS', ephemeral_requests),
        ):
            p = patch.object(target_mod, attr, val)
            p.start()
            self.addCleanup(p.stop)

    def test_dpapi_encrypt_decrypt_roundtrip(self):
        secret = b'ephemeral-guest-secret-2026!'
        blob = coding_guest_runner.dpapi_encrypt(secret)
        self.assertNotIn(secret, blob)
        self.assertEqual(coding_guest_runner.dpapi_decrypt(blob), secret)
        with self.assertRaises(ValueError):
            coding_guest_runner.dpapi_encrypt(b'')

    def test_bundle_excludes_secrets_git_and_databases(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            _create_git_fixture(work)
            (work / '.env').write_text('SECRET_KEY=never_ship', encoding='utf-8')
            (work / 'private_key.pem').write_text('PRIVATE', encoding='utf-8')
            (work / 'local.sqlite3').write_bytes(b'SQLite format 3')
            (work / 'cred.dpapi').write_bytes(b'dpapi')
            subprocess.run(['git', 'add', '-f', '.env', 'private_key.pem', 'local.sqlite3', 'cred.dpapi'], cwd=work, check=True, capture_output=True)

            files = dict(coding_guest_runner.collect_worktree_files(work, required_paths=('number_summary.py', 'test_number_summary.py')))
            self.assertIn('number_summary.py', files)
            self.assertIn('test_number_summary.py', files)
            self.assertNotIn('.env', files)
            self.assertNotIn('private_key.pem', files)
            self.assertNotIn('local.sqlite3', files)
            self.assertNotIn('cred.dpapi', files)
            self.assertFalse(any(k.startswith('.git') for k in files))

    def test_explicit_windows_vm_strictly_fails_closed_without_host_or_wsl2_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            _create_git_fixture(repo)
            env_overrides = {
                'AI_BS_EXECUTION_BACKEND': 'wsl2_vm',
                'AI_BS_ALLOW_TRUSTED_HOST_EXECUTION': 'true',
                'AI_BS_ALLOW_VBOX_WINDOWS_VM': 'true',
                'AI_BS_ALLOW_WSL2_ISOLATED_VM': 'true',
            }
            unavailable_vbox = {'provider': 'vbox_windows', 'available': False, 'reason': 'No enrolled Windows guest'}
            with patch.dict(os.environ, env_overrides, clear=False), \
                 patch.object(coding_guest_runner, 'inspect_vbox_provider', return_value=unavailable_vbox), \
                 patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host fallback forbidden')), \
                 patch.object(coding_guest_runner, 'run_wsl2_isolated_check', side_effect=AssertionError('WSL2 substitution for windows_vm forbidden')):
                res = coding_workflow.run_coding_task(
                    str(repo),
                    'Explicit windows_vm must strictly fail closed when vbox_windows is unavailable',
                    [{'path': 'number_summary.py', 'content': GOOD_SUMMARY}],
                    [['python', '-m', 'unittest', 'test_number_summary']],
                    execution_backend='windows_vm',
                )
                self.assertEqual(res['status'], 'failed')
                self.assertEqual(res['state'], 'FAILED')
                self.assertEqual(res['error_code'], 'ISOLATION_UNAVAILABLE')
                self.assertNotIn('review_seal', res)

                chat_reply = coding_chat.coding_request({
                    'prompt': f'Fix `number_summary.py` in `{repo}` and verify with `python -m unittest test_number_summary`',
                    'execution_backend': 'windows_vm',
                })
                self.assertTrue(chat_reply.get('coding_error'))
                self.assertEqual(chat_reply.get('error_code'), 'ISOLATION_UNAVAILABLE')

    def test_vbox_provider_isolation_and_licensing_preflight_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / 'vm_cfg'
            cfg_dir.mkdir(parents=True)
            cfg_file = cfg_dir / 'vbox_guest_config.json'
            pw_file = cfg_dir / 'vbox_guest_password.dpapi'
            fake_vbox = cfg_dir / 'VBoxManage.exe'
            fake_vbox.write_bytes(b'MZ')
            pw_file.write_bytes(coding_guest_runner.dpapi_encrypt(b'unit-test-secret'))

            snap_uuid = '11111111-2222-3333-4444-555555555555'
            dedicated_uuid = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'

            with patch.object(coding_guest_runner, 'CONFIG_DIR', cfg_dir), \
                 patch.object(coding_guest_runner, 'VBOX_CONFIG_FILE', cfg_file), \
                 patch.object(coding_guest_runner, 'VBOX_PASSWORD_FILE', pw_file), \
                 patch.object(coding_guest_runner, '_vbox_manage_path', return_value=fake_vbox), \
                 patch.object(coding_guest_runner, '_vbox_env', return_value={}):

                # 1. Preserved integration guest UUID is blocked per Record 126
                cfg_file.write_text(json.dumps({
                    'vm_uuid': '6c5a53da-ab80-4ecb-8be6-4059266f736e',
                    'snapshot_uuid': snap_uuid,
                    'licensing_verified': True,
                }), encoding='utf-8')
                r1 = coding_guest_runner.inspect_vbox_provider()
                self.assertFalse(r1['available'])
                self.assertIn('Record 126', r1['reason'])

                # 2. Unlicensed evaluation guest is blocked per WINDOWS_EVALUATION_REVIEW.md
                cfg_file.write_text(json.dumps({
                    'vm_uuid': dedicated_uuid,
                    'snapshot_uuid': snap_uuid,
                    'licensing_verified': False,
                }), encoding='utf-8')
                r2 = coding_guest_runner.inspect_vbox_provider()
                self.assertFalse(r2['available'])
                self.assertIn('licensing is unverified', r2['reason'])

                # 3. Active NIC / clipboard / VRDE violates isolation preflight
                cfg_file.write_text(json.dumps({
                    'vm_uuid': dedicated_uuid,
                    'snapshot_uuid': snap_uuid,
                    'licensing_verified': True,
                }), encoding='utf-8')
                dirty_vm = MagicMock(
                    returncode=0,
                    stdout=f'nic1="nat"\nclipboard="bidirectional"\nvrde="on"\nCurrentSnapshotUUID="{snap_uuid}"\n',
                    stderr='',
                )
                with patch('core.coding_guest_runner.subprocess.run', return_value=dirty_vm):
                    r3 = coding_guest_runner.inspect_vbox_provider()
                self.assertFalse(r3['available'])
                self.assertIn('nic1=nat', r3['reason'])
                self.assertIn('clipboard=bidirectional', r3['reason'])
                self.assertIn('vrde=on', r3['reason'])

                # 4. Clean, isolated, licensed dedicated Windows VM passes preflight and resolves windows_vm
                clean_lines = '\n'.join([*(f'nic{i}="none"' for i in range(1, 9)),
                                         'clipboard="disabled"', 'draganddrop="disabled"',
                                         'vrde="off"', f'CurrentSnapshotUUID="{snap_uuid}"'])
                clean_vm = MagicMock(returncode=0, stdout=clean_lines, stderr='')
                with patch('core.coding_guest_runner.subprocess.run', return_value=clean_vm), \
                     patch.dict(os.environ, {'AI_BS_ALLOW_VBOX_WINDOWS_VM': 'true'}, clear=False):
                    r4 = coding_guest_runner.inspect_vbox_provider()
                    self.assertTrue(r4['available'])
                    self.assertTrue(r4['isolated'])
                    plan = coding_guest_runner.resolve_coding_execution_plan('windows_vm')
                    self.assertEqual(plan['execution_mode'], 'windows_vm')
                    self.assertEqual(plan['guest_provider'], 'vbox_windows')

    def test_zero_host_fallback_when_wsl2_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / 'repo'
            _create_git_fixture(repo)
            unavailable_wsl = {'provider': 'wsl2_isolated', 'available': False, 'reason': 'WSL2 offline'}
            with patch.dict(os.environ, {'AI_BS_ALLOW_WSL2_ISOLATED_VM': 'true'}, clear=False), \
                 patch.object(coding_guest_runner, 'inspect_wsl2_provider', return_value=unavailable_wsl), \
                 patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host fallback forbidden')):
                res = coding_workflow.run_coding_task(
                    str(repo),
                    'Unavailable WSL2 must fail closed without host fallback',
                    [{'path': 'number_summary.py', 'content': GOOD_SUMMARY}],
                    [['python', '-m', 'unittest', 'test_number_summary']],
                    execution_backend='wsl2_vm',
                )
                self.assertEqual(res['status'], 'failed')
                self.assertEqual(res['error_code'], 'ISOLATION_UNAVAILABLE')

    def test_live_wsl2_containment_escape_denials_and_timeout(self):
        info = coding_guest_runner.inspect_wsl2_provider()
        self.assertTrue(info['available'], f"Expected live WSL2 provider on host: {info}")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / 'test_guard.py').write_text('x = 1\n', encoding='utf-8')
            (work / 'escape_probe.py').write_text(
                """import json, os, socket, subprocess
def sock_status(fam):
    try:
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.close()
        return 'OPEN'
    except OSError as exc:
        return f'{type(exc).__name__}:{exc.errno}'

tamper = None
try:
    open('test_guard.py', 'w').close()
except OSError as exc:
    tamper = type(exc).__name__

cmd_launch = None
try:
    subprocess.run(['/mnt/c/Windows/System32/cmd.exe', '/c', 'echo', 'leak'], timeout=2)
except OSError as exc:
    cmd_launch = type(exc).__name__

print(json.dumps({
    'uid': os.getuid(),
    'gid': os.getgid(),
    'ppid': os.getppid(),
    'mnt': os.listdir('/mnt'),
    'run': os.listdir('/run'),
    'inet': sock_status(socket.AF_INET),
    'inet6': sock_status(socket.AF_INET6),
    'vsock': sock_status(socket.AF_VSOCK),
    'tamper': tamper,
    'cmd': cmd_launch,
}))
""",
                encoding='utf-8',
            )
            ev = coding_guest_runner.run_wsl2_isolated_check(
                ['python', 'escape_probe.py'],
                work,
                required_paths=('escape_probe.py', 'test_guard.py'),
                timeout_seconds=15,
            )
            self.assertEqual(ev['returncode'], 0, msg=str(ev))
            self.assertIsNone(ev.get('error'))
            data = json.loads(ev['stdout'].strip())
            self.assertEqual(data['uid'], 65534)
            self.assertEqual(data['gid'], 65534)
            self.assertEqual(data['ppid'], 1)
            self.assertEqual(data['mnt'], [])
            self.assertEqual(data['run'], [])
            self.assertTrue(data['inet'].startswith('PermissionError:'))
            self.assertTrue(data['inet6'].startswith('PermissionError:'))
            self.assertTrue(data['vsock'].startswith('PermissionError:'))
            self.assertEqual(data['tamper'], 'PermissionError')
            self.assertEqual(data['cmd'], 'FileNotFoundError')

            (work / 'sleep_forever.py').write_text('import time\ntime.sleep(30)\n', encoding='utf-8')
            timeout_ev = coding_guest_runner.run_wsl2_isolated_check(
                ['python', 'sleep_forever.py'],
                work,
                required_paths=('sleep_forever.py',),
                timeout_seconds=1.0,
            )
            self.assertEqual(timeout_ev.get('error'), 'timeout')

            cancel_ev = coding_guest_runner.run_wsl2_isolated_check(
                ['python', 'sleep_forever.py'],
                work,
                required_paths=('sleep_forever.py',),
                timeout_seconds=10.0,
                cancelled=lambda: True,
            )
            self.assertEqual(cancel_ev.get('error'), 'cancelled')

    def test_live_7_test_canary_workflow_review_seal_and_failing_candidate(self):
        env_overrides = {
            'AI_BS_EXECUTION_BACKEND': 'wsl2_vm',
            'AI_BS_ALLOW_WSL2_ISOLATED_VM': 'true',
        }
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, env_overrides, clear=False), \
             patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host runner must NEVER run for VM tasks')):

            # 1. Failing candidate in wsl2_vm produces FAILED without review_seal
            bad_repo = Path(tmp) / 'bad_repo'
            _create_git_fixture(bad_repo)
            bad_res = coding_workflow.run_coding_task(
                str(bad_repo),
                'Broken candidate must fail honestly in isolated guest',
                [{'path': 'number_summary.py', 'content': 'def summarize(values):\n    return {"count": -1}\n'}],
                [['python', '-m', 'unittest', 'test_number_summary']],
                execution_backend='wsl2_vm',
            )
            self.assertEqual(bad_res['status'], 'failed')
            self.assertEqual(bad_res['state'], 'FAILED')
            self.assertNotIn('review_seal', bad_res)

            # 2. Non-promoting 7-test Number Summary canary in wsl2_vm + review_seal + review_task
            good_repo = Path(tmp) / 'good_repo'
            _create_git_fixture(good_repo)
            good_res = coding_workflow.run_coding_task(
                str(good_repo),
                'Implement 7-test Number Summary canary in wsl2_vm',
                [{'path': 'number_summary.py', 'content': GOOD_SUMMARY}],
                [['python', '-m', 'unittest', 'test_number_summary']],
                execution_backend='wsl2_vm',
            )
            self.assertEqual(good_res['status'], 'success')
            self.assertEqual(good_res['state'], 'VERIFIED')
            self.assertEqual(good_res['execution_mode'], 'wsl2_vm')
            self.assertEqual(good_res['guest_provider'], 'wsl2_isolated')
            self.assertTrue(good_res['isolation_verified'])
            self.assertTrue(good_res['originals_unchanged'])
            self.assertFalse(good_res['merged'])
            self.assertIn('Ran 7 tests', good_res['checks'][0]['stderr'] + good_res['checks'][0]['stdout'])
            self.assertEqual((good_repo / 'number_summary.py').read_text(encoding='utf-8'), STUB_SUMMARY)

            rev = coding_review.review_task(good_res['task_id'])
            self.assertTrue(rev['can_apply'])
            self.assertEqual(rev['execution_mode'], 'wsl2_vm')
            self.assertEqual(rev['guest_provider'], 'wsl2_isolated')
            self.assertTrue(rev['isolation_verified'])
            self.assertEqual((good_repo / 'number_summary.py').read_text(encoding='utf-8'), STUB_SUMMARY)

    def test_coding_chat_adapter_end_to_end_isolated_vm(self):
        env_overrides = {
            'AI_BS_EXECUTION_BACKEND': 'wsl2_vm',
            'AI_BS_ALLOW_WSL2_ISOLATED_VM': 'true',
        }
        with tempfile.TemporaryDirectory() as tmp, \
             patch.dict(os.environ, env_overrides, clear=False), \
             patch.object(coding_chat, '_generate', return_value={'files': [{'path': 'number_summary.py', 'content': GOOD_SUMMARY}]}), \
             patch.object(coding_workflow, 'run_bounded_check', side_effect=AssertionError('Host runner forbidden')):
            repo = Path(tmp) / 'chat_repo'
            _create_git_fixture(repo)
            reply = coding_chat.coding_request({
                'prompt': f'Implement `number_summary.py` in `{repo}` and verify with `python -m unittest test_number_summary`',
            })
            self.assertIsNotNone(reply)
            self.assertFalse(reply.get('coding_error', False), msg=str(reply))
            task = reply['coding_task']
            self.assertEqual(task['state'], 'VERIFIED')
            self.assertEqual(task['execution_mode'], 'wsl2_vm')
            self.assertTrue(task['isolation_verified'])
            self.assertEqual((repo / 'number_summary.py').read_text(encoding='utf-8'), STUB_SUMMARY)

    def test_coding_review_card_4_mirror_sha256_parity(self):
        mirrors = [
            REPO_ROOT / 'frontend/src/components/CodingTaskReviewCard.jsx',
            REPO_ROOT / 'frontend/components/CodingTaskReviewCard.jsx',
            REPO_ROOT / 'frontend/src/components/components/CodingTaskReviewCard.jsx',
            REPO_ROOT / 'frontend/components/components/CodingTaskReviewCard.jsx',
        ]
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in mirrors]
        self.assertEqual(len(set(hashes)), 1, f'Mirror drift in CodingTaskReviewCard.jsx: {hashes}')
        text = mirrors[0].read_text(encoding='utf-8')
        self.assertIn("executionMode === 'wsl2_vm'", text)
        self.assertIn("executionMode === 'windows_vm'", text)
        self.assertIn("executionMode === 'trusted_host'", text)


if __name__ == '__main__':
    unittest.main()
