# File: c:/AI-BS/codex_pipe.py
import os
from pathlib import Path
import subprocess
import sys
from typing import List


DEFAULT_TIMEOUT_SECONDS: int = 120


def resolve_python_executable() -> str:
    venv_python: Path = Path(r"C:\AI-BS\pyppeteer_env\Scripts\python.exe")
    if venv_python.exists():
        return str(venv_python)
    return sys.executable if sys.executable else "python"


def resolve_executor_script() -> str:
    candidates: List[Path] = [
        Path(__file__).resolve().parent / "sandbox_executor.py",
        Path(r"C:\AI-BS\sandbox_executor.py"),
        Path(r"C:\AI-BS\backend\sandbox_executor.py"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "sandbox_executor.py"


def route_payload() -> int:
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    raw_payload: str = sys.stdin.read()

    if not raw_payload.strip():
        print("FATAL: Empty payload received from Phase I.")
        return 1

    cmd: List[str] = [
        resolve_python_executable(),
        resolve_executor_script(),
        "--mode",
        "strict-ingest",
    ]

    try:
        codex_process: subprocess.CompletedProcess[str] = subprocess.run(
            cmd,
            input=raw_payload,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            check=False,
            env=dict(os.environ),
        )
    except subprocess.TimeoutExpired as exc:
        print(f"CODEX REJECTION LOG:\nSandbox execution timed out after {exc.timeout}s.")
        return 124
    except OSError as exc:
        print(f"CODEX REJECTION LOG:\nProcess invocation error: {exc}")
        return 127

    if codex_process.stdout:
        print(codex_process.stdout.rstrip("\r\n"))

    if codex_process.returncode != 0:
        print(f"CODEX REJECTION LOG:\n{codex_process.stderr}")
        return int(codex_process.returncode)

    return 0


if __name__ == "__main__":
    sys.exit(route_payload())

