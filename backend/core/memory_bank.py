"""
memory_bank.py — AI-BS Python Memory Bank & Heuristic Storage Layer.
Provides high-speed vector retrieval via ChromaDB and durable persistence
to master_memory_dump.json and SQLite stehouwer_vault.db.
"""

import os
import sys
import json
import logging
import sqlite3
import time
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from .coding_locks import record_lock
except ImportError:
    from coding_locks import record_lock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [MemoryBank] %(message)s"
)
logger = logging.getLogger("MemoryBank")

_backend_dir = Path(__file__).resolve().parent.parent
_root_dir = _backend_dir.parent

# Resolve Master Memory Dump paths (SSD prioritization)
MASTER_MEMORY_CANDIDATES = [
    r"D:\AI-BS_Master_Memory\master_memory_dump.json",
    r"G:\AI-BS_Master_Memory\master_memory_dump.json",
    str(_root_dir / "master_memory_dump.json"),
    str(_backend_dir / "master_memory_dump.json"),
]

def get_master_memory_path() -> str:
    for p in MASTER_MEMORY_CANDIDATES:
        if os.path.exists(p):
            return p
    # Resolving a path must not create or repair an operational data source.
    return str(_root_dir / "master_memory_dump.json")

VAULT_DB_PATH = str(_backend_dir / "stehouwer_vault.db")
VECTOR_DB_DIR = str(_root_dir / "stehouwer_vector_memory")

chroma_client = None
heuristics_collection = None
cases_collection = None

_chroma_attempted = False
_chroma_retry_after = 0.0


def _ensure_collections() -> bool:
    """Connect lazily to the existing HTTP owner; never open local Chroma files.

    An unavailable daemon must not trigger a second database owner or collection
    creation against retained recovery sources. SQLite and the journal remain
    independent durability paths.
    """
    global _chroma_attempted, _chroma_retry_after, chroma_client, heuristics_collection, cases_collection
    now = time.monotonic()
    if chroma_client is not None:
        return True
    if now < _chroma_retry_after:
        return False
    _chroma_attempted = True
    _chroma_retry_after = now + 30.0
    try:
        import chromadb
        client = chromadb.HttpClient(host="127.0.0.1", port=8001)
        client.heartbeat()
        heuristics_collection = client.get_collection(name="stehouwer_llm_memory")
        cases_collection = client.get_collection(name="stehouwer_cases_v2")
        chroma_client = client
        return True
    except Exception as exc:
        heuristics_collection = None
        cases_collection = None
        logger.debug("Chroma HTTP memory unavailable; retained vector files were not opened: %s", exc)
        return False


def _append_master_entry(entry: Dict[str, Any]) -> None:
    """Append and fsync a JSONL record without rewriting historical JSON bytes.

    The existing JSON array (including malformed evidence) is retained exactly.
    A process-owned lock serializes cooperating writers. If an earlier interrupted
    append left a partial line, a separator preserves that line for recovery.
    """
    encoded = (json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    journal = Path(get_master_memory_path() + "l")
    with record_lock(str(journal) + ".lock"):
        with journal.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell():
                stream.seek(-1, os.SEEK_END)
                if stream.read(1) != b"\n":
                    stream.write(b"\n")
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())

def store_heuristic(heuristic_text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Stores a learned heuristic in ChromaDB, SQLite Vault, and master_memory_dump.json."""
    if not isinstance(heuristic_text, str) or not heuristic_text.strip():
        return False

    meta = dict(metadata or {})
    meta["timestamp"] = meta.get("timestamp", time.time())
    meta["source"] = meta.get("source", "infinite_learning_loop")
    doc_id = f"heur_{uuid.uuid4().hex}"
    persisted = False

    # 1. Store in ChromaDB
    _ensure_collections()
    if heuristics_collection is not None:
        try:
            clean_meta = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in meta.items()}
            heuristics_collection.add(
                documents=[heuristic_text],
                metadatas=[clean_meta],
                ids=[doc_id]
            )
            persisted = True
        except Exception as e:
            logger.debug(f"ChromaDB storage notice: {e}")

    # 2. Store in SQLite Vault
    conn = None
    try:
        conn = sqlite3.connect(VAULT_DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                collection TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute(
            "INSERT INTO vault_items (title, content, collection, tags) VALUES (?, ?, ?, ?);",
            (
                meta.get("title", f"Heuristic Tick {meta.get('iteration', '')}"),
                heuristic_text,
                "stehouwer_heuristics",
                str(meta.get("source", "memory_bank"))
            )
        )
        conn.commit()
        persisted = True
    except Exception as e:
        logger.debug(f"SQLite vault insert notice: {e}")
    finally:
        if conn is not None:
            conn.close()

    # 3. Store in master_memory_dump.json (streaming / memory-bounded)
    try:
        entry = {
            "id": doc_id,
            "text": heuristic_text,
            "metadata": meta,
            "timestamp": meta["timestamp"]
        }
        _append_master_entry(entry)
        persisted = True
    except Exception as e:
        logger.debug(f"Master memory dump write notice: {e}")

    return persisted

def add_memory(memory_text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    return store_heuristic(memory_text, metadata)

def store_case_resolution(error_trace: str, resolution_patch: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Stores a historical error resolution trace in the Case Library."""
    meta = dict(metadata or {})
    meta["error_trace"] = error_trace[:300]
    meta["timestamp"] = time.time()
    doc_id = f"case_{uuid.uuid4().hex}"

    _ensure_collections()
    if cases_collection is not None:
        try:
            clean_meta = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in meta.items()}
            cases_collection.add(
                documents=[resolution_patch],
                metadatas=[clean_meta],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            logger.debug(f"ChromaDB case storage notice: {e}")

    return False

def query_similar_cases(current_error_trace: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Queries the Case Library for similar past errors and their resolutions."""
    _ensure_collections()
    if cases_collection is None:
        return []
    try:
        results = cases_collection.query(
            query_texts=[current_error_trace],
            n_results=n_results
        )
        output = []
        if results and "documents" in results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                output.append({
                    "resolution": doc,
                    "metadata": results["metadatas"][0][i] if "metadatas" in results else {}
                })
        return output
    except Exception as e:
        logger.debug(f"Case query notice: {e}")
        return []

def get_memory_bank_status() -> Dict[str, Any]:
    """Read bounded local evidence; never initialize or open a Chroma database."""
    mem_path = get_master_memory_path()
    dump_count = None
    dump_size_kb = 0
    dump_state = "missing"
    if os.path.exists(mem_path):
        try:
            dump_size_kb = round(os.path.getsize(mem_path) / 1024, 2)
            if os.path.getsize(mem_path) <= 5 * 1024 * 1024:
                with open(mem_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    dump_count = len(data) if isinstance(data, list) else 1
                dump_state = "readable"
            else:
                dump_state = "count_unavailable_size_limit"
        except Exception:
            dump_state = "unreadable_retained"

    journal_count = 0
    journal_state = "missing"
    journal = Path(mem_path + "l")
    if journal.exists():
        journal_count = None
        try:
            if journal.stat().st_size <= 5 * 1024 * 1024:
                journal_count = 0
                invalid_lines = False
                with journal.open("r", encoding="utf-8") as stream:
                    for line in stream:
                        try:
                            if line.strip():
                                json.loads(line)
                                journal_count += 1
                        except (ValueError, TypeError):
                            invalid_lines = True
                journal_state = "partial_retained" if invalid_lines else "readable"
            else:
                journal_state = "count_unavailable_size_limit"
        except Exception:
            journal_state = "unreadable_retained"

    vault_count = None
    conn = None
    if os.path.exists(VAULT_DB_PATH):
        try:
            conn = sqlite3.connect(Path(VAULT_DB_PATH).resolve().as_uri() + "?mode=ro", uri=True, timeout=0.25)
            conn.execute("PRAGMA query_only=ON")
            row = conn.execute("SELECT COUNT(*) FROM vault_items;").fetchone()
            if row:
                vault_count = row[0]
        except Exception:
            pass
        finally:
            if conn is not None:
                conn.close()

    chroma_online = None
    chroma_count = None
    if heuristics_collection is not None:
        try:
            chroma_count = heuristics_collection.count()
            chroma_online = True
        except Exception:
            chroma_online = False

    return {
        "status": "available" if vault_count is not None or dump_count is not None or journal_state == "readable" or chroma_online else "unavailable",
        "master_memory_path": mem_path,
        "master_memory_blocks": dump_count,
        "master_memory_size_kb": dump_size_kb,
        "master_memory_state": dump_state,
        "master_memory_journal_path": str(journal),
        "master_memory_journal_blocks": journal_count,
        "master_memory_journal_state": journal_state,
        "master_memory_journal_retrieval": "not_indexed; retained durability evidence only",
        "master_memory_journal_reconciliation_required": journal.exists(),
        "sqlite_vault_records": vault_count,
        "chroma_online": chroma_online,
        "chroma_state": "not_checked" if chroma_online is None else "reachable" if chroma_online else "unavailable",
        "chroma_heuristics_count": chroma_count,
        "timestamp": time.time()
    }
