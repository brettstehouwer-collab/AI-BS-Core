import os
import sqlite3
import urllib.parse
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/audio", tags=["Audio Catalog & Search"])

DB_PATH = r"C:\AI-BS\database\audio_catalog.db"

def get_db():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="Audio catalog database not found. Run audio scan first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/stats")
def get_audio_stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM audio_assets")
    total = cur.fetchone()["total"]

    cur.execute("SELECT category, COUNT(*) as count FROM audio_assets GROUP BY category ORDER BY count DESC")
    cats = {row["category"]: row["count"] for row in cur.fetchall()}

    cur.execute("SELECT COUNT(DISTINCT bpm) as bpm_variants, COUNT(DISTINCT musical_key) as key_variants FROM audio_assets")
    variants = cur.fetchone()

    conn.close()
    return {
        "total_assets": total,
        "categories": cats,
        "bpm_variants": variants["bpm_variants"],
        "key_variants": variants["key_variants"],
        "db_path": DB_PATH
    }

@router.get("/search")
def search_audio_assets(
    q: Optional[str] = Query(None, description="Keyword search query"),
    category: Optional[str] = Query(None, description="Category filter (e.g. Melody Loop, Drum / Percussion, 808 / Bass, Vocal, Guitar, MIDI)"),
    bpm_min: Optional[int] = Query(None, description="Minimum BPM"),
    bpm_max: Optional[int] = Query(None, description="Maximum BPM"),
    musical_key: Optional[str] = Query(None, description="Musical Key (e.g. C Maj, G Min, A# Min)"),
    extension: Optional[str] = Query(None, description="Extension filter (.wav, .mp3, .mid)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    conn = get_db()
    cur = conn.cursor()

    conditions = []
    params = []

    # If query string present, use FTS5 if possible
    if q and q.strip():
        clean_q = q.strip().replace('"', '""')
        # Check if FTS query is safe
        conditions.append("a.id IN (SELECT rowid FROM audio_assets_fts WHERE audio_assets_fts MATCH ?)")
        params.append(f'"{clean_q}"*')

    if category and category != "All":
        conditions.append("a.category = ?")
        params.append(category)

    if bpm_min is not None:
        conditions.append("a.bpm >= ?")
        params.append(bpm_min)

    if bpm_max is not None:
        conditions.append("a.bpm <= ?")
        params.append(bpm_max)

    if musical_key and musical_key != "All":
        conditions.append("LOWER(a.musical_key) LIKE ?")
        params.append(f"%{musical_key.lower()}%")

    if extension and extension != "All":
        ext = extension if extension.startswith('.') else f".{extension}"
        conditions.append("a.extension = ?")
        params.append(ext.lower())

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    # Count total matching
    count_sql = f"SELECT COUNT(*) as total FROM audio_assets a {where_clause}"
    cur.execute(count_sql, params)
    total_count = cur.fetchone()["total"]

    # Fetch rows
    fetch_sql = f"""
        SELECT a.id, a.filename, a.extension, a.path, a.rel_path, a.size_bytes, a.bpm, a.musical_key, a.category, a.modified_ts
        FROM audio_assets a
        {where_clause}
        ORDER BY a.id ASC
        LIMIT ? OFFSET ?
    """
    cur.execute(fetch_sql, params + [limit, offset])
    rows = cur.fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            "id": r["id"],
            "filename": r["filename"],
            "extension": r["extension"],
            "path": r["path"],
            "rel_path": r["rel_path"],
            "size_bytes": r["size_bytes"],
            "size_formatted": f"{round(r['size_bytes'] / (1024*1024), 2)} MB" if r["size_bytes"] >= 1024*1024 else f"{round(r['size_bytes']/1024, 1)} KB",
            "bpm": r["bpm"],
            "musical_key": r["musical_key"],
            "category": r["category"],
            "modified_ts": r["modified_ts"],
            "stream_url": f"/api/audio/stream?path={urllib.parse.quote(r['path'])}"
        })

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "items": items
    }

@router.get("/stream")
def stream_audio_file(path: str = Query(..., description="Absolute path to audio file")):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    ext = os.path.splitext(path)[1].lower()
    media_types = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.ogg': 'audio/ogg',
        '.flac': 'audio/flac',
        '.aif': 'audio/aiff',
        '.aiff': 'audio/aiff',
        '.m4a': 'audio/mp4',
        '.mid': 'audio/midi',
        '.midi': 'audio/midi'
    }
    media_type = media_types.get(ext, 'application/octet-stream')

    return FileResponse(
        path=path,
        media_type=media_type,
        filename=os.path.basename(path)
    )
