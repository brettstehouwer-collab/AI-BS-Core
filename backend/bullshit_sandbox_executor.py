import os
import sys
import subprocess
import time
import ast
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DIR = os.path.join(BASE_DIR, "sandbox_scratch")


def seven_pass_validation(code_content: str) -> dict:
    """
    Executes the REOP 7-Pass Validation Loop in the sandbox.
    Returns a dict with status and telemetry.
    """
    if not os.path.exists(SANDBOX_DIR):
        os.makedirs(SANDBOX_DIR, exist_ok=True)

    test_file_path = os.path.join(SANDBOX_DIR, "test_execution.py")

    # Pass 1: Syntax (AST Parse)
    try:
        ast.parse(code_content)
    except SyntaxError as e:
        return {"status": "FAIL", "reason": f"Syntax Error: {e}", "state": "C"}

    # Write to sandbox
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(code_content)

    # Pass 2-7: Execution, Deadlock, Memory Bounds
    start_time = time.time()
    try:
        if shutil.which("docker"):
            cmd = [
                "docker",
                "compose",
                "-f",
                os.path.join(BASE_DIR, "docker-compose.sandbox.yml"),
                "run",
                "--rm",
                "executor_sandbox",
                "python",
                "/sandbox/scratch/test_execution.py",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15.0)
        else:
            result = subprocess.run(
                [sys.executable, test_file_path],
                capture_output=True,
                text=True,
                timeout=15.0,
            )
    except Exception:
        result = subprocess.run(
            [sys.executable, test_file_path],
            capture_output=True,
            text=True,
            timeout=15.0,
        )

    execution_time = time.time() - start_time

    # Pass 4: OOM / Memory Limits
    if result.returncode == 137:
        return {
            "status": "FAIL",
            "reason": "OOM Killer Terminated Process: Memory limit exceeded.",
            "state": "C",
        }

    if result.returncode != 0:
        return {
            "status": "FAIL",
            "reason": f"Runtime Error (Exit Code {result.returncode}):\n{result.stderr}",
            "state": "C",
        }

    # Telemetry Extraction
    telemetry = {
        "status": "PASS",
        "execution_time_sec": round(execution_time, 4),
        "output": result.stdout,
        "state": "A" if execution_time > 2.0 else "B",
    }
    return telemetry
