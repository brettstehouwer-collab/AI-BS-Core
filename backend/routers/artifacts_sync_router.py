import os
import glob
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

WORKSPACE_ROOT = r"C:\AI-BS"
router = APIRouter(prefix="/api/artifacts", tags=["Artifacts & Program Builder"])

class ProgramBuildRequest(BaseModel):
    project_name: str
    language: str = "python"
    description: str = "Autonomous program build"
    files: List[Dict[str, str]]
    entrypoint: str = "main.py"
    run_immediately: bool = True

class ProgramRunRequest(BaseModel):
    project_name: str
    entrypoint: Optional[str] = "main.py"

def get_file_info(file_path: str, category: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return None
    stat = os.stat(file_path)
    preview = ""
    try:
        if file_path.endswith((".md", ".txt", ".json", ".py", ".js")):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                preview = f.read(1500)
    except Exception:
        pass

    return {
        "name": os.path.basename(file_path),
        "path": file_path,
        "category": category,
        "size_bytes": stat.st_size,
        "modified_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        "preview": preview
    }

@router.get("/live")
def get_live_artifacts() -> Dict[str, Any]:
    """Scans and returns all live tasks, implementation plans, media, manuals, and built programs."""
    tasks = []
    plans = []
    media = []
    manuals = []

    # 1. Master Task & Active Tasks
    active_task = os.path.join(WORKSPACE_ROOT, "task.md")
    if os.path.exists(active_task):
        info = get_file_info(active_task, "active_task")
        if info:
            tasks.append(info)

    task_history = glob.glob(os.path.join(WORKSPACE_ROOT, "Agent_Tasks_History", "*.md"))
    for th in sorted(task_history, key=os.path.getmtime, reverse=True)[:10]:
        info = get_file_info(th, "task_history")
        if info:
            tasks.append(info)

    # 2. Master Implementation Plan & History
    active_plan = os.path.join(WORKSPACE_ROOT, "implementation_plan.md")
    if os.path.exists(active_plan):
        info = get_file_info(active_plan, "active_plan")
        if info:
            plans.append(info)

    plan_history = glob.glob(os.path.join(WORKSPACE_ROOT, "Agent_Implementation_Plans_History", "*.md"))
    for ph in sorted(plan_history, key=os.path.getmtime, reverse=True)[:10]:
        info = get_file_info(ph, "plan_history")
        if info:
            plans.append(info)

    # 3. System Manuals & Ledgers
    ledger_path = os.path.join(WORKSPACE_ROOT, "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md")
    manual_path = os.path.join(WORKSPACE_ROOT, "docs", "AI_BS_MASTER_ECOSYSTEM_MANUAL.md")
    checkpoint_path = os.path.join(WORKSPACE_ROOT, "SAVED_CHECKPOINT.md")
    for doc in [ledger_path, manual_path, checkpoint_path]:
        if os.path.exists(doc):
            info = get_file_info(doc, "system_manual")
            if info:
                manuals.append(info)

    # 4. Media & Visual Artifacts
    media_patterns = [
        os.path.join(WORKSPACE_ROOT, "saved_data", "artifacts", "*.*"),
        os.path.join(WORKSPACE_ROOT, "saved_data", "media", "*.*"),
    ]
    for pattern in media_patterns:
        for mf in sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)[:15]:
            ext = os.path.splitext(mf)[1].lower()
            if ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".mp4", ".wav", ".mp3", ".md"):
                info = get_file_info(mf, "media")
                if info:
                    media.append(info)

    # 5. Built Programs
    try:
        from core.program_builder_engine import AutonomousProgramBuilder
        programs = AutonomousProgramBuilder.list_programs()
    except Exception:
        programs = []

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tasks": tasks,
        "plans": plans,
        "manuals": manuals,
        "media": media,
        "programs": programs,
        "total_artifacts": len(tasks) + len(plans) + len(manuals) + len(media) + len(programs)
    }

@router.post("/programs/build")
def build_program(req: ProgramBuildRequest):
    """Builds and optionally executes an autonomous program."""
    try:
        from core.program_builder_engine import AutonomousProgramBuilder
        res = AutonomousProgramBuilder.build_program(
            project_name=req.project_name,
            language=req.language,
            description=req.description,
            files=req.files,
            entrypoint=req.entrypoint,
            run_immediately=req.run_immediately
        )
        return {"status": "success", "program": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/programs/run")
def run_program(req: ProgramRunRequest):
    """Runs an existing built program."""
    try:
        from core.program_builder_engine import AutonomousProgramBuilder
        res = AutonomousProgramBuilder.run_existing_program(
            project_name=req.project_name,
            entrypoint=req.entrypoint
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/programs/list")
def list_programs():
    """Lists all built programs."""
    try:
        from core.program_builder_engine import AutonomousProgramBuilder
        return {"programs": AutonomousProgramBuilder.list_programs()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/programs/download/{project_name}")
def download_program_zip(project_name: str):
    """Downloads the built program ZIP archive."""
    clean_name = "".join(c for c in project_name if c.isalnum() or c in ("-", "_")).lower()
    zip_path = os.path.join(WORKSPACE_ROOT, "saved_data", "built_programs", f"{clean_name}.zip")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Program ZIP archive not found.")
    return FileResponse(zip_path, media_type="application/zip", filename=f"{clean_name}.zip")
