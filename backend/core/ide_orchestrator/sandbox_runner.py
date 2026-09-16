import os
import sys
import time
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

@dataclass
class SandboxResult:
    status: str  # "PASSED", "FAILED", "TIMEOUT", "EXECUTION_ERROR"
    exit_code: int
    execution_time_sec: float
    stdout: str
    stderr: str
    patch_applied: bool

class SubprocessSandboxRunner:
    def __init__(self, default_timeout_sec: float = 10.0):
        self.default_timeout_sec = default_timeout_sec

    def execute_in_sandbox(
        self,
        original_file_path: str,
        modified_code: str,
        test_script_code: Optional[str] = None,
        timeout_sec: Optional[float] = None
    ) -> SandboxResult:
        timeout = timeout_sec or self.default_timeout_sec
        start_time = time.perf_counter()

        # 1. Create temporary isolated directory
        with tempfile.TemporaryDirectory(prefix="ide_sandbox_") as temp_dir:
            temp_path = Path(temp_dir)
            target_name = Path(original_file_path).name
            sandbox_target_file = temp_path / target_name

            # 2. Write modified code into sandbox workspace
            try:
                sandbox_target_file.write_text(modified_code, encoding="utf-8")
            except Exception as e:
                return SandboxResult(
                    status="EXECUTION_ERROR",
                    exit_code=-1,
                    execution_time_sec=0.0,
                    stdout="",
                    stderr=f"Failed to write candidate code to sandbox: {str(e)}",
                    patch_applied=False
                )

            # 3. Create entrypoint execution script
            entrypoint_script = temp_path / "_runner_entrypoint.py"
            if test_script_code:
                entrypoint_script.write_text(test_script_code, encoding="utf-8")
            else:
                # Default sanity check: compile and run simple import test
                entrypoint_script.write_text(
                    f"import sys\n"
                    f"sys.path.insert(0, '.')\n"
                    f"import {sandbox_target_file.stem}\n"
                    f"print('Compilation and import successful.')\n",
                    encoding="utf-8"
                )

            # 4. Strip environment variables for isolated execution
            sanitized_env: Dict[str, str] = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(temp_path),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # Required for Windows process startup
                "USERPROFILE": os.environ.get("USERPROFILE", ""), # Required for Path.home() which chromadb uses
                "PYTHONUNBUFFERED": "1"
            }

            # 5. Launch isolated subprocess
            try:
                process = subprocess.run(
                    [sys.executable, str(entrypoint_script)],
                    cwd=str(temp_path),
                    env=sanitized_env,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

                elapsed_time = time.perf_counter() - start_time
                status = "PASSED" if process.returncode == 0 else "FAILED"

                return SandboxResult(
                    status=status,
                    exit_code=process.returncode,
                    execution_time_sec=round(elapsed_time, 4),
                    stdout=process.stdout,
                    stderr=process.stderr,
                    patch_applied=True
                )

            except subprocess.TimeoutExpired as e:
                elapsed_time = time.perf_counter() - start_time
                return SandboxResult(
                    status="TIMEOUT",
                    exit_code=-1,
                    execution_time_sec=round(elapsed_time, 4),
                    stdout=e.stdout.decode("utf-8") if e.stdout and isinstance(e.stdout, bytes) else (e.stdout or ""),
                    stderr=f"Execution timed out after {timeout} seconds.",
                    patch_applied=True
                )

            except Exception as e:
                elapsed_time = time.perf_counter() - start_time
                return SandboxResult(
                    status="EXECUTION_ERROR",
                    exit_code=-1,
                    execution_time_sec=round(elapsed_time, 4),
                    stdout="",
                    stderr=f"Subprocess runner error: {str(e)}",
                    patch_applied=False
                )
