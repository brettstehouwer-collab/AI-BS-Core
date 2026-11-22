"""Independently authenticated, owner-scoped project preparation only."""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from core import coding_preparation as preparation_service
from core.coding_preparation import (PreparationPlan, PreparePayload, preview_preparation, prepare_request,
    read_preparation, recover_preparation, list_preparations, PreparationConflict, PreparationNotFound, PreparationEvidenceError, PreparationScopeError, ID_PATTERN)
from security.firebase_auth import get_admin_principal
from core import coding_preparation_planning as planning
from core import coding_preparation_proposals as proposals

router = APIRouter(prefix='/preparations',tags=['Project preparation'])


async def require_preparation_owner(request: Request):
    key = request.headers.get('x-admin-key','') or request.headers.get('x-api-key','')
    owner = await asyncio.to_thread(get_admin_principal,key,request.headers.get('authorization',''))
    if owner is None: raise HTTPException(403,'Administrator authorization is required for project preparation.')
    return owner


async def _call(function,*args,**kwargs):
    try: return await asyncio.to_thread(function,*args,**kwargs)
    except PreparationNotFound: raise HTTPException(404,'Preparation not found.') from None
    except PreparationConflict: raise HTTPException(409,'Preparation inputs or progress changed; preserve the record and review current state.') from None
    except PreparationScopeError: raise HTTPException(403,'The requested preparation scope is unavailable.') from None
    except ValueError: raise HTTPException(422,'Preparation plan or selected source is invalid; nothing was executed.') from None
    except (OSError,PreparationEvidenceError): raise HTTPException(503,'Preparation evidence could not be confirmed. Retained files were not discarded.') from None


@router.post('/preview')
async def preview(body: PreparationPlan,owner: str = Depends(require_preparation_owner)):
    return await _call(preview_preparation,owner,body.model_dump(mode='json'))


@router.post('')
async def prepare(body: PreparePayload,owner: str = Depends(require_preparation_owner)):
    return await _call(prepare_request,owner,body.model_dump(mode='json'))


@router.get('/identity')
async def identity(owner: str = Depends(require_preparation_owner)):
    return {'owner':owner,'repository_ids':list(preparation_service.REPOSITORIES),
            'execution_authorized':False,'verification_status':'not_run'}


@router.get('')
async def history(limit: int = Query(20,ge=1,le=50),cursor: str | None = Query(None,pattern=ID_PATTERN),owner: str = Depends(require_preparation_owner)):
    return await _call(list_preparations,owner,limit=limit,cursor=cursor)


@router.get('/{request_id}')
async def inspect(request_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(read_preparation,owner,request_id)


@router.post('/{request_id}/recover')
async def recover(request_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(recover_preparation,owner,request_id)


@router.post('/{request_id}/plans')
async def generate_plan(request_id: str,body: planning.PlanPayload,owner: str = Depends(require_preparation_owner)):
    try:return await planning.generate_plan(owner,request_id,body.plan_id)
    except PreparationNotFound:raise HTTPException(404,'Preparation or plan not found.') from None
    except PreparationConflict:raise HTTPException(409,'Planning is active or this ID already has evidence. Inspect the retained state.') from None
    except PreparationScopeError:raise HTTPException(403,'Planning scope is unavailable.') from None
    except ValueError:raise HTTPException(422,'Planning input is invalid; no project code was executed.') from None
    except (OSError,PreparationEvidenceError):raise HTTPException(503,'Planning evidence could not be confirmed. Retained inputs were preserved.') from None


@router.get('/{request_id}/plans')
async def plan_history(request_id: str,limit: int = Query(20,ge=1,le=50),cursor: str | None = Query(None,pattern=ID_PATTERN),owner: str = Depends(require_preparation_owner)):
    return await _call(planning.list_plans,owner,request_id,limit=limit,cursor=cursor)


@router.get('/{request_id}/plans/{plan_id}')
async def inspect_plan(request_id: str,plan_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(planning.read_plan,owner,request_id,plan_id)


@router.post('/{request_id}/plans/{plan_id}/recover')
async def recover_plan(request_id: str,plan_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(planning.recover_plan,owner,request_id,plan_id)


@router.post('/{request_id}/plans/{plan_id}/cancel')
async def cancel_plan(request_id: str,plan_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(planning.cancel_plan,owner,request_id,plan_id)


@router.get('/{request_id}/plans/{plan_id}/proposal-review')
async def proposal_review(request_id: str,plan_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(proposals.review_plan,owner,request_id,plan_id)


@router.get('/{request_id}/plans/{plan_id}/proposals')
async def proposal_history(request_id: str,plan_id: str,limit: int = Query(20,ge=1,le=50),cursor: str | None = Query(None,pattern=ID_PATTERN),owner: str = Depends(require_preparation_owner)):
    return await _call(proposals.list_proposals,owner,request_id,plan_id,limit=limit,cursor=cursor)


@router.post('/{request_id}/plans/{plan_id}/proposals')
async def generate_proposal(request_id: str,plan_id: str,body: proposals.ProposalPayload,owner: str = Depends(require_preparation_owner)):
    try:
        return await proposals.generate_proposal(owner,request_id,plan_id,body.proposal_id,body.reviewed_plan_sha256)
    except PreparationNotFound:raise HTTPException(404,'Preparation, plan or proposal not found.') from None
    except PreparationConflict:raise HTTPException(409,'Proposal inputs or progress changed; inspect the retained state.') from None
    except PreparationScopeError:raise HTTPException(403,'Proposal scope is unavailable.') from None
    except ValueError:raise HTTPException(422,'Proposal input is invalid or complete source exceeds the limit; no code was executed.') from None
    except (OSError,PreparationEvidenceError):raise HTTPException(503,'Proposal evidence could not be confirmed. Retained inputs were preserved.') from None


@router.get('/{request_id}/plans/{plan_id}/proposals/{proposal_id}')
async def inspect_proposal(request_id: str,plan_id: str,proposal_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(proposals.read_proposal,owner,request_id,plan_id,proposal_id)


@router.post('/{request_id}/plans/{plan_id}/proposals/{proposal_id}/recover')
async def recover_proposal(request_id: str,plan_id: str,proposal_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(proposals.recover_proposal,owner,request_id,plan_id,proposal_id)


@router.post('/{request_id}/plans/{plan_id}/proposals/{proposal_id}/cancel')
async def cancel_proposal(request_id: str,plan_id: str,proposal_id: str,owner: str = Depends(require_preparation_owner)):
    return await _call(proposals.cancel_proposal,owner,request_id,plan_id,proposal_id)
