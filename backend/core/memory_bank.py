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
from typing import Dict, Any, List, Optional
from pathlib import Path

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
    # Fallback to local root path
    fallback = str(_root_dir / "master_memory_dump.json")
    try:
        if not os.path.exists(fallback):
            with open(fallback, "w", encoding="utf-8") as f:
                json.dump([], f)
    except Exception as e:
        logger.warning(f"Could not create master memory fallback file: {e}")
    return fallback

VAULT_DB_PATH = str(_backend_dir / "stehouwer_vault.db")
VECTOR_DB_DIR = str(_root_dir / "stehouwer_vector_memory")

try:
    import chromadb
    from chromadb.utils import embedding_functions
    chroma_client = chromadb.PersistentClient(path=VECTOR_DB_DIR)
    default_ef = embedding_functions.ONNXMiniLM_L6_V2(preferred_providers=['CPUExecutionProvider'])
    heuristics_collection = chroma_client.get_or_create_collection(name="stehouwer_llm_memory", embedding_function=default_ef)
    cases_collection = chroma_client.get_or_create_collection(name="stehouwer_cases_v2", embedding_function=default_ef)
    logger.info("ChromaDB Memory Collections (stehouwer_llm_memory) initialized with CPU provider.")
except Exception as e:
    logger.warning(f"ChromaDB local client unavailable ({e}), using SQLite vault fallback.")

def store_heuristic(heuristic_text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Stores a learned heuristic in ChromaDB, SQLite Vault, and master_memory_dump.json."""
    if not heuristic_text or not heuristic_text.strip():
        return False

    meta = metadata or {}
    meta["timestamp"] = meta.get("timestamp", time.time())
    meta["source"] = meta.get("source", "infinite_learning_loop")
    doc_id = f"heur_{int(meta['timestamp'] * 1000)}_{abs(hash(heuristic_text)) % 100000}"

    # 1. Store in ChromaDB
    if heuristics_collection:
        try:
            clean_meta = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in meta.items()}
            heuristics_collection.add(
                documents=[heuristic_text],
                metadatas=[clean_meta],
                ids=[doc_id]
            )
        except BaseException as e:
            logger.debug(f"ChromaDB storage notice: {e}")

    # 2. Store in SQLite Vault
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
        conn.close()
    except Exception as e:
        logger.debug(f"SQLite vault insert notice: {e}")

    # 3. Store in master_memory_dump.json
    try:
        mem_path = get_master_memory_path()
        entries = []
        if os.path.exists(mem_path):
            with open(mem_path, "r", encoding="utf-8", errors="ignore") as f:
                try:
                    entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = [entries]
                except Exception:
                    entries = []

        entry = {
            "id": doc_id,
            "text": heuristic_text,
            "metadata": meta,
            "timestamp": meta["timestamp"]
        }
        entries.append(entry)
        if len(entries) > 1000:
            entries = entries[-1000:]

        with open(mem_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        logger.debug(f"Master memory dump write notice: {e}")

    return True

def add_memory(memory_text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    return store_heuristic(memory_text, metadata)

def store_case_resolution(error_trace: str, resolution_patch: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Stores a historical error resolution trace in the Case Library."""
    meta = metadata or {}
    meta["error_trace"] = error_trace[:300]
    meta["timestamp"] = time.time()
    doc_id = f"case_{int(meta['timestamp'] * 1000)}_{abs(hash(error_trace + resolution_patch)) % 100000}"

    if cases_collection:
        try:
            clean_meta = {k: str(v) if isinstance(v, (dict, list)) else v for k, v in meta.items()}
            cases_collection.add(
                documents=[resolution_patch],
                metadatas=[clean_meta],
                ids=[doc_id]
            )
        except Exception as e:
            logger.debug(f"ChromaDB case storage notice: {e}")

    return True

def query_similar_cases(current_error_trace: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Queries the Case Library for similar past errors and their resolutions."""
    if not cases_collection:
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
    """Retrieves high-level diagnostics on the Memory Bank and Master Memory Dump."""
    mem_path = get_master_memory_path()
    dump_count = 0
    dump_size_kb = 0
    if os.path.exists(mem_path):
        try:
            dump_size_kb = round(os.path.getsize(mem_path) / 1024, 2)
            with open(mem_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
                dump_count = len(data) if isinstance(data, list) else 1
        except Exception:
            pass

    vault_count = 0
    if os.path.exists(VAULT_DB_PATH):
        try:
            conn = sqlite3.connect(VAULT_DB_PATH)
            row = conn.execute("SELECT COUNT(*) FROM vault_items;").fetchone()
            if row:
                vault_count = row[0]
            conn.close()
        except Exception:
            pass

    chroma_online = False
    chroma_count = 0
    chroma_db_file = os.path.join(VECTOR_DB_DIR, "chroma.sqlite3")
    if os.path.exists(chroma_db_file):
        try:
            c_conn = sqlite3.connect(chroma_db_file)
            c_row = c_conn.execute("SELECT COUNT(*) FROM embeddings;").fetchone()
            if c_row:
                chroma_count = c_row[0]
                chroma_online = True
            c_conn.close()
        except Exception:
            pass
    elif heuristics_collection is not None:
        chroma_online = True

    return {
        "status": "online",
        "master_memory_path": mem_path,
        "master_memory_blocks": dump_count,
        "master_memory_size_kb": dump_size_kb,
        "sqlite_vault_records": vault_count,
        "chroma_online": chroma_online,
        "chroma_heuristics_count": chroma_count,
        "timestamp": time.time()
    }
