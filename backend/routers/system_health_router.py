from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse
import asyncio
import sqlite3
import json
import os

from core.system_logger import active_sse_queues, LOG_DB_PATH

router = APIRouter(prefix="/api/system", tags=["System Health"])

@router.get("/logs/history")
async def get_log_history(
    limit: int = 100, 
    offset: int = 0, 
    level: str = None, 
    search: str = None
):
    try:
        conn = sqlite3.connect(LOG_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = "SELECT id, timestamp, level, name, message FROM logs"
        params = []
        conditions = []
        
        if level and level.upper() != "ALL":
            conditions.append("level = ?")
            params.append(level.upper())
            
        if search:
            conditions.append("(message LIKE ? OR name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        c.execute(query, params)
        rows = c.fetchall()
        
        logs = [dict(row) for row in rows]
        
        # Get total count
        count_query = "SELECT COUNT(*) FROM logs"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        c.execute(count_query, params[:-2])
        total = c.fetchone()[0]
        
        conn.close()
        
        return {"status": "success", "total": total, "logs": logs}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/logs/stream")
async def stream_logs(request: Request):
    async def log_generator():
        q = asyncio.Queue()
        active_sse_queues.append(q)
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                # Wait for the next log entry
                log_entry = await q.get()
                yield f"data: {json.dumps(log_entry)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if q in active_sse_queues:
                active_sse_queues.remove(q)

    return StreamingResponse(log_generator(), media_type="text/event-stream")
