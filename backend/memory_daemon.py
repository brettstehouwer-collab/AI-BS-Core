"""
memory_daemon.py — Background vector-memory sync daemon for the AI-BS ecosystem.

Responsibilities
----------------
- Polls session_history_archive.json on POLL_INTERVAL.
- Embeds new entries via a local Ollama embedding model (nomic-embed-text).
- Upserts vectors into ChromaDB collection 'ai_bs_context_memory'.
- Writes structured heartbeat logs to memory_daemon_logs.jsonl.
- Writes its own .pid file UNLESS launched by DaemonManager
  (detected via DAEMON_MANAGER_OWNED env var).
- Polls reasoning_traces_pending.jsonl and upserts pending traces into
  the 'reasoning_traces' ChromaDB collection (Phase 5 upgrade).

Environment variables
---------------------
MEMORY_POLL_INTERVAL   float  seconds between scan cycles  (default 30)
MEMORY_ARCHIVE_PATH    str    path to session_history_archive.json
MEMORY_LOG_PATH        str    path to memory_daemon_logs.jsonl
MEMORY_EMBED_MODEL     str    Ollama embedding model name   (default nomic-embed-text)
MEMORY_CHROMA_HOST     str    ChromaDB host                (default localhost)
MEMORY_CHROMA_PORT     int    ChromaDB port                (default 8001)
DAEMON_MANAGER_OWNED   1|0    set by DaemonManager to skip self-PID write
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WORKSPACE_ROOT = Path(__file__).parent.resolve()

POLL_INTERVAL = float(os.getenv("MEMORY_POLL_INTERVAL", "30"))
ARCHIVE_PATH = Path(
    os.getenv(
        "MEMORY_ARCHIVE_PATH", str(WORKSPACE_ROOT / "session_history_archive.json")
    )
)
LOG_PATH = Path(
    os.getenv("MEMORY_LOG_PATH", str(WORKSPACE_ROOT / "memory_daemon_logs.jsonl"))
)
EMBED_MODEL = os.getenv("MEMORY_EMBED_MODEL", "nomic-embed-text")
CHROMA_HOST = os.getenv("MEMORY_CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("MEMORY_CHROMA_PORT", "8001"))
PID_FILE = WORKSPACE_ROOT / "memory_daemon.pid"
COLLECTION_NAME = "ai_bs_context_memory"
REASONING_TRACES_PENDING = WORKSPACE_ROOT / "reasoning_traces_pending.jsonl"
REASONING_TRACES_COLLECTION = "reasoning_traces"
REASONING_TRACES_DB = WORKSPACE_ROOT / "reasoning_traces_pending.db"

OLLAMA_EMBED_URL = os.environ.get("OLLAMA_EMBED_URL", "http://127.0.0.1:11435/api/embed")
MANAGED = bool(os.getenv("DAEMON_MANAGER_OWNED", ""))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("memory_daemon")


def _write_log(level: str, message: str, extra: Dict[str, Any] | None = None) -> None:
    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "source": "memory_daemon",
    }
    if extra:
        entry.update(extra)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# PID management
# ---------------------------------------------------------------------------


def _write_pid() -> None:
    if not MANAGED:
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _cleanup_pid() -> None:
    if not MANAGED:
        PID_FILE.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# ChromaDB client (lazy import — optional dependency)
# ---------------------------------------------------------------------------


def _get_chroma_collection():
    """Return a ChromaDB collection, or None if ChromaDB is unavailable."""
    try:
        import chromadb

        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        return client.get_or_create_collection(COLLECTION_NAME)
    except Exception as exc:
        logger.warning(
            "ChromaDB unavailable (%s) — vectors will not be persisted.", exc
        )
        return None


# ---------------------------------------------------------------------------
# Embedding via Ollama
# ---------------------------------------------------------------------------

_http_client = None


def _get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(timeout=30.0)
    return _http_client


def _embed(text: str) -> List[float] | None:
    """Request an embedding from the local Ollama server."""
    try:
        client = _get_http_client()
        r = client.post(OLLAMA_EMBED_URL, json={"model": EMBED_MODEL, "input": text})
        r.raise_for_status()
        return r.json().get("embeddings", [[]])[0]
    except Exception as exc:
        logger.warning("Embedding request failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Core sync loop
# ---------------------------------------------------------------------------

_seen_hashes: set[str] = set()


def _entry_id(entry: Dict[str, Any]) -> str:
    raw = json.dumps(entry, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _sync_archive(collection) -> int:
    """Read session archive, embed new entries, upsert into ChromaDB. Returns count synced."""
    if not ARCHIVE_PATH.exists():
        logger.debug("Archive not found: %s", ARCHIVE_PATH)
        return 0

    try:
        with ARCHIVE_PATH.open("r", encoding="utf-8") as f:
            entries: List[Dict[str, Any]] = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read archive: %s", exc)
        return 0

    synced = 0
    for entry in entries:
        eid = _entry_id(entry)
        if eid in _seen_hashes:
            continue

        # Build a text representation for embedding
        endpoint = entry.get("endpoint", "")
        request = json.dumps(entry.get("request", {}))
        response = json.dumps(entry.get("response", {}))
        text = f"{endpoint} | req: {request} | res: {response}"

        vector = _embed(text)
        if vector is None:
            continue  # skip — will retry next cycle

        if collection is not None:
            try:
                collection.upsert(
                    ids=[eid],
                    documents=[text],
                    embeddings=[vector],
                    metadatas=[
                        {
                            "endpoint": endpoint,
                            "timestamp": entry.get("timestamp", ""),
                            "method": entry.get("method", ""),
                        }
                    ],
                )
            except Exception as exc:
                logger.warning("ChromaDB upsert failed for %s: %s", eid, exc)
                continue

        _seen_hashes.add(eid)
        synced += 1

        # Bound the dedup set
        if len(_seen_hashes) > 20_000:
            overflow = list(_seen_hashes)[:5_000]
            _seen_hashes.difference_update(overflow)

    return synced


def _sync_reasoning_traces_sqlite(collection) -> int:
    """
    Pull pending reasoning traces from the SQLite DB, embed them, and upsert into the
    'reasoning_traces' collection. Successful rows are deleted from the DB.
    Returns the number of traces successfully synced.
    """
    if not REASONING_TRACES_DB.exists():
        return 0

    try:
        conn = sqlite3.connect(REASONING_TRACES_DB)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
    except sqlite3.Error as exc:
        logger.warning("_sync_reasoning_traces_sqlite: cannot open DB — %s", exc)
        return 0

    synced = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, document, metadata FROM pending")
        rows = cursor.fetchall()
        for row in rows:
            doc_id, document, metadata_json = row
            metadata = json.loads(metadata_json)
            vector = _embed(document)
            if vector is None:
                continue  # will retry next cycle
            try:
                collection.upsert(
                    ids=[doc_id],
                    documents=[document],
                    embeddings=[vector],
                    metadatas=[metadata],
                )
                synced += 1
                logger.info("_sync_reasoning_traces_sqlite: ingested %s", doc_id)
                # Delete after successful upsert
                cursor.execute("DELETE FROM pending WHERE id = ?", (doc_id,))
            except Exception as exc:
                logger.warning(
                    "_sync_reasoning_traces_sqlite: upsert failed for %s — %s",
                    doc_id,
                    exc,
                )
        conn.commit()
    finally:
        conn.close()
    return synced


def _run() -> None:
    logger.info(
        "Memory daemon PID %d — polling every %.0fs", os.getpid(), POLL_INTERVAL
    )
    _write_log(
        "INFO",
        "Memory daemon started",
        {"pid": os.getpid(), "poll_interval": POLL_INTERVAL},
    )

    collection = _get_chroma_collection()

    cycle = 0
    while True:
        try:
            synced = _sync_archive(collection)
            traces_synced = _sync_reasoning_traces_sqlite(collection)
            total = synced + traces_synced
            if total:
                logger.info(
                    "Cycle %d — synced %d archive entries, %d reasoning traces to ChromaDB.",
                    cycle,
                    synced,
                    traces_synced,
                )
                _write_log(
                    "INFO",
                    f"Synced {total} entries",
                    {
                        "cycle": cycle,
                        "archive_synced": synced,
                        "traces_synced": traces_synced,
                    },
                )
            else:
                logger.debug("Cycle %d — nothing new.", cycle)
                _write_log("DEBUG", "No new entries", {"cycle": cycle})
        except Exception as exc:
            logger.error("Unhandled error in sync cycle %d: %s", cycle, exc)
            _write_log("ERROR", str(exc), {"cycle": cycle})

        cycle += 1
        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    _write_pid()
    try:
        _run()
    except KeyboardInterrupt:
        _write_log("INFO", "Memory daemon stopped (Ctrl+C)")
        logger.info("Stopped.")
    finally:
        _cleanup_pid()


if __name__ == "__main__":
    main()
