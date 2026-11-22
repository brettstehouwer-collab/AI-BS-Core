"""Administrator-only review and explicit application of verified coding tasks."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from core.coding_review import apply_task, review_task
from core.coding_recovery import REQUESTS, list_coding_records, recover_request, recover_task, request_coding_cancellation
from core.coding_workflow import STORE
from security.firebase_auth import verify_admin_credentials
from routers.coding_preparation_router import router as coding_preparation_router
from routers.coding_mode_router import router as coding_mode_router

router = APIRouter(prefix='/api/chat/coding-tasks', tags=['Coding task review'])
router.include_router(coding_preparation_router)
router.include_router(coding_mode_router)


async def require_coding_admin(request: Request):
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    authorization = request.headers.get('authorization', '')
    if not await asyncio.to_thread(verify_admin_credentials, key, authorization):
        raise HTTPException(status_code=403, detail='Administrator authorization required')


class ApplyRequest(BaseModel):
    review_token: str


@router.post('/{task_id}/cancel', dependencies=[Depends(require_coding_admin)])
async def cancel_coding_task(task_id: str):
    try:
        return await asyncio.to_thread(request_coding_cancellation,task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc


@router.get('', dependencies=[Depends(require_coding_admin)])
async def list_saved_coding_tasks():
    return {'items':await asyncio.to_thread(list_coding_records)}


@router.get('/{task_id}/review', dependencies=[Depends(require_coding_admin)])
async def get_coding_review(task_id: str):
    try:
        return await asyncio.to_thread(review_task, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/{task_id}/apply', dependencies=[Depends(require_coding_admin)])
async def apply_coding_review(task_id: str, body: ApplyRequest):
    try:
        result = await asyncio.to_thread(apply_task, task_id, body.review_token)
        return {'task_id':task_id,'application':result['application']}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/{task_id}/recover', dependencies=[Depends(require_coding_admin)])
async def recover_saved_coding_task(task_id: str):
    try:
        if len(task_id)!=32 or any(ch not in '0123456789abcdef' for ch in task_id):
            raise ValueError('Invalid task ID')
        if (STORE/task_id/'result.json').is_file():
            return await asyncio.to_thread(recover_task, task_id)
        if (REQUESTS/task_id/'request.json').is_file():
            return await asyncio.to_thread(recover_request, task_id)
        raise ValueError('Task or request not found')
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
