from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from shell_adapter import build_command

TRUSTED_BASES: tuple[Path, ...] = (
    Path(r"C:\AI-BS"),
    Path(r"D:\AI-BS"),
    Path(r"E:\AI_BS_Resources"),
    Path.home(),
)

_DESTRUCTIVE_ACTIONS = {
    "open_path": {
        "risk": "medium",
        "description": "Open a local file or folder via the OS shell handler.",
        "requires": ["path"],
    },
    "terminate_process": {
        "risk": "high",
        "description": "Terminate a specific PID only, with the target process id required.",
        "requires": ["pid"],
    },
}

WINDOWS_SAFE_ACTIONS = {
    "list_directory": {
        "risk": "low",
        "description": "List directory contents using cmd.exe /c dir without modifying any file or process.",
        "requires": ["path"],
    },
    "read_file": {
        "risk": "medium",
        "description": "Read a file using PowerShell Get-Content for diagnostic review only.",
        "requires": ["path"],
    },
    "git_status": {
        "risk": "low",
        "description": "Check repository status without mutating files.",
        "requires": ["repo_path"],
    },
    "process_list": {
        "risk": "low",
        "description": "Enumerate system process metadata without termination.",
        "requires": [],
    },
    "run_python_script": {
        "risk": "medium",
        "description": "Run a Python script already under the trusted workspace; this is still restricted to trusted local users.",
        "requires": ["script"],
    },
}

ALLOWED_ACTIONS = dict(WINDOWS_SAFE_ACTIONS)

_ALLOW_DESTRUCTIVE_ACTIONS = os.getenv("AI_BS_ALLOW_DESTRUCTIVE_ACTIONS", "0").strip().lower() in {"1", "true", "yes", "on"}
if _ALLOW_DESTRUCTIVE_ACTIONS:
    ALLOWED_ACTIONS.update(_DESTRUCTIVE_ACTIONS)

PRIVILEGED_ACTIONS = set(_DESTRUCTIVE_ACTIONS)
ACTION_ALLOWLIST = set(ALLOWED_ACTIONS)


def get_action_policy(action: str) -> dict[str, Any]:
    return dict(ALLOWED_ACTIONS.get(action, {}))


def list_allowed_actions() -> List[str]:
    return sorted(ACTION_ALLOWLIST)


def _is_within_trusted_base(target: Path) -> bool:
    resolved = target.resolve(strict=False)
    for base in TRUSTED_BASES:
        base_str = str(base).lower()
        resolved_str = str(resolved).lower()
        if resolved_str == base_str or resolved_str.startswith(base_str + os.sep):
            return True
    return False


def _safe_path(raw: str | os.PathLike[str] | None, default: str | None = None) -> Path:
    candidate = raw or default or str(Path.cwd())
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve(strict=False)
    if not _is_within_trusted_base(path):
        raise ValueError(f"Path '{path}' is outside the trusted local workspace: {TRUSTED_BASES}")
    return path


def _validate_pid(raw: Any) -> int:
    if isinstance(raw, bool):
        raise ValueError("PID must be an integer, not a boolean.")
    try:
        pid = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("PID must be an integer.") from exc
    if pid <= 0 or pid > 65535:
        raise ValueError("PID must be a positive integer under 65535.")
    return pid


def build_trusted_command(action: str, parameters: Dict[str, Any] | None = None, cwd: str | os.PathLike[str] | None = None) -> Dict[str, Any]:
    """Build a Windows-safe argv array from an explicit allowlist of actions."""
    if action not in ACTION_ALLOWLIST:
        raise ValueError(f"Action '{action}' is not in the local allowlist: {list_allowed_actions()}")

    params = parameters or {}
    base_cwd = _safe_path(cwd or Path.cwd(), default=str(Path.cwd()))

    if action == "list_directory":
        target = _safe_path(params.get("path"), default=str(base_cwd))
        return {
            "cwd": str(base_cwd),
            "argv": build_command("cmd", "/c", "dir", str(target)),
        }

    if action == "read_file":
        target = _safe_path(params.get("path"), default=str(base_cwd))
        return {
            "cwd": str(base_cwd),
            "argv": build_command(
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"Get-Content -LiteralPath '{str(target)}' -Raw",
            ),
        }

    if action == "open_path":
        target = _safe_path(params.get("path"), default=str(base_cwd))
        return {
            "cwd": str(base_cwd),
            "argv": build_command("explorer.exe", str(target)),
        }

    if action == "run_python_script":
        script = _safe_path(params.get("script"), default=str(base_cwd / "main.py"))
        extra_args = params.get("args", [])
        if isinstance(extra_args, str):
            extra_args = [extra_args]
        return {
            "cwd": str(base_cwd),
            "argv": build_command(sys.executable, str(script), *extra_args),
        }

    if action == "git_status":
        repo = _safe_path(params.get("repo_path"), default=str(base_cwd))
        return {
            "cwd": str(repo),
            "argv": build_command("git", "status", "--short", "--branch"),
        }

    if action == "process_list":
        return {
            "cwd": str(base_cwd),
            "argv": build_command(
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process | Select-Object Id, Name, CPU, WorkingSet | Format-Table -AutoSize",
            ),
        }

    if action == "terminate_process":
        pid = _validate_pid(params.get("pid"))
        return {
            "cwd": str(base_cwd),
            "argv": build_command("taskkill", "/PID", str(pid), "/F", "/T"),
        }

    raise ValueError(f"Unsupported local automation action: {action}")
