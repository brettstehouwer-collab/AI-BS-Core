# File: backend/executive_runtime_router.py
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\AI-BS")
SCRATCH_DIR = WORKSPACE_ROOT / ".temp_executor"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
(WORKSPACE_ROOT / "scratch").mkdir(parents=True, exist_ok=True)
(WORKSPACE_ROOT / "Stehouwer_Server" / "Projects" / ".temp_executor").mkdir(parents=True, exist_ok=True)


def resolve_host_path(raw_path: str) -> Path:
    p = str(raw_path or "").strip().replace("file:///", "").replace("file://", "")
    # Seamless G:\Stehouwer_Server -> C:\AI-BS\Stehouwer_Server fallback when G: is unmounted
    if p.lower().startswith("g:\\stehouwer_server") or p.lower().startswith("g:/stehouwer_server"):
        if not Path("G:\\").exists():
            rel = p[len("g:\\stehouwer_server"):].lstrip("/\\")
            return WORKSPACE_ROOT / "Stehouwer_Server" / rel
    if len(p) >= 2 and p[1] == ":":
        return Path(p)
    p = p.lstrip("/\\")
    if p.lower().startswith("ai-bs\\") or p.lower().startswith("ai-bs/"):
        return Path("C:\\") / p
    return WORKSPACE_ROOT / p


def execute_multi_runtime(command_type: str = "powershell", target: str = "", payload: dict = None, **kwargs) -> dict:
    # Normalize kwargs from callers (e.g. if called as execute_multi_runtime(command=..., runtime=..., cwd=..., file_path=...))
    if "runtime" in kwargs and kwargs["runtime"]:
        command_type = kwargs["runtime"]
    elif "command_type" in kwargs and kwargs["command_type"]:
        command_type = kwargs["command_type"]

    if "command" in kwargs and kwargs["command"]:
        target = kwargs["command"]
    elif "target" in kwargs and kwargs["target"]:
        target = kwargs["target"]

    payload = payload or kwargs.get("payload") or {}
    if "file_path" in kwargs and kwargs["file_path"]:
        payload["file_path"] = kwargs["file_path"]
    if "cwd" in kwargs and kwargs["cwd"]:
        payload["cwd"] = kwargs["cwd"]

    timeout = int(payload.get("timeout_seconds", 120))
    t0 = time.perf_counter()

    try:
        # 1. UNIVERSAL FILE READ
        if command_type in ("file_read", "read"):
            fpath = resolve_host_path(target)
            if not fpath.exists():
                return {"status": "error", "message": f"File not found: {fpath}"}
            content = fpath.read_text(encoding="utf-8", errors="replace")
            return {
                "status": "success",
                "result": {
                    "status": "success",
                    "path": str(fpath),
                    "content": content,
                    "lines": len(content.splitlines()),
                    "size_bytes": fpath.stat().st_size
                },
                "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)
            }

        # 2. UNIVERSAL FILE WRITE (ANY EXTENSION + AUTO .BAK BACKUP)
        if command_type in ("file_write", "write"):
            fpath = resolve_host_path(target)
            fpath.parent.mkdir(parents=True, exist_ok=True)
            content = payload.get("content", "")
            backup_file = None
            if fpath.exists():
                backup_file = f"{fpath}.{int(time.time())}.bak"
                shutil.copy2(fpath, backup_file)
            fpath.write_text(content, encoding="utf-8")
            return {
                "status": "success",
                "result": {
                    "status": "success",
                    "path": str(fpath),
                    "bytes_written": fpath.stat().st_size,
                    "backup_created": bool(backup_file),
                    "backup_file": backup_file
                },
                "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)
            }

        # 3. MULTI-SHELL & MULTI-LANGUAGE SUBPROCESS EXECUTION (AIBS-DIR-000 Compliant)
        cmd_list = []
        temp_file = None
        extra_args = payload.get("args") or []
        if not isinstance(extra_args, list):
            extra_args = [str(extra_args)]

        py_exe = r"C:\AI-BS\pyppeteer_env\Scripts\python.exe"
        if not os.path.exists(py_exe):
            py_exe = sys.executable

        if command_type in ("powershell", "ps", "ps1"):
            if os.path.exists(resolve_host_path(target)) and "\n" not in target and str(target).lower().endswith(".ps1"):
                cmd_list = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(resolve_host_path(target))] + extra_args
            else:
                cmd_list = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", target]
        elif command_type in ("cmd", "batch", "bat"):
            cmd_list = ["cmd.exe", "/d", "/s", "/c", target]
        elif command_type in ("pip", "pip3"):
            import shlex
            clean_cmd = target.strip()
            if clean_cmd.startswith("pip3 "):
                clean_cmd = clean_cmd[5:].strip()
            elif clean_cmd.startswith("pip "):
                clean_cmd = clean_cmd[4:].strip()
            elif clean_cmd.startswith("python -m pip "):
                clean_cmd = clean_cmd[14:].strip()
            elif clean_cmd.startswith("py -m pip "):
                clean_cmd = clean_cmd[10:].strip()

            if clean_cmd in ("install pip", "get-pip", "ensurepip", "setup pip"):
                cmd_list = [py_exe, "-m", "ensurepip", "--upgrade"]
            elif not clean_cmd or clean_cmd in ("list", "--version", "-V"):
                cmd_list = [py_exe, "-m", "pip", "list"] if not clean_cmd else [py_exe, "-m", "pip", clean_cmd]
            else:
                first_arg = clean_cmd.split()[0].lower()
                if first_arg not in ("install", "uninstall", "list", "show", "freeze", "check", "config", "search", "cache", "wheel", "download"):
                    cmd_list = [py_exe, "-m", "pip", "install"] + shlex.split(clean_cmd) + extra_args
                else:
                    cmd_list = [py_exe, "-m", "pip"] + shlex.split(clean_cmd) + extra_args
        elif command_type in ("wsl", "bash", "sh", "zsh", "shell"):
            distro = payload.get("distro", "Ubuntu")
            git_bash = r"C:\Program Files\Git\bin\bash.exe"
            env_mode = payload.get("environment", "auto").lower()

            if command_type == "wsl" or env_mode == "wsl":
                cmd_list = ["wsl.exe", "-d", distro, "--", "bash", "-lc", target]
            elif os.path.exists(git_bash):
                bash_script = f'export PATH="/c/AI-BS/pyppeteer_env/Scripts:/c/AI-BS/pyppeteer_env:/usr/bin:/bin:$PATH"; {target}'
                cmd_list = [git_bash, "-c", bash_script]
            else:
                cmd_list = ["wsl.exe", "-d", distro, "--", "bash", "-lc", target]
        elif command_type in ("python", "py"):
            if os.path.exists(resolve_host_path(target)) and "\n" not in target:
                cmd_list = [py_exe, str(resolve_host_path(target))] + extra_args
            else:
                temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.py"
                temp_file.write_text(target, encoding="utf-8")
                cmd_list = [py_exe, str(temp_file)] + extra_args
        elif command_type in ("node", "javascript", "js", "mjs"):
            if os.path.exists(resolve_host_path(target)) and "\n" not in target:
                cmd_list = ["node", str(resolve_host_path(target))] + extra_args
            else:
                temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.js"
                temp_file.write_text(target, encoding="utf-8")
                cmd_list = ["node", str(temp_file)] + extra_args
        elif command_type in ("ts", "typescript"):
            if os.path.exists(resolve_host_path(target)) and "\n" not in target:
                cmd_list = ["npx", "--yes", "tsx", str(resolve_host_path(target))] + extra_args
            else:
                temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.ts"
                temp_file.write_text(target, encoding="utf-8")
                cmd_list = ["npx", "--yes", "tsx", str(temp_file)] + extra_args
        elif command_type in ("go", "golang"):
            if os.path.exists(resolve_host_path(target)) and "\n" not in target:
                cmd_list = ["go", "run", str(resolve_host_path(target))] + extra_args
            else:
                temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.go"
                temp_file.write_text(target, encoding="utf-8")
                cmd_list = ["go", "run", str(temp_file)] + extra_args
        elif command_type in ("rust", "rs"):
            if os.path.exists(resolve_host_path(target)) and "\n" not in target:
                src_rs = resolve_host_path(target)
                exe_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.exe"
                cmd_list = ["cmd.exe", "/c", f'rustc "{src_rs}" -o "{exe_file}" && "{exe_file}"']
            else:
                temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.rs"
                exe_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.exe"
                temp_file.write_text(target, encoding="utf-8")
                cmd_list = ["cmd.exe", "/c", f'rustc "{temp_file}" -o "{exe_file}" && "{exe_file}"']
        elif command_type in ("cpp", "c"):
            ext = ".c" if command_type == "c" else ".cpp"
            compiler = "gcc" if command_type == "c" else "g++"
            if os.path.exists(resolve_host_path(target)) and "\n" not in target:
                src_c = resolve_host_path(target)
                exe_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.exe"
                cmd_list = ["cmd.exe", "/c", f'{compiler} "{src_c}" -o "{exe_file}" && "{exe_file}"']
            else:
                temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}{ext}"
                exe_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.exe"
                temp_file.write_text(target, encoding="utf-8")
                cmd_list = ["cmd.exe", "/c", f'{compiler} "{temp_file}" -o "{exe_file}" && "{exe_file}"']
        elif command_type == "sql":
            temp_file = SCRATCH_DIR / f"_exec_{int(time.time()*1000)}.py"
            sql_runner = (
                "import duckdb, json\n"
                f"q = {repr(target)}\n"
                "res = duckdb.sql(q).fetchall()\n"
                "print(json.dumps(res, indent=2, default=str))\n"
            )
            temp_file.write_text(sql_runner, encoding="utf-8")
            cmd_list = [py_exe, str(temp_file)]
        else:
            return {"status": "error", "message": f"Unsupported command_type: {command_type}"}

        proc = subprocess.run(
            cmd_list,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )

        # Record outcome under AIBS-DIR-000 Section 2.3 (Two-Strike Diagnostic Halt Rule)
        two_strike_info = {}
        try:
            from sovereign_privilege_engine import record_command_execution_outcome
            two_strike_info = record_command_execution_outcome(
                command_type=command_type,
                target=target,
                returncode=proc.returncode,
                stderr=proc.stderr
            )
        except Exception:
            pass

        return {
            "status": "success" if proc.returncode == 0 else "error",
            "command_type": command_type,
            "runtime_used": command_type,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "two_strike_governance": two_strike_info,
            "sandbox_dir": str(SCRATCH_DIR),
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)
        }


def auto_heal_code(code: str, stderr: str, runtime_type: str = "python", stdout: str = "") -> dict:
    r"""
    Autonomous Self-Healing Execution Engine.
    Submits failing source code and stderr traceback to local qwen2.5-coder on Port 11434 (GPU)
    or Port 11435 (CPU shadow) with format='json' (Grammar-Constrained Token Masking).
    Returns strict JSON: {root_cause, fix_explanation, fixed_code}.
    """
    import urllib.request
    import json

    t0 = time.perf_counter()
    prompt = (
        f"You are the autonomous self-healing debugger for AI-BS BS-Chat on Windows 11.\n"
        f"Runtime / Shell: {runtime_type}\n\n"
        f"--- FAILING CODE ---\n{code}\n\n"
        f"--- STDERR TRACEBACK ---\n{stderr}\n\n"
    )
    if stdout.strip():
        prompt += f"--- STDOUT ---\n{stdout[:1000]}\n\n"

    prompt += (
        "Diagnose the root cause and provide the complete, corrected code that resolves the failure.\n"
        "You must respond with a single JSON object containing exact keys:\n"
        "1. 'root_cause': Brief diagnosis of what went wrong.\n"
        "2. 'fix_explanation': Concise explanation of the applied fix.\n"
        "3. 'fixed_code': Complete corrected runnable code block ready for direct execution.\n"
    )

    ollama_endpoints = ["http://127.0.0.1:11434/api/generate", "http://127.0.0.1:11435/api/generate"]
    last_err = None

    for endpoint in ollama_endpoints:
        try:
            req_body = {
                "model": "qwen2.5-coder:latest",
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 4096
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(req_body).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_response = data.get("response", "{}")
                parsed = json.loads(raw_response)
                
                fixed_code = parsed.get("fixed_code") or ""
                # Strip markdown fencing if accidentally included inside JSON string
                if fixed_code.startswith("```"):
                    lines = fixed_code.splitlines()
                    if len(lines) >= 2 and lines[-1].strip() == "```":
                        fixed_code = "\n".join(lines[1:-1])

                return {
                    "status": "success",
                    "root_cause": parsed.get("root_cause", "Error identified in traceback."),
                    "fix_explanation": parsed.get("fix_explanation", "Code repaired."),
                    "fixed_code": fixed_code,
                    "endpoint_used": endpoint,
                    "model_used": data.get("model", "qwen2.5-coder:latest"),
                    "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)
                }
        except Exception as e:
            last_err = e
            continue

    return {
        "status": "error",
        "message": f"Auto-heal generation failed across Ollama endpoints: {last_err}",
        "execution_time_ms": round((time.perf_counter() - t0) * 1000, 2)
    }

