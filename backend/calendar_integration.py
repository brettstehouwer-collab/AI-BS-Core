"""
Calendar integration module for AI-BS Matrix.
Adds /api/calendar/* endpoints that use a local SQLite database
and optionally store appointment metadata in ChromaDB for semantic search.
"""

from fastapi import HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import httpx
import json
import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join("c:\\AI-BS", "database", "calendar.db")
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                client_id TEXT DEFAULT 'stehouwer_publishing',
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT,
                time TEXT,
                start_datetime TEXT,
                end_datetime TEXT,
                notes TEXT,
                category TEXT
            )
        """)

        conn.commit()


init_db()


class CalendarAppointment(BaseModel):
    title: str
    date: Optional[str] = ""
    time: Optional[str] = ""
    start_datetime: Optional[str] = ""
    end_datetime: Optional[str] = ""
    notes: Optional[str] = ""
    category: Optional[str] = "General"


class CalendarNLPRequest(BaseModel):
    text: str  # E.g., "Doctor appointment next Tuesday at 3 PM"


async def _embed_query(text: str, embed_model: str = "nomic-embed-text") -> list:
    """Request embedding from local Ollama."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "http://127.0.0.1:11434/api/embed",
                json={"model": embed_model, "input": text},
            )
            r.raise_for_status()
            return r.json().get("embeddings", [[]])[0]
    except Exception as e:
        print(f"[Calendar Embedding Error] {e}")
        return []


def get_calendar_routes(app, memory_service_dep):
    """
    Inject calendar endpoints into the FastAPI app.
    Requires: app (FastAPI instance), memory_service_dep (Depends() callable)
    """

    @app.get("/api/calendar/appointments")
    async def get_appointments():
        """Fetch all appointments from SQLite backend."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM appointments")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/calendar/appointments")
    async def create_appointment(
        apt: CalendarAppointment, memory=Depends(memory_service_dep)
    ):
        """Create appointment in SQLite and optionally archive to ChromaDB."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO appointments (title, date, time, start_datetime, end_datetime, notes, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        apt.title,
                        apt.date,
                        apt.time,
                        apt.start_datetime,
                        apt.end_datetime,
                        apt.notes,
                        apt.category,
                    ),
                )
                conn.commit()
                apt_id = cursor.lastrowid

            saved_apt = apt.dict()
            saved_apt["id"] = apt_id

            # Archive to ChromaDB for semantic search
            if memory and memory.is_online:
                try:
                    doc_text = (
                        f"Appointment: {apt.title}\n"
                        f"Date: {apt.date}\n"
                        f"Time: {apt.time}\n"
                        f"Start: {apt.start_datetime}\n"
                        f"Category: {apt.category}\n"
                        f"Notes: {apt.notes}"
                    )
                    vector = await _embed_query(doc_text)
                    if vector:
                        await memory.add_heuristic(
                            documents=[doc_text],
                            metadatas=[
                                {
                                    "source": "calendar",
                                    "date": apt.date,
                                    "category": apt.category,
                                }
                            ],
                            ids=[f"appointment-{apt_id}"],
                            embeddings=[vector],
                        )
                except Exception as archive_err:
                    print(
                        f"[Calendar] Warning: ChromaDB archival failed: {archive_err}"
                    )

            return {"status": "success", "appointment": saved_apt}

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/calendar/nlp/parse")
    async def nlp_parse_appointment(req: CalendarNLPRequest):
        """
        NLP parsing: send natural language text to Ollama and extract appointment details.
        """
        try:
            text = req.text.strip()
            if not text:
                raise HTTPException(status_code=400, detail="Text required")

            system_prompt = (
                "You are a calendar assistant. Parse natural language appointment descriptions "
                "and extract: start_datetime (ISO 8601), end_datetime (ISO 8601), title, notes, and category (Medical/Work/Personal/General/Sales). "
                "Return ONLY valid JSON with these fields. If date is relative (e.g., 'next Tuesday'), infer it from today's date. "
                "Assume a default duration of 1 hour if not specified. "
                f"Right now is {datetime.now().isoformat()}."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parse: {text}"},
            ]

            async with httpx.AsyncClient() as client:
                r = await client.post(
                    OLLAMA_CHAT_URL,
                    json={
                        "model": "llama3.1:latest",
                        "messages": messages,
                        "stream": False,
                        "format": "json",
                    },
                    timeout=30.0,
                )
                r.raise_for_status()
                response_text = r.json().get("message", {}).get("content", "")

            # Extract JSON from response
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=502, detail="LLM could not parse appointment text"
                )

            return {
                "status": "success",
                "parsed": parsed,
                "raw_response": response_text,
            }

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/api/calendar/appointments/{apt_id}")
    async def delete_appointment(apt_id: int):
        """Delete appointment from SQLite."""
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

    @app.put("/api/calendar/appointments/{apt_id}")
    async def update_appointment(apt_id: int, apt: CalendarAppointment):
        """Update appointment in SQLite."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE appointments 
                    SET title=?, date=?, time=?, start_datetime=?, end_datetime=?, notes=?, category=?
                    WHERE id=?
                """,
                    (
                        apt.title,
                        apt.date,
                        apt.time,
                        apt.start_datetime,
                        apt.end_datetime,
                        apt.notes,
                        apt.category,
                        apt_id,
                    ),
                )

                conn.commit()
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Appointment not found")

                saved_apt = apt.dict()
                saved_apt["id"] = apt_id
                return {"status": "success", "appointment": saved_apt}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/calendar/search")
    async def search_calendar(query: str, memory=Depends(memory_service_dep)):
        """Semantic search for appointments via ChromaDB."""
        if not memory or not memory.is_online:
            raise HTTPException(status_code=503, detail="ChromaDB offline")

        try:
            if not query.strip():
                raise HTTPException(status_code=400, detail="Query required")

            vector = await _embed_query(query)
            if not vector:
                raise HTTPException(status_code=500, detail="Embedding failed")

            results = await memory.retrieve_heuristics(
                vector, n_results=5, source_filter="calendar"
            )

            return {"status": "success", "query": query, "results": results}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    print(
        "[Calendar] Routes registered: GET /api/calendar/*, POST /api/calendar/nlp/parse, etc."
    )
