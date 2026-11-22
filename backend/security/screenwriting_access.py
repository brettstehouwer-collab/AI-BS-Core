"""Administrator-only screenplay workflows with file-scoped audio grants."""
import re
from fastapi import HTTPException, Request
from security.firebase_auth import verify_admin_credentials
from security.document_access import _valid_media_ticket


def is_screenwriting_path(path):
    path = path.lower().rstrip('/')
    return (path in {'/api/screenwriting', '/api/screenplay'}
            or path.startswith('/api/screenwriting/') or path.startswith('/api/screenplay/'))


def screenwriting_request_allowed(request: Request):
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    if verify_admin_credentials(key, request.headers.get('authorization', '')):
        return True
    match = re.fullmatch(r'/api/screenwriting/projects/([^/]+)/audio/stream/?', request.url.path)
    ticket = request.query_params.get('ticket', '')
    if request.method not in {'GET', 'HEAD'} or not match or not ticket:
        return False
    try:
        from routers.screenwriting_router import _project_audio_file
        target = _project_audio_file(match.group(1))
        return _valid_media_ticket(ticket, target, 'preview')
    except (HTTPException, ValueError, OSError):
        return False


def require_screenwriting_access(request: Request):
    if not screenwriting_request_allowed(request):
        raise HTTPException(403, 'Administrator authorization is required for screenplay access.')
