"""Offline regressions for observable handoff evidence; no VM/provider execution."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_sync import sync_gateway as gateway


class TestEvidence(unittest.TestCase):
    def summary(self, output, code=0, **kwargs):
        return gateway.summarize_test_evidence(['python', '-m', 'unittest'], code,
                                               stderr=output, **kwargs)

    def test_actual_counts_and_complete_evidence_replace_fixed_claims(self):
        output = 'fixture diagnostic\n' * 100 + '\nRan 9 tests in 0.01s\n\nOK\n'
        result = self.summary(output)
        self.assertTrue(result['passed'])
        self.assertEqual(result['counts']['run'], 9)
        self.assertEqual(result['counts']['confirmed_passed'], 9)
        self.assertEqual(result['stderr'], output)
        self.assertEqual(result['stderr_sha256'], hashlib.sha256(output.encode()).hexdigest())
        rendered = gateway.acceptance_markdown(result)
        self.assertIn('run=9', rendered)
        self.assertNotIn('47/47', rendered)
        self.assertNotIn('live wsl2_vm guest isolation', rendered)

    def test_crlf_and_single_test_are_supported(self):
        self.assertTrue(self.summary('Ran 1 test in 0.003s\r\n\r\nOK\r\n')['passed'])

    def test_zero_tests_skips_and_expected_failures_are_incomplete(self):
        for output in ('Ran 0 tests in 0.001s\n\nOK\n',
                       'Ran 7 tests in 0.1s\n\nOK (skipped=2)\n',
                       'Ran 7 tests in 0.1s\n\nOK (expected failures=1)\n'):
            with self.subTest(output=output):
                result = self.summary(output)
                self.assertFalse(result['passed'])
                self.assertEqual(result['status'], 'incomplete')
                self.assertIsNone(result['counts']['confirmed_passed'])

    def test_failures_and_nonzero_exit_cannot_be_overridden_by_ok(self):
        for output, code in [('debug OK\n', 0), ('Ran 2 tests in 0.1s\n\nOK\n', 1),
                             ('Ran 2 tests in 0.1s\n\nFAILED (failures=1, errors=1)\n', 1),
                             ('Ran 2 tests in 0.1s\n\nFAILED (unexpected successes=1)\n', 1)]:
            with self.subTest(output=output):
                self.assertFalse(self.summary(output, code)['passed'])

    def test_multiple_subtest_failures_are_retained_without_inventing_pass_count(self):
        result = self.summary('Ran 1 test in 0.1s\n\nFAILED (failures=3)\n', 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['counts']['failures'], 3)
        self.assertIsNone(result['counts']['confirmed_passed'])

    def test_ambiguous_malformed_or_nonterminal_summary_fails_closed(self):
        for output in ('Ran 1 test in 0.1s\n\nOK\nRan 2 tests in 0.1s\n\nOK\n',
                       'Ran 2 tests in 0.1s\n\nOK (unknown=1)\n',
                       'Ran 2 tests in 0.1s\n\nOK (skipped=1, skipped=1)\n',
                       'Ran 2 tests in -s\n\nOK\n',
                       'Ran 2 tests in 0.1s\n\nOK ()\n',
                       'Ran 2 tests in 0.1s\n\nOK (,,)\n',
                       'Ran 2 tests in 0.1s\n\nOK (skipped=0,)\n',
                       'Ran 2 tests in 0.1s\n\nOK\nnot a completed receipt\n'):
            with self.subTest(output=output):
                self.assertFalse(self.summary(output)['passed'])

    def test_timeout_keeps_partial_output_and_cannot_pass(self):
        partial = b'Ran 2 tests in 0.1s\n\nOK\n'
        with patch.object(gateway.subprocess, 'run', side_effect=subprocess.TimeoutExpired('suite', 120, stderr=partial)):
            result = gateway.run_acceptance_tests()
        self.assertFalse(result['passed'])
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(result['stderr'], partial.decode())
        self.assertIsNone(result['counts']['confirmed_passed'])
        self.assertIsNone(result['returncode'])

    def test_start_failure_and_exact_command_are_recorded(self):
        with patch.object(gateway.subprocess, 'run', side_effect=OSError('fixture start failure')) as run:
            result = gateway.run_acceptance_tests()
        self.assertEqual(result['status'], 'execution_error')
        self.assertFalse(result['passed'])
        self.assertEqual(run.call_args.args[0], result['command'])
        self.assertEqual(run.call_args.kwargs['encoding'], 'utf-8')

    def test_real_tiny_unittest_output_is_accepted(self):
        # Actual stdlib runner on a synthetic fixture, without loading any AI-BS suite.
        code = ('import unittest\nclass T(unittest.TestCase):\n'
                ' def test_fixture(self): self.assertEqual(2 + 2, 4)\n'
                'unittest.main()\n')
        completed = subprocess.run([sys.executable, '-X', 'utf8', '-c', code], capture_output=True,
                                   text=True, encoding='utf-8', timeout=10)
        result = gateway.summarize_test_evidence(completed.args, completed.returncode,
                                                completed.stdout, completed.stderr)
        self.assertTrue(result['passed'])
        self.assertEqual(result['counts']['run'], 1)

    def test_manifest_has_advisory_separation_and_actual_markdown(self):
        failed = self.summary('Ran 3 tests in 0.1s\n\nFAILED (failures=1)\n', 1)
        failed['advisory_judge'] = {'score': 1.0, 'recommendation': 'pass'}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'backend').mkdir()
            for rel in ('AI_BS_MASTER_ARCHITECTURAL_LEDGER.md', 'package.json', 'backend/requirements.txt'):
                (root / rel).write_text('fixture', encoding='utf-8')
            with patch.multiple(gateway, REPO_ROOT=root, MANIFESTS_DIR=root / 'manifests',
                                CRITICAL_FILES=['package.json'], MIRROR_GROUPS={}), \
                    patch.object(gateway, 'get_git_info', return_value={'commit': 'fixture', 'branch': 'fixture'}), \
                    patch.object(gateway, 'run_acceptance_tests', return_value=failed), redirect_stdout(io.StringIO()):
                manifest = gateway.generate_handoff_manifest('fixture', 'fixture', [], 'fixture next step')
            self.assertFalse(manifest['checklist']['5_acceptance_tests'])
            self.assertEqual(manifest['synchronization_score'], '6/7')
            self.assertEqual(manifest['model_quality_evaluation']['status'], 'not_run')
            self.assertFalse(manifest['model_quality_evaluation']['affects_acceptance'])
            text = next((root / 'manifests').glob('*.md')).read_text(encoding='utf-8')
            recorded = json.loads(next((root / 'manifests').glob('*.json')).read_text(encoding='utf-8'))
            self.assertIn('run=3', text)
            self.assertIn('failures=1', text)
            self.assertNotIn('47/47', text)
            self.assertEqual(recorded['acceptance_tests']['stderr'], failed['stderr'])


if __name__ == '__main__':
    unittest.main()
