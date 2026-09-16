import os
import sqlite3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger("KnowledgeRouter")

router = APIRouter(
    prefix="/api/v1/knowledge",
    tags=["Federated Knowledge DBs"]
)

E_DRIVE_DB_PATH = r"E:\AI_BS_Resources\Databases"

class QueryRequest(BaseModel):
    db_name: str
    query: str

@router.get("/databases")
async def list_databases():
    """Returns a list of all available domain databases on the E: drive."""
    if not os.path.exists(E_DRIVE_DB_PATH):
        return {"databases": [], "status": "E: Drive not mounted or inaccessible"}
    
    dbs = [f for f in os.listdir(E_DRIVE_DB_PATH) if f.endswith(".db")]
    return {"databases": dbs, "count": len(dbs), "status": "active"}

@router.post("/query")
async def query_database(req: QueryRequest):
    """
    Executes a READ-ONLY SQL query against a specific domain database.
    Guarantees no data loss by enforcing SQLite read-only URI mode and STRICT query parsing.
    """
    # Safety Check 1: Ensure it's a read operation
    unsafe_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "TRUNCATE"]
    upper_query = req.query.upper()
    if any(kw in upper_query for kw in unsafe_keywords):
        raise HTTPException(status_code=403, detail="Only READ (SELECT) operations are permitted.")

    # Safety Check 2: Validate DB name to prevent path traversal
    if not req.db_name.endswith(".db") or "/" in req.db_name or "\\" in req.db_name:
        raise HTTPException(status_code=400, detail="Invalid database name.")

    db_path = os.path.join(E_DRIVE_DB_PATH, req.db_name)
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail=f"Database {req.db_name} not found on E: drive.")

    # Convert to URI for Read-Only mode
    # SQLite URIs require forward slashes
    uri_path = db_path.replace('\\', '/')
    db_uri = f"file:{uri_path}?mode=ro"

    try:
        # Safety Check 3: SQLite native read-only connection
        conn = sqlite3.connect(db_uri, uri=True)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(req.query)
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        
        cursor.close()
        conn.close()
        
        return {"db": req.db_name, "results_count": len(results), "data": results}
    except sqlite3.Error as e:
        logger.error(f"SQLite Error in {req.db_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
