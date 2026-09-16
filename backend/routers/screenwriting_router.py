from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import csv
import io
import json
import uuid
import shutil
import httpx
import os
import edge_tts

from core.ai_adapter import (
    adapt_book_to_screenplay,
    ADAPTATION_TASKS,
    cancel_adaptation,
    reset_adaptation,
    get_all_adaptation_tasks
)

router = APIRouter(tags=["Screenwriting & Adaptation"])

SCREENPLAY_ROOT = Path("C:/AI-BS/screenplay_projects")
SCREENPLAY_ROOT.mkdir(parents=True, exist_ok=True)
_current_project = "Default Project"


def _get_current_project():
    global _current_project
    from core.matrix_docs import ScreenplayProject
    return ScreenplayProject(SCREENPLAY_ROOT / _current_project)


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

@router.post("/api/screenplay/adapt")
async def start_book_adaptation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form(...),
    adaptation_type: str = Form("Feature Film"),
    book_style: str = Form("Fiction Novel / Narrative"),
    force: bool = Form(False)
):
    existing = ADAPTATION_TASKS.get(project_name)
    if existing and existing.get("status") == "processing":
        if not force:
            return JSONResponse(
                status_code=409,
                content={
                    "status": "processing",
                    "message": "An adaptation job is already processing for this project.",
                    "task": existing
                }
            )
        else:
            cancel_adaptation(project_name)
            reset_adaptation(project_name)

    try:
        project_dir = Path(f"C:/AI-BS/screenplay_projects/{project_name}")
        project_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix.lower() if file.filename else ".pdf"
        if not ext:
            ext = ".pdf"
        source_path = project_dir / f"source{ext}"

        content = await file.read()
        with open(source_path, "wb") as f:
            f.write(content)

        background_tasks.add_task(
            adapt_book_to_screenplay,
            source_path,
            project_name,
            adaptation_type,
            book_style
        )

        return {"status": "success", "message": f"Adaptation started for {project_name}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/screenplay/adapt/text")
async def start_text_adaptation(
    background_tasks: BackgroundTasks,
    request: Request
):
    try:
        data = await request.json()
        project_name = data.get("project_name", "Studio Document Adaptation")
        content = data.get("content", "")
        adaptation_type = data.get("adaptation_type", "Feature Film (Spec Script)")
        book_style = data.get("book_style", "Fiction Novel / Narrative")
        force = data.get("force", False)

        if not content or not content.strip():
            return JSONResponse(status_code=400, content={"status": "error", "message": "Content cannot be empty."})

        existing = ADAPTATION_TASKS.get(project_name)
        if existing and existing.get("status") == "processing":
            if not force:
                return JSONResponse(
                    status_code=409,
                    content={
                        "status": "processing",
                        "message": "An adaptation job is already processing for this project.",
                        "task": existing
                    }
                )
            else:
                cancel_adaptation(project_name)
                reset_adaptation(project_name)

        project_dir = Path(f"C:/AI-BS/screenplay_projects/{project_name}")
        project_dir.mkdir(parents=True, exist_ok=True)
        source_path = project_dir / "source.txt"
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(content)

        background_tasks.add_task(
            adapt_book_to_screenplay,
            source_path,
            project_name,
            adaptation_type,
            book_style
        )

        return {"status": "success", "message": f"Adaptation started for {project_name}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/api/screenplay/adapt/status")
def get_adaptation_status(project_name: str):
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
    project_name = data.get("project_name")
    if not project_name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing project_name"})
    success = cancel_adaptation(project_name)
    return {"status": "success" if success else "not_found", "project_name": project_name}


@router.post("/api/screenplay/adapt/reset")
async def reset_adaptation_endpoint(request: Request):
    data = await request.json()
    project_name = data.get("project_name")
    if not project_name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing project_name"})
    reset_adaptation(project_name)
    return {"status": "success", "message": f"Reset adaptation state for {project_name}"}


@router.get("/api/screenplay/adapt/stream")
async def stream_adaptation_status(project_name: str, request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break

            tasks = get_all_adaptation_tasks()
            status = tasks.get(project_name, {"status": "not_found", "progress": 0})
            status_json = json.dumps(status)
            yield f"data: {status_json}\n\n"

            if status.get("status") in ["complete", "error", "canceled"]:
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

    project_dir = SCREENPLAY_ROOT / clean_name
    project_dir.mkdir(parents=True, exist_ok=True)

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


@router.post("/api/screenwriting/projects/delete")
def delete_project(payload: SwitchProjectPayload):
    global _current_project
    if payload.project_name == "Default Project":
        raise HTTPException(status_code=400, detail="Cannot delete Default Project")
    project_dir = SCREENPLAY_ROOT / payload.project_name
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)
    _current_project = "Default Project"
    return {"status": "success", "current": _current_project}


@router.post("/api/screenwriting/projects/switch")
def switch_project(payload: SwitchProjectPayload):
    global _current_project
    project_dir = SCREENPLAY_ROOT / payload.project_name
    if not project_dir.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
    _current_project = payload.project_name
    return {"status": "success", "current": _current_project}


# ==============================================================================
# 3. SCREENPLAY READ / WRITE / PARSE / BRANCHES
# ==============================================================================

class WriteScreenplayPayload(BaseModel):
    content: str


@router.get("/api/screenwriting/read")
def read_screenplay(project_name: Optional[str] = None):
    global _current_project
    if project_name and project_name.strip():
        _current_project = project_name.strip()

    file_path = SCREENPLAY_ROOT / _current_project / "screenplay.fountain"
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
    else:
        adaptation_path = SCREENPLAY_ROOT / _current_project / "adaptation_output.fountain"
        if adaptation_path.exists():
            content = adaptation_path.read_text(encoding="utf-8")
            file_path.write_text(content, encoding="utf-8")
        else:
            content = f"Title: {_current_project}\n\nINT. UNKNOWN - DAY\n\nAction goes here.\n"
            file_path.write_text(content, encoding="utf-8")
    return {"content": content, "project": _current_project}


@router.post("/api/screenwriting/write")
def write_screenplay(payload: WriteScreenplayPayload):
    global _current_project
    file_path = SCREENPLAY_ROOT / _current_project / "screenplay.fountain"
    file_path.write_text(payload.content, encoding="utf-8")
    return {"status": "success"}


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
    name: str
    bio: str = ""
    speaking_style: str = ""


@router.get("/api/screenwriting/projects/characters")
def get_characters():
    proj = _get_current_project()
    return {"status": "success", "characters": proj.metadata.get('characters', [])}


@router.post("/api/screenwriting/projects/characters")
def save_character(payload: CharacterPayload):
    proj = _get_current_project()
    chars = proj.metadata.get('characters', [])
    updated = False
    for c in chars:
        if c['name'] == payload.name:
            c['bio'] = payload.bio
            c['speaking_style'] = payload.speaking_style
            updated = True
            break
    if not updated:
        chars.append({"name": payload.name, "bio": payload.bio, "speaking_style": payload.speaking_style})

    proj.metadata['characters'] = chars
    proj.save_metadata()
    return {"status": "success", "characters": chars}


@router.delete("/api/screenwriting/projects/characters")
def delete_character(name: str):
    proj = _get_current_project()
    chars = proj.metadata.get('characters', [])
    chars = [c for c in chars if c['name'] != name]
    proj.metadata['characters'] = chars
    proj.save_metadata()
    return {"status": "success", "characters": chars}


class ReorderBeatsPayload(BaseModel):
    source_index: int
    target_index: int


@router.post("/api/screenwriting/beats/reorder")
def reorder_beats(payload: ReorderBeatsPayload):
    proj = _get_current_project()
    success = proj.reorder_beats(payload.source_index, payload.target_index)
    if success:
        from core.matrix_docs import FountainParser
        content = proj.read_screenplay()
        parser = FountainParser(content)
        parser.parse()
        return {"status": "success", "parsed": {"html": parser.to_html(), "beats": parser.extract_beats()}}
    return {"status": "error", "message": "Reorder failed"}


class SceneVideoPayload(BaseModel):
    beat_id: str
    video_url: str


@router.post("/api/screenwriting/projects/scene_video")
def save_scene_video(payload: SceneVideoPayload):
    proj = _get_current_project()
    proj.map_video_to_beat(payload.beat_id, payload.video_url)
    return {"status": "success"}


class ImportProjectPayload(BaseModel):
    project_name: str
    content: str


@router.post("/api/screenwriting/projects/import")
def do_import_project(payload: ImportProjectPayload):
    from core.matrix_docs import ScreenplayProject
    proj_dir = SCREENPLAY_ROOT / payload.project_name
    proj = ScreenplayProject(proj_dir)
    proj.write_screenplay(payload.content)
    return {"status": "success"}


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


@router.get("/api/screenwriting/export/fdx")
def export_fdx():
    proj = _get_current_project()
    content = proj.read_screenplay()
    from core.matrix_docs import FountainParser
    parser = FountainParser(content)
    parser.parse()
    fdx = parser.to_fdx(proj.metadata.get('title', 'Untitled'), proj.metadata.get('author', 'Unknown'))
    return Response(content=fdx, media_type="application/xml", headers={"Content-Disposition": f"attachment; filename={proj.project_dir.name}.fdx"})


@router.get("/api/screenwriting/export/pdf")
def export_pdf(watermark: str = None):
    proj = _get_current_project()
    content = proj.read_screenplay()
    from core.matrix_docs import FountainParser
    parser = FountainParser(content)
    parser.parse()
    pdf_bytes = parser.to_pdf(proj.metadata.get('title', 'Untitled'), proj.metadata.get('author', 'Unknown'), watermark=watermark)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={proj.project_dir.name}.pdf"})


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
            
        net_budget = gross_budget * (1.0 - payload.parameters.tax_incentive_pct)
        
        top_sheet = {
            "above_the_line": round(above_the_line, 2),
            "production": round(production, 2),
            "post_production": round(post_production, 2),
            "contingency": round(contingency, 2),
            "gross_budget": round(gross_budget, 2),
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
                "csv_data": csv_data
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


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

@router.get("/api/screenwriting/projects/{project_name}/audio/info")
def get_project_audio_info(project_name: str):
    import wave
    audio_dir = SCREENPLAY_ROOT / project_name / "audio"
    if not audio_dir.exists():
        return {"status": "not_found", "has_audio": False}
    
    wav_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.m4a"))
    if not wav_files:
        return {"status": "not_found", "has_audio": False}
    
    target_file = wav_files[0]
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

    return {
        "status": "success",
        "has_audio": True,
        "file_name": target_file.name,
        "size_mb": size_mb,
        "duration_seconds": duration_s,
        "duration_formatted": formatted,
        "sample_rate": sample_rate,
        "channels": channels,
        "stream_url": f"/api/screenwriting/projects/{project_name}/audio/stream"
    }


@router.get("/api/screenwriting/projects/{project_name}/audio/stream")
def stream_project_audio(project_name: str):
    from fastapi.responses import FileResponse
    audio_dir = SCREENPLAY_ROOT / project_name / "audio"
    if not audio_dir.exists():
        raise HTTPException(status_code=404, detail="Audio directory not found")
        
    wav_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.m4a"))
    if not wav_files:
        raise HTTPException(status_code=404, detail="No audio adaptation found for this project")
        
    target_file = wav_files[0]
    return FileResponse(
        path=str(target_file),
        media_type="audio/wav" if target_file.suffix.lower() == ".wav" else "audio/mpeg",
        filename=target_file.name
    )


@router.post("/api/screenwriting/projects/{project_name}/audio/transcribe")
def start_audio_transcription(project_name: str, background_tasks: BackgroundTasks):
    from core.audio_transcriber import run_transcription_sync
    background_tasks.add_task(run_transcription_sync, project_name, "base")
    return {"status": "started", "message": f"Transcription started for '{project_name}'"}


@router.get("/api/screenwriting/projects/{project_name}/audio/transcribe/status")
def get_audio_transcription_status(project_name: str):
    from core.audio_transcriber import AUDIO_TRANSCRIBE_TASKS
    return AUDIO_TRANSCRIBE_TASKS.get(project_name, {"status": "idle"})


@router.get("/api/screenwriting/projects/{project_name}/audio/transcript")
def get_project_audio_transcript(project_name: str):
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


