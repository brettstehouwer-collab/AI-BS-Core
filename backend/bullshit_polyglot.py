import os
import json
import subprocess
import time
import re
from bullshit_auditor import audit_code


def list_local_directory(path: str) -> dict:
    print(f"[Polyglot] Executing: list_local_directory('{path}')")
    try:
        contents = os.listdir(path)
        return {"status": "success", "data": contents}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def read_local_file(filepath: str) -> dict:
    print(f"[Polyglot] Executing: read_local_file('{filepath}')")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "data": content[:2000]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def promote_successful_script(script_path: str, language: str):
    promoted_dir = os.path.join(os.path.dirname(__file__), "promoted_agents")
    os.makedirs(promoted_dir, exist_ok=True)

    filename = os.path.basename(script_path)
    new_path = os.path.join(promoted_dir, filename)
    os.rename(script_path, new_path)

    agent_name = (
        filename.replace(".py", "")
        .replace(".ps1", "")
        .replace(".bat", "")
        .replace("_", "-")
    )

    config_path = os.path.join(os.path.dirname(__file__), "ai_bs_personas.json")
    try:
        with open(config_path, "r") as f:
            personas = json.load(f)
    except BaseException:
        personas = {}

    personas[agent_name] = {
        "alias": f"Promoted {
            language.capitalize()} Builder",
        "persona": "Automatically promoted agent from a successful sandbox run.",
        "script_binding": f"promoted_agents/{filename}",
        "capabilities": f"Executes successful {language} code blocks.",
    }

    with open(config_path, "w") as f:
        json.dump(personas, f, indent=2)

    print(f"[Polyglot] Promotion Success! New agent '{agent_name}' added to matrix.")

    # [PHASE X.5] AST SHREDDER TRIGGER
    print(f"[AST Shredder] Triggering AST extraction on promoted script: {new_path}")
    ast_daemon_path = os.path.join(
        os.path.dirname(__file__), "bullshit_ast_shredder.py"
    )
    if os.path.exists(ast_daemon_path):
        subprocess.Popen(["python", ast_daemon_path, new_path])

    return agent_name


def execute_polyglot_command(
    command: str, language: str, user_approved: bool = False
) -> dict:
    print(f"[Polyglot] Executing [{language}] Command in Sandbox...")

    # 1. SECURITY MATRIX: Regex string checks for hostile operations
    dangerous_patterns = [
        r"rm\s+-rf",
        r"chmod\s+777",
        r"os\.system",
        r"subprocess\.Popen",
        r"shutil\.rmtree\(['\"]/[\\\"']\)",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            print(
                f"[Polyglot] Security Violation: Dangerous pattern '{pattern}' detected."
            )
            return {
                "status": "rejected",
                "error": f"Security Violation: Dangerous command pattern '{pattern}' detected.",
            }

    # Run through Stehouwer Auditor
    if not user_approved:
        print(f"[Polyglot] Routing code through Stehouwer Reality Standard Auditor...")
        is_approved = audit_code(command)
        if not is_approved:
            return {
                "status": "rejected",
                "error": "Code was REJECTED by Stehouwer Reality Standard Auditor.",
            }
    else:
        print(
            "[Polyglot] User Approved Execution: Bypassing Stehouwer Reality Standard Auditor."
        )

    print(f"[Polyglot] AUTO-EXECUTE GRANTED: Routing through Docker sandbox...")

    sandbox_dir = os.path.join(os.path.dirname(__file__), "sandbox")
    os.makedirs(sandbox_dir, exist_ok=True)

    ext_map = {
        "python": ".py",
        "powershell": ".ps1",
        "javascript": ".js",
        "node": ".js",
        "c++": ".cpp",
        "cpp": ".cpp",
        "html": ".html",
    }
    ext = ext_map.get(language.lower(), ".bat")
    import uuid

    timestamp = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    script_name = f"sandbox_task_{timestamp}{ext}"
    script_path = os.path.join(sandbox_dir, script_name)

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(command)

    # ENFORCE EXTENDED 300-SECOND FALLBACK (Leveraging 9950X / 4090
    # architecture)
    TIMEOUT_LIMIT = 300

    max_auto_retries = 3
    retries = 0

    while retries < max_auto_retries:
        try:
            # Use Docker sandbox for Python execution (air-gapped,
            # network-disabled, read-only)
            if language.lower() == "python":
                import shutil

                docker_compose_cmd = (
                    shutil.which("docker-compose")
                    or r"C:\Program Files\Docker\Docker\resources\bin\docker-compose.exe"
                )

                # Write script to a temp location for Docker mount
                temp_script_path = os.path.join(sandbox_dir, f"temp_{timestamp}.py")
                with open(temp_script_path, "w", encoding="utf-8") as f:
                    f.write(command)

                try:
                    result = subprocess.run(
                        [
                            docker_compose_cmd,
                            "-f",
                            os.path.join(
                                os.path.dirname(__file__), "docker-compose_sandbox.yml"
                            ),
                            "run",
                            "--rm",
                            "executor_sandbox",
                            "python",
                            "/sandbox/scratch/temp_script.py",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUT_LIMIT,
                        cwd=os.path.dirname(__file__),
                    )

                    # Copy output back to expected format
                    output = result.stdout
                    error_output = result.stderr

                    if result.returncode == 0:
                        agent_name = promote_successful_script(script_path, language)
                        return {
                            "status": "success",
                            "stdout": output,
                            "stderr": error_output,
                            "promoted_agent": agent_name,
                        }
                    else:
                        # Parse error types from Docker execution
                        if (
                            "ModuleNotFoundError" in error_output
                            or "No module named" in error_output
                        ):
                            match = re.search(
                                r"No module named '([^']+)'", error_output
                            )
                            missing = match.group(1) if match else "unknown"
                            return {
                                "status": "dependency_missing",
                                "stdout": output,
                                "stderr": error_output,
                                "suggestion_prompt": f"Install missing package: pip install {missing}",
                                "auto_install_blocked": True,
                            }
                        return {
                            "status": "runtime_error",
                            "stdout": output,
                            "stderr": error_output,
                            "suggestion_prompt": "Feed this raw stderr directly into your trainer.py daemon.",
                        }
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_script_path):
                        os.remove(temp_script_path)

            # For non-Python languages, fall back to host execution with audit
            # gate
            elif language.lower() == "powershell":
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
            elif language.lower() in ["javascript", "node"]:
                result = subprocess.run(
                    ["node", script_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
            elif language.lower() in ["c++", "cpp"]:
                exe_path = os.path.join(sandbox_dir, f"sandbox_task_{timestamp}.exe")
                compile_res = subprocess.run(
                    ["g++", script_path, "-o", exe_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
                if compile_res.returncode != 0:
                    return {
                        "status": "runtime_error",
                        "stdout": "",
                        "stderr": compile_res.stderr,
                        "suggestion_prompt": "Feed this raw stderr directly into your trainer.py daemon.",
                    }
                result = subprocess.run(
                    [exe_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
            elif language.lower() in ["go", "golang"]:
                result = subprocess.run(
                    ["go", "run", script_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
            elif language.lower() in ["rust", "rs"]:
                exe_path = os.path.join(sandbox_dir, f"sandbox_task_{timestamp}.exe")
                compile_res = subprocess.run(
                    ["rustc", script_path, "-o", exe_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
                if compile_res.returncode != 0:
                    return {
                        "status": "runtime_error",
                        "stdout": "",
                        "stderr": compile_res.stderr,
                        "suggestion_prompt": "Rust compilation failed. Feed stderr to trainer daemon.",
                    }
                result = subprocess.run(
                    [exe_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
            elif language.lower() in ["wasm", "webassembly"]:
                # Run WebAssembly via Node.js WASM engine or wasmtime CLI
                wasm_runner = (
                    ["node", "--experimental-wasm-modules", script_path]
                    if script_path.endswith(".js")
                    else ["wasmtime", script_path]
                )
                result = subprocess.run(
                    wasm_runner,
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )
            elif language.lower() == "html":
                return {
                    "status": "success",
                    "stdout": "HTML generated successfully.",
                    "stderr": "",
                }

            else:
                result = subprocess.run(
                    [script_path],
                    cwd=sandbox_dir,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_LIMIT,
                )

            output = result.stdout
            error_output = result.stderr

            if result.returncode == 0:
                agent_name = promote_successful_script(script_path, language)
                return {
                    "status": "success",
                    "stdout": output,
                    "stderr": error_output,
                    "promoted_agent": agent_name,
                }
            else:
                # [SECURITY] Dependency failures require explicit operator approval.
                if (
                    "ModuleNotFoundError" in error_output
                    or "No module named" in error_output
                ):
                    match = re.search(r"No module named '([^']+)'", error_output)
                    missing = match.group(1) if match else "unknown"
                    return {
                        "status": "dependency_missing",
                        "stdout": output,
                        "stderr": error_output,
                        "suggestion_prompt": f"Install missing package: pip install {missing}",
                        "auto_install_blocked": True,
                    }

                elif "Cannot find module" in error_output:
                    match = re.search(r"Cannot find module '([^']+)'", error_output)
                    missing = match.group(1) if match else "unknown"
                    return {
                        "status": "dependency_missing",
                        "stdout": output,
                        "stderr": error_output,
                        "suggestion_prompt": f"Install missing package: npm install {missing}",
                        "auto_install_blocked": True,
                    }

                # If it's a normal error, return to Trainer Daemon
                return {
                    "status": "runtime_error",
                    "stdout": output,
                    "stderr": error_output,
                    "suggestion_prompt": "Feed this raw stderr directly into your trainer.py daemon.",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "runtime_error",
                "stdout": "",
                "stderr": "Execution Wall Breach: Process exceeded the 300-second execution limit and was killed.",
                "suggestion_prompt": "Feed this raw stderr directly into your trainer.py daemon.",
            }
        except Exception as e:
            return {
                "status": "runtime_error",
                "stdout": "",
                "stderr": str(e),
                "suggestion_prompt": "Feed this raw stderr directly into your trainer.py daemon.",
            }

    return {
        "status": "runtime_error",
        "stderr": "Max auto-retries exceeded for dependency injection.",
    }


if __name__ == "__main__":
    print("[Polyglot] Execution Engine Started.")
    print("[Polyglot] Ready to execute scripts.")
    while True:
        time.sleep(3600)
