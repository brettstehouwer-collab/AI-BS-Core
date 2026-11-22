"""Verified financial owner boundary. Client-supplied tenant IDs are never owners."""
import asyncio
from fastapi import HTTPException, Request, Response
from security.firebase_auth import get_admin_principal


async def require_financial_owner(request: Request, response: Response):
    response.headers['Cache-Control'] = 'private, no-store'
    response.headers['Vary'] = 'Authorization, X-Admin-Key, X-Api-Key'
    owner = await asyncio.to_thread(get_admin_principal,
        request.headers.get('x-admin-key') or request.headers.get('x-api-key', ''),
        request.headers.get('authorization', ''))
    if not owner:
        raise HTTPException(403, 'Financial administrator access required',
                            headers={'Cache-Control': 'private, no-store'})
    return owner
