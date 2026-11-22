"""Public telemetry intake is separate from private reports and execution."""
import asyncio
from fastapi import HTTPException, Request
from security.firebase_auth import verify_admin_credentials

PREFIXES = (
    '/api/analytics', '/v1/analytics', '/v1/api/analytics',
    '/api/v1/analytics', '/api/v1/chef/analytics', '/api/admin',
)
PUBLIC_INTAKE = frozenset({
    '/api/analytics/track', '/v1/analytics/track', '/v1/api/analytics/track',
    '/api/analytics/security-event', '/api/v1/chef/analytics/ingest-event',
})


def is_analytics_path(path: str) -> bool:
    path = path.lower().rstrip('/')
    return any(path == prefix or path.startswith(prefix + '/') for prefix in PREFIXES)


async def require_analytics_admin(request: Request):
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    if not await asyncio.to_thread(verify_admin_credentials, key, request.headers.get('authorization', '')):
        raise HTTPException(403, 'Administrator authorization is required for analytics reports and actions.')


async def require_analytics_access(request: Request):
    if request.method == 'POST' and request.url.path.rstrip('/') in PUBLIC_INTAKE:
        return
    await require_analytics_admin(request)
