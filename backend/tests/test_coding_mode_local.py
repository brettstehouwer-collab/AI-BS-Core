"""Explicit trusted-local checks against disposable synthetic repositories only."""
import json
import time
import unittest
import uuid
from unittest.mock import patch

import test_coding_mode_execution as fixtures
from core import coding_mode_execution as service
from core import coding_mode_local as local
from core import coding_preparation as preparation


class TrustedLocalTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.CodingModeTests.setUpClass.__func__)
    payload = fixtures.CodingModeTests.payload
    job = fixtures.CodingModeTests.job
    client = fixtures.CodingModeTests.client
    generate = fixtures.CodingModeTests.generate
    fresh_plan = fixtures.CodingModeTests.fresh_plan

    def prepare_and_plan(self):
        if any(f['relative_path'] == 'src/app.py' for f in self.plan['files']):
            (self.repo/'tests/__init__.py').write_bytes(b'')
            (self.repo/'tests/test_app.py').write_text(getattr(self, 'check_source',
                'import unittest, runpy\nclass Check(unittest.TestCase):\n'
                ' def test_value(self):\n  self.assertEqual(runpy.run_path("src/app.py")["value"], 42)\n'), encoding='utf-8')
            if not any(f['relative_path'] == 'tests/__init__.py' for f in self.plan['files']):
                self.plan['files'].append({'relative_path':'tests/__init__.py', 'role':'dependency'})
        fixtures.CodingModeTests.prepare_and_plan(self)

    def setUp(self):
        fixtures.CodingModeTests.setUp(self)
        self.execution.update(execution_backend='trusted_host', trusted_local_ack=True)

    def run_task(self):
        service.prepare_execution(self.owner, self.execution)
        return self.finish()

    def finish(self):
        deadline = time.monotonic()+12
        while time.monotonic() < deadline:
            result = service.read_execution(self.owner, self.execution['execution_id'])
            folder = service._folder(self.owner, self.execution['execution_id'])
            if result['state'] not in {'RUNNING', 'INCOMPLETE'} and not local._active(folder):
                return result
            time.sleep(.025)
        self.fail('Synthetic local check exceeded the bounded test deadline')

    def remake(self):
        self.fresh_plan()
        self.generate()
        self.execution.update(execution_id=uuid.uuid4().hex, request_id=self.plan['request_id'],
                              plan_id=self.plan_id, proposal_id=self.proposal_id)

    def test_actual_python_check_review_and_explicit_apply_preserve_original_backup(self):
        from pathlib import Path
        import win32security
        source = self.repo/'src/app.py'
        stream = Path(str(source)+':coding-fixture')
        stream.write_bytes(b'original alternate stream')
        def source_dacl():
            return win32security.ConvertSecurityDescriptorToStringSecurityDescriptor(
                win32security.GetFileSecurity(str(source), win32security.DACL_SECURITY_INFORMATION),
                win32security.SDDL_REVISION_1, win32security.DACL_SECURITY_INFORMATION)
        dacl = source_dacl()
        result = self.run_task()
        self.assertEqual(result['state'], 'VERIFIED', result)
        self.assertEqual(result['checks'][0]['returncode'], 0)
        self.assertFalse(result['isolation_verified'])
        self.assertEqual((self.repo/'src/app.py').read_bytes(), b'value = 1\n')
        review = service.review_execution(self.owner, self.execution['execution_id'])
        self.assertTrue(review['can_apply'])
        applied = service.apply_execution(self.owner, self.execution['execution_id'], review['review_token'])
        self.assertEqual(applied['application']['state'], 'APPLIED')
        self.assertEqual((self.repo/'src/app.py').read_bytes(), b'value = 42\n')
        self.assertEqual(stream.read_bytes(), b'original alternate stream')
        self.assertEqual(source_dacl(), dacl)
        folder = service._folder(self.owner, self.execution['execution_id'])
        self.assertEqual((folder/'application_backups/src/app.py').read_bytes(), b'value = 1\n')

    def test_actual_node_check_on_retained_javascript(self):
        (self.repo/'src/app.js').write_bytes(b'const value = 1;\n')
        (self.repo/'tests/app.test.cjs').write_bytes(
            b"const test=require('node:test'); const assert=require('node:assert/strict');\n"
            b"test('candidate',()=>assert.match(require('node:fs').readFileSync('src/app.js','utf8'),/value = 42/));\n")
        self.plan['files'] = [{'relative_path':'src/app.js','role':'editable'},
                              {'relative_path':'tests/app.test.cjs','role':'verification'}]
        self.plan['checks'] = [{'check_id':'node','profile':'node_test','targets':['tests/app.test.cjs']}]
        self.remake()
        result = self.run_task()
        self.assertEqual(result['state'], 'VERIFIED', result)
        folder = service._folder(self.owner, self.execution['execution_id'])
        value, _ = service._read(self.owner, self.execution['execution_id'])
        log = local.read_log(folder, value, 'node')['evidence']
        self.assertEqual(log['argv'], [str(local.NODE),'--test','tests/app.test.cjs'])

    def test_actual_npm_selected_script_disables_lifecycle_hooks(self):
        (self.repo/'src/app.js').write_bytes(b'const value = 1;\n')
        package = {'scripts': {'check': 'node --test tests/app.test.cjs',
                              'precheck': 'node -e "process.exit(23)"', 'postcheck': 'node -e "process.exit(24)"'}}
        (self.repo/'package.json').write_text(json.dumps(package), encoding='utf-8')
        (self.repo/'tests/app.test.cjs').write_bytes(
            b"require('node:test')('candidate',()=>require('node:assert/strict').match("
            b"require('node:fs').readFileSync('src/app.js','utf8'),/value = 42/));\n")
        self.plan['files'] = [{'relative_path':'src/app.js','role':'editable'},
            {'relative_path':'tests/app.test.cjs','role':'verification'},
            {'relative_path':'package.json','role':'dependency'},
            {'relative_path':'package-lock.json','role':'dependency'}]
        self.plan['checks'] = [{'check_id':'npm','profile':'npm_script','targets':['check']}]
        self.remake()
        result = self.run_task()
        self.assertEqual(result['state'], 'VERIFIED', result)
        folder = service._folder(self.owner, self.execution['execution_id'])
        value, _ = service._read(self.owner, self.execution['execution_id'])
        self.assertIn('--ignore-scripts', local.read_log(folder, value, 'npm')['evidence']['argv'])

    def test_trusted_ack_required_and_isolated_never_falls_back(self):
        with self.assertRaises(preparation.PreparationScopeError):
            service.prepare_execution(self.owner, {**self.execution, 'trusted_local_ack': False})
        with patch.object(local, 'start', side_effect=AssertionError('No fallback allowed')):
            result = service.prepare_execution(self.owner, {**self.execution,
                'execution_backend':'isolated', 'trusted_local_ack':False})
        self.assertEqual(result['state'], 'BLOCKED')

    def test_repeated_request_and_recovery_never_reexecute_checks(self):
        first = self.run_task()
        with patch.object(local, 'run_bounded_check', side_effect=AssertionError('No replay allowed')):
            self.assertEqual(service.prepare_execution(self.owner, self.execution)['checks'], first['checks'])
            result = service.recover_execution(self.owner, self.execution['execution_id'])
        self.assertFalse(result['replayed'])

    def test_stale_original_rejects_apply_with_previously_issued_token(self):
        self.assertEqual(self.run_task()['state'], 'VERIFIED')
        review = service.review_execution(self.owner, self.execution['execution_id'])
        (self.repo/'src/app.py').write_bytes(b'value = 800\n')
        with self.assertRaises(preparation.PreparationConflict):
            service.apply_execution(self.owner, self.execution['execution_id'], review['review_token'])
        self.assertEqual((self.repo/'src/app.py').read_bytes(), b'value = 800\n')

    def test_resealed_result_cannot_forge_runtime_verification(self):
        self.run_task()
        folder = service._folder(self.owner, self.execution['execution_id'])
        result = preparation._load(folder/'result.json')
        result['checks'][0]['stdout'] = 'forged check output'
        (folder/'result.json').write_text(json.dumps(preparation._sealed(result)), encoding='utf-8')
        self.assertEqual(service.read_execution(self.owner, self.execution['execution_id'])['state'], 'UNCONFIRMED')
        self.assertFalse(service.review_execution(self.owner, self.execution['execution_id'])['can_apply'])

    def test_restart_authority_loss_blocks_apply_without_replay(self):
        self.run_task()
        with patch.object(local, '_KEY', b'new synthetic runtime authority'):
            self.assertEqual(service.read_execution(self.owner, self.execution['execution_id'])['state'], 'UNCONFIRMED')
            self.assertFalse(service.recover_execution(self.owner, self.execution['execution_id'])['replayed'])
            self.assertFalse(service.review_execution(self.owner, self.execution['execution_id'])['can_apply'])

    def test_cancel_actual_slow_check_drains_owned_process(self):
        self.check_source = ('import unittest,time,subprocess,sys,pathlib\nclass Check(unittest.TestCase):\n'
            ' def test_slow(self):\n'
            '  child=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"])\n'
            '  pathlib.Path("owned-child.pid").write_text(str(child.pid))\n'
            '  time.sleep(8)\n')
        self.remake()
        service.prepare_execution(self.owner, self.execution)
        folder = service._folder(self.owner, self.execution['execution_id'])
        pid_file = folder/'candidate/owned-child.pid'
        deadline = time.monotonic()+3
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(.025)
        self.assertTrue(pid_file.exists(), 'Owned synthetic child was not created')
        child_pid = int(pid_file.read_text())
        response = service.cancel_execution(self.owner, self.execution['execution_id'])
        self.assertTrue(response['cancel_requested'])
        result = self.finish()
        self.assertEqual(result['state'], 'CANCELLED', result)
        self.assertFalse(local._active(service._folder(self.owner, self.execution['execution_id'])))
        import psutil
        self.assertFalse(psutil.pid_exists(child_pid), 'Owned check descendant survived cancellation')

    def test_check_modifying_immutable_test_input_fails_but_status_stays_readable(self):
        self.check_source = ('import unittest,pathlib\nclass Check(unittest.TestCase):\n'
            ' def test_mutation(self):\n  pathlib.Path("tests/test_app.py").write_text("# changed")\n')
        self.remake()
        result = self.run_task()
        self.assertEqual(result['state'], 'FAILED', result)
        self.assertIn('changed', result['error'])
        self.assertFalse(service.review_execution(self.owner, self.execution['execution_id'])['can_apply'])

    def test_failed_checks_never_issue_apply_token(self):
        self.check_source = ('import unittest\nclass Check(unittest.TestCase):\n'
                             ' def test_failure(self):\n  self.fail("synthetic failure")\n')
        self.remake()
        result = self.run_task()
        self.assertEqual(result['state'], 'FAILED', result)
        self.assertNotEqual(result['checks'][0]['returncode'], 0)
        self.assertFalse(service.review_execution(self.owner, self.execution['execution_id'])['can_apply'])

    def test_forged_resealed_review_token_does_not_authorize_apply(self):
        self.run_task()
        service.review_execution(self.owner, self.execution['execution_id'])
        folder = service._folder(self.owner, self.execution['execution_id'])
        import hashlib
        review_paths = list(folder.glob('review-*.json'))
        path = review_paths[-1] if review_paths else folder/'local_review.json'
        record = preparation._load(path)
        record['token_sha256'] = hashlib.sha256(b'forged-review-token').hexdigest()
        record['runtime_seal'] = '0'*64
        forged_path = folder/('review-'+hashlib.sha256(b'forged-review-token').hexdigest()+'.json') if review_paths else path
        forged_path.write_text(json.dumps(preparation._sealed(record)), encoding='utf-8')
        with self.assertRaises(preparation.PreparationConflict):
            service.apply_execution(self.owner, self.execution['execution_id'], 'forged-review-token')

    def test_partial_multifile_apply_retains_backups_and_recovery_does_not_replay(self):
        (self.repo/'src/other.py').write_bytes(b'value = 1\n')
        self.plan['files'].append({'relative_path':'src/other.py','role':'editable'})
        self.remake()
        self.assertEqual(self.run_task()['state'], 'VERIFIED')
        review = service.review_execution(self.owner, self.execution['execution_id'])
        actual_replace = local._replace
        calls = []
        def fail_second(destination, staged, backup):
            calls.append(destination)
            if len(calls) == 2:
                raise OSError('Synthetic second-file promotion failure')
            return actual_replace(destination, staged, backup)
        with patch.object(local, '_replace', side_effect=fail_second):
            with self.assertRaises(OSError):
                service.apply_execution(self.owner, self.execution['execution_id'], review['review_token'])
        retained = service.read_execution(self.owner, self.execution['execution_id'])
        self.assertEqual(retained['application']['state'], 'PARTIAL')
        self.assertEqual(retained['application']['completed'], ['src/app.py'])
        self.assertEqual((self.repo/'src/app.py').read_bytes(), b'value = 42\n')
        self.assertEqual((self.repo/'src/other.py').read_bytes(), b'value = 1\n')
        folder = service._folder(self.owner, self.execution['execution_id'])
        self.assertEqual((folder/'application_backups/src/app.py').read_bytes(), b'value = 1\n')
        with patch.object(local, '_replace', side_effect=AssertionError('No recovery replay')):
            recovered = service.recover_execution(self.owner, self.execution['execution_id'])
        self.assertFalse(recovered['replayed'])
        self.assertEqual(recovered['application']['state'], 'PARTIAL')


if __name__ == '__main__':
    unittest.main()
