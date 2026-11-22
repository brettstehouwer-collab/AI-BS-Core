"""
Calendar & Action Items / Tasks Router for AI-BS Matrix.
Provides full CRUD, AI-powered Action Item extraction, calendar event sync,
and subtask checklist management backed by SQLite (database/calendar.db).
"""

import os
import json
import sqlite3
from datetime import datetime, date
from typing import Optional, List, Any
import httpx
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/calendar", tags=["Calendar & Action Items"])

DB_PATH = os.path.join("C:\\AI-BS", "database", "calendar.db")
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"


def init_calendar_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Appointments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT DEFAULT 'stehouwer_publishing',
                title TEXT NOT NULL,
                date TEXT,
                time TEXT,
                start_datetime TEXT,
                end_datetime TEXT,
                notes TEXT,
                category TEXT DEFAULT 'General'
            )
        """)

        # Action Items & Tasks Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calendar_action_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT DEFAULT 'stehouwer_publishing',
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT DEFAULT '',
                due_time TEXT DEFAULT '',
                priority TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Todo',
                category TEXT DEFAULT 'General',
                assigned_to TEXT DEFAULT 'Brett',
                calendar_event_id INTEGER DEFAULT NULL,
                subtasks TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()


# Initialize database on module load
init_calendar_db()


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class CalendarAppointmentSchema(BaseModel):
    title: str
    date: Optional[str] = ""
    time: Optional[str] = ""
    start_datetime: Optional[str] = ""
    end_datetime: Optional[str] = ""
    notes: Optional[str] = ""
    category: Optional[str] = "General"


class SubtaskItem(BaseModel):
    id: Optional[str] = None
    title: str
    done: bool = False


class TaskCreateSchema(BaseModel):
    title: str
    description: Optional[str] = ""
    due_date: Optional[str] = ""
    due_time: Optional[str] = ""
    priority: Optional[str] = "Medium"  # Urgent, High, Medium, Low
    status: Optional[str] = "Todo"  # Todo, In Progress, Completed, Deferred
    category: Optional[str] = "General"  # Screenplay, Tech, Client, General, Personal
    assigned_to: Optional[str] = "Brett"
    calendar_event_id: Optional[int] = None
    subtasks: Optional[List[SubtaskItem]] = []
    tags: Optional[List[str]] = []


class TaskUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    calendar_event_id: Optional[int] = None
    subtasks: Optional[List[SubtaskItem]] = None
    tags: Optional[List[str]] = None


class NLPTextRequest(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Appointments Endpoints (Backward Compatible)
# ---------------------------------------------------------------------------

@router.get("/appointments")
async def get_appointments():
    """Fetch all appointments from SQLite."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments ORDER BY start_datetime ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/appointments")
async def create_appointment(apt: CalendarAppointmentSchema):
    """Create a new appointment."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO appointments (title, date, time, start_datetime, end_datetime, notes, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (apt.title, apt.date, apt.time, apt.start_datetime, apt.end_datetime, apt.notes, apt.category))
            conn.commit()
            apt_id = cursor.lastrowid

        saved = apt.dict()
        saved["id"] = apt_id
        return {"status": "success", "appointment": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/appointments/{apt_id}")
async def update_appointment(apt_id: int, apt: CalendarAppointmentSchema):
    """Update an existing appointment."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE appointments 
                SET title=?, date=?, time=?, start_datetime=?, end_datetime=?, notes=?, category=?
                WHERE id=?
            """, (apt.title, apt.date, apt.time, apt.start_datetime, apt.end_datetime, apt.notes, apt.category, apt_id))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Appointment not found")

        saved = apt.dict()
        saved["id"] = apt_id
        return {"status": "success", "appointment": saved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/appointments/{apt_id}")
async def delete_appointment(apt_id: int):
    """Delete an appointment."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM appointments WHERE id = ?", (apt_id,))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Appointment not found")
            return {"status": "success", "deleted_id": apt_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/nlp/parse")
async def nlp_parse_appointment(req: NLPTextRequest):
    """NLP parsing: extract appointment details from free-form text using local LLM."""
    try:
        text = req.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text required")

        system_prompt = (
            "You are a calendar assistant. Parse natural language appointment descriptions "
            "and extract: start_datetime (ISO 8601), end_datetime (ISO 8601), title, notes, and category (Medical/Work/Personal/General/Sales). "
            "Return ONLY valid JSON with these fields. If date is relative (e.g. 'next Tuesday'), infer it from today's date. "
            f"Right now is {datetime.now().isoformat()}."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Parse: {text}"},
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                OLLAMA_CHAT_URL,
                json={
                    "model": "stehouwer_llm",
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                }
            )
            if r.status_code != 200:
                # Fallback to local Ollama default
                r = await client.post(
                    OLLAMA_CHAT_URL,
                    json={
                        "model": "nemotron-3.5-lightning",
                        "messages": messages,
                        "stream": False,
                        "format": "json",
                    }
                )
            r.raise_for_status()
            response_text = r.json().get("message", {}).get("content", "{}")
            parsed = json.loads(response_text)

        return {"status": "success", "parsed": parsed}
    except Exception as e:
        # Graceful fallback heuristic
        now_str = datetime.now().isoformat()
        return {
            "status": "success",
            "parsed": {
                "title": req.text[:40],
                "start_datetime": now_str,
                "end_datetime": now_str,
                "category": "General",
                "notes": req.text
            }
        }


# ---------------------------------------------------------------------------
# Action Items & Tasks Endpoints
# ---------------------------------------------------------------------------

@router.get("/tasks")
async def get_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Fetch action items / tasks with filtering."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM calendar_action_tasks WHERE 1=1"
            params = []

            if status and status.lower() != "all":
                query += " AND LOWER(status) = LOWER(?)"
                params.append(status)

            if priority and priority.lower() != "all":
                query += " AND LOWER(priority) = LOWER(?)"
                params.append(priority)

            if category and category.lower() != "all":
                query += " AND LOWER(category) = LOWER(?)"
                params.append(category)

            if search:
                query += " AND (title LIKE ? OR description LIKE ?)"
                params.append(f"%{search}%")
                params.append(f"%{search}%")

            query += " ORDER BY CASE priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, due_date ASC, id DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                item = dict(row)
                try:
                    item["subtasks"] = json.loads(item["subtasks"]) if item["subtasks"] else []
                except Exception:
                    item["subtasks"] = []
                try:
                    item["tags"] = json.loads(item["tags"]) if item["tags"] else []
                except Exception:
                    item["tags"] = []
                tasks.append(item)

            return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks")
async def create_task(task: TaskCreateSchema):
    """Create a new action item / task."""
    try:
        now = datetime.now().isoformat()
        subtasks_json = json.dumps([st.dict() for st in (task.subtasks or [])])
        tags_json = json.dumps(task.tags or [])

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO calendar_action_tasks 
                (title, description, due_date, due_time, priority, status, category, assigned_to, calendar_event_id, subtasks, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.title,
                task.description or "",
                task.due_date or "",
                task.due_time or "",
                task.priority or "Medium",
                task.status or "Todo",
                task.category or "General",
                task.assigned_to or "Brett",
                task.calendar_event_id,
                subtasks_json,
                tags_json,
                now,
                now
            ))
            conn.commit()
            task_id = cursor.lastrowid

        saved = task.dict()
        saved["id"] = task_id
        saved["created_at"] = now
        saved["updated_at"] = now
        return {"status": "success", "task": saved}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/tasks/{task_id}")
async def update_task(task_id: int, updates: TaskUpdateSchema):
    """Update an action item / task."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calendar_action_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")

            current = dict(row)
            now = datetime.now().isoformat()

            new_title = updates.title if updates.title is not None else current["title"]
            new_desc = updates.description if updates.description is not None else current["description"]
            new_due_date = updates.due_date if updates.due_date is not None else current["due_date"]
            new_due_time = updates.due_time if updates.due_time is not None else current["due_time"]
            new_priority = updates.priority if updates.priority is not None else current["priority"]
            new_status = updates.status if updates.status is not None else current["status"]
            new_category = updates.category if updates.category is not None else current["category"]
            new_assigned = updates.assigned_to if updates.assigned_to is not None else current["assigned_to"]
            new_cal_id = updates.calendar_event_id if updates.calendar_event_id is not None else current["calendar_event_id"]
            
            if updates.subtasks is not None:
                new_subtasks = json.dumps([st.dict() for st in updates.subtasks])
            else:
                new_subtasks = current["subtasks"]

            if updates.tags is not None:
                new_tags = json.dumps(updates.tags)
            else:
                new_tags = current["tags"]

            cursor.execute("""
                UPDATE calendar_action_tasks
                SET title=?, description=?, due_date=?, due_time=?, priority=?, status=?, category=?, assigned_to=?, calendar_event_id=?, subtasks=?, tags=?, updated_at=?
                WHERE id=?
            """, (
                new_title, new_desc, new_due_date, new_due_time, new_priority, new_status, new_category, new_assigned, new_cal_id, new_subtasks, new_tags, now, task_id
            ))
            conn.commit()

            cursor.execute("SELECT * FROM calendar_action_tasks WHERE id = ?", (task_id,))
            updated_row = dict(cursor.fetchone())
            try:
                updated_row["subtasks"] = json.loads(updated_row["subtasks"])
            except Exception:
                updated_row["subtasks"] = []
            try:
                updated_row["tags"] = json.loads(updated_row["tags"])
            except Exception:
                updated_row["tags"] = []

            return {"status": "success", "task": updated_row}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/tasks/{task_id}/toggle")
async def toggle_task_status(task_id: int):
    """Toggle a task between Completed and Todo."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM calendar_action_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Task not found")

            current_status = row["status"]
            new_status = "Completed" if current_status != "Completed" else "Todo"
            now = datetime.now().isoformat()

            cursor.execute("""
                UPDATE calendar_action_tasks 
                SET status = ?, updated_at = ? 
                WHERE id = ?
            """, (new_status, now, task_id))
            conn.commit()

            return {"status": "success", "id": task_id, "new_status": new_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/tasks/{task_id}/status")
async def update_task_status(task_id: int, status: str = Body(..., embed=True)):
    """Set task status directly (Todo, In Progress, Completed, Deferred)."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE calendar_action_tasks 
                SET status = ?, updated_at = ? 
                WHERE id = ?
            """, (status, now, task_id))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"status": "success", "id": task_id, "new_status": status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """Delete an action item / task."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM calendar_action_tasks WHERE id = ?", (task_id,))
            conn.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"status": "success", "deleted_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# AI Action Item Extractor (NLP)
# ---------------------------------------------------------------------------

@router.post("/tasks/ai-extract")
async def ai_extract_action_items(req: NLPTextRequest):
    """
    AI LLM Action Item Extractor:
    Takes raw notes, meeting minutes, or directives and automatically extracts
    structured action items with titles, due dates, priorities, categories, and subtasks.
    """
    try:
        text = req.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        today_iso = date.today().isoformat()

        prompt = f"""
You are the AI-BS Project & Action Item Specialist.
Extract structured actionable tasks and todo items from the following user notes or prompt.

Today's date is: {today_iso}.

For each distinct action item, extract:
- title: concise, active task description (e.g. "Review Scene 4 Dialogue")
- description: extra context or requirements
- due_date: YYYY-MM-DD (infer relative dates like 'tomorrow', 'Friday', 'next week' relative to {today_iso})
- due_time: HH:MM in 24h format if mentioned, else empty string
- priority: one of "Urgent", "High", "Medium", "Low"
- category: one of "Screenplay & Writing", "Tech & Dev", "Client & Publishing", "Personal", "General"
- subtasks: array of strings representing checklist steps, if any

Return JSON matching this schema:
{{
  "tasks": [
    {{
      "title": "Task title",
      "description": "Details",
      "due_date": "YYYY-MM-DD",
      "due_time": "14:00",
      "priority": "High",
      "category": "Screenplay & Writing",
      "subtasks": ["Step 1", "Step 2"]
    }}
  ]
}}

User Input:
{text}
"""

        messages = [
            {"role": "system", "content": "You are a task extractor. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ]

        extracted_tasks = []
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                r = await client.post(
                    OLLAMA_CHAT_URL,
                    json={
                        "model": "stehouwer_llm",
                        "messages": messages,
                        "stream": False,
                        "format": "json"
                    }
                )
                if r.status_code != 200:
                    r = await client.post(
                        OLLAMA_CHAT_URL,
                        json={
                            "model": "nemotron-3.5-lightning",
                            "messages": messages,
                            "stream": False,
                            "format": "json"
                        }
                    )
                r.raise_for_status()
                data = r.json().get("message", {}).get("content", "{}")
                parsed = json.loads(data)
                extracted_tasks = parsed.get("tasks", [])
        except Exception as llm_err:
            print(f"[Calendar Tasks AI Extractor Fallback] {llm_err}")
            # Heuristic fallback: split by lines
            lines = [l.strip("-* 1234567890.") for l in text.split("\n") if l.strip()]
            for l in lines[:5]:
                extracted_tasks.append({
                    "title": l,
                    "description": "Auto-extracted from notes",
                    "due_date": today_iso,
                    "due_time": "",
                    "priority": "Medium",
                    "category": "General",
                    "subtasks": []
                })

        # Save all extracted tasks to DB
        created_items = []
        now = datetime.now().isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for t in extracted_tasks:
                subtasks_formatted = [{"id": f"st-{i+1}", "title": st, "done": False} if isinstance(st, str) else st for i, st in enumerate(t.get("subtasks", []))]
                subtasks_json = json.dumps(subtasks_formatted)
                
                cursor.execute("""
                    INSERT INTO calendar_action_tasks
                    (title, description, due_date, due_time, priority, status, category, assigned_to, subtasks, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'Todo', ?, 'Brett', ?, '[]', ?, ?)
                """, (
                    t.get("title", "New Task"),
                    t.get("description", ""),
                    t.get("due_date", today_iso),
                    t.get("due_time", ""),
                    t.get("priority", "Medium"),
                    t.get("category", "General"),
                    subtasks_json,
                    now,
                    now
                ))
                task_id = cursor.lastrowid
                created_items.append({
                    "id": task_id,
                    "title": t.get("title", "New Task"),
                    "description": t.get("description", ""),
                    "due_date": t.get("due_date", today_iso),
                    "due_time": t.get("due_time", ""),
                    "priority": t.get("priority", "Medium"),
                    "status": "Todo",
                    "category": t.get("category", "General"),
                    "assigned_to": "Brett",
                    "subtasks": subtasks_formatted,
                    "tags": [],
                    "created_at": now,
                    "updated_at": now
                })
            conn.commit()

        return {"status": "success", "count": len(created_items), "tasks": created_items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Combined Calendar & Task Events Fusion (For Big Calendar View)
# ---------------------------------------------------------------------------

@router.get("/combined-events")
async def get_combined_calendar_events(include_tasks: bool = True):
    """
    Returns appointments AND tasks formatted for react-big-calendar display.
    Tasks with due dates appear as distinct action items on the calendar.
    """
    try:
        combined = []
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Fetch appointments
            cursor.execute("SELECT * FROM appointments")
            for row in cursor.fetchall():
                apt = dict(row)
                start_dt = apt.get("start_datetime") or apt.get("date") or datetime.now().isoformat()
                end_dt = apt.get("end_datetime") or start_dt
                combined.append({
                    "id": f"apt-{apt['id']}",
                    "raw_id": apt["id"],
                    "title": apt["title"],
                    "start": start_dt,
                    "end": end_dt,
                    "category": apt.get("category", "General"),
                    "notes": apt.get("notes", ""),
                    "isTask": False,
                    "status": "Scheduled"
                })

            # 2. Fetch action tasks (if requested)
            if include_tasks:
                cursor.execute("SELECT * FROM calendar_action_tasks WHERE due_date != ''")
                for row in cursor.fetchall():
                    task = dict(row)
                    due_date = task["due_date"]
                    due_time = task["due_time"] or "09:00"
                    
                    try:
                        start_dt = f"{due_date}T{due_time}:00"
                    except Exception:
                        start_dt = f"{due_date}T09:00:00"

                    # Calculate end 1 hour later
                    try:
                        end_dt = f"{due_date}T{int(due_time.split(':')[0])+1:02d}:{due_time.split(':')[1]}:00"
                    except Exception:
                        end_dt = start_dt

                    try:
                        subtasks = json.loads(task["subtasks"]) if task["subtasks"] else []
                    except Exception:
                        subtasks = []

                    p_icon = "🔴" if task["priority"] == "Urgent" else ("🟠" if task["priority"] == "High" else "📋")
                    status_prefix = "✅ " if task["status"] == "Completed" else f"{p_icon} "

                    combined.append({
                        "id": f"task-{task['id']}",
                        "raw_id": task["id"],
                        "title": f"{status_prefix}{task['title']}",
                        "start": start_dt,
                        "end": end_dt,
                        "category": task.get("category", "General"),
                        "priority": task.get("priority", "Medium"),
                        "notes": task.get("description", ""),
                        "isTask": True,
                        "status": task["status"],
                        "subtasks": subtasks
                    })

        return combined
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_task_statistics():
    """Get overview metrics for action items."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM calendar_action_tasks")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM calendar_action_tasks WHERE status = 'Completed'")
            completed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM calendar_action_tasks WHERE status = 'In Progress'")
            in_progress = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM calendar_action_tasks WHERE status = 'Todo'")
            todo = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM calendar_action_tasks WHERE priority = 'Urgent' AND status != 'Completed'")
            urgent = cursor.fetchone()[0]

            today_iso = date.today().isoformat()
            cursor.execute("SELECT COUNT(*) FROM calendar_action_tasks WHERE due_date < ? AND status != 'Completed' AND due_date != ''", (today_iso,))
            overdue = cursor.fetchone()[0]

            rate = round((completed / total * 100), 1) if total > 0 else 0.0

            return {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "todo": todo,
                "urgent": urgent,
                "overdue": overdue,
                "completion_rate": rate
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
