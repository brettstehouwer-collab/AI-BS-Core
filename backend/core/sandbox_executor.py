"""
sandbox_executor.py — Universal sandbox layer for AI-BS Matrix tool execution.

Every tool call that mutates the filesystem or runs a shell command first
operates in a sandboxed copy under /sandbox/dry_run/<timestamp>/. Only if
the dry-run succeeds does the executor sync changes back to the project root.

This enforces the "Pre-Crime Sandbox" principle from the Stehouwer Reality
standard: the project root is NEVER touched if the sandbox run fails.

Supported operations
--------------------
- ShellCommand   — executes the argv in a sandboxed CWD
- FileOp         — reads/writes/deletes in a sandboxed copy of the target path

Integration
-----------
The SandboxExecutor is the final execution layer after:
  1. Pydantic schema validation (tool_schemas.py)
  2. FrictionManager approval gate (friction_manager.py)
  3. AgentState step checkpoint (agent_state.py)

Usage
-----
    from sandbox_executor import SandboxExecutor
    from tool_schemas import ShellCommand
    from pathlib import Path

    executor = SandboxExecutor()

    cmd = ShellCommand(
        command="npm",
        args=["run", "build"],
        cwd=Path("frontend"),
        sandbox=True,
    )
    result = executor.run(cmd)
    if result.ok:
        print("Build succeeded — changes synced to project root")
    else:
        print(f"Build failed in sandbox — project root untouched")
        print(result.diagnostics)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from tool_result import DiagnosticTrace, ToolResult, fail, ok, timed
from tool_schemas import FileOp, ShellCommand

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SANDBOX_BASE = WORKSPACE_ROOT / "sandbox" / "dry_run"


# ---------------------------------------------------------------------------
# SandboxExecutor
# ---------------------------------------------------------------------------


class SandboxExecutor:
    """
    Wraps ShellCommand and FileOp execution in a sandboxed dry-run.

    The project root is NEVER modified if the sandboxed operation fails.

    Parameters
    ----------
    sandbox_base : Path
        Root directory for sandbox copies. Defaults to /sandbox/dry_run/.
    keep_sandbox : bool
        If False (default), the sandbox directory is removed after execution.
        Set to True during debugging to inspect the sandbox state.
    """

    def __init__(
        self,
        sandbox_base: Path = SANDBOX_BASE,
        keep_sandbox: bool = False,
    ) -> None:
        self.sandbox_base = sandbox_base
        self.keep_sandbox = keep_sandbox
        self.sandbox_base.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, op: Union[ShellCommand, FileOp]) -> ToolResult:
        """
        Execute an operation with optional sandbox isolation.

        If op.sandbox is False, the operation runs directly (used only for
        operations that are explicitly marked safe, e.g. read-only file ops).
        """
        if isinstance(op, ShellCommand):
            if not op.sandbox:
                return self._run_direct_shell(op)
            return self._run_sandboxed_shell(op)
        elif isinstance(op, FileOp):
            if (
                op.operation == "read" or not op.sandbox
                if hasattr(op, "sandbox")
                else False
            ):
                return self._run_direct_file(op)
            return self._run_sandboxed_file(op)
        else:
            return fail(
                tool_name="sandbox_executor",
                stderr=f"Unsupported operation type: {
                    type(op).__name__}",
                status=400,
                diagnostics=DiagnosticTrace(
                    error_type="UnsupportedOperation",
                    message=f"SandboxExecutor does not support {
                        type(op).__name__}",
                    suggested_fix="Pass a ShellCommand or FileOp instance.",
                ),
            )

    # ------------------------------------------------------------------
    # ShellCommand execution
    # ------------------------------------------------------------------

    def _run_sandboxed_shell(self, cmd: ShellCommand) -> ToolResult:
        """
        Run a ShellCommand in a sandboxed copy of cmd.cwd.
        On success: sync changed files back to project root.
        On failure: return ToolResult(500) — project root untouched.
        """
        sandbox_path = self._setup_sandbox_dir(cmd.cwd)
        tool_name = f"sandbox_shell:{cmd.command}"
        logger.info(
            "SandboxExecutor: running %s in sandbox %s", cmd.full_argv, sandbox_path
        )

        with timed() as t:
            result = self._execute_subprocess(cmd, cwd=sandbox_path)

        result.elapsed_ms = t.ms
        result.tool_name = tool_name
        result.metadata["sandbox_path"] = str(sandbox_path)
        result.metadata["project_cwd"] = str(cmd.cwd)

        if result.ok:
            logger.info(
                "SandboxExecutor: sandbox run succeeded — syncing to %s", cmd.cwd
            )
            sync_result = self._sync_to_root(sandbox_path, cmd.cwd)
            if not sync_result:
                result = fail(
                    tool_name=tool_name,
                    stderr="Sandbox succeeded but sync to project root failed",
                    diagnostics=DiagnosticTrace(
                        error_type="SyncError",
                        message="Could not sync sandbox output to project root",
                        context={
                            "sandbox_path": str(sandbox_path),
                            "cwd": str(cmd.cwd),
                        },
                        suggested_fix="Check filesystem permissions on the project root.",
                    ),
                    elapsed_ms=t.ms,
                )
        else:
            logger.warning(
                "SandboxExecutor: sandbox run FAILED (%d) — project root untouched. stderr: %s",
                result.status,
                result.stderr[:200],
            )

        if not self.keep_sandbox:
            self._cleanup(sandbox_path)

        return result

    def _run_direct_shell(self, cmd: ShellCommand) -> ToolResult:
        """Run a ShellCommand directly on the project root (sandbox=False only)."""
        tool_name = f"direct_shell:{cmd.command}"
        logger.info("SandboxExecutor: DIRECT run %s in %s", cmd.full_argv, cmd.cwd)
        with timed() as t:
            result = self._execute_subprocess(cmd, cwd=cmd.cwd)
        result.elapsed_ms = t.ms
        result.tool_name = tool_name
        return result

    def _execute_subprocess(self, cmd: ShellCommand, cwd: Path) -> ToolResult:
        """Run the subprocess and capture stdout/stderr."""
        env = os.environ.copy()
        env.update(cmd.env_overrides)
        try:
            proc = subprocess.run(
                cmd.full_argv,
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=cmd.timeout,
            )
            if proc.returncode == 0:
                return ok(
                    tool_name=cmd.command,
                    stdout=proc.stdout,
                    metadata={"exit_code": 0, "cwd": str(cwd)},
                )
            else:
                return fail(
                    tool_name=cmd.command,
                    stderr=proc.stderr or proc.stdout,
                    status=500,
                    diagnostics=DiagnosticTrace(
                        error_type="SubprocessError",
                        message=f"Command exited with code {proc.returncode}",
                        context={
                            "argv": cmd.full_argv,
                            "exit_code": proc.returncode,
                            "cwd": str(cwd),
                            "stderr_preview": proc.stderr[:500],
                        },
                        suggested_fix=(
                            "Check the command arguments and ensure dependencies are installed."
                        ),
                    ),
                )
        except subprocess.TimeoutExpired:
            return fail(
                tool_name=cmd.command,
                stderr=f"Command timed out after {cmd.timeout}s",
                status=408,
                diagnostics=DiagnosticTrace(
                    error_type="TimeoutError",
                    message=f"{cmd.command} did not complete within {cmd.timeout}s",
                    context={"argv": cmd.full_argv, "timeout": cmd.timeout},
                    suggested_fix="Increase ShellCommand.timeout or investigate slow command.",
                ),
            )
        except FileNotFoundError:
            return fail(
                tool_name=cmd.command,
                stderr=f"Executable not found: {cmd.command}",
                status=400,
                diagnostics=DiagnosticTrace(
                    error_type="FileNotFoundError",
                    message=f"Executable '{cmd.command}' not found in PATH",
                    context={"command": cmd.command, "cwd": str(cwd)},
                    suggested_fix=f"Ensure '{cmd.command}' is installed and on PATH.",
                ),
            )
        except Exception as exc:
            return fail(
                tool_name=cmd.command,
                stderr=str(exc),
                status=500,
                diagnostics=DiagnosticTrace(
                    error_type=type(exc).__name__,
                    message=str(exc),
                    context={"argv": cmd.full_argv},
                ),
            )

    # ------------------------------------------------------------------
    # FileOp execution
    # ------------------------------------------------------------------

    def _run_sandboxed_file(self, op: FileOp) -> ToolResult:
        """
        Execute a write/delete FileOp in a sandboxed copy of the target path.
        On success: overwrite the real file.
        On failure: real file untouched.
        """
        tool_name = f"sandbox_file:{op.operation}"
        sandbox_path = self._setup_sandbox_file(op.path)

        with timed() as t:
            result = self._execute_file_op(op, target=sandbox_path)

        result.elapsed_ms = t.ms
        result.tool_name = tool_name

        if result.ok:
            try:
                if op.operation == "delete":
                    op.path.unlink(missing_ok=True)
                else:
                    op.path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(sandbox_path, op.path)
                logger.info(
                    "SandboxExecutor: file op '%s' synced to %s", op.operation, op.path
                )
            except Exception as exc:
                return fail(
                    tool_name=tool_name,
                    stderr=str(exc),
                    diagnostics=DiagnosticTrace(
                        error_type="SyncError",
                        message=f"Sandbox file op succeeded but sync to {
                            op.path} failed",
                        context={"path": str(op.path), "error": str(exc)},
                        suggested_fix="Check filesystem permissions.",
                    ),
                    elapsed_ms=t.ms,
                )

        if not self.keep_sandbox and sandbox_path.exists():
            sandbox_path.unlink(missing_ok=True)

        return result

    def _run_direct_file(self, op: FileOp) -> ToolResult:
        """Execute a read FileOp directly (no sandbox needed for reads)."""
        with timed() as t:
            result = self._execute_file_op(op, target=op.path)
        result.elapsed_ms = t.ms
        result.tool_name = f"direct_file:{op.operation}"
        return result

    def _execute_file_op(self, op: FileOp, target: Path) -> ToolResult:
        try:
            if op.operation == "read":
                content = target.read_text(encoding=op.encoding)
                return ok(tool_name="file_read", stdout=content)
            elif op.operation == "write":
                if op.idempotent_check and target.exists():
                    existing = target.read_text(encoding=op.encoding)
                    if existing == op.content:
                        return ok(
                            tool_name="file_write",
                            stdout="Skipped (content unchanged — idempotent)",
                        )
                if op.create_parents:
                    target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(op.content or "", encoding=op.encoding)
                return ok(tool_name="file_write", stdout=f"Written: {target}")
            elif op.operation == "delete":
                target.unlink(missing_ok=True)
                return ok(tool_name="file_delete", stdout=f"Deleted: {target}")
            else:
                return fail(
                    tool_name="file_op",
                    stderr=f"Unknown operation: {op.operation}",
                    status=400,
                )
        except Exception as exc:
            return fail(
                tool_name=f"file_{op.operation}",
                stderr=str(exc),
                diagnostics=DiagnosticTrace(
                    error_type=type(exc).__name__,
                    message=str(exc),
                    context={"path": str(target), "operation": op.operation},
                ),
            )

    # ------------------------------------------------------------------
    # Sandbox setup / teardown
    # ------------------------------------------------------------------

    def _setup_sandbox_dir(self, source_cwd: Path) -> Path:
        """
        Create a sandbox directory and copy the source CWD into it.
        Only copies files (not node_modules or .git) to keep it fast.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        sandbox_path = self.sandbox_base / ts
        sandbox_path.mkdir(parents=True, exist_ok=True)

        EXCLUDE = {
            "node_modules",
            ".git",
            "build-output",
            "__pycache__",
            "stehouwer_vector_memory",
        }

        for item in source_cwd.iterdir():
            if item.name in EXCLUDE:
                continue
            dest = sandbox_path / item.name
            try:
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            except Exception as exc:
                logger.warning("SandboxExecutor: could not copy %s — %s", item, exc)

        logger.debug("SandboxExecutor: sandbox ready at %s", sandbox_path)
        return sandbox_path

    def _setup_sandbox_file(self, path: Path) -> Path:
        """Create a sandbox copy of a single file."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        sandbox_path = self.sandbox_base / ts / path.name
        sandbox_path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            shutil.copy2(path, sandbox_path)
        return sandbox_path

    def _sync_to_root(self, sandbox_path: Path, root_cwd: Path) -> bool:
        """Copy changed files from sandbox back to the real project directory."""
        try:
            for item in sandbox_path.iterdir():
                dest = root_cwd / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            return True
        except Exception as exc:
            logger.error("SandboxExecutor: sync failed — %s", exc)
            return False

    def _cleanup(self, sandbox_path: Path) -> None:
        """Remove the sandbox directory after execution."""
        try:
            shutil.rmtree(sandbox_path, ignore_errors=True)
            logger.debug("SandboxExecutor: cleaned up %s", sandbox_path)
        except Exception as exc:
            logger.warning("SandboxExecutor: cleanup failed — %s", exc)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

sandbox_executor = SandboxExecutor()
