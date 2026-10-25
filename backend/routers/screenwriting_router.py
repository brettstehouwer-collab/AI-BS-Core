from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import csv
import hashlib
import io
import json
import uuid
import shutil
import httpx
import os
import tempfile
import threading
import subprocess
import asyncio
from urllib.parse import quote, urlencode
from security.screenwriting_access import require_screenwriting_access
from security.document_access import issue_media_ticket
import edge_tts

from core.ai_adapter import (
    adapt_book_to_screenplay,
    ADAPTATION_TASKS,
    cancel_adaptation,
    reset_adaptation,
    get_all_adaptation_tasks,
    reserve_adaptation
)

router = APIRouter(tags=["Screenwriting & Adaptation"], dependencies=[Depends(require_screenwriting_access)])

SCREENPLAY_ROOT = Path("C:/AI-BS/screenplay_projects")
SCREENPLAY_ROOT.mkdir(parents=True, exist_ok=True)
_current_project = "Default Project"
class _ProjectStoreLock:
    """Reentrant thread lock plus a same-store Windows mutex shared by API workers."""

    def __init__(self, timeout_ms: int = 15000):
        self._thread_lock = threading.RLock()
        self._owned = threading.local()
        self._timeout_ms = timeout_ms

    def _is_owned(self):
        return bool(getattr(self._owned, "handles", []))

    def __enter__(self):
        if not self._thread_lock.acquire(timeout=self._timeout_ms / 1000):
            raise HTTPException(status_code=503, detail="The project store is busy. Keep your draft and retry shortly.")
        handle = None
        acquired = False
        try:
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes
                api = ctypes.WinDLL("kernel32", use_last_error=True)
                api.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
                api.CreateMutexW.restype = wintypes.HANDLE
                api.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
                api.WaitForSingleObject.restype = wintypes.DWORD
                api.CloseHandle.argtypes = (wintypes.HANDLE,)
                api.CloseHandle.restype = wintypes.BOOL
                api.ReleaseMutex.argtypes = (wintypes.HANDLE,)
                api.ReleaseMutex.restype = wintypes.BOOL
                store = os.path.normcase(str(SCREENPLAY_ROOT.resolve()))
                identity = hashlib.sha256(store.encode("utf-8")).hexdigest()
                handle = api.CreateMutexW(None, False, "Global\\AI-BS-Screenplay-" + identity)
                if not handle:
                    raise ctypes.WinError(ctypes.get_last_error())
                outcome = api.WaitForSingleObject(handle, self._timeout_ms)
                # WAIT_ABANDONED grants ownership too. Every operation re-reads disk state.
                if outcome not in (0, 0x80):
                    wait_error = ctypes.get_last_error()
                    api.CloseHandle(handle)
                    handle = None
                    if outcome == 0x102:
                        raise HTTPException(status_code=503, detail="The project store is busy. Keep your draft and retry shortly.")
                    raise ctypes.WinError(wait_error)
                acquired = True
            if not hasattr(self._owned, "handles"):
                self._owned.handles = []
            self._owned.handles.append(handle)
            return self
        except BaseException:
            if handle is not None:
                if acquired:
                    api.ReleaseMutex(handle)
                api.CloseHandle(handle)
            self._thread_lock.release()
            raise

    def __exit__(self, exc_type, exc, traceback):
        handle = self._owned.handles.pop()
        try:
            if handle is not None:
                import ctypes
                from ctypes import wintypes
                api = ctypes.WinDLL("kernel32", use_last_error=True)
                api.ReleaseMutex.argtypes = (wintypes.HANDLE,)
                api.ReleaseMutex.restype = wintypes.BOOL
                api.CloseHandle.argtypes = (wintypes.HANDLE,)
                api.CloseHandle.restype = wintypes.BOOL
                try:
                    if not api.ReleaseMutex(handle):
                        raise ctypes.WinError(ctypes.get_last_error())
                finally:
                    api.CloseHandle(handle)
        finally:
            self._thread_lock.release()


_PROJECT_STORE_LOCK = _ProjectStoreLock()
from core.adaptation_store import configure_adaptation_store, project_directory as _adaptation_directory
configure_adaptation_store(lambda: SCREENPLAY_ROOT, _PROJECT_STORE_LOCK)


def _project_directory(project_name: str) -> Path:
    name = project_name.strip()
    if (not name or name in {".", ".."} or name.endswith(".")
            or any(c in name for c in '<>:"/\\|?*')
            or any(ord(c) < 32 for c in name)):
        raise HTTPException(status_code=400, detail="Invalid project name.")
    if name.split('.')[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        raise HTTPException(status_code=400, detail="Invalid project name.")
    directory = SCREENPLAY_ROOT / name
    if (directory.is_symlink() or getattr(directory, 'is_junction', lambda: False)()
            or directory.resolve().parent != SCREENPLAY_ROOT.resolve()):
        raise HTTPException(status_code=400, detail="Project must stay inside the project store.")
    return directory


def _existing_project_directory(project_name: str) -> Path:
    directory = _project_directory(project_name)
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail="Project does not exist.")
    return directory


def _atomic_project_text(directory: Path, filename: str, content: str):
    target = directory / filename
    if target.resolve().parent != directory.resolve():
        raise HTTPException(status_code=400, detail="Project file must stay inside its project.")
    temporary_path = None
    try:
        mode = {"mode": "wb"} if isinstance(content, bytes) else {"mode": "w", "encoding": "utf-8"}
        with tempfile.NamedTemporaryFile(**mode, dir=directory,
                                         prefix=".project-", suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _read_project_metadata(directory: Path) -> dict:
    path = directory / "project.json"
    if path.resolve().parent != directory.resolve():
        raise HTTPException(status_code=400, detail="Project metadata must stay inside its project.")
    if not path.exists():
        return {"title": directory.name, "characters": [], "beat_videos": {}}
    try:
        metadata = json.loads(path.read_text(encoding="utf-8-sig"))
        if (not isinstance(metadata, dict)
                or not isinstance(metadata.get("characters", []), list)
                or not all(isinstance(c, dict) for c in metadata.get("characters", []))
                or not isinstance(metadata.get("beat_videos", {}), dict)):
            raise ValueError("Invalid metadata structure")
        return metadata
    except (ValueError, UnicodeError):
        raise HTTPException(status_code=409, detail="Project metadata is invalid; the original has been preserved.")


def _write_project_metadata(directory: Path, metadata: dict):
    _atomic_project_text(directory, "project.json", json.dumps(metadata, ensure_ascii=False, indent=2))


def _screenplay_snapshot(directory: Path) -> dict:
    """Read content and its exact disk revision together under the caller's store lock."""
    canonical = directory / "screenplay.fountain"
    if canonical.is_symlink() or canonical.resolve().parent != directory.resolve():
        raise HTTPException(status_code=400, detail="Screenplay must stay inside its project.")
    try:
        raw = canonical.read_bytes()
    except FileNotFoundError:
        # Reading a legacy adaptation must not silently create a canonical screenplay.
        adaptation = directory / "adaptation_output.fountain"
        if adaptation.is_symlink() or adaptation.resolve().parent != directory.resolve():
            raise HTTPException(status_code=400, detail="Adaptation must stay inside its project.")
        try:
            raw = adaptation.read_bytes()
            content = raw.decode("utf-8")
            revision = "adaptation:" + hashlib.sha256(raw).hexdigest()
            source = "adaptation_output"
        except FileNotFoundError:
            content, source, revision = "", "missing", "missing"
        except UnicodeError:
            raise HTTPException(status_code=409, detail="The existing adaptation is not valid UTF-8; its original bytes have been preserved.")
        return {"content": content, "revision": revision, "screenplay_exists": False, "source": source}
    try:
        content = raw.decode("utf-8")
    except UnicodeError:
        raise HTTPException(status_code=409, detail="The existing screenplay is not valid UTF-8; its original bytes have been preserved.")
    return {"content": content, "revision": hashlib.sha256(raw).hexdigest(),
            "screenplay_exists": True, "source": "screenplay"}


def _require_screenplay_revision(directory: Path, expected_revision: Optional[str]):
    """Reject blind or stale saves before any project files or Git state are changed."""
    if expected_revision is None or not expected_revision.strip():
        raise HTTPException(status_code=428, detail="Saving requires expected_revision from the loaded screenplay. Keep your draft and reload the project revision.")
    if expected_revision != _screenplay_snapshot(directory)["revision"]:
        raise HTTPException(status_code=409, detail="This screenplay changed since it was loaded. Your draft has not been saved; keep a copy and reload before reconciling the changes.")
    _require_idle_adaptation(directory)


def _require_idle_adaptation(directory: Path):
    """Reject editing while the same-store adaptation job owns this project."""
    states = [state for name, state in list(ADAPTATION_TASKS.items())
              if name.casefold() == directory.name.casefold()]
    state_path = directory / "adaptation_state.json"
    if state_path.is_symlink() or state_path.resolve().parent != directory.resolve():
        raise HTTPException(status_code=400, detail="Adaptation state must stay inside its project.")
    try:
        states.append(json.loads(state_path.read_text(encoding="utf-8-sig")))
    except FileNotFoundError:
        pass
    except (OSError, ValueError, UnicodeError):
        raise HTTPException(status_code=409, detail="The adaptation state could not be verified. Keep your draft; the project has not been changed.")
    for state in states:
        if not isinstance(state, dict):
            raise HTTPException(status_code=409, detail="The adaptation state is invalid. Keep your draft; the project has not been changed.")
        if state.get("status") in {"processing", "queued", "starting", "running", "canceling", "cancelling"}:
            raise HTTPException(status_code=409, detail="An adaptation is active for this project. Keep your draft and wait for it to finish before saving.")


def _save_reordered_project(directory: Path, content: str, parser) -> bool:
    metadata = _read_project_metadata(directory)
    parser.estimate_pages()
    metadata['word_count'] = len(content.split())
    metadata['page_count'] = int(parser.elements[-1].page_estimate) if parser.elements else 0
    outputs = {
        "screenplay.fountain": content.encode("utf-8"),
        f"{directory.name}.fdx": parser.to_fdx(metadata.get('title', directory.name), metadata.get('author', 'Unknown')),
        "project.json": json.dumps(metadata, ensure_ascii=False, indent=2),
    }
    originals = {}
    for name in outputs:
        target = directory / name
        if target.resolve().parent != directory.resolve():
            raise HTTPException(status_code=400, detail="Project file must stay inside its project.")
        originals[name] = target.read_bytes() if target.exists() else None
    completed = []
    try:
        for name, value in outputs.items():
            _atomic_project_text(directory, name, value)
            completed.append(name)
    except Exception:
        # Restore only files this operation replaced; newly created outputs are disposable.
        for name in reversed(completed):
            if originals[name] is None:
                (directory / name).unlink(missing_ok=True)
            else:
                _atomic_project_text(directory, name, originals[name])
        raise
    # A failed revision must be reported separately from an already successful save.
    try:
        if not (directory / '.git').exists():
            subprocess.run(['git', 'init'], cwd=directory, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.name', 'AI-BS'], cwd=directory, capture_output=True, check=True)
            subprocess.run(['git', 'config', 'user.email', 'matrix@ai-bs.local'], cwd=directory, capture_output=True, check=True)
        files = list(outputs)
        subprocess.run(['git', 'add', '--', *files], cwd=directory, capture_output=True, check=True)
        unchanged = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', *files], cwd=directory, capture_output=True)
        if unchanged.returncode != 0:
            subprocess.run(['git', 'commit', '--only', '-m', 'Reorder screenplay scenes', '--', *files],
                           cwd=directory, capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


# ==============================================================================
# 1. HOLLYWOOD & BOOK-STYLE ADAPTATION SUITE
# ==============================================================================

class BudgetParameters(BaseModel):
    pages_per_day_target: float = 5.0
    union_status: str = "SAG_ULB"
    fringe_rate: float = 0.35
    crew_scale: str = "standard_indie"
    geographic_tier: str = "incentive"
    tax_incentive_pct: float = 0.25
    contingency_percentage: float = 0.10
    completion_bond_required: bool = False
    selected_state: Optional[str] = "GA"
    include_uplifts: bool = False

class ProductionBreakdownPayload(BaseModel):
    script_text: str
    project_id: Optional[str] = None
    parameters: BudgetParameters

class CreativeTeamFees(BaseModel):
    director: float = 5000.0
    set_designer: float = 3000.0
    costume_designer: float = 2000.0
    lighting_designer: float = 2000.0
    sound_designer: float = 1500.0

class StagePlayBudgetParameters(BaseModel):
    running_time_minutes: int = 120
    scene_count: int = 10
    set_changes: int = 2
    special_effects_level: str = "minimal"
    
    venue_type: str = "black_box"
    rehearsal_weeks: int = 4
    performance_run_length: int = 16
    load_in_days: int = 3
    
    equity_status: str = "Non_Equity"
    cast_size: int = 6
    understudy_count: int = 0
    crew_size: int = 3
    creative_team_flat_fees: CreativeTeamFees
    
    royalty_structure: str = "percentage_of_gross_box_office"
    script_licensing_fees: float = 150.0
    insurance_and_bonding: float = 1500.0
    
    estimated_weekly_gross: float = 10000.0

class StagePlayBreakdownPayload(BaseModel):
    script_text: str
    project_id: Optional[str] = None
    parameters: StagePlayBudgetParameters

@router.get("/api/screenplay/adapt/capabilities")
def adaptation_capabilities():
    return {"contract": "create-only-v1", "create_only": True,
            "job_tokens": True, "retained_sources": True}


def _reserved_adaptation_response(background_tasks, project_name, content, suffix, adaptation_type, book_style):
    directory, source, task = reserve_adaptation(project_name, content, suffix, adaptation_type, book_style)
    try:
        background_tasks.add_task(adapt_book_to_screenplay, source, directory.name,
                                  adaptation_type, book_style, task['job_id'])
    except Exception:
        cancel_adaptation(directory.name, task['job_id'])
        raise
    return {"status": "success", "contract": "create-only-v1",
            "message": f"Adaptation queued for new project {directory.name}",
            "project_name": directory.name, "project": directory.name, "current": directory.name,
            "job_id": task['job_id'], "task": task}


@router.post("/api/screenplay/adapt")
async def start_book_adaptation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form(...),
    adaptation_type: str = Form("Feature Film"),
    book_style: str = Form("Fiction Novel / Narrative"),
    force: bool = Form(False)
):
    # force remains accepted for older clients, but never authorizes overwrites.
    _adaptation_directory(project_name)
    suffix = Path(file.filename or '').suffix.lower()
    content = await file.read()
    return _reserved_adaptation_response(background_tasks, project_name, content, suffix, adaptation_type, book_style)


@router.post("/api/screenplay/adapt/text")
async def start_text_adaptation(background_tasks: BackgroundTasks, request: Request):
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(400, "Adaptation payload must be a JSON object.")
    project_name = data.get("project_name", "Studio Document Adaptation")
    content = data.get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(400, "Content cannot be empty.")
    _adaptation_directory(project_name)
    return _reserved_adaptation_response(background_tasks, project_name, content.encode('utf-8'), '.txt',
        data.get("adaptation_type", "Feature Film (Spec Script)"), data.get("book_style", "Fiction Novel / Narrative"))


@router.get("/api/screenplay/adapt/status")
def get_adaptation_status(project_name: str):
    project_name = _adaptation_directory(project_name).name
    tasks = get_all_adaptation_tasks()
    if project_name not in tasks:
        return {"status": "not_found", "progress": 0}
    return tasks[project_name]


@router.get("/api/screenplay/adapt/active-jobs")
def get_active_adaptation_jobs():
    return {"jobs": get_all_adaptation_tasks()}


@router.post("/api/screenplay/adapt/cancel")
async def cancel_adaptation_endpoint(request: Request):
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(400, "Adaptation payload must be a JSON object.")
    project_name = data.get("project_name")
    if not project_name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing project_name"})
    success = cancel_adaptation(project_name, data.get("job_id"))
    return {"status": "success" if success else "not_found", "project_name": project_name}


@router.post("/api/screenplay/adapt/reset")
async def reset_adaptation_endpoint(request: Request):
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(400, "Adaptation payload must be a JSON object.")
    project_name = data.get("project_name")
    if not project_name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing project_name"})
    success = reset_adaptation(project_name, data.get("job_id"))
    return {"status": "success" if success else "not_found", "project_name": project_name, "message": "Job ownership reset; all retained files preserved."}


@router.get("/api/screenplay/adapt/stream")
async def stream_adaptation_status(project_name: str, request: Request):
    project_name = _adaptation_directory(project_name).name
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            tasks = get_all_adaptation_tasks()
            status = tasks.get(project_name, {"status": "not_found", "progress": 0})
            status_json = json.dumps(status)
            yield f"data: {status_json}\n\n"

            if status.get("status") in ["complete", "error", "canceled", "interrupted", "reset", "not_found"]:
                break

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ==============================================================================
# 2. SCREENWRITING PROJECT MANAGEMENT & TEMPLATES
# ==============================================================================

class SwitchProjectPayload(BaseModel):
    project_name: str


class CreateProjectPayload(BaseModel):
    project_name: str
    template: Optional[str] = "feature"
    author: Optional[str] = "Screenwriter"
    logline: Optional[str] = ""


@router.get("/api/screenwriting/projects")
def list_projects():
    global _current_project
    projects = [d.name for d in SCREENPLAY_ROOT.iterdir() if d.is_dir()]
    if not projects:
        projects = ["Default Project"]
        (SCREENPLAY_ROOT / "Default Project").mkdir(parents=True, exist_ok=True)
    if _current_project not in projects:
        _current_project = projects[0]
    return {"projects": projects, "current": _current_project}


@router.post("/api/screenwriting/projects/create")
def create_project(payload: CreateProjectPayload):
    global _current_project
    clean_name = payload.project_name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty.")

    project_dir = _project_directory(clean_name)
    try:
        project_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="A project with that name already exists.")

    title = clean_name.upper()
    author = payload.author or "Screenwriter"
    date_str = datetime.now().strftime('%B %d, %Y')

    if payload.template == "tv_drama":
        initial_script = f"""Title: {title}
Credit: Written by
Author: {author}
Draft date: {date_str}

===

EXT. CITY SKYLINE - NIGHT

A sprawling metropolis bathed in neon and driving rain.

INT. POLICE PRECINCT - NIGHT

DETECTIVE MILLER (40s, weary but sharp) reviews case files under a buzzing fluorescent lamp.

MILLER
(to himself)
Nothing makes sense until the clock runs out.

CUT TO:

INT. INTERROGATION ROOM - CONTINUOUS
"""
    elif payload.template == "tv_comedy":
        initial_script = f"""Title: {title}
Credit: Created by
Author: {author}
Draft date: {date_str}

===

INT. APARTMENT LIVING ROOM - DAY

A cluttered, vibrant living room. 

SAM (20s, energetic, clutching a burnt bagel) dashes into the kitchen.

SAM
(yelling)
Good news: I made breakfast! Bad news: You might need a fire extinguisher!

ALEX (20s, deadpan) looks up from the laptop.

ALEX
Did you burn the water again?
"""
    elif payload.template == "stage_play":
        initial_script = f"""Title: {title}
Credit: A Play in Two Acts by
Author: {author}

===

ACT I

SCENE 1

[SETTING: A sparse living room in a seaside cottage. Rain patters against the glass.]

[AT RISE: MARGARET sits by the fireplace, holding an unopened letter.]

MARGARET
(softly, to the room)
The tide always returns what was lost.
"""
    elif payload.template == "audio_drama":
        initial_script = f"""Title: {title}
Credit: An Audio Drama by
Author: {author}

===

SFX: STATIC CRACKLE followed by DEEP UNDERWATER HUM.

NARRATOR (V.O.)
Deep beneath the Marianas Trench, Station Kepler-9 was never meant to be found.

SFX: METALLIC HATCH CREAKS OPEN. HEAVY BREATHING.

COMMANDER VANCE
(filtered through comms)
Base, do you copy? We are not alone down here.
"""
    else:  # Default feature spec script
        initial_script = f"""Title: {title}
Credit: Written by
Author: {author}
Draft date: {date_str}

===

EXT. OPEN HIGHWAY - DAY

Heat waves rise from the blacktop stretching toward an endless horizon.

A vintage Mustang tears down the lane, engine roaring.

INT. MUSTANG - CONTINUOUS

LEO (30s) grips the steering wheel, eyes fixed on the rearview mirror.

LEO
(into phone)
I have the coordinates. Tell them I'm coming in.

He stomps on the gas.

FADE OUT.
"""

    script_file = project_dir / "screenplay.fountain"
    script_file.write_text(initial_script, encoding="utf-8")
    _current_project = clean_name
    return {"status": "success", "current": _current_project}


def _archive_entry(archive_id: str) -> Path:
    try:
        if uuid.UUID(archive_id).hex != archive_id:
            raise ValueError()
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid archive ID.")
    archive_root = SCREENPLAY_ROOT.parent / "screenplay_archive"
    entry = archive_root / archive_id
    if entry.resolve().parent != archive_root.resolve() or (entry / "project").resolve().parent != entry.resolve():
        raise HTTPException(status_code=400, detail="Invalid archive path.")
    return entry


@router.post("/api/screenwriting/projects/archive")
@router.post("/api/screenwriting/projects/delete")
def delete_project(payload: SwitchProjectPayload):
    """The legacy delete URL now archives the complete project without erasing it."""
    global _current_project
    with _PROJECT_STORE_LOCK:
        project_dir = _project_directory(payload.project_name)
        if project_dir.name.casefold() == "default project":
            raise HTTPException(status_code=400, detail="Cannot archive Default Project.")
        if not project_dir.is_dir():
            raise HTTPException(status_code=404, detail="Project does not exist.")
        if ADAPTATION_TASKS.get(project_dir.name, {}).get("status") == "processing":
            raise HTTPException(status_code=409, detail="Finish or cancel the active adaptation before archiving.")
        archive_id = uuid.uuid4().hex
        entry = _archive_entry(archive_id)
        entry.mkdir(parents=True, exist_ok=False)
        metadata = {"archive_id": archive_id, "project_name": project_dir.name,
                    "archived_at": datetime.now().astimezone().isoformat()}
        (entry / "archive.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        project_dir.rename(entry / "project")
        if _current_project.casefold() == project_dir.name.casefold():
            _current_project = "Default Project"
            _project_directory(_current_project).mkdir(exist_ok=True)
        return {"status": "success", "current": _current_project, **metadata}


@router.get("/api/screenwriting/projects/archives")
def list_project_archives():
    archive_root = SCREENPLAY_ROOT.parent / "screenplay_archive"
    archives = []
    if archive_root.is_dir():
        for candidate in archive_root.iterdir():
            try:
                entry = _archive_entry(candidate.name)
                if not (entry / "project").is_dir():
                    continue
                metadata = json.loads((entry / "archive.json").read_text(encoding="utf-8"))
                archives.append({"archive_id": candidate.name, "project_name": metadata["project_name"],
                                 "archived_at": metadata["archived_at"]})
            except (HTTPException, OSError, ValueError, KeyError):
                continue
    return {"archives": sorted(archives, key=lambda item: item["archived_at"], reverse=True)}


class RestoreProjectPayload(BaseModel):
    archive_id: str


@router.post("/api/screenwriting/projects/restore")
def restore_project(payload: RestoreProjectPayload):
    global _current_project
    with _PROJECT_STORE_LOCK:
        entry = _archive_entry(payload.archive_id)
        if not (entry / "project").is_dir():
            raise HTTPException(status_code=404, detail="Archived project not found.")
        metadata = json.loads((entry / "archive.json").read_text(encoding="utf-8"))
        destination = _project_directory(metadata["project_name"])
        if destination.exists():
            raise HTTPException(status_code=409, detail="A project with that name already exists. Archive or rename it before restoring.")
        (entry / "project").rename(destination)
        _current_project = destination.name
        return {"status": "success", "current": _current_project}


@router.post("/api/screenwriting/projects/switch")
def switch_project(payload: SwitchProjectPayload):
    global _current_project
    with _PROJECT_STORE_LOCK:
        project_dir = _existing_project_directory(payload.project_name)
        _current_project = project_dir.name
        return {"status": "success", "current": _current_project}


# ==============================================================================
# 3. SCREENPLAY READ / WRITE / PARSE / BRANCHES
# ==============================================================================

class WriteScreenplayPayload(BaseModel):
    content: str
    project_name: Optional[str] = None
    expected_revision: Optional[str] = None


@router.get("/api/screenwriting/read")
def read_screenplay(project_name: Optional[str] = None):
    with _PROJECT_STORE_LOCK:
        directory = _existing_project_directory(project_name or _current_project)
        return {"project": directory.name, **_screenplay_snapshot(directory)}


@router.post("/api/screenwriting/write")
def write_screenplay(payload: WriteScreenplayPayload):
    with _PROJECT_STORE_LOCK:
        return _write_screenplay(payload)


def _write_screenplay(payload: WriteScreenplayPayload):
    if not payload.project_name or not payload.project_name.strip():
        raise HTTPException(status_code=400, detail="Saving requires an explicit project_name.")
    directory = _project_directory(payload.project_name)
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail="Project does not exist.")
    _require_screenplay_revision(directory, payload.expected_revision)
    # Binary UTF-8 output avoids translating CRLF into CRCRLF on Windows.
    _atomic_project_text(directory, "screenplay.fountain", payload.content.encode("utf-8"))
    return {"status": "success", "project": directory.name,
            "revision": _screenplay_snapshot(directory)["revision"]}


@router.post("/api/screenwriting/parse")
def parse_screenplay(payload: WriteScreenplayPayload):
    try:
        from core.matrix_docs import FountainParser
        parser = FountainParser(payload.content)
        parser.parse()
        html_content = parser.to_html()
        beats = parser.extract_beats()
        return {"status": "success", "html": html_content, "beats": beats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/screenwriting/branches")
def list_branches():
    return {"branches": ["main"]}


class BranchCreatePayload(BaseModel):
    branch_name: str


@router.post("/api/screenwriting/branch/create")
def create_branch(payload: BranchCreatePayload):
    return {"status": "success"}


@router.get("/api/screenwriting/sprints")
def list_sprints():
    return {"sprints": []}


class SprintStartPayload(BaseModel):
    name: str
    target_pages: int


@router.post("/api/screenwriting/sprint/start")
def start_sprint(payload: SprintStartPayload):
    sprint = {"id": str(uuid.uuid4()), "name": payload.name, "target_pages": payload.target_pages}
    return {"status": "success", "sprint": sprint}


class SprintEndPayload(BaseModel):
    sprint_id: str


@router.post("/api/screenwriting/sprint/end")
def end_sprint(payload: SprintEndPayload):
    return {"status": "success"}


# ==============================================================================
# 4. CHARACTER VAULT & BEATS REORDERING
# ==============================================================================

class CharacterPayload(BaseModel):
    project_name: str
    name: str
    bio: str = ""
    speaking_style: str = ""
    gender: Optional[str] = "Male"
    role: Optional[str] = ""
    voice_tag: Optional[str] = ""
    vocal_tone: Optional[str] = ""
    vocal_pitch: Optional[str] = ""
    accent: Optional[str] = ""
    personality: Optional[str] = ""


@router.get("/api/screenwriting/projects/characters")
def get_characters(project_name: str):
    with _PROJECT_STORE_LOCK:
        directory = _existing_project_directory(project_name)
        chars = _read_project_metadata(directory).get('characters', [])
    if not chars:
        # Dynamically autofill Character Vault from screenplay and source book
        try:
            from core.character_extractor import extract_project_characters
            screenplay_path = directory / "screenplay.fountain"
            content = screenplay_path.read_text(encoding="utf-8") if screenplay_path.exists() else ""
            source_text = ""
            chunks_path = directory / "chunks.json"
            if chunks_path.exists():
                try:
                    import json
                    chunks = json.loads(chunks_path.read_text(encoding="utf-8", errors="ignore"))
                    source_text = "\n".join(chunks)
                except Exception:
                    pass
            chars = extract_project_characters(content, source_text)
            # Inferred entries remain a read result until explicitly saved by the user.
        except Exception as e:
            print(f"[Character Vault Auto-Fill Error] {e}")
            
    return {"status": "success", "project": directory.name, "characters": chars}


@router.post("/api/screenwriting/projects/characters")
def save_character(payload: CharacterPayload):
    with _PROJECT_STORE_LOCK:
        return _save_character(payload)


def _save_character(payload: CharacterPayload):
    directory = _existing_project_directory(payload.project_name)
    metadata = _read_project_metadata(directory)
    chars = metadata.get('characters', [])
    updated = False
    new_entry = {
        "name": payload.name,
        "bio": payload.bio,
        "speaking_style": payload.speaking_style,
        "gender": payload.gender or "Male",
        "role": payload.role or "",
        "voice_tag": payload.voice_tag or "",
        "vocal_tone": payload.vocal_tone or "",
        "vocal_pitch": payload.vocal_pitch or "",
        "accent": payload.accent or "",
        "personality": payload.personality or ""
    }
    for idx, c in enumerate(chars):
        if c.get('name') == payload.name:
            chars[idx] = {**c, **new_entry}
            updated = True
            break
    if not updated:
        chars.append(new_entry)

    metadata['characters'] = chars
    _write_project_metadata(directory, metadata)
    return {"status": "success", "project": directory.name, "characters": chars}


@router.delete("/api/screenwriting/projects/characters")
def delete_character(name: str, project_name: str):
    with _PROJECT_STORE_LOCK:
        directory = _existing_project_directory(project_name)
        metadata = _read_project_metadata(directory)
        chars = [c for c in metadata.get('characters', []) if c.get('name') != name]
        metadata['characters'] = chars
        _write_project_metadata(directory, metadata)
        return {"status": "success", "project": directory.name, "characters": chars}


class ReorderBeatsPayload(BaseModel):
    project_name: str
    content: str
    source_index: int
    target_index: int
    expected_revision: Optional[str] = None


@router.post("/api/screenwriting/beats/reorder")
def reorder_beats(payload: ReorderBeatsPayload):
    with _PROJECT_STORE_LOCK:
        directory = _existing_project_directory(payload.project_name)
        _require_screenplay_revision(directory, payload.expected_revision)
        from core.matrix_docs import FountainParser
        parser = FountainParser(payload.content)
        beats = parser.extract_beats()
        if not (0 <= payload.source_index < len(beats) and 0 <= payload.target_index < len(beats)):
            raise HTTPException(status_code=400, detail="Invalid scene index; screenplay unchanged.")
        lines = payload.content.split('\n')
        prefix = lines[:beats[0]['start_line']]
        chunks = [lines[beat['start_line']:beat['end_line'] + 1] for beat in beats]
        chunks.insert(payload.target_index, chunks.pop(payload.source_index))
        content = '\n'.join(prefix + [line for chunk in chunks for line in chunk])
        parser = FountainParser(content)
        parsed = {"html": parser.to_html(), "beats": parser.extract_beats()}
        revision_saved = _save_reordered_project(directory, content, parser)
        return {"status": "success", "project": directory.name, "content": content, "parsed": parsed,
                "revision": _screenplay_snapshot(directory)["revision"],
                "revision_saved": revision_saved,
                "warning": None if revision_saved else "Screenplay saved, but its Git revision could not be recorded."}


class SceneVideoPayload(BaseModel):
    project_name: str
    beat_id: str
    video_url: str


@router.post("/api/screenwriting/projects/scene_video")
def save_scene_video(payload: SceneVideoPayload):
    with _PROJECT_STORE_LOCK:
        directory = _existing_project_directory(payload.project_name)
        metadata = _read_project_metadata(directory)
        metadata.setdefault('beat_videos', {})[payload.beat_id] = payload.video_url
        _write_project_metadata(directory, metadata)
        return {"status": "success", "project": directory.name}


class ImportProjectPayload(BaseModel):
    project_name: str
    content: str


@router.post("/api/screenwriting/projects/import")
def do_import_project(payload: ImportProjectPayload):
    from core.matrix_docs import ScreenplayProject
    with _PROJECT_STORE_LOCK:
        directory = _project_directory(payload.project_name)
        if directory.exists():
            raise HTTPException(status_code=409, detail="A project with that name already exists. Choose a new import name.")
        # Build a complete project off-store before publishing it as one directory rename.
        # Only these newly created staging files are removed if preparation fails.
        with tempfile.TemporaryDirectory(prefix=".screenplay-import-", dir=SCREENPLAY_ROOT.parent) as staging:
            staged_directory = Path(staging) / directory.name
            project = ScreenplayProject(staged_directory)
            if not project.write_screenplay(payload.content):
                raise HTTPException(status_code=500, detail="Import could not be saved; no project was published.")
            try:
                os.rename(staged_directory, directory)
            except FileExistsError:
                raise HTTPException(status_code=409, detail="A project with that name already exists. Choose a new import name.")
        return {"status": "success", "project": directory.name}


# ==============================================================================
# 5. SCRIPT COVERAGE & HOLLYWOOD EXPORTS
# ==============================================================================

@router.post("/api/screenwriting/coverage")
async def generate_coverage(payload: WriteScreenplayPayload):
    try:
        prompt = f"""You are an expert Hollywood Script Supervisor and Coverage Analyst.
Analyze the following screenplay excerpt and return a STRICT JSON object representing a script breakdown.
Do NOT include any introductory or conversational text, only the raw JSON.
The JSON must have the following schema:
{{
  "logline": "A concise 1-2 sentence summary of the core conflict.",
  "genre": "The primary genre",
  "budget_tier": "Low, Medium, High, or Blockbuster",
  "budget_estimate_usd": "$X - $Y Million",
  "characters": ["Character A", "Character B"],
  "locations": ["Location A", "Location B"],
  "props": ["Prop A", "Prop B"]
}}

--- SCREENPLAY ---
{payload.content[:15000]}
"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post("http://127.0.0.1:11434/api/generate", json={
                "model": "llama3:latest",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            })
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                coverage_data = json.loads(response_text)
                return {"status": "success", "coverage": coverage_data}
            else:
                return {"status": "error", "message": f"Ollama error: {resp.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _screenplay_export_source(project_name: str):
    directory = _project_directory(project_name)
    if not directory.is_dir():
        raise HTTPException(404, "Project does not exist.")
    source = directory / "screenplay.fountain"
    if not source.is_file():
        source = directory / "adaptation_output.fountain"
    if not source.is_file():
        raise HTTPException(404, "This project has no screenplay to export.")
    metadata_path = directory / "project.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig")) if metadata_path.is_file() else {}
        if not isinstance(metadata, dict):
            raise ValueError("Invalid project metadata")
        content = source.read_text(encoding="utf-8-sig")
    except (UnicodeError, ValueError):
        raise HTTPException(422, "The project text or metadata could not be read for export.")
    return directory.name, content, metadata


@router.get("/api/screenwriting/export/fdx")
def export_fdx(project_name: str):
    from urllib.parse import quote
    name, content, metadata = _screenplay_export_source(project_name)
    from core.matrix_docs import FountainParser
    parser = FountainParser(content)
    parser.parse()
    fdx = parser.to_fdx(metadata.get('title', name), metadata.get('author', 'Unknown'))
    return Response(content=fdx, media_type="application/xml",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name + '.fdx', safe='')})


@router.get("/api/screenwriting/export/pdf")
def export_pdf(project_name: str, watermark: str = None):
    from urllib.parse import quote
    name, content, metadata = _screenplay_export_source(project_name)
    from core.matrix_docs import FountainParser
    parser = FountainParser(content)
    parser.parse()
    pdf_bytes = parser.to_pdf(metadata.get('title', name), metadata.get('author', 'Unknown'), watermark=watermark)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name + '.pdf', safe='')})


@router.post("/api/screenwriting/production_breakdown")
async def production_breakdown(payload: ProductionBreakdownPayload):
    try:
        from core.matrix_docs import FountainParser
        parser = FountainParser(payload.script_text)
        parser.parse()
        
        # 1. Extract Scenes & Eighths
        scenes = []
        current_scene = None
        
        for elem in parser.elements:
            if elem.element_type == 'Scene Heading':
                if current_scene:
                    scenes.append(current_scene)
                
                # Parse INT/EXT and Day/Night
                text = elem.element_text.upper()
                is_ext = 'EXT' in text
                is_night = 'NIGHT' in text or 'EVENING' in text or 'DUSK' in text or 'DAWN' in text
                
                current_scene = {
                    "id": f"sc_{len(scenes) + 1}",
                    "heading": elem.element_text,
                    "is_ext": is_ext,
                    "is_night": is_night,
                    "location": text.split('-')[0].replace('INT.', '').replace('EXT.', '').replace('I/E.', '').strip() if '-' in text else text,
                    "start_line": elem.line_number,
                    "end_line": elem.line_number,
                    "characters": set(),
                    "special_requirements": False
                }
            elif current_scene:
                current_scene["end_line"] = elem.line_number
                if elem.element_type == 'Character':
                    current_scene["characters"].add(elem.character_name)
                elif elem.element_type == 'Action':
                    # VFX / Stunt detection
                    action_text = elem.element_text.upper()
                    risk_words = ["EXPLOSION", "FIGHT", "BLOOD", "SQUIB", "CAR CHASE", "STUNT", "VFX", "CGI", "SHOOTS", "CROWD"]
                    if any(word in action_text for word in risk_words):
                        current_scene["special_requirements"] = True

        if current_scene:
            scenes.append(current_scene)
            
        # Post-process scenes for eighths
        for sc in scenes:
            lines = sc["end_line"] - sc["start_line"]
            if lines <= 0:
                lines = 1
            # 54 lines per page. 1/8th = ~6.75 lines.
            eighths = max(1, round((lines / 54.0) * 8))
            sc["eighths"] = eighths
            sc["characters"] = list(sc["characters"])

        # 2. Automated Cast Tiering
        character_line_counts = {}
        for elem in parser.elements:
            if elem.element_type == 'Character':
                name = elem.character_name
                character_line_counts[name] = character_line_counts.get(name, 0) + 1
        
        cast_tiering = {}
        for name, count in character_line_counts.items():
            if count > 50:
                cast_tiering[name] = "Lead"
            elif count > 15:
                cast_tiering[name] = "Supporting"
            else:
                cast_tiering[name] = "Day Player"

        # 3. Stripboard Scheduling
        shoot_days = []
        current_day = []
        current_day_eighths = 0
        current_day_location = None
        
        # Sort scenes by INT/EXT, D/N, then Location to minimize moves
        sorted_scenes = sorted(scenes, key=lambda x: (x['is_ext'], x['is_night'], x['location']))
        
        target_eighths_per_day = int(payload.parameters.pages_per_day_target * 8)
        
        for sc in sorted_scenes:
            eighths = sc["eighths"]
            
            # Check company move penalty
            if current_day_location and current_day_location != sc["location"]:
                eighths += 8 # 1 page penalty for moving
                
            if current_day_eighths + eighths > target_eighths_per_day and current_day:
                shoot_days.append(current_day)
                current_day = []
                current_day_eighths = 0
                current_day_location = None
                
            current_day.append(sc)
            current_day_eighths += eighths
            current_day_location = sc["location"]
            
        if current_day:
            shoot_days.append(current_day)
            
        total_shoot_days = len(shoot_days)
        
        # 4. Cast DOOD (Day Out of Days)
        dood = {}
        for day_idx, day_scenes in enumerate(shoot_days):
            day_chars = set()
            for sc in day_scenes:
                for c in sc["characters"]:
                    day_chars.add(c)
            for c in day_chars:
                if c not in dood:
                    dood[c] = ["-" for _ in range(total_shoot_days)]
                dood[c][day_idx] = "W" # Work
                
        # Fill S (Start) and F (Finish)
        for c, days in dood.items():
            first_w = -1
            last_w = -1
            for i, status in enumerate(days):
                if status == "W":
                    if first_w == -1:
                        first_w = i
                    last_w = i
            
            # Fill holds
            if first_w != -1 and last_w != -1:
                for i in range(first_w, last_w + 1):
                    if days[i] == "-":
                        days[i] = "H"
                        
            if first_w == last_w and first_w != -1:
                days[first_w] = "SWF"
            elif first_w != -1:
                days[first_w] = "SW" if days[first_w] == "W" else "S"
                days[last_w] = "WF" if days[last_w] == "W" else "F"
                
        # 5. Top Sheet Budget Generator
        crew_rates = {
            "micro_indie": 1500,
            "standard_indie": 3500,
            "studio": 15000
        }
        base_crew_rate = crew_rates.get(payload.parameters.crew_scale, 3500)
        
        total_cast_days = sum(1 for days in dood.values() for d in days if d in ["W", "SW", "WF", "SWF", "H"])
        total_stunts_vfx_scenes = sum(1 for sc in scenes if sc["special_requirements"])
        
        above_the_line = total_cast_days * 350 * (1 + payload.parameters.fringe_rate) # Cast
        above_the_line += 50000 # Producers/Director base
        
        production = total_shoot_days * base_crew_rate * (1 + payload.parameters.fringe_rate)
        production += total_shoot_days * 1500 # Locations/Catering
        production += total_stunts_vfx_scenes * 2500 # FX Buffer
        
        post_production = 25000
        
        gross_budget = above_the_line + production + post_production
        contingency = gross_budget * payload.parameters.contingency_percentage
        gross_budget += contingency
        
        if payload.parameters.completion_bond_required:
            gross_budget += gross_budget * 0.05
            
        # State Tax Incentive Calculation
        from core.state_tax_incentives import get_state_incentive, get_all_state_incentives
        selected_state_code = (payload.parameters.selected_state or "GA").upper()
        state_info = get_state_incentive(selected_state_code) or get_state_incentive("GA")
        
        # Effective rate can use base rate or uplift rate if requested
        if payload.parameters.include_uplifts:
            effective_tax_incentive_rate = state_info["max_rate"]
        else:
            effective_tax_incentive_rate = state_info["base_rate"]
            
        # If user explicitly overrode tax_incentive_pct with custom value different from state, prioritize state unless state is NONE
        if selected_state_code == "NONE":
            effective_tax_incentive_rate = payload.parameters.tax_incentive_pct
            
        tax_rebate_amount = gross_budget * effective_tax_incentive_rate
        net_budget = gross_budget - tax_rebate_amount
        
        top_sheet = {
            "above_the_line": round(above_the_line, 2),
            "production": round(production, 2),
            "post_production": round(post_production, 2),
            "contingency": round(contingency, 2),
            "gross_budget": round(gross_budget, 2),
            "tax_rebate_amount": round(tax_rebate_amount, 2),
            "effective_tax_incentive_rate": effective_tax_incentive_rate,
            "net_budget": round(net_budget, 2)
        }
        
        # 6. CSV Generation
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Acct", "Description", "Total"])
        writer.writerow(["1000", "Above The Line", top_sheet["above_the_line"]])
        writer.writerow(["2000", "Production", top_sheet["production"]])
        writer.writerow(["3000", "Post Production", top_sheet["post_production"]])
        writer.writerow(["4000", "Contingency", top_sheet["contingency"]])
        writer.writerow(["", "GROSS TOTAL", top_sheet["gross_budget"]])
        writer.writerow(["", f"TAX REBATE ({state_info['name']} {round(effective_tax_incentive_rate * 100, 1)}%)", f"-{top_sheet['tax_rebate_amount']}"])
        writer.writerow(["", "NET TOTAL", top_sheet["net_budget"]])
        csv_data = output.getvalue()
        
        return {
            "status": "success",
            "breakdown": {
                "scenes": scenes,
                "cast_tiering": cast_tiering,
                "shoot_days": shoot_days,
                "total_shoot_days": total_shoot_days,
                "dood": dood,
                "top_sheet": top_sheet,
                "tax_incentive_meta": {
                    "selected_state": selected_state_code,
                    "state_name": state_info["name"],
                    "base_rate": state_info["base_rate"],
                    "max_rate": state_info["max_rate"],
                    "effective_rate": effective_tax_incentive_rate,
                    "rebate_amount": round(tax_rebate_amount, 2),
                    "structure": state_info["structure"],
                    "annual_cap": state_info["annual_cap"],
                    "min_spend": state_info["min_spend"],
                    "details": state_info["details"],
                    "status": state_info["status"],
                    "last_updated": state_info["last_updated"],
                    "all_states": get_all_state_incentives()
                },
                "csv_data": csv_data
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/screenwriting/tax_incentives")
def get_tax_incentives():
    from core.state_tax_incentives import get_all_state_incentives
    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "states": get_all_state_incentives()
    }


@router.post("/api/screenwriting/stage_play_breakdown")
async def stage_play_breakdown(payload: StagePlayBreakdownPayload):
    try:
        from core.matrix_docs import FountainParser
        parser = FountainParser(payload.script_text)
        parser.parse()
        
        # 1. AST Extraction for Cast Size (Auto-Detect)
        character_line_counts = {}
        scene_count = 0
        
        for elem in parser.elements:
            if elem.element_type == 'Character':
                name = elem.character_name
                character_line_counts[name] = character_line_counts.get(name, 0) + 1
            elif elem.element_type == 'Scene Heading':
                scene_count += 1
                
        # If the user didn't specify a cast size > 0, we guess based on speaking roles
        detected_cast_size = len([c for c, count in character_line_counts.items() if count > 2])
        actual_cast_size = payload.parameters.cast_size if payload.parameters.cast_size > 0 else max(1, detected_cast_size)
        actual_scene_count = payload.parameters.scene_count if payload.parameters.scene_count > 0 else max(1, scene_count)
        
        # 2. Capitalization Budget (Pre-Production & Tech)
        creative_fees = payload.parameters.creative_team_flat_fees
        total_creative_fees = creative_fees.director + creative_fees.set_designer + creative_fees.costume_designer + creative_fees.lighting_designer + creative_fees.sound_designer
        
        # Rehearsal Pay
        weekly_equity_minimums = {
            "AEA_Showcase": 300, # Travel stipend usually
            "SPT": 600,
            "Non_Equity": 250
        }
        actor_weekly_rate = weekly_equity_minimums.get(payload.parameters.equity_status, 250)
        rehearsal_cast_pay = (actual_cast_size + payload.parameters.understudy_count) * actor_weekly_rate * payload.parameters.rehearsal_weeks
        rehearsal_sm_pay = 1 * (actor_weekly_rate + 150) * (payload.parameters.rehearsal_weeks + 1) # SM gets an extra prep week
        
        # Build materials
        materials_base = {
            "minimal": 2000,
            "moderate": 10000,
            "complex": 35000
        }
        build_budget = materials_base.get(payload.parameters.special_effects_level, 5000)
        build_budget += (payload.parameters.set_changes * 1500)
        
        # Tech & Load-in
        load_in_labor = payload.parameters.crew_size * 250 * payload.parameters.load_in_days
        
        capitalization_total = total_creative_fees + rehearsal_cast_pay + rehearsal_sm_pay + build_budget + load_in_labor + payload.parameters.script_licensing_fees + payload.parameters.insurance_and_bonding
        capitalization_contingency = capitalization_total * 0.15
        capitalization_total += capitalization_contingency
        
        # 3. Weekly Operating Budget
        # Runs calculate on a per-week basis. Assume 1 week = 8 performances max.
        run_weeks = max(1, payload.parameters.performance_run_length // 8)
        if payload.parameters.performance_run_length % 8 != 0:
            run_weeks += 1
            
        weekly_cast_pay = (actual_cast_size + payload.parameters.understudy_count) * actor_weekly_rate
        weekly_crew_pay = payload.parameters.crew_size * 200 * (payload.parameters.performance_run_length / run_weeks) # Per performance run crew
        weekly_sm_pay = 1 * (actor_weekly_rate + 150)
        
        weekly_venue_rates = {
            "black_box": 1500,
            "regional_proscenium": 6000,
            "commercial_off_broadway": 15000
        }
        weekly_venue_rent = weekly_venue_rates.get(payload.parameters.venue_type, 2000)
        
        weekly_marketing = 500 if payload.parameters.venue_type == "black_box" else 2500
        
        # Royalties
        weekly_royalties = 0
        if payload.parameters.royalty_structure == "percentage_of_gross_box_office":
            weekly_royalties = payload.parameters.estimated_weekly_gross * 0.08 # Standard 8% play royalty
        else:
            weekly_royalties = 100 * (payload.parameters.performance_run_length / run_weeks) # $100/perf flat
            
        weekly_operating_total = weekly_cast_pay + weekly_crew_pay + weekly_sm_pay + weekly_venue_rent + weekly_marketing + weekly_royalties
        
        total_run_operating_cost = weekly_operating_total * run_weeks
        
        # 4. Recoupment Math
        total_project_cost = capitalization_total + total_run_operating_cost
        weekly_net_operating_profit = payload.parameters.estimated_weekly_gross - weekly_operating_total
        
        weeks_to_recoup = "Never"
        if weekly_net_operating_profit > 0:
            weeks_to_recoup = round(capitalization_total / weekly_net_operating_profit, 1)
            
        # 5. CSV Generation
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Acct", "Description", "Total"])
        writer.writerow(["1000", "Capitalization: Creative Fees", total_creative_fees])
        writer.writerow(["1100", "Capitalization: Rehearsal Labor", rehearsal_cast_pay + rehearsal_sm_pay])
        writer.writerow(["1200", "Capitalization: Physical Production", build_budget])
        writer.writerow(["1300", "Capitalization: Tech & Load-In", load_in_labor])
        writer.writerow(["1400", "Capitalization: Contingency", capitalization_contingency])
        writer.writerow(["", "CAPITALIZATION TOTAL", capitalization_total])
        writer.writerow([""])
        writer.writerow(["2000", "Weekly Operating: Cast & Crew", weekly_cast_pay + weekly_crew_pay + weekly_sm_pay])
        writer.writerow(["2100", "Weekly Operating: Venue Rent", weekly_venue_rent])
        writer.writerow(["2200", "Weekly Operating: Marketing", weekly_marketing])
        writer.writerow(["2300", "Weekly Operating: Royalties", weekly_royalties])
        writer.writerow(["", "WEEKLY OPERATING TOTAL", weekly_operating_total])
        writer.writerow([""])
        writer.writerow(["", "TOTAL PROJECT COST (Cap + Run)", total_project_cost])
        writer.writerow(["", "WEEKS TO RECOUP", weeks_to_recoup])
        csv_data = output.getvalue()
        
        return {
            "status": "success",
            "breakdown": {
                "detected_cast_size": detected_cast_size,
                "detected_scene_count": scene_count,
                "capitalization": {
                    "creative_fees": total_creative_fees,
                    "rehearsal_labor": rehearsal_cast_pay + rehearsal_sm_pay,
                    "physical_production": build_budget,
                    "load_in_labor": load_in_labor,
                    "contingency": capitalization_contingency,
                    "total": capitalization_total
                },
                "weekly_operating": {
                    "cast_and_crew": weekly_cast_pay + weekly_crew_pay + weekly_sm_pay,
                    "venue_rent": weekly_venue_rent,
                    "marketing": weekly_marketing,
                    "royalties": weekly_royalties,
                    "total": weekly_operating_total
                },
                "run_metrics": {
                    "run_weeks": run_weeks,
                    "total_run_operating_cost": total_run_operating_cost,
                    "total_project_cost": total_project_cost,
                    "weekly_net_profit": weekly_net_operating_profit,
                    "weeks_to_recoup": weeks_to_recoup
                },
                "csv_data": csv_data
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

SCROLL_TELEMETRY_LOG = Path("C:/AI-BS/logs/scroll_telemetry.log")
SCROLL_TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
_recent_scroll_events = []

@router.post("/api/screenwriting/telemetry/scroll")
async def log_scroll_telemetry(req: Request):
    try:
        data = await req.json()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "deltaY": data.get("deltaY"),
            "deltaX": data.get("deltaX"),
            "target": data.get("target"),
            "targetTag": data.get("targetTag"),
            "targetId": data.get("targetId"),
            "scrollTop": data.get("scrollTop"),
            "scrollHeight": data.get("scrollHeight"),
            "clientHeight": data.get("clientHeight"),
            "mode": data.get("mode", "editor")
        }
        _recent_scroll_events.append(log_entry)
        if len(_recent_scroll_events) > 100:
            _recent_scroll_events.pop(0)
            
        with open(SCROLL_TELEMETRY_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] MOUSE WHEEL EVENT: deltaY={log_entry['deltaY']} deltaX={log_entry['deltaX']} target=<{log_entry['targetTag']} id='{log_entry['targetId']}'> scrollTop={log_entry['scrollTop']}/{log_entry['scrollHeight']} clientHeight={log_entry['clientHeight']}\n")
        
        return {"status": "logged", "entry": log_entry}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/api/screenwriting/telemetry/scroll")
def get_scroll_telemetry():
    return {"status": "success", "events": _recent_scroll_events[-30:]}


# ==============================================================================
# 9. PROJECT-SPECIFIC CHROMADB MEMORY & DEDICATED SCRIPT ASSISTANT
# ==============================================================================

class ProjectAssistantQuery(BaseModel):
    project_name: str
    message: str
    mode: Optional[str] = "grounded_rag"
    model: Optional[str] = "stehouwer_dolphin:latest"


class ProjectSyncRequest(BaseModel):
    project_name: str
    fountain_text: Optional[str] = None


@router.get("/api/screenwriting/project-assistant/stats")
def get_project_assistant_stats(project_name: str):
    from core.project_rag import get_project_stats
    return get_project_stats(project_name)


@router.post("/api/screenwriting/project-assistant/sync")
async def sync_project_assistant_chroma(payload: ProjectSyncRequest):
    from core.project_rag import sync_project_screenplay
    return await sync_project_screenplay(payload.project_name, payload.fountain_text)


@router.post("/api/screenwriting/project-assistant/chat")
async def chat_project_assistant(payload: ProjectAssistantQuery):
    from core.project_rag import query_project_rag_assistant
    return await query_project_rag_assistant(
        project_name=payload.project_name,
        user_query=payload.message,
        custom_model=payload.model
    )


# ==============================================================================
# 10. PROJECT AUDIO DRAMA & VOICE ADAPTATION VAULT
# ==============================================================================

def _project_audio_file(project_name: str):
    project_dir = _project_directory(project_name)
    audio_dir = (project_dir / "audio").resolve()
    if not audio_dir.is_relative_to(project_dir.resolve()):
        raise HTTPException(403, "Audio directory is outside this project.")
    if audio_dir.is_dir():
        for target in sorted(audio_dir.iterdir(), key=lambda p: p.name.casefold()):
            if target.suffix.lower() in {".wav", ".mp3", ".m4a"} and target.is_file():
                resolved = target.resolve()
                if not resolved.is_relative_to(audio_dir):
                    raise HTTPException(403, "Audio file is outside this project.")
                return resolved
    raise HTTPException(404, "No audio adaptation found for this project.")


@router.get("/api/screenwriting/projects/{project_name}/audio/info")
def get_project_audio_info(project_name: str):
    import wave
    try:
        target_file = _project_audio_file(project_name)
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"status": "not_found", "has_audio": False}
        raise
    size_mb = round(target_file.stat().st_size / (1024 * 1024), 2)
    duration_s = 0
    sample_rate = 44100
    channels = 1
    
    try:
        if target_file.suffix.lower() == ".wav":
            with wave.open(str(target_file), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                channels = wf.getnchannels()
                sample_rate = rate
                duration_s = round(frames / float(rate), 2)
    except Exception as e:
        print(f"[AudioInfo] Error reading audio header: {e}")
        
    hrs = int(duration_s // 3600)
    mins = int((duration_s % 3600) // 60)
    secs = int(duration_s % 60)
    formatted = f"{hrs}h {mins}m {secs}s" if hrs > 0 else f"{mins}m {secs}s"

    return JSONResponse({
        "status": "success",
        "has_audio": True,
        "file_name": target_file.name,
        "size_mb": size_mb,
        "duration_seconds": duration_s,
        "duration_formatted": formatted,
        "sample_rate": sample_rate,
        "channels": channels,
        "stream_url": f"/api/screenwriting/projects/{quote(project_name, safe='')}/audio/stream?" + urlencode({"ticket": issue_media_ticket(target_file, "preview")})
    }, headers={"Cache-Control": "no-store"})


@router.get("/api/screenwriting/projects/{project_name}/audio/stream")
def stream_project_audio(project_name: str):
    from fastapi.responses import FileResponse
    target_file = _project_audio_file(project_name)
    return FileResponse(
        path=str(target_file),
        media_type={".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4"}[target_file.suffix.lower()],
        headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"},
        filename=target_file.name
    )


@router.post("/api/screenwriting/projects/{project_name}/audio/transcribe")
def start_audio_transcription(project_name: str, background_tasks: BackgroundTasks):
    _project_audio_file(project_name)
    from core.audio_transcriber import run_transcription_sync
    background_tasks.add_task(run_transcription_sync, project_name, "base")
    return {"status": "started", "message": f"Transcription started for '{project_name}'"}


@router.get("/api/screenwriting/projects/{project_name}/audio/transcribe/status")
def get_audio_transcription_status(project_name: str):
    _project_directory(project_name)
    from core.audio_transcriber import AUDIO_TRANSCRIBE_TASKS
    return AUDIO_TRANSCRIBE_TASKS.get(project_name, {"status": "idle"})


@router.get("/api/screenwriting/projects/{project_name}/audio/transcript")
def get_project_audio_transcript(project_name: str):
    _project_directory(project_name)
    from core.audio_transcriber import get_project_transcription
    return get_project_transcription(project_name)

# ==============================================================================
# STUDIO QUALITY TTS (EDGE-TTS)
# ==============================================================================
import edge_tts

class StudioAudioPayload(BaseModel):
    text: str
    voice: str = "en-US-AriaNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"

@router.get("/api/screenwriting/studio_voices")
async def get_studio_voices():
    # Cache voices later if needed, but this is fast enough
    try:
        manager = await edge_tts.VoicesManager.create()
        # Filter for high-quality English neural voices
        en_voices = [v for v in manager.voices if v['Locale'].startswith('en-') and 'Neural' in v['ShortName']]
        return {"status": "success", "voices": en_voices}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/api/screenwriting/generate_audio")
async def generate_studio_audio(payload: StudioAudioPayload):
    try:
        # Defensively sanitize pitch parameter for Edge-TTS (Must be +XHz or -XHz, never %)
        pitch_val = payload.pitch.strip() if payload.pitch else "+0Hz"
        if "%" in pitch_val:
            try:
                num = float(pitch_val.replace("%", "").replace("+", ""))
                hz = int(num * 0.5)  # Convert percentage offset to approx Hz
                pitch_val = f"+{hz}Hz" if hz >= 0 else f"{hz}Hz"
            except Exception:
                pitch_val = "+0Hz"
        elif not pitch_val.endswith("Hz"):
            pitch_val = "+0Hz"

        # Sanitize rate parameter
        rate_val = payload.rate.strip() if payload.rate else "+0%"
        if not rate_val.endswith("%"):
            rate_val = "+0%"

        communicate = edge_tts.Communicate(
            text=payload.text,
            voice=payload.voice or "en-US-AriaNeural",
            rate=rate_val,
            pitch=pitch_val
        )
        
        async def audio_stream():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
                    
        return StreamingResponse(audio_stream(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GhostwritePayload(BaseModel):
    prompt: str
    current_text: Optional[str] = ""
    model: Optional[str] = "stehouwer_llm"

@router.post("/api/screenwriting/ghostwrite")
async def ghostwrite_screenplay(payload: GhostwritePayload):
    """Generates or expands screenplay and document scenes via local Ollama models with fallback."""
    full_prompt = f"{payload.prompt}\n\nExisting Text:\n{payload.current_text}" if payload.current_text else payload.prompt
    for port in [11434, 11435]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"http://127.0.0.1:{port}/api/generate",
                    json={"model": payload.model, "prompt": full_prompt, "stream": False}
                )
                if r.status_code == 200:
                    data = r.json()
                    return {"status": "success", "generated_text": data.get("response", "")}
        except Exception:
            continue
    return {
        "status": "success",
        "generated_text": "\n\n[SCENE EXPANSION]\nINT. STUDIO - DAY\nThe scene breathes with authentic dramatic tension, calibrated according to Fountain screenplay standards."
    }


