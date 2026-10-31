"""Exercise legacy validation through injected guest results; no code executes."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class LegacySandboxIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.runner_module = load_file('_audit_sandbox_runner', 'backend/core/ide_orchestrator/sandbox_runner.py')
        self.legacy = load_file('_audit_legacy_executor', 'backend/bullshit_sandbox_executor.py')
        self.temp = tempfile.TemporaryDirectory(prefix='legacy_validation_')
        self.addCleanup(self.temp.cleanup)
        self.legacy.SANDBOX_DIR = str(Path(self.temp.name)/'scratch')
        self.host = patch.object(subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='', stderr='')).start()
        self.addCleanup(patch.stopall)

    def test_unconfigured_ide_never_executes_on_host(self):
        with patch.dict('os.environ', {'AI_BS_EXECUTION_BACKEND': ''}):
            result = self.runner_module.SubprocessSandboxRunner().execute_in_sandbox('demo.py', 'print(1)')
        self.assertEqual(result.status, 'ISOLATION_UNAVAILABLE')
        self.assertFalse(result.patch_applied)
        self.host.assert_not_called()

    def test_unconfigured_legacy_never_falls_back_to_host(self):
        with patch.dict('os.environ', {'AI_BS_EXECUTION_BACKEND': ''}), patch.object(self.legacy.shutil, 'which', return_value=None):
            result = self.legacy.seven_pass_validation('print(1)')
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['state'], 'C')
        self.host.assert_not_called()

    def test_legacy_syntax_failure_has_no_scratch_or_process(self):
        result = self.legacy.seven_pass_validation('def invalid(:')
        self.assertEqual(result['status'], 'FAIL')
        self.assertFalse(Path(self.legacy.SANDBOX_DIR).exists())
        self.host.assert_not_called()

    def test_guest_success_is_validation_not_patch_application(self):
        guest = types.ModuleType('backend.core.coding_guest_runner')
        guest.resolve_coding_execution_plan = Mock(return_value={'isolation_verified': True, 'guest_provider': 'vbox_windows'})
        guest.run_guest_check = Mock(return_value={'returncode': 0, 'stdout': 'ok', 'stderr': '', 'isolated': True})
        with patch.dict('os.environ', {'AI_BS_EXECUTION_BACKEND': 'windows_vm'}), \
                patch.dict(sys.modules, {'backend.core.coding_guest_runner': guest}):
            result = self.runner_module.SubprocessSandboxRunner().execute_in_sandbox('demo.py', 'print(1)')
        self.assertEqual(result.status, 'PASSED')
        self.assertFalse(result.patch_applied)
        self.assertTrue(result.isolation_verified)
        guest.run_guest_check.assert_called_once()
        self.host.assert_not_called()

    def test_forged_nonisolated_success_is_rejected(self):
        guest = types.ModuleType('backend.core.coding_guest_runner')
        guest.resolve_coding_execution_plan = Mock(return_value={'isolation_verified': False})
        guest.run_guest_check = Mock(return_value={'returncode': 0, 'isolated': False})
        with patch.dict('os.environ', {'AI_BS_EXECUTION_BACKEND': 'trusted_host'}), \
                patch.dict(sys.modules, {'backend.core.coding_guest_runner': guest}):
            result = self.runner_module.SubprocessSandboxRunner().execute_in_sandbox('demo.py', 'print(1)')
        self.assertNotEqual(result.status, 'PASSED')
        guest.run_guest_check.assert_not_called()
        self.host.assert_not_called()

    def test_promotion_rejects_forged_success_without_guest_isolation(self):
        sys.modules['sandbox_runner'] = self.runner_module
        evaluator = types.ModuleType('implication_evaluator')
        evaluator.ImplicationRiskEvaluator = Mock()
        evaluator.RiskReport = object
        with patch.dict(sys.modules, {'implication_evaluator': evaluator}):
            promoter = load_file('_audit_patch_promoter', 'backend/core/ide_orchestrator/patch_promoter.py')
        from dataclasses import dataclass
        @dataclass
        class Risk:
            is_blocked: bool = False
        instance = promoter.PatchPromoter(self.temp.name, str(Path(self.temp.name)/'symbols.json'), enable_git_commit=False)
        instance.evaluator.evaluate_patch.return_value = Risk()
        fake = self.runner_module.SandboxResult('PASSED', 0, 0.1, '', '', False, False)
        instance.sandbox_runner.execute_in_sandbox = Mock(return_value=fake)
        result = instance.promote_patch('candidate.py', 'print(1)')
        self.assertEqual(result.status, 'BLOCKED_SANDBOX')
        self.assertFalse((Path(self.temp.name)/'candidate.py').exists())

    def test_promotion_rejects_path_escape_before_read_or_write(self):
        sys.modules['sandbox_runner'] = self.runner_module
        evaluator = types.ModuleType('implication_evaluator')
        evaluator.ImplicationRiskEvaluator = Mock()
        evaluator.RiskReport = object
        with patch.dict(sys.modules, {'implication_evaluator': evaluator}):
            promoter = load_file('_audit_patch_promoter_path', 'backend/core/ide_orchestrator/patch_promoter.py')
        workspace = Path(self.temp.name)/'workspace'
        workspace.mkdir()
        (Path(self.temp.name)/'outside.py').write_text('original', encoding='utf-8')
        instance = promoter.PatchPromoter(str(workspace), str(workspace/'symbols.json'), enable_git_commit=False)
        with patch.object(Path, 'read_text', side_effect=AssertionError('outside path read forbidden')):
            result = instance.promote_patch('../outside.py', 'print(1)')
        self.assertEqual(result.status, 'BLOCKED_PATH')

    def promotion_fixture(self):
        sys.modules['sandbox_runner'] = self.runner_module
        evaluator = types.ModuleType('implication_evaluator')
        evaluator.ImplicationRiskEvaluator = Mock()
        evaluator.RiskReport = object
        with patch.dict(sys.modules, {'implication_evaluator': evaluator}):
            module = load_file('_audit_durable_promoter', 'backend/core/ide_orchestrator/patch_promoter.py')
        from dataclasses import dataclass
        @dataclass
        class Risk:
            is_blocked: bool = False
        instance = module.PatchPromoter(self.temp.name, str(Path(self.temp.name)/'symbols.json'), enable_git_commit=False)
        instance.evaluator.evaluate_patch.return_value = Risk()
        checked = self.runner_module.SandboxResult('PASSED', 0, 0.1, '', '', False, True)
        instance.sandbox_runner.execute_in_sandbox = Mock(return_value=checked)
        target = Path(self.temp.name)/'candidate.py'
        target.write_bytes(b'original source bytes\r\n')
        return instance, target, checked

    def test_partial_temporary_write_preserves_original(self):
        instance, target, checked = self.promotion_fixture()
        factory = tempfile.NamedTemporaryFile
        def partial_file(*args, **kwargs):
            handle = factory(*args, **kwargs)
            write = handle.write
            def partial_write(data):
                write(data[:2])
                raise OSError('fixture partial staging write')
            handle.write = partial_write
            return handle
        with patch.object(tempfile, 'NamedTemporaryFile', side_effect=partial_file):
            result = instance.promote_patch('candidate.py', 'print("new complete source")\n')
        self.assertEqual(result.status, 'FILE_WRITE_ERROR')
        self.assertEqual(target.read_bytes(), b'original source bytes\r\n')
        self.assertFalse(checked.patch_applied)
        self.assertEqual(list(target.parent.glob('.candidate.py.aibs_*.tmp')), [])

    def test_changed_baseline_after_guest_validation_is_preserved(self):
        instance, target, checked = self.promotion_fixture()
        def changed_while_validating(**kwargs):
            target.write_bytes(b'concurrent owner edit\n')
            return checked
        instance.sandbox_runner.execute_in_sandbox.side_effect = changed_while_validating
        result = instance.promote_patch('candidate.py', 'print("stale candidate")\n')
        self.assertEqual(result.status, 'BLOCKED_CONCURRENT')
        self.assertEqual(target.read_bytes(), b'concurrent owner edit\n')
        self.assertFalse(checked.patch_applied)

    def test_successful_publication_uses_atomic_replace(self):
        instance, target, checked = self.promotion_fixture()
        import os
        original_replace = os.replace
        with patch.object(os, 'replace', wraps=original_replace) as replaced:
            result = instance.promote_patch('candidate.py', 'print("complete candidate")\n')
        self.assertEqual(result.status, 'PROMOTED')
        replaced.assert_called_once()
        self.assertEqual(target.read_bytes(), b'print("complete candidate")\n')
        self.assertTrue(checked.patch_applied)
        self.assertEqual(list(target.parent.glob('.candidate.py.aibs_*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
