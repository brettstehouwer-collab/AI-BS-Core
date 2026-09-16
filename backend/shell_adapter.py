import os
import subprocess
import sys
from typing import Iterable, Sequence


def _coerce_arg(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, os.PathLike)):
        return str(value)
    raise TypeError(f"Unsupported shell argument type: {type(value).__name__}")


def build_command(*parts: Sequence[object]) -> list[str]:
    """Assemble a Windows-safe command without string interpolation.

    This keeps the command shape explicit and avoids shell=True injection risks.
    """
    cmd: list[str] = []
    for part in parts:
        if isinstance(part, (list, tuple)):
            for item in part:
                cmd.append(_coerce_arg(item))
        else:
            cmd.append(_coerce_arg(part))
    return cmd


def run_assembled_command(*parts: Sequence[object], cwd=None, timeout=None, check=False, capture_output=True):
    argv = build_command(*parts)
    if not argv:
        raise ValueError("A shell command must include at least one argument.")
    return subprocess.run(
        argv,
        cwd=cwd,
        timeout=timeout,
        check=check,
        capture_output=capture_output,
        text=True,
        shell=False,
    )


def launch_windows_open(target_path: str):
    """Open a path or URL via the OS without shell string interpolation."""
    if not target_path:
        raise ValueError("A target path or URL is required.")
    if sys.platform == "win32":
        try:
            os.startfile(target_path)  # type: ignore[attr-defined]
            return None
        except AttributeError:
            pass
    return subprocess.Popen(
        ["cmd", "/c", "start", "", str(target_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
