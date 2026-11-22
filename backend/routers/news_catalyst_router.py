"""Public advisory telemetry only. GET never creates a DB or starts inference."""
import sqlite3
import time
from fastapi import APIRouter, HTTPException, Query
from backend.trading.news_schema import NEWS_DB_PATH, NewsStore, NewsIntegrityError

router = APIRouter(prefix="/api/telemetry", tags=["Advisory Crypto News"])


@router.get("/news-catalysts")
def get_news_catalysts(limit: int = Query(10, ge=1, le=50)):
    if not NEWS_DB_PATH.exists():
        return {"configured": False, "worker_state": "not_configured", "advisory_only": True,
                "trading_enabled": False, "items": [], "feeds": [], "counts": {}}
    try:
        store = NewsStore(NEWS_DB_PATH)
        if store.scope != "LIVE_PUBLIC_NEWS":
            raise NewsIntegrityError("offline fixtures are not live news")
        return store.recent(now=int(time.time()), limit=limit)
    except (NewsIntegrityError, sqlite3.Error, ValueError, TypeError, KeyError, OSError):
        raise HTTPException(status_code=503, detail="News telemetry unavailable; no inference or trading action taken")
