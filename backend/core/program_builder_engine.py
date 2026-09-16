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
    def build_program(
        cls,
        project_name: str,
        language: str,
        description: str,
        files: List[Dict[str, str]],
        entrypoint: str = "main.py",
        run_immediately: bool = True
    ) -> Dict[str, Any]:
        """
        Builds a complete multi-file software program.
        files: [{"path": "main.py", "content": "..."}, ...]
        """
        cls.ensure_dir()
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

        execution_output = {
            "executed": False,
            "status": "not_run",
            "stdout": "",
            "stderr": "",
            "exit_code": 0
        }

        # Live execution if requested and syntax passed
        if run_immediately and not syntax_errors:
            entry_full = os.path.join(project_dir, entrypoint)
            if os.path.exists(entry_full) and entrypoint.endswith(".py"):
                try:
                    res = subprocess.run(
                        [PYTHON_EXE, entry_full],
                        cwd=project_dir,
                        capture_output=True,
                        text=True,
                        timeout=15.0
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
                        "stderr": "Execution timed out (15s limit reached).",
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
    def run_existing_program(cls, project_name: str, entrypoint: Optional[str] = None) -> Dict[str, Any]:
        """Runs an existing built program and captures output."""
        clean_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")).lower()
        project_dir = os.path.join(PROGRAMS_DIR, clean_name)
        if not os.path.exists(project_dir):
            return {"status": "error", "message": f"Program '{project_name}' not found."}

        manifest_path = os.path.join(project_dir, "program_manifest.json")
        if not entrypoint and os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
                entrypoint = manifest.get("entrypoint", "main.py")

        entrypoint = entrypoint or "main.py"
        entry_full = os.path.join(project_dir, entrypoint)
        if not os.path.exists(entry_full):
            return {"status": "error", "message": f"Entrypoint '{entrypoint}' not found in {project_dir}."}

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
