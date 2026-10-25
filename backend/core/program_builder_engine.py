import os
import sys
import time
import json
import shutil
import zipfile
import subprocess
import ntpath
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .code_quality_gate import sanitize_and_validate_llm_code

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

    @staticmethod
    def _relative_path(value: str) -> str:
        """Reject ambiguous Windows names before any project writes occur."""
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError("File paths must be nonempty relative text without surrounding whitespace")
        if ntpath.isabs(value) or ntpath.splitdrive(value)[0]:
            raise ValueError("Absolute, drive-relative and UNC file paths are not permitted")
        parts = value.replace("\\", "/").split("/")
        reserved = {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}
        for part in parts:
            if not part or part in {".", ".."} or part.endswith((".", " ")):
                raise ValueError("Empty, traversal and Windows alias path segments are not permitted")
            if any(ord(c) < 32 or c in '<>:"|?*' for c in part) or part.split(".", 1)[0].upper() in reserved:
                raise ValueError("Reserved Windows filenames and alternate data streams are not permitted")
        return os.path.join(*parts)

    @staticmethod
    def _contained_path(root: str, relative: str) -> str:
        target = os.path.abspath(os.path.join(root, relative))
        root_real = os.path.normcase(os.path.realpath(root))
        target_real = os.path.normcase(os.path.realpath(target))
        if os.path.commonpath([root_real, target_real]) != root_real or target_real == root_real:
            raise ValueError("A project path resolves outside its permitted directory")
        return target

    @classmethod
    def _existing_files(cls, project_dir: str, *, exclude_generated: bool = False) -> List[str]:
        found = []
        if not os.path.isdir(project_dir):
            return found
        excluded = {"node_modules", ".git", ".venv", "venv", "env", "__pycache__", "dist", "build", "backups", ".aibs_backups"}
        for directory, subdirs, names in os.walk(project_dir, followlinks=False):
            for name in [*subdirs, *names]:
                cls._contained_path(project_dir, os.path.relpath(os.path.join(directory, name), project_dir))
            if exclude_generated:
                subdirs[:] = [name for name in subdirs if name.lower() not in excluded]
            for name in names:
                found.append(os.path.relpath(os.path.join(directory, name), project_dir))
        return found

    @staticmethod
    def _preserve_existing(path: str) -> None:
        if os.path.lexists(path):
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.copy2(path, f"{path}.{stamp}_{uuid.uuid4().hex[:8]}.bak")

    @classmethod
    def _atomic_text(cls, path: str, content: str) -> None:
        """Keep previous content and replace the destination without truncating it."""
        cls._preserve_existing(path)
        descriptor, staged = tempfile.mkstemp(prefix=".aibs_write_", dir=os.path.dirname(path))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                stream.write(content)
            os.replace(staged, path)
        except BaseException:
            # Retain the failed staging file for review; do not delete user data.
            raise

    @classmethod
    def _quality_for_existing(cls, project_dir: str, overlay: Optional[Dict[str, str]] = None,
                              strict: bool = False, include_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        if not isinstance(strict, bool):
            raise ValueError("strict_quality_gate must be a boolean")
        overlay = overlay or {}
        sources = dict(overlay)
        case_names = {os.path.normcase(name) for name in sources}
        existing = cls._existing_files(project_dir, exclude_generated=True)
        for relative in include_paths or []:
            relative = cls._relative_path(relative)
            path = cls._contained_path(project_dir, relative)
            if os.path.isfile(path) and relative not in existing:
                existing.append(relative)
        for relative in existing:
            if relative.lower().endswith((".py", ".pyw")) and os.path.normcase(relative) not in case_names:
                path = cls._contained_path(project_dir, relative)
                try:
                    with open(path, "r", encoding="utf-8", newline="") as stream:
                        sources[relative] = stream.read()
                except (OSError, UnicodeError) as exc:
                    return {"valid": False, "strict": strict, "files": {},
                        "errors": [f"{relative}: Cannot read Python source ({type(exc).__name__})"]}
        results = {name: sanitize_and_validate_llm_code(content, strict=strict)
            for name, content in sources.items() if name.lower().endswith((".py", ".pyw"))}
        for name, result in results.items():
            if name not in overlay and result["sanitized_code"] != sources[name]:
                result["valid"] = False
                result["errors"].append("Existing source requires an explicit sanitized update before execution; original left unchanged")
        return {"valid": all(value["valid"] for value in results.values()), "strict": strict,
            "files": results, "errors": [f"{name}: {message}" for name, result in results.items() for message in result["errors"]]}

    @staticmethod
    def _quality_failure(project_name: str, project_dir: str, quality: Dict[str, Any],
                         message: str = "Program rejected before writes, build or execution") -> Dict[str, Any]:
        return {"status": "error", "message": message, "project_name": project_name,
            "project_dir": project_dir, "files": [], "syntax_errors": quality.get("errors", []),
            "code_quality": quality,
            "build": {"executed": False, "status": "blocked_by_quality_gate", "command": "", "stdout": "", "stderr": message, "exit_code": 1},
            "execution": {"executed": False, "status": "blocked_by_quality_gate", "stdout": "", "stderr": message, "exit_code": 1}}

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
        execute_build: bool = True,
        strict_quality_gate: bool = False
    ) -> Dict[str, Any]:
        """
        Builds a complete multi-file software program and executes build steps.
        files: [{"path": "main.py", "content": "..."}, ...]
        """
        display_name = project_name
        clean_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")).lower()
        if not clean_name:
            clean_name = f"program_{int(time.time())}"

        project_dir = os.path.join(PROGRAMS_DIR, clean_name)
        try:
            cls._contained_path(PROGRAMS_DIR, clean_name)
            cls._contained_path(PROGRAMS_DIR, clean_name + ".zip")
            if os.path.lexists(project_dir) and not os.path.isdir(project_dir):
                raise ValueError("The project name already belongs to a file")
            entrypoint = cls._relative_path(entrypoint)
            cls._contained_path(project_dir, entrypoint)
            prepared: Dict[str, str] = {}
            normalized_names = set()
            if not isinstance(strict_quality_gate, bool):
                raise ValueError("strict_quality_gate must be a boolean")
            for file_info in files:
                rel_path = cls._relative_path(file_info.get("path", ""))
                if os.path.normcase(rel_path) in normalized_names:
                    raise ValueError("Duplicate or case-equivalent paths are not permitted")
                if os.path.normcase(rel_path) == "program_manifest.json":
                    raise ValueError("program_manifest.json is reserved for builder metadata")
                cls._contained_path(project_dir, rel_path)
                content = file_info.get("content", "")
                if not isinstance(content, str):
                    raise ValueError("Source file content must be text")
                content.encode("utf-8", errors="strict")
                normalized_names.add(os.path.normcase(rel_path))
                prepared[rel_path] = content
            for relative in prepared:
                parent = os.path.dirname(relative)
                while parent:
                    if os.path.normcase(parent) in normalized_names:
                        raise ValueError("A supplied file cannot also be a parent directory")
                    parent = os.path.dirname(parent)
            quality = cls._quality_for_existing(project_dir, prepared, strict_quality_gate, [entrypoint])
        except (ValueError, TypeError, AttributeError, OSError, UnicodeError) as exc:
            quality = {"valid": False, "strict": strict_quality_gate, "files": {},
                "errors": [f"Invalid project input: {exc}"]}
        if not quality["valid"]:
            return cls._quality_failure(clean_name, project_dir, quality)
        for rel_path, result in quality["files"].items():
            if rel_path in prepared:
                prepared[rel_path] = result["sanitized_code"]
        # All supplied/existing Python sources pass before the first mutation.
        cls.ensure_dir()
        os.makedirs(project_dir, exist_ok=True)
        written_files = []
        for rel_path, content in prepared.items():
            full_file_path = cls._contained_path(project_dir, rel_path)
            os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
            cls._atomic_text(full_file_path, content)
            
            written_files.append({
                "name": rel_path,
                "size_bytes": len(content.encode("utf-8")),
                "content": content
            })

        # Validation has already completed in memory, without executing code or
        # creating .pyc files. Retain the manifest field for existing clients.
        syntax_errors = []

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
                elif entrypoint.lower().endswith((".py", ".pyw")):
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
        cls._preserve_existing(zip_path)
        staged_zip = zip_path + "." + uuid.uuid4().hex + ".staged"
        with zipfile.ZipFile(staged_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for relative in cls._existing_files(project_dir):
                zf.write(cls._contained_path(project_dir, relative), relative)
        os.replace(staged_zip, zip_path)

        manifest = {
            "project_name": clean_name,
            "display_name": project_name,
            "language": language,
            "description": description,
            "entrypoint": entrypoint,
            "project_dir": project_dir,
            "files": written_files,
            "syntax_errors": syntax_errors,
            "code_quality": quality,
            "build": build_output,
            "execution": execution_output,
            "zip_path": zip_path,
            "zip_name": zip_filename,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        manifest_path = os.path.join(project_dir, "program_manifest.json")
        cls._atomic_text(manifest_path, json.dumps(manifest, indent=2))

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
    def run_existing_program(cls, project_name: str, entrypoint: Optional[str] = None, powershell_command: Optional[str] = None,
                             strict_quality_gate: bool = False) -> Dict[str, Any]:
        """Runs an existing built program and captures output via Python or PowerShell."""
        clean_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")).lower()
        project_dir = os.path.join(PROGRAMS_DIR, clean_name)
        if not os.path.exists(project_dir):
            return {"status": "error", "message": f"Program '{project_name}' not found."}

        try:
            if not clean_name:
                raise ValueError("A nonempty program name is required")
            cls._contained_path(PROGRAMS_DIR, clean_name)
        except (ValueError, TypeError, OSError, UnicodeError) as exc:
            quality = {"valid": False, "files": {}, "errors": [str(exc)]}
            return cls._quality_failure(clean_name, project_dir, quality)

        manifest_path = cls._contained_path(project_dir, "program_manifest.json")
        if not entrypoint and os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                entrypoint = manifest.get("entrypoint", "main.py")

        try:
            entrypoint = cls._relative_path(entrypoint or "main.py")
            entry_full = cls._contained_path(project_dir, entrypoint)
            quality = cls._quality_for_existing(project_dir, strict=strict_quality_gate, include_paths=[entrypoint])
        except (ValueError, TypeError, OSError) as exc:
            return cls._quality_failure(clean_name, project_dir,
                {"valid": False, "files": {}, "errors": [str(exc)]})
        if not quality["valid"]:
            return cls._quality_failure(clean_name, project_dir, quality)

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
    def build_project(cls, project_name_or_dir: str, build_command: Optional[str] = None, timeout_seconds: int = 300,
                      strict_quality_gate: bool = False) -> Dict[str, Any]:
        """Executes a build in a project directory, auto-detecting build tools if build_command is omitted."""
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

        try:
            quality = cls._quality_for_existing(target_dir, strict=strict_quality_gate)
        except (ValueError, TypeError, OSError, UnicodeError) as exc:
            quality = {"valid": False, "files": {}, "errors": [str(exc)]}
        if not quality["valid"]:
            return cls._quality_failure(project_name_or_dir, target_dir, quality)

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
                cls._atomic_text(manifest_path, json.dumps(manifest, indent=2))
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

