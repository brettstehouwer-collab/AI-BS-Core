import os
import sys
import time
import json
import shutil
import zipfile
import subprocess
import py_compile
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = r"C:\AI-BS"
PROGRAMS_DIR = os.path.join(WORKSPACE_ROOT, "saved_data", "built_programs")
PYTHON_EXE = os.path.join(WORKSPACE_ROOT, "pyppeteer_env", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

class AutonomousProgramBuilder:
    """
    Autonomous software engineering & program construction engine for AI-BS.
    Scaffolds, generates multi-file structures, executes syntax validation, runs in sandbox,
    captures stdout/stderr, and creates downloadable packages.
    """

    @staticmethod
    def ensure_dir():
        os.makedirs(PROGRAMS_DIR, exist_ok=True)

    @classmethod
    def detect_build_command(cls, project_dir: str, language: Optional[str] = None) -> Optional[str]:
        """Inspects a project directory to auto-detect its primary build/compilation command."""
        if not os.path.isdir(project_dir):
            return None

        # Priority 1: Explicit build script files in the project
        if os.path.exists(os.path.join(project_dir, "build.ps1")):
            return f'powershell -ExecutionPolicy Bypass -File "{os.path.join(project_dir, "build.ps1")}"'
        if os.path.exists(os.path.join(project_dir, "build.bat")):
            return f'cmd.exe /c "{os.path.join(project_dir, "build.bat")}"'
        if os.path.exists(os.path.join(project_dir, "build.cmd")):
            return f'cmd.exe /c "{os.path.join(project_dir, "build.cmd")}"'
        if os.path.exists(os.path.join(project_dir, "build.sh")):
            return f'bash "{os.path.join(project_dir, "build.sh")}"'

        # Priority 2: Standard ecosystem package & compilation manifests
        if os.path.exists(os.path.join(project_dir, "package.json")):
            if not os.path.exists(os.path.join(project_dir, "node_modules")):
                return "npm install && npm run build"
            return "npm run build"

        if os.path.exists(os.path.join(project_dir, "Cargo.toml")):
            return "cargo build"

        if os.path.exists(os.path.join(project_dir, "go.mod")):
            return "go build ./..."

        if os.path.exists(os.path.join(project_dir, "CMakeLists.txt")):
            return "cmake -B build && cmake --build build"

        if os.path.exists(os.path.join(project_dir, "Makefile")) or os.path.exists(os.path.join(project_dir, "makefile")):
            return "make"

        if os.path.exists(os.path.join(project_dir, "requirements.txt")):
            return f'& "{PYTHON_EXE}" -m pip install -r requirements.txt'

        if os.path.exists(os.path.join(project_dir, "setup.py")) or os.path.exists(os.path.join(project_dir, "pyproject.toml")):
            return f'& "{PYTHON_EXE}" -m pip install -e .'

        try:
            for f in os.listdir(project_dir):
                if f.endswith((".csproj", ".sln", ".fsproj")):
                    return "dotnet build"
        except Exception:
            pass

        return None

    @classmethod
    def build_program(
        cls,
        project_name: str,
        language: str,
        description: str,
        files: List[Dict[str, str]],
        entrypoint: str = "main.py",
        run_immediately: bool = True,
        powershell_command: Optional[str] = None,
        build_command: Optional[str] = None,
        execute_build: bool = True
    ) -> Dict[str, Any]:
        """
        Builds a complete multi-file software program and executes build steps.
        files: [{"path": "main.py", "content": "..."}, ...]
        """
        cls.ensure_dir()
        display_name = project_name
        clean_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")).lower()
        if not clean_name:
            clean_name = f"program_{int(time.time())}"

        project_dir = os.path.join(PROGRAMS_DIR, clean_name)
        os.makedirs(project_dir, exist_ok=True)

        written_files = []
        for file_info in files:
            rel_path = file_info.get("path", "").strip().lstrip("/\\")
            content = file_info.get("content", "")
            if not rel_path:
                continue

            full_file_path = os.path.join(project_dir, rel_path)
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
            with open(full_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            written_files.append({
                "name": rel_path,
                "size_bytes": len(content.encode("utf-8")),
                "content": content
            })

        # Pre-flight syntax validation for Python files
        syntax_errors = []
        for wf in written_files:
            if wf["name"].endswith(".py"):
                py_path = os.path.join(project_dir, wf["name"])
                try:
                    py_compile.compile(py_path, doraise=True)
                except py_compile.PyCompileError as e:
                    syntax_errors.append(f"{wf['name']}: {str(e)}")

        # Project Build Execution Step
        build_output = {
            "executed": False,
            "status": "not_run",
            "command": "",
            "stdout": "",
            "stderr": "",
            "exit_code": 0
        }

        active_build_cmd = build_command
        if not active_build_cmd and execute_build:
            active_build_cmd = cls.detect_build_command(project_dir, language)

        if execute_build and active_build_cmd:
            try:
                from core.powershell_process_engine import PowerShellProcessEngine
                b_res = PowerShellProcessEngine.execute_powershell(
                    command_or_script=active_build_cmd,
                    execution_policy="Bypass",
                    timeout_seconds=180,
                    working_directory=project_dir
                )
                build_output = {
                    "executed": True,
                    "status": b_res.get("status", "error"),
                    "command": active_build_cmd,
                    "stdout": b_res.get("stdout", ""),
                    "stderr": b_res.get("stderr", ""),
                    "exit_code": b_res.get("exit_code", 0)
                }
            except Exception as e:
                build_output = {
                    "executed": True,
                    "status": "error",
                    "command": active_build_cmd,
                    "stdout": "",
                    "stderr": str(e),
                    "exit_code": 1
                }

        build_failed = build_output["executed"] and build_output["exit_code"] != 0

        execution_output = {
            "executed": False,
            "status": "not_run",
            "stdout": "",
            "stderr": "",
            "exit_code": 0
        }

        # Live execution if requested, syntax passed, and build succeeded
        if build_failed:
            execution_output = {
                "executed": False,
                "status": "blocked_by_build_failure",
                "stdout": "",
                "stderr": f"Execution halted: Project build failed with exit code {build_output['exit_code']}.",
                "exit_code": build_output["exit_code"]
            }
        elif run_immediately and not syntax_errors:
            entry_full = os.path.join(project_dir, entrypoint)
            
            # Check for custom PowerShell command first
            if powershell_command:
                try:
                    from core.powershell_process_engine import PowerShellProcessEngine
                    ps_res = PowerShellProcessEngine.execute_powershell(
                        command_or_script=powershell_command,
                        execution_policy="Bypass",
                        timeout_seconds=60,
                        working_directory=project_dir
                    )
                    execution_output = {
                        "executed": True,
                        "status": ps_res.get("status", "error"),
                        "stdout": ps_res.get("stdout", ""),
                        "stderr": ps_res.get("stderr", ""),
                        "exit_code": ps_res.get("exit_code", 0)
                    }
                except Exception as e:
                    execution_output = {
                        "executed": True,
                        "status": "error",
                        "stdout": "",
                        "stderr": str(e),
                        "exit_code": 1
                    }
            elif os.path.exists(entry_full):
                if entrypoint.endswith(".ps1") or language.lower() in ("powershell", "ps1"):
                    try:
                        from core.powershell_process_engine import PowerShellProcessEngine
                        ps_res = PowerShellProcessEngine.execute_powershell(
                            command_or_script=f"& '{entry_full}'",
                            execution_policy="Bypass",
                            timeout_seconds=60,
                            working_directory=project_dir
                        )
                        execution_output = {
                            "executed": True,
                            "status": ps_res.get("status", "error"),
                            "stdout": ps_res.get("stdout", ""),
                            "stderr": ps_res.get("stderr", ""),
                            "exit_code": ps_res.get("exit_code", 0)
                        }
                    except Exception as e:
                        execution_output = {
                            "executed": True,
                            "status": "error",
                            "stdout": "",
                            "stderr": str(e),
                            "exit_code": 1
                        }
                elif entrypoint.endswith((".bat", ".cmd")):
                    try:
                        from core.powershell_process_engine import PowerShellProcessEngine
                        ps_res = PowerShellProcessEngine.execute_powershell(
                            command_or_script=f"cmd.exe /c '{entry_full}'",
                            execution_policy="Bypass",
                            timeout_seconds=60,
                            working_directory=project_dir
                        )
                        execution_output = {
                            "executed": True,
                            "status": ps_res.get("status", "error"),
                            "stdout": ps_res.get("stdout", ""),
                            "stderr": ps_res.get("stderr", ""),
                            "exit_code": ps_res.get("exit_code", 0)
                        }
                    except Exception as e:
                        execution_output = {
                            "executed": True,
                            "status": "error",
                            "stdout": "",
                            "stderr": str(e),
                            "exit_code": 1
                        }
                elif entrypoint.endswith(".py"):
                    try:
                        res = subprocess.run(
                            [PYTHON_EXE, entry_full],
                            cwd=project_dir,
                            capture_output=True,
                            text=True,
                            timeout=20.0
                        )
                        execution_output = {
                            "executed": True,
                            "status": "success" if res.returncode == 0 else "error",
                            "stdout": res.stdout,
                            "stderr": res.stderr,
                            "exit_code": res.returncode
                        }
                    except subprocess.TimeoutExpired:
                        execution_output = {
                            "executed": True,
                            "status": "timeout",
                            "stdout": "",
                            "stderr": "Execution timed out (20s limit reached).",
                            "exit_code": -1
                        }
                    except Exception as e:
                        execution_output = {
                            "executed": True,
                            "status": "error",
                            "stdout": "",
                            "stderr": str(e),
                            "exit_code": 1
                        }

        # Package as ZIP archive
        zip_filename = f"{clean_name}.zip"
        zip_path = os.path.join(PROGRAMS_DIR, zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, fnames in os.walk(project_dir):
                for fn in fnames:
                    fp = os.path.join(root, fn)
                    arcname = os.path.relpath(fp, project_dir)
                    zf.write(fp, arcname)

        manifest = {
            "project_name": clean_name,
            "display_name": project_name,
            "language": language,
            "description": description,
            "entrypoint": entrypoint,
            "project_dir": project_dir,
            "files": written_files,
            "syntax_errors": syntax_errors,
            "build": build_output,
            "execution": execution_output,
            "zip_path": zip_path,
            "zip_name": zip_filename,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        manifest_path = os.path.join(project_dir, "program_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Auto-record in Personal Intelligence Memory Vault
        try:
            from core.personal_intelligence_memory import personal_memory
            personal_memory.record_ecosystem_event(
                event_type="program_built",
                summary=f"Scaffolded & Verified Program: {display_name} ({len(files)} files)",
                metadata={"project_name": clean_name, "files": [f["name"] for f in files], "zip": zip_filename}
            )
        except Exception as e:
            pass

        return manifest

    @classmethod
    def run_existing_program(cls, project_name: str, entrypoint: Optional[str] = None, powershell_command: Optional[str] = None) -> Dict[str, Any]:
        """Runs an existing built program and captures output via Python or PowerShell."""
        clean_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")).lower()
        project_dir = os.path.join(PROGRAMS_DIR, clean_name)
        if not os.path.exists(project_dir):
            return {"status": "error", "message": f"Program '{project_name}' not found."}

        manifest_path = os.path.join(project_dir, "program_manifest.json")
        if not entrypoint and os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                entrypoint = manifest.get("entrypoint", "main.py")

        # Custom PowerShell command execution
        if powershell_command:
            try:
                from core.powershell_process_engine import PowerShellProcessEngine
                return PowerShellProcessEngine.execute_powershell(
                    command_or_script=powershell_command,
                    execution_policy="Bypass",
                    timeout_seconds=60,
                    working_directory=project_dir
                )
            except Exception as e:
                return {"status": "error", "stderr": str(e), "stdout": ""}

        entrypoint = entrypoint or "main.py"
        entry_full = os.path.join(project_dir, entrypoint)
        if not os.path.exists(entry_full):
            return {"status": "error", "message": f"Entrypoint '{entrypoint}' not found in {project_dir}."}

        if entrypoint.endswith(".ps1"):
            try:
                from core.powershell_process_engine import PowerShellProcessEngine
                return PowerShellProcessEngine.execute_powershell(
                    command_or_script=f"& '{entry_full}'",
                    execution_policy="Bypass",
                    timeout_seconds=60,
                    working_directory=project_dir
                )
            except Exception as e:
                return {"status": "error", "stderr": str(e), "stdout": ""}

        if entrypoint.endswith((".bat", ".cmd")):
            try:
                from core.powershell_process_engine import PowerShellProcessEngine
                return PowerShellProcessEngine.execute_powershell(
                    command_or_script=f"cmd.exe /c '{entry_full}'",
                    execution_policy="Bypass",
                    timeout_seconds=60,
                    working_directory=project_dir
                )
            except Exception as e:
                return {"status": "error", "stderr": str(e), "stdout": ""}

        try:
            res = subprocess.run(
                [PYTHON_EXE, entry_full],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=20.0
            )
            return {
                "status": "success" if res.returncode == 0 else "error",
                "stdout": res.stdout,
                "stderr": res.stderr,
                "exit_code": res.returncode,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "stderr": "Execution timed out (20s limit).", "stdout": ""}
        except Exception as e:
            return {"status": "error", "stderr": str(e), "stdout": ""}

    @classmethod
    def list_programs(cls) -> List[Dict[str, Any]]:
        """Returns all built programs in saved_data/built_programs."""
        cls.ensure_dir()
        programs = []
        for item in os.listdir(PROGRAMS_DIR):
            item_path = os.path.join(PROGRAMS_DIR, item)
            if os.path.isdir(item_path):
                manifest_path = os.path.join(item_path, "program_manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            programs.append(json.load(f))
                    except Exception:
                        pass
                else:
                    files = os.listdir(item_path)
                    programs.append({
                        "project_name": item,
                        "display_name": item,
                        "language": "python" if any(f.endswith(".py") for f in files) else "other",
                        "description": "Custom user generated program",
                        "project_dir": item_path,
                        "files": [{"name": f, "size_bytes": os.path.getsize(os.path.join(item_path, f))} for f in files],
                        "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getctime(item_path)))
                    })
        return sorted(programs, key=lambda x: x.get("created_at", ""), reverse=True)

    @classmethod
    def resolve_project_dir(cls, project_name_or_dir: str) -> Optional[str]:
        """Resolves a project name or path to an absolute existing directory."""
        if not project_name_or_dir:
            return None
        candidate = os.path.abspath(project_name_or_dir)
        if os.path.isdir(candidate):
            return candidate
        # Try relative to WORKSPACE_ROOT
        candidate_aibs = os.path.abspath(os.path.join(WORKSPACE_ROOT, project_name_or_dir))
        if os.path.isdir(candidate_aibs):
            return candidate_aibs
        # Try in PROGRAMS_DIR by clean name
        clean_name = "".join(c for c in project_name_or_dir if c.isalnum() or c in ("-", "_")).lower()
        prog_path = os.path.join(PROGRAMS_DIR, clean_name)
        if os.path.isdir(prog_path):
            return prog_path
        # Try in PROGRAMS_DIR direct
        prog_direct = os.path.join(PROGRAMS_DIR, project_name_or_dir)
        if os.path.isdir(prog_direct):
            return prog_direct
        return None

    @classmethod
    def build_project(cls, project_name_or_dir: str, build_command: Optional[str] = None, timeout_seconds: int = 300) -> Dict[str, Any]:
        """Executes a build in a project directory, auto-detecting build tools if build_command is omitted."""
        cls.ensure_dir()
        target_dir = cls.resolve_project_dir(project_name_or_dir)
        if not target_dir:
            return {
                "status": "error",
                "message": f"Project directory not found for identifier: '{project_name_or_dir}'",
                "project_name_or_dir": project_name_or_dir,
                "stdout": "",
                "stderr": f"Target directory could not be resolved from '{project_name_or_dir}'",
                "exit_code": 1
            }

        cmd = build_command
        if not cmd:
            cmd = cls.detect_build_command(target_dir)

        if not cmd:
            return {
                "status": "error",
                "message": f"No build configuration or build script detected in {target_dir}. Specify a custom build command.",
                "project_dir": target_dir,
                "stdout": "",
                "stderr": "No package.json, Cargo.toml, go.mod, CMakeLists.txt, Makefile, requirements.txt, or build script found.",
                "exit_code": 1
            }

        try:
            from core.powershell_process_engine import PowerShellProcessEngine
            b_res = PowerShellProcessEngine.execute_powershell(
                command_or_script=cmd,
                execution_policy="Bypass",
                timeout_seconds=timeout_seconds,
                working_directory=target_dir
            )
            result = {
                "status": "success" if b_res.get("exit_code", 0) == 0 else "error",
                "project_dir": target_dir,
                "command": cmd,
                "stdout": b_res.get("stdout", ""),
                "stderr": b_res.get("stderr", ""),
                "exit_code": b_res.get("exit_code", 0),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            result = {
                "status": "error",
                "project_dir": target_dir,
                "command": cmd,
                "stdout": "",
                "stderr": str(e),
                "exit_code": 1,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        # Update program_manifest.json if it exists in the project dir
        manifest_path = os.path.join(target_dir, "program_manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                manifest["build"] = {
                    "executed": True,
                    "status": result["status"],
                    "command": cmd,
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "exit_code": result["exit_code"],
                    "timestamp": result["timestamp"]
                }
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
            except Exception:
                pass

        # Record in Personal Intelligence Memory Vault
        try:
            from core.personal_intelligence_memory import personal_memory
            personal_memory.record_ecosystem_event(
                event_type="project_built",
                summary=f"Executed Build in {os.path.basename(target_dir)}: {cmd} (Exit: {result['exit_code']})",
                metadata={"project_dir": target_dir, "command": cmd, "exit_code": result["exit_code"], "status": result["status"]}
            )
        except Exception:
            pass

        return result

