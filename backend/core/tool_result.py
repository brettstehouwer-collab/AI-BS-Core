"""
tool_result.py — Universal structured response envelope for all AI-BS Matrix tools.

Every tool call in the AI-BS ecosystem must return a ToolResult instead of
raw stdout strings. This enables:

  - Machine-readable status codes (200/400/500)
  - Structured diagnostic traces for trainer_daemon learning
  - Frontend friction modal enrichment (status + suggested fix)
  - ChromaDB reasoning logger ingestion

Usage
-----
    from tool_result import ToolResult, DiagnosticTrace, ok, fail, bad_input

    # Happy path
    result = ok(tool_name="npm_build", stdout="Build successful")

    # Failure with diagnostic
    result = fail(
        tool_name="git_push",
        stderr="Permission denied",
        diagnostics=DiagnosticTrace(
            error_type="AuthError",
            message="Remote rejected push",
            context={"remote": "stehouwer", "branch": "master"},
            suggested_fix="Run: git credential-manager configure",
        ),
    )

    # Serialize for logging / ChromaDB
    log_entry = result.to_dict()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# DiagnosticTrace
# ---------------------------------------------------------------------------


@dataclass
class DiagnosticTrace:
    """
    Structured failure record — emitted by every failing tool.

    This is what trainer_daemon.py learns from and what the Friction modal
    renders for the operator.

    Attributes
    ----------
    error_type : str
        Short machine-readable error class (e.g. "AuthError", "FileNotFound",
        "TimeoutError", "ValidationError").
    message : str
        Human-readable description of what went wrong.
    context : Dict[str, Any]
        Arbitrary key-value pairs giving execution context
        (command, cwd, exit_code, etc.).
    suggested_fix : Optional[str]
        One-line actionable fix for the operator or orchestrator to attempt.
    traceback : Optional[str]
        Full Python traceback string if an exception was raised.
    """

    error_type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_fix: Optional[str] = None
    traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.error_type,
            "message": self.message,
            "context": self.context,
            "suggested_fix": self.suggested_fix,
            "traceback": self.traceback,
        }


# ---------------------------------------------------------------------------
# ToolResult
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    """
    Universal execution envelope returned by every AI-BS Matrix tool.

    Status Codes
    ------------
    200  — Success
    400  — Bad input (validation failed before execution)
    408  — Timeout
    500  — Internal / subprocess error
    503  — Dependency unavailable (ChromaDB, Ollama, etc.)

    Attributes
    ----------
    status : int
        HTTP-style status code.
    tool_name : str
        Name of the tool that produced this result.
    stdout : str
        Raw standard output from the tool.
    stderr : str
        Raw standard error from the tool.
    elapsed_ms : float
        Wall-clock milliseconds the tool took to execute.
    timestamp : str
        ISO-8601 UTC timestamp of when the result was created.
    diagnostics : Optional[DiagnosticTrace]
        Populated only on failure; contains structured error information.
    metadata : Dict[str, Any]
        Arbitrary key-value pairs for tool-specific context
        (e.g. {"sandbox_path": "...", "git_remote": "stehouwer"}).
    """

    status: int
    tool_name: str
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    diagnostics: Optional[DiagnosticTrace] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def ok(self) -> bool:
        """True if the tool completed successfully (status == 200)."""
        return self.status == 200

    @property
    def failed(self) -> bool:
        return not self.ok

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict — suitable for JSONL logging."""
        return {
            "status": self.status,
            "tool_name": self.tool_name,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "timestamp": self.timestamp,
            "diagnostics": self.diagnostics.to_dict() if self.diagnostics else None,
            "metadata": self.metadata,
        }

    def to_friction_payload(self, friction_id: str, action: str) -> Dict[str, Any]:
        """
        Build the WebSocket payload consumed by FrictionManager.broadcast_friction().
        Enriches the existing flat payload with full structured ToolResult data.
        """
        return {
            "type": "FRICTION_REQUIRED",
            "friction_id": friction_id,
            "action": action,
            "tool_result": self.to_dict(),
            # Legacy flat field for backwards-compat with existing frontend
            "diagnostic_trace": (
                self.diagnostics.message if self.diagnostics else self.stderr
            ),
        }

    def __repr__(self) -> str:
        diag = f" | {self.diagnostics.error_type}" if self.diagnostics else ""
        return (
            f"<ToolResult [{self.status}] {self.tool_name}{diag} "
            f"({self.elapsed_ms:.0f}ms)>"
        )


# ---------------------------------------------------------------------------
# Convenience factory functions
# ---------------------------------------------------------------------------


def ok(
    tool_name: str,
    stdout: str = "",
    elapsed_ms: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> ToolResult:
    """Return a successful ToolResult (status=200)."""
    return ToolResult(
        status=200,
        tool_name=tool_name,
        stdout=stdout,
        elapsed_ms=elapsed_ms,
        metadata=metadata or {},
    )


def fail(
    tool_name: str,
    stderr: str = "",
    diagnostics: Optional[DiagnosticTrace] = None,
    status: int = 500,
    elapsed_ms: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> ToolResult:
    """Return a failed ToolResult (status=500 by default)."""
    return ToolResult(
        status=status,
        tool_name=tool_name,
        stderr=stderr,
        elapsed_ms=elapsed_ms,
        diagnostics=diagnostics,
        metadata=metadata or {},
    )


def bad_input(
    tool_name: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> ToolResult:
    """Return a validation-failure ToolResult (status=400)."""
    return ToolResult(
        status=400,
        tool_name=tool_name,
        diagnostics=DiagnosticTrace(
            error_type="ValidationError",
            message=message,
            context=context or {},
            suggested_fix="Review and correct the tool input schema.",
        ),
    )


# ---------------------------------------------------------------------------
# Timer context manager — measure elapsed_ms automatically
# ---------------------------------------------------------------------------


class timed:
    """
    Context manager that captures wall-clock time and injects it into a ToolResult.

    Usage
    -----
        with timed() as t:
            # ... do work ...
        result = ok(tool_name="my_tool", stdout=output, elapsed_ms=t.ms)
    """

    def __enter__(self) -> "timed":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: object) -> None:
        self.ms = (time.perf_counter() - self._start) * 1000

    @property
    def ms(self) -> float:
        return self._ms

    @ms.setter
    def ms(self, value: float) -> None:
        self._ms = value
