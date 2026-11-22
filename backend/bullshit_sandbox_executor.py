"""Legacy response adapter; generated source never runs on the host.

The historical seven-pass name remains for compatibility. A passing result means
syntax plus one isolated guest execution succeeded, not seven independent proofs.
Existing VM provider controls remain authoritative.
"""
from __future__ import annotations

import ast
import os
import shutil  # retained for callers inspecting legacy dependency availability

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DIR = os.path.join(BASE_DIR, 'sandbox_scratch')  # historical identity only


def seven_pass_validation(code_content: str) -> dict:
    try:
        ast.parse(code_content)
    except (SyntaxError, TypeError, ValueError) as exc:
        return {'status': 'FAIL', 'reason': f'Syntax Error: {exc}', 'state': 'C',
                'isolation_verified': False, 'patch_applied': False}
    try:
        try:
            from backend.core.ide_orchestrator.sandbox_runner import SubprocessSandboxRunner
        except ModuleNotFoundError:
            from core.ide_orchestrator.sandbox_runner import SubprocessSandboxRunner
        checked = SubprocessSandboxRunner(default_timeout_sec=15.0).execute_in_sandbox(
            original_file_path='candidate.py', modified_code=code_content,
        )
    except Exception as exc:
        return {'status': 'FAIL', 'reason': f'Isolated validation unavailable: {exc}', 'state': 'C',
                'isolation_verified': False, 'patch_applied': False}
    if checked.status != 'PASSED' or checked.isolation_verified is not True:
        return {'status': 'FAIL', 'reason': checked.stderr or checked.status, 'state': 'C',
                'isolation_verified': checked.isolation_verified, 'patch_applied': False}
    return {'status': 'PASS', 'execution_time_sec': checked.execution_time_sec,
            'output': checked.stdout, 'state': 'A' if checked.execution_time_sec > 2.0 else 'B',
            'isolation_verified': True, 'patch_applied': False,
            'verification_scope': 'syntax_and_one_guest_execution'}
