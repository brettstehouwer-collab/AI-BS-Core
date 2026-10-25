import os
import asyncio
import sys
import time
import logging
import aiohttp
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_core_dir = os.path.join(_backend_dir, "core")
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)

from core.chat_archive import archive_chat, ArchiveConflict
from routers.conversation_router import router as conversations_router, require_conversation_owner
from core.owned_vault import (list_records, search_records, store_record, hide_record, read_record,
    list_collections as owned_collections, VaultEvidenceError, VaultRecordNotFound)
from core.memory_bank import (
    store_heuristic,
    add_memory,
    get_memory_bank_status,
    get_master_memory_path,
    VAULT_DB_PATH
)
from core.infinite_learning_loop import learning_loop_instance

logger = logging.getLogger("MemoryRouter")
router = APIRouter(prefix="/api/memory", tags=["Vector Vault & Memory Engine"], dependencies=[Depends(require_conversation_owner)])
router.include_router(conversations_router)

CHROMA_HOST = os.environ.get("CHROMA_HOST", "http://127.0.0.1:8002")

async def _owned_call(function, *args, **kwargs):
    try:
        return await asyncio.to_thread(function, *args, **kwargs)
    except VaultRecordNotFound:
        raise HTTPException(404, 'Memory record not found.') from None
    except PermissionError:
        raise HTTPException(403, 'Verified memory ownership is required.') from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except (sqlite3.Error, OSError, VaultEvidenceError):
        raise HTTPException(503, 'Memory storage or bounded retrieval is unavailable; retained sources were not replaced.') from None


@router.get('/items/{record_id}')
async def read_vault_item(record_id: int, owner: str = Depends(require_conversation_owner)):
    record = await _owned_call(read_record, VAULT_DB_PATH, owner, record_id)
    return {'status': 'success', 'record': record, 'full_source': True}


class MemoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(..., max_length=2000, description="Owner-scoped lexical search query")
    collection: str = Field(default="stehouwer_heuristics", description="Target vector collection")
    top_k: int = Field(default=5, ge=1, le=50)

class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., description="Document or heuristic title")
    content: str = Field(..., description="Context content text")
    tags: List[str] = Field(default_factory=list)
    collection: str = Field(default="stehouwer_heuristics")

@router.get("")
async def get_all_memories(owner: str = Depends(require_conversation_owner)):
    rows = await _owned_call(list_records, VAULT_DB_PATH, owner)
    return {'status': 'success', 'ids': [str(r['id']) for r in rows],
            'documents': [f"[{r.get('title', '')}] {r.get('content', '')}" for r in rows],
            'metadatas': [{k: r.get(k) for k in ('title','collection','tags','created_at','owner','ownership_legacy',
                'content_sha256','content_characters','content_truncated','char_start','char_end',
                'tags_truncated','tags_sha256','title_truncated')} for r in rows],
            'count': len(rows), 'scope': 'verified_owner', 'preview_only': True}

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

@router.get('/collections')
async def list_collections(owner: str = Depends(require_conversation_owner)):
    collections = await _owned_call(owned_collections, VAULT_DB_PATH, owner)
    return {'status': 'success', 'collections': collections, 'scope': 'verified_owner', 'limit': 50}

@router.post('/query')
async def query_vector_memory(req: MemoryQuery, owner: str = Depends(require_conversation_owner)):
    results = await _owned_call(search_records, VAULT_DB_PATH, owner, req.query, collection=req.collection, limit=req.top_k)
    return {'status': 'success', 'query': req.query, 'collection': req.collection,
            'count': len(results), 'results': results, 'search_type': 'lexical', 'preview_only': True}

@router.post('/store')
async def store_memory_item(item: MemoryRecord, owner: str = Depends(require_conversation_owner)):
    record = await _owned_call(store_record, VAULT_DB_PATH, owner, item.title, item.content, collection=item.collection, tags=item.tags)
    return {'status': 'success', 'message': 'Memory confirmed in the owner-scoped SQLite vault.',
            'vault_item_id': record['id'], 'owner': owner, 'content_sha256': record['content_sha256'],
            'durable': True, 'memory_index_status': 'not_indexed'}

class DirectMemoryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str
    metadata: Optional[Dict[str, Any]] = None

@router.post('')
async def create_memory_direct(payload: DirectMemoryPayload, owner: str = Depends(require_conversation_owner)):
    meta = payload.metadata or {}
    record = await _owned_call(store_record, VAULT_DB_PATH, owner, meta.get('title', f'Memory_{int(time.time())}'),
        payload.content, collection=meta.get('collection', 'stehouwer_heuristics'), tags=meta.get('tags', ['telemetry_suite']))
    return {'status': 'success', 'message': 'Memory confirmed in the owner-scoped SQLite vault.',
            'vault_item_id': record['id'], 'owner': owner, 'content_sha256': record['content_sha256'],
            'durable': True, 'memory_index_status': 'not_indexed'}

@router.delete('/{memory_id}')
async def delete_memory_by_id(memory_id: int, owner: str = Depends(require_conversation_owner)):
    result = await _owned_call(hide_record, VAULT_DB_PATH, owner, memory_id)
    return {'status': 'success', 'deleted_id': str(memory_id), **result}

class ChatIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: List[Dict[str, Any]]
    session_title: Optional[str] = "Chat Session Archive"
    source: Optional[str] = "chat_ui"
    archive_id: Optional[str] = None

@router.post('/ingest-chat')
async def ingest_chat_messages(req: ChatIngestRequest, owner: str = Depends(require_conversation_owner)):
    try:
        receipt = await asyncio.to_thread(archive_chat, VAULT_DB_PATH, req.messages, owner=owner, archive_id=req.archive_id,
            session_title=req.session_title or 'Chat Session Archive', source=req.source or 'chat_ui')
    except ArchiveConflict:
        raise HTTPException(409, 'Archive inputs changed; retain the conversation and review its saved state.') from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except PermissionError:
        raise HTTPException(403, 'Verified archive ownership is required.') from None
    except Exception as exc:
        logger.warning('Chat archive could not be confirmed (%s)', type(exc).__name__)
        raise HTTPException(503, 'Archive could not be confirmed. Keep the conversation and retry the same snapshot.') from None
    return {'status': 'success', 'message': 'Conversation confirmed in the owner-scoped SQLite vault.',
            'session_title': req.session_title or 'Chat Session Archive', 'items_saved': receipt['message_count'],
            'archive_receipt': receipt, 'memory_index_status': 'not_indexed'}

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
