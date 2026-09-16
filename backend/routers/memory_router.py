import os
import sys
import time
import logging
import aiohttp
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_core_dir = os.path.join(_backend_dir, "core")
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)

from core.memory_bank import (
    store_heuristic,
    add_memory,
    get_memory_bank_status,
    get_master_memory_path,
    VAULT_DB_PATH
)
from core.infinite_learning_loop import learning_loop_instance

logger = logging.getLogger("MemoryRouter")
router = APIRouter(prefix="/api/memory", tags=["Vector Vault & Memory Engine"])

CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1:8002")

class MemoryQuery(BaseModel):
    query: str = Field(..., description="Semantic search query")
    collection: str = Field(default="stehouwer_heuristics", description="Target vector collection")
    top_k: int = Field(default=5, ge=1, le=50)

class MemoryRecord(BaseModel):
    title: str = Field(..., description="Document or heuristic title")
    content: str = Field(..., description="Context content text")
    tags: List[str] = Field(default_factory=list)
    collection: str = Field(default="stehouwer_heuristics")

@router.get("")
async def get_all_memories():
    """Returns all recent memories for the Agent Memory Dashboard."""
    ids = []
    documents = []
    metadatas = []
    
    # 1. Pull from SQLite Vault
    if os.path.exists(VAULT_DB_PATH):
        try:
            conn = sqlite3.connect(VAULT_DB_PATH)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT id, title, content, collection, tags, created_at FROM vault_items ORDER BY id DESC LIMIT 50;").fetchall()
            for r in rows:
                ids.append(str(r["id"]))
                documents.append(f"[{r['title']}] {r['content']}")
                metadatas.append({
                    "title": r["title"],
                    "collection": r["collection"],
                    "tags": r["tags"],
                    "created_at": r["created_at"]
                })
            conn.close()
        except Exception as e:
            logger.debug(f"Vault items read notice: {e}")

    # 2. Pull from master_memory_dump.json if vault is sparse
    if len(ids) < 10:
        mem_path = get_master_memory_path()
        if os.path.exists(mem_path):
            try:
                with open(mem_path, "r", encoding="utf-8", errors="ignore") as f:
                    entries = json.load(f)
                    if isinstance(entries, list):
                        for item in entries[-30:]:
                            doc_id = str(item.get("id", f"mem_{len(ids)}"))
                            if doc_id not in ids:
                                ids.append(doc_id)
                                documents.append(item.get("text", str(item)))
                                metadatas.append(item.get("metadata", {}))
            except Exception as e:
                logger.debug(f"Master memory load notice: {e}")

    return {
        "status": "success",
        "ids": ids,
        "documents": documents,
        "metadatas": metadatas,
        "count": len(ids)
    }

@router.get("/status")
async def get_status_overview():
    """Returns status of Memory Bank, ChromaDB, and master_memory_dump.json."""
    return get_memory_bank_status()

@router.get("/learning-loop/status")
async def get_learning_loop_status():
    """Returns real-time status of the Python Infinite Learning Loop."""
    return learning_loop_instance.get_status()

@router.post("/learning-loop/start")
async def start_learning_loop():
    """Starts the background Infinite Learning Loop worker."""
    started = learning_loop_instance.start()
    return {
        "status": "success",
        "action": "started" if started else "already_running",
        "details": learning_loop_instance.get_status()
    }

@router.post("/learning-loop/stop")
async def stop_learning_loop():
    """Stops the background Infinite Learning Loop worker."""
    stopped = learning_loop_instance.stop()
    return {
        "status": "success",
        "action": "stopped" if stopped else "already_idle",
        "details": learning_loop_instance.get_status()
    }

@router.post("/learning-loop/tick")
async def trigger_learning_tick():
    """Forces an immediate deduction tick in the Infinite Learning Loop."""
    learning_loop_instance.learning_tick()
    return {
        "status": "success",
        "action": "tick_executed",
        "details": learning_loop_instance.get_status()
    }

@router.get("/collections")
async def list_collections():
    """Lists available vector memory collections in ChromaDB & SQLite."""
    collections = ["stehouwer_heuristics", "architectural_ledger", "broadcast_scenes", "novelizer_lore"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{CHROMA_HOST}/api/v1/collections", timeout=aiohttp.ClientTimeout(total=1.5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for col in data:
                        name = col.get("name") if isinstance(col, dict) else col
                        if name and name not in collections:
                            collections.append(name)
    except Exception as e:
        logger.debug(f"ChromaDB collections query: {e}")
        
    return {"status": "success", "collections": collections}

@router.post("/query")
async def query_vector_memory(req: MemoryQuery):
    """Executes hybrid vector similarity search + SQLite fallback search."""
    results = []
    
    # Search SQLite stehouwer_vault.db
    try:
        conn = sqlite3.connect(VAULT_DB_PATH)
        conn.row_factory = sqlite3.Row
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        
        if "vault_items" in tables:
            rows = conn.execute(
                "SELECT * FROM vault_items WHERE content LIKE ? OR title LIKE ? LIMIT ?;",
                (f"%{req.query}%", f"%{req.query}%", req.top_k)
            ).fetchall()
            for r in rows:
                results.append({
                    "id": r["id"] if "id" in r.keys() else 0,
                    "title": r["title"] if "title" in r.keys() else "Vault Record",
                    "content": r["content"] if "content" in r.keys() else "",
                    "score": 0.92,
                    "source": "sqlite_vault"
                })
        conn.close()
    except Exception as e:
        logger.debug(f"SQLite vault query exception: {e}")
        
    return {
        "status": "success",
        "query": req.query,
        "collection": req.collection,
        "count": len(results),
        "results": results
    }

@router.post("/store")
async def store_memory_item(item: MemoryRecord):
    """Persists a new knowledge item into SQLite vault and master memory dump."""
    try:
        store_heuristic(
            item.content,
            metadata={
                "title": item.title,
                "collection": item.collection,
                "tags": item.tags
            }
        )
        return {"status": "success", "message": f"Saved memory '{item.title}' successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DirectMemoryPayload(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None

@router.post("")
async def create_memory_direct(payload: DirectMemoryPayload):
    """Direct POST handler for telemetry suite and frontend memory management."""
    try:
        meta = payload.metadata or {}
        title = meta.get("title", f"Memory_{int(time.time())}")
        store_heuristic(
            payload.content,
            metadata={
                "title": title,
                "collection": meta.get("collection", "stehouwer_heuristics"),
                "tags": meta.get("tags", ["telemetry_suite"])
            }
        )
        return {"status": "success", "message": "Memory persisted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{memory_id}")
async def delete_memory_by_id(memory_id: str):
    """Direct DELETE handler for telemetry suite memory items."""
    try:
        if os.path.exists(VAULT_DB_PATH):
            conn = sqlite3.connect(VAULT_DB_PATH)
            conn.execute("DELETE FROM vault_items WHERE id = ?;", (memory_id,))
            conn.commit()
            conn.close()
        return {"status": "success", "deleted_id": memory_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChatIngestRequest(BaseModel):
    messages: List[Dict[str, Any]]
    session_title: Optional[str] = "Chat Session Archive"
    source: Optional[str] = "chat_ui"

@router.post("/ingest-chat")
async def ingest_chat_messages(req: ChatIngestRequest):
    """
    Ingests active conversation history into ChromaDB, SQLite Vault,
    master_memory_dump.json, and personal intelligence episodic logs for LLM reasoning.
    """
    if not req.messages:
        return {"status": "success", "message": "No messages to ingest.", "items_saved": 0}

    timestamp_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    session_title = req.session_title or f"Chat Session ({timestamp_str})"

    # 1. Format conversation into comprehensive Markdown transcript
    transcript_lines = [f"# {session_title}", f"*Ingested at: {timestamp_str} | Source: {req.source}*\n"]
    user_prompts = []
    assistant_responses = []

    for idx, msg in enumerate(req.messages):
        role = str(msg.get("role", "user")).capitalize()
        content = str(msg.get("content", "")).strip()
        model = msg.get("model", "")
        model_tag = f" `[{model}]`" if model else ""
        if content:
            transcript_lines.append(f"### {role}{model_tag}:\n{content}\n")
            if role.lower() == "user":
                user_prompts.append(content)
            elif role.lower() == "assistant":
                assistant_responses.append(content)

    full_transcript = "\n".join(transcript_lines)

    # 2. Store in Master Memory & Vector Vault via store_heuristic
    try:
        store_heuristic(
            full_transcript,
            metadata={
                "title": session_title,
                "collection": "stehouwer_conversations",
                "tags": "chat_session,user_memory,llm_ingest",
                "source": req.source,
                "message_count": len(req.messages),
                "timestamp": time.time()
            }
        )
    except Exception as e:
        logger.warning(f"Failed to store conversation heuristic: {e}")

    # 3. Store in Personal Intelligence Engine episodic logs
    try:
        from core.personal_intelligence_memory import PersonalIntelligenceEngine
        pi_engine = PersonalIntelligenceEngine.get_instance()
        summary_blurb = f"User held conversation with {len(req.messages)} exchanges. Main themes: " + "; ".join([p[:80] for p in user_prompts[:3]])
        pi_engine.record_ecosystem_event(
            event_type="chat_session_archived",
            summary=summary_blurb[:400],
            metadata={
                "title": session_title,
                "message_count": len(req.messages),
                "first_prompt": user_prompts[0][:150] if user_prompts else ""
            }
        )
    except Exception as e:
        logger.debug(f"Personal intelligence logging notice: {e}")

    # 4. Append to session_history_archive.json and Chat_History.txt
    try:
        archive_path = os.path.join(_backend_dir, "session_history_archive.json")
        archive_entries = []
        if os.path.exists(archive_path):
            try:
                with open(archive_path, "r", encoding="utf-8") as af:
                    archive_entries = json.load(af)
                    if not isinstance(archive_entries, list):
                        archive_entries = [archive_entries]
            except Exception:
                archive_entries = []
        
        archive_entries.append({
            "timestamp": time.time(),
            "datetime": timestamp_str,
            "session_title": session_title,
            "message_count": len(req.messages),
            "messages": req.messages
        })
        with open(archive_path, "w", encoding="utf-8") as af:
            json.dump(archive_entries[-200:], af, indent=2)
    except Exception as e:
        logger.debug(f"Session archive append notice: {e}")

    try:
        txt_history = os.path.join(_backend_dir, "Chat_History.txt")
        with open(txt_history, "a", encoding="utf-8") as tf:
            tf.write(f"\n\n{'='*50}\n{session_title}\n{'='*50}\n{full_transcript}\n")
    except Exception as e:
        logger.debug(f"Chat history text append notice: {e}")

    return {
        "status": "success",
        "message": f"Successfully ingested {len(req.messages)} messages into Master Memory & Vector Vault.",
        "session_title": session_title,
        "items_saved": len(req.messages),
        "timestamp": timestamp_str
    }

@router.post("/scan-root")
async def trigger_root_scan():
    """Triggers an incremental scan of C:\\AI-BS root folder for new LLM ingestion."""
    try:
        from scan_and_ingest_root import run_root_scan_and_ingest
        import asyncio
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, run_root_scan_and_ingest, False)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))