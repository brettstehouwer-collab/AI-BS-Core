from fastapi import APIRouter, Query
from pydantic import BaseModel
import sqlite3
import os

router = APIRouter(prefix="/api/v1/assets/unreal", tags=["unreal_assets"])

MASTER_DB = os.path.join(os.path.dirname(__file__), "aibs_master.db")
DB_PATH = MASTER_DB if os.path.exists(MASTER_DB) else os.path.join(os.path.dirname(__file__), "unreal_assets.db")

@router.get("/search")
async def search_assets(
    keyword: str = Query("", description="Keyword to search in asset names"),
    asset_type: str = Query(None, description="Filter by asset type (e.g., Material, StaticMesh, Blueprint)"),
    limit: int = Query(50, description="Max results to return")
):
    if not os.path.exists(DB_PATH):
        return {"status": "error", "message": "Asset database not found."}

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    query = "SELECT * FROM assets WHERE asset_name LIKE ?"
    params = [f"%{keyword}%"]

    if asset_type and asset_type.lower() != 'all':
        query += " AND asset_type = ?"
        params.append(asset_type)
        
    query += " LIMIT ?"
    params.append(limit)

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    results = [dict(row) for row in rows]
    return {"status": "success", "results": results}
