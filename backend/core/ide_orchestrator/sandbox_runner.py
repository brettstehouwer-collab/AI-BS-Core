"""Compatibility adapter for isolated guest validation, with no host fallback.

A temporary working directory and sanitized environment are not an OS sandbox.
The legacy class name remains for callers, but generated code is dispatched only
through the existing VM guest providers. Validation never applies a host patch.
"""
from __future__ import annotations

import ast
import math
import os
from dataclasses import dataclass
from pathlib import Path
import tempfile
import time
from typing import Optional


@dataclass
class SandboxResult:
    status: str
    exit_code: int
    execution_time_sec: float
    stdout: str
    stderr: str
    patch_applied: bool
    isolation_verified: bool = False


class SubprocessSandboxRunner:
    def __init__(self, default_timeout_sec: float = 10.0):
        self.default_timeout_sec = default_timeout_sec

    def execute_in_sandbox(
        self,
        original_file_path: str,
        modified_code: str,
        test_script_code: Optional[str] = None,
        timeout_sec: Optional[float] = None,
    ) -> SandboxResult:
        started = time.perf_counter()

        def result(status, message='', *, code=-1, stdout='', isolated=False):
            return SandboxResult(status, code, round(time.perf_counter()-started, 4),
                                 stdout, message, False, isolated)

        try:
            ast.parse(modified_code)
            if test_script_code is not None:
                ast.parse(test_script_code)
            timeout = float(self.default_timeout_sec if timeout_sec is None else timeout_sec)
            if not math.isfinite(timeout) or not 0 < timeout <= 300:
                raise ValueError('Validation timeout must be finite and between 0 and 300 seconds')
        except (SyntaxError, TypeError, ValueError) as exc:
            return result('EXECUTION_ERROR', f'Candidate validation failed: {exc}')

        requested = os.environ.get('AI_BS_EXECUTION_BACKEND', '').strip()
        if requested not in ('windows_vm', 'wsl2_vm'):
            return result('ISOLATION_UNAVAILABLE',
                          'Select a configured windows_vm or wsl2_vm provider. Host execution is not a sandbox.')
        try:
            try:
                from backend.core.coding_guest_runner import resolve_coding_execution_plan, run_guest_check
            except ModuleNotFoundError:
                from core.coding_guest_runner import resolve_coding_execution_plan, run_guest_check
            plan = resolve_coding_execution_plan(requested)
            if plan.get('isolation_verified') is not True:
                return result('ISOLATION_UNAVAILABLE', 'The selected provider did not verify isolation.')
            with tempfile.TemporaryDirectory(prefix='ide_guest_validation_') as folder:
                work = Path(folder)
                # The original path is identity only; never read or modify it.
                target = Path(original_file_path).name
                if not target.endswith('.py') or target == '_runner_entrypoint.py':
                    return result('EXECUTION_ERROR', 'Candidate must have a distinct Python filename.')
                (work/target).write_text(modified_code, encoding='utf-8')
                if test_script_code is None:
                    # runpy handles filenames that are not import identifiers.
                    test_script_code = f'import runpy\nrunpy.run_path({target!r}, run_name="__candidate__")\n'
                (work/'_runner_entrypoint.py').write_text(test_script_code, encoding='utf-8')
                checked = run_guest_check(
                    plan, ['python', '-B', '_runner_entrypoint.py'], work,
                    required_paths=(target, '_runner_entrypoint.py'),
                    timeout_seconds=timeout, output_limit=262144,
                )
            isolated = checked.get('isolated') is True
            if not isolated:
                return result('ISOLATION_UNAVAILABLE', 'Guest response did not verify isolation.')
            exit_code = checked.get('returncode')
            error = checked.get('error')
            if error:
                return result('TIMEOUT' if 'timeout' in str(error).lower() else 'EXECUTION_ERROR',
                              str(error), stdout=str(checked.get('stdout', '')), isolated=isolated)
            passed = type(exit_code) is int and exit_code == 0
            return result('PASSED' if passed else 'FAILED', str(checked.get('stderr', '')),
                          code=exit_code if type(exit_code) is int else -1,
                          stdout=str(checked.get('stdout', '')), isolated=isolated)
        except Exception as exc:
            return result('ISOLATION_UNAVAILABLE', f'Isolated validation unavailable: {exc}')
