"""
AI-BS Audio Corpus & Sonification Router (v5.154.0)
SQLite FTS5 Sub-Millisecond Parametric & BM25 Audio Retrieval Engine
Supports HTTP 206 Partial Content Byte-Range Streaming, Dynamic Data Sonification & Neural DAW Matrix
"""

import os
import sqlite3
import urllib.parse
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse

router = APIRouter(prefix="/api/audio", tags=["AI-BS Audio Corpus & Sonification"])

DB_PATHS = [
    r"C:\AI-BS\database\audio_catalog.db",
    r"C:\AIBS\audio_matrix\audio_corpus.db",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "audio_catalog.db"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "audio_catalog.db")
]

def resolve_db_path() -> str:
    for p in DB_PATHS:
        if os.path.exists(p):
            return os.path.abspath(p)
    return r"C:\AI-BS\database\audio_catalog.db"

def get_db():
    db_path = resolve_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=503, detail=f"Audio database not found at {db_path}.")
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Sub-2ms memory-mapped read velocity PRAGMAs
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA mmap_size = 536870912;")  # 512 MB memory map
    conn.execute("PRAGMA cache_size = -64000;")     # 64 MB page cache
    return conn

@router.get("/stats")
async def get_audio_stats():
    conn = get_db()
    cur = conn.cursor()
    
    # Check if virtual table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audio_corpus_fts';")
    has_fts = bool(cur.fetchone())
    
    total = 0
    categories = {}
    
    if has_fts:
        cur.execute("SELECT COUNT(*) as total FROM audio_corpus_fts;")
        total = cur.fetchone()["total"]
        cur.execute("SELECT category, COUNT(*) as count FROM audio_corpus_fts GROUP BY category ORDER BY count DESC;")
        categories = {row["category"]: row["count"] for row in cur.fetchall()}
    elif os.path.exists(resolve_db_path()):
        cur.execute("SELECT COUNT(*) as total FROM audio_assets;")
        total = cur.fetchone()["total"]
        cur.execute("SELECT category, COUNT(*) as count FROM audio_assets GROUP BY category ORDER BY count DESC;")
        categories = {row["category"]: row["count"] for row in cur.fetchall()}

    conn.close()
    return {
        "status": "online",
        "engine": "SQLite FTS5 Memory-Mapped",
        "mmap_size_mb": 512,
        "total_indexed_assets": total,
        "categories": categories,
        "database_path": resolve_db_path()
    }

@router.get("/search")
async def search_audio(
    q: Optional[str] = Query(None, description="Free text or token search"),
    category: Optional[str] = Query(None, description="Category filter (stinger, drone, melody_loop, drum_percussion, bass_808, one_shot, stem, vocal, guitar, foley_fx)"),
    bpm: Optional[str] = Query(None, description="Exact BPM string (e.g. 140, 128)"),
    bpm_min: Optional[int] = Query(None, description="Minimum BPM"),
    bpm_max: Optional[int] = Query(None, description="Maximum BPM"),
    musical_key: Optional[str] = Query(None, description="Musical Key (e.g. Cmin, Emin, F#maj, Amin)"),
    timbral_spectrum: Optional[str] = Query(None, description="Timbral qualities (bright, dark, percussive, sharp, sustained, metallic, acoustic)"),
    semantic_context: Optional[str] = Query(None, description="Emotional/narrative tags (tension, triumph, critical, positive, action, dark)"),
    data_bindings: Optional[str] = Query(None, description="Data trigger binding (metric_drop, high_variance, threshold_breach, positive_trend)"),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    conn = get_db()
    cur = conn.cursor()
    
    # Check if audio_corpus_fts exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audio_corpus_fts';")
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=500, detail="audio_corpus_fts table not indexed. Run build_audio_corpus_fts.py.")

    clauses = []
    if q and q.strip():
        clauses.append(f'"{q.strip()}"*')
    if category and category != "All":
        clean_cat = category.lower().replace(" ", "_").replace("-", "_").replace("/", "_")
        clauses.append(f"category: {clean_cat}")
    if bpm:
        clauses.append(f"bpm: {bpm}")
    if musical_key and musical_key != "All":
        clean_key = musical_key.replace(" ", "")
        clauses.append(f"musical_key: {clean_key}*")
    if timbral_spectrum:
        clauses.append(f"timbral_spectrum: {timbral_spectrum}")
    if semantic_context:
        clauses.append(f"semantic_context: {semantic_context}")
    if data_bindings:
        clauses.append(f"data_bindings: {data_bindings}")

    match_expression = " AND ".join(clauses) if clauses else "category: *"

    sql = """
        SELECT asset_id, file_path, sample_rate, duration_ms, category, bpm, musical_key, 
               timbral_spectrum, semantic_context, data_bindings,
               bm25(audio_corpus_fts, 0.0, 0.0, 0.0, 0.0, 2.0, 5.0, 5.0, 2.0, 3.0, 4.0) AS relevance
        FROM audio_corpus_fts
        WHERE audio_corpus_fts MATCH ?
        ORDER BY relevance ASC
        LIMIT ? OFFSET ?;
    """
    
    try:
        cur.execute(sql, (match_expression, limit, offset))
        rows = cur.fetchall()
    except Exception as e:
        # Fallback to simple category wildcard if query syntax is ambiguous
        cur.execute(sql, ("category: *", limit, offset))
        rows = cur.fetchall()

    results = []
    for r in rows:
        fn = os.path.basename(r["file_path"]) if r["file_path"] else "audio_asset.wav"
        results.append({
            "asset_id": r["asset_id"],
            "filename": fn,
            "file_path": r["file_path"],
            "sample_rate": r["sample_rate"],
            "duration_ms": r["duration_ms"],
            "category": r["category"],
            "bpm": r["bpm"],
            "musical_key": r["musical_key"],
            "timbral_spectrum": r["timbral_spectrum"],
            "semantic_context": r["semantic_context"],
            "data_bindings": r["data_bindings"],
            "relevance": round(float(r["relevance"]), 4) if r["relevance"] is not None else 0.0,
            "stream_url": f"/api/audio/stream/{r['asset_id']}"
        })

    conn.close()
    return {
        "query": match_expression,
        "count": len(results),
        "limit": limit,
        "offset": offset,
        "results": results
    }

@router.get("/stream/{asset_id}")
async def stream_audio_asset(asset_id: str, request: Request):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM audio_corpus_fts WHERE asset_id = ? LIMIT 1;", (asset_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row["file_path"] or not os.path.exists(row["file_path"]):
        raise HTTPException(status_code=404, detail="Audio asset not found on physical storage.")

    file_path = row["file_path"]
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    ext = os.path.splitext(file_path)[1].lower()
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
    content_type = media_types.get(ext, 'audio/wav')

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        length = (end - start) + 1

        def iterfile():
            with open(file_path, "rb") as f:
                f.seek(start)
                yield f.read(length)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)

    return StreamingResponse(
        open(file_path, "rb"), 
        media_type=content_type, 
        headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes", "Access-Control-Allow-Origin": "*"}
    )

@router.get("/stream")
async def stream_audio_by_path(path: str = Query(..., description="Absolute path to audio file"), request: Request = None):
    """Backwards-compatible path streamer supporting HTTP 206 Range requests."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range") if request else None

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
    content_type = media_types.get(ext, 'audio/wav')

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        length = (end - start) + 1

        def iterfile():
            with open(path, "rb") as f:
                f.seek(start)
                yield f.read(length)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
        }
        return StreamingResponse(iterfile(), status_code=206, headers=headers)

    return FileResponse(path=path, media_type=content_type, filename=os.path.basename(path))

@router.get("/sonify/query")
async def query_sonification_cues(
    event_type: str = Query("table_cell", description="Event type: 'table_cell', 'variance_breach', 'script_marker', 'row_transition'"),
    valence: str = Query("positive", description="'positive', 'negative', 'critical', 'tension', 'triumph'"),
    variance: Optional[float] = Query(0.0, description="Numerical delta / variance (e.g. +15.2 or -35.0)"),
    preferred_key: Optional[str] = Query(None, description="Harmonic preference (e.g. Emin, Cmaj)"),
    preferred_bpm: Optional[str] = Query(None, description="Tempo preference (e.g. 140, 128)")
):
    """
    Sub-millisecond data sonification mapping helper.
    Returns acoustic assets for background beds, transient stingers, and sidechain ducking levels.
    """
    conn = get_db()
    cur = conn.cursor()

    stinger_binding = "high_variance" if abs(variance or 0.0) > 10.0 else "anomaly_flag"
    if valence in ["critical", "negative", "tension"]:
        bed_context = "tension"
        bed_category = "drone"
    else:
        bed_context = "triumph"
        bed_category = "melody_loop"

    # 1. Fetch Transient Stinger if variance or critical trigger
    stinger_results = []
    if abs(variance or 0.0) > 5.0 or event_type in ["variance_breach", "script_marker"]:
        stinger_match = f"category: stinger AND timbral_spectrum: sharp"
        try:
            cur.execute("""
                SELECT asset_id, file_path, category, bpm, musical_key,
                       bm25(audio_corpus_fts, 0.0, 0.0, 0.0, 0.0, 2.0, 5.0, 5.0, 2.0, 3.0, 4.0) AS relevance
                FROM audio_corpus_fts
                WHERE audio_corpus_fts MATCH ?
                ORDER BY relevance ASC LIMIT 3;
            """, (stinger_match,))
            for r in cur.fetchall():
                stinger_results.append({
                    "asset_id": r["asset_id"],
                    "filename": os.path.basename(r["file_path"]),
                    "stream_url": f"/api/audio/stream/{r['asset_id']}",
                    "gain_db": -6.0
                })
        except Exception:
            pass

    # 2. Fetch Harmonic Bed Loop
    bed_results = []
    key_clause = f"AND musical_key: {preferred_key}*" if preferred_key else ""
    bpm_clause = f"AND bpm: {preferred_bpm}" if preferred_bpm else ""
    bed_match = f"category: {bed_category} AND semantic_context: {bed_context} {key_clause} {bpm_clause}".strip()
    
    try:
        cur.execute("""
            SELECT asset_id, file_path, category, bpm, musical_key,
                   bm25(audio_corpus_fts, 0.0, 0.0, 0.0, 0.0, 2.0, 5.0, 5.0, 2.0, 3.0, 4.0) AS relevance
            FROM audio_corpus_fts
            WHERE audio_corpus_fts MATCH ?
            ORDER BY relevance ASC LIMIT 3;
        """, (bed_match,))
        for r in cur.fetchall():
            bed_results.append({
                "asset_id": r["asset_id"],
                "filename": os.path.basename(r["file_path"]),
                "stream_url": f"/api/audio/stream/{r['asset_id']}",
                "gain_db": -16.0,
                "loop": True
            })
    except Exception:
        pass

    conn.close()

    return {
        "event_type": event_type,
        "valence": valence,
        "variance": variance,
        "sidechain_duck_db": -14.0,
        "sidechain_release_ms": 350,
        "transient_stingers": stinger_results,
        "harmonic_beds": bed_results
    }
