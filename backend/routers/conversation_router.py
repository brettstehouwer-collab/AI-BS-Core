"""Authenticated private conversation revisions; mounted by memory_router."""
import asyncio
from pathlib import Path
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path as ApiPath, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from core.conversation_sessions import (
    ConversationConflict, ConversationEvidenceError, ConversationNotFound,
    MAX_REVISION, list_conversations, read_conversation, save_conversation,
)
from security.firebase_auth import get_admin_principal

router = APIRouter(prefix='/conversations', tags=['Private conversation recovery'])
DB_PATH = Path(__file__).resolve().parents[1] / 'stehouwer_vault.db'
ID_PATTERN = r'^[a-f0-9]{32}$'


async def require_conversation_owner(request: Request):
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    owner = await asyncio.to_thread(get_admin_principal, key, request.headers.get('authorization', ''))
    if owner is None:
        raise HTTPException(403, 'Administrator authorization is required for conversation history.')
    return owner


class ConversationSaveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: str = Field(pattern=ID_PATTERN)
    expected_revision: StrictInt = Field(ge=0, lt=MAX_REVISION)
    messages: list[dict[str, Any]]
    title: str = Field(default='Chat', max_length=2000)


async def _store_call(function, *args, **kwargs):
    try:
        return await asyncio.to_thread(function, *args, **kwargs)
    except ConversationNotFound:
        raise HTTPException(404, 'Conversation or revision not found.') from None
    except ConversationConflict:
        raise HTTPException(409, 'Conversation inputs changed; retain pending content and reload the current revision.') from None
    except ConversationEvidenceError:
        raise HTTPException(503, 'Conversation evidence could not be confirmed; retain pending content.') from None
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except (sqlite3.Error, OSError):
        raise HTTPException(503, 'Conversation storage is unavailable; retain pending content.') from None


@router.get('/identity')
async def conversation_identity(owner: str = Depends(require_conversation_owner)):
    return {'owner': owner, 'storage': 'sqlite_vault', 'schema': 1}


@router.get('')
async def conversation_list(limit: int = Query(default=20, ge=1, le=50),
                            before: str | None = Query(default=None, pattern=ID_PATTERN),
                            owner: str = Depends(require_conversation_owner)):
    return await _store_call(list_conversations, DB_PATH, owner, limit=limit, before=before)


@router.get('/{conversation_id}')
async def conversation_read(conversation_id: str = ApiPath(pattern=ID_PATTERN),
                            revision: int | None = Query(default=None, ge=1, le=MAX_REVISION),
                            owner: str = Depends(require_conversation_owner)):
    return await _store_call(read_conversation, DB_PATH, owner, conversation_id, revision=revision)


@router.post('/{conversation_id}')
async def conversation_save(payload: ConversationSaveRequest,
                            conversation_id: str = ApiPath(pattern=ID_PATTERN),
                            owner: str = Depends(require_conversation_owner)):
    receipt = await _store_call(save_conversation, DB_PATH, owner, conversation_id,
                               **payload.model_dump())
    return {'status': 'success', 'receipt': receipt, 'memory_index_status': 'not_indexed'}
