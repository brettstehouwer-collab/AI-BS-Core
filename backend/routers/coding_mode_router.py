"""Feature-gated, independently owner-authenticated Coding mode bridge."""
from fastapi import APIRouter, Depends, HTTPException, Query
from core import coding_mode_execution as service
from routers.coding_preparation_router import require_preparation_owner, _call
from pydantic import BaseModel, ConfigDict, Field


class ApplyPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    review_token: str = Field(min_length=1, max_length=256)

router = APIRouter(prefix='/mode', tags=['Coding mode'])


def require_enabled():
    if not service.enabled():
        raise HTTPException(404, 'Coding mode is disabled.')


@router.get('/capabilities')
async def capabilities(owner: str = Depends(require_preparation_owner)):
    return {**service.capabilities(), 'owner': owner}


@router.get('/executions', dependencies=[Depends(require_enabled)])
async def history(limit: int = Query(20, ge=1, le=50),
                  cursor: str | None = Query(None, pattern=service.preparation.ID_PATTERN),
                  owner: str = Depends(require_preparation_owner)):
    return await _call(service.list_executions, owner, limit=limit, cursor=cursor)


@router.post('/executions', dependencies=[Depends(require_enabled)])
async def prepare(body: service.ExecutionPayload, owner: str = Depends(require_preparation_owner)):
    return await _call(service.prepare_execution, owner, body.model_dump(mode='json'))


@router.get('/executions/{execution_id}', dependencies=[Depends(require_enabled)])
async def inspect(execution_id: str, owner: str = Depends(require_preparation_owner)):
    return await _call(service.read_execution, owner, execution_id)


@router.post('/executions/{execution_id}/recover', dependencies=[Depends(require_enabled)])
async def recover(execution_id: str, owner: str = Depends(require_preparation_owner)):
    return await _call(service.recover_execution, owner, execution_id)


@router.post('/executions/{execution_id}/cancel', dependencies=[Depends(require_enabled)])
async def cancel(execution_id: str, owner: str = Depends(require_preparation_owner)):
    return await _call(service.cancel_execution, owner, execution_id)


@router.post('/executions/{execution_id}/review', dependencies=[Depends(require_enabled)])
async def review(execution_id: str, owner: str = Depends(require_preparation_owner)):
    return await _call(service.review_execution, owner, execution_id)


@router.get('/executions/{execution_id}/checks/{check_id}', dependencies=[Depends(require_enabled)])
async def check_log(execution_id: str, check_id: str, owner: str = Depends(require_preparation_owner)):
    return await _call(service.read_check_log, owner, execution_id, check_id)


@router.post('/executions/{execution_id}/apply', dependencies=[Depends(require_enabled)])
async def apply(execution_id: str, body: ApplyPayload | None = None, owner: str = Depends(require_preparation_owner)):
    return await _call(service.apply_execution, owner, execution_id, body.review_token if body else None)
