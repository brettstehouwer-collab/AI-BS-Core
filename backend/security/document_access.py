"""Admin document access and narrowly scoped temporary media links."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import HTTPException, Request
from security.firebase_auth import verify_admin_credentials

_MEDIA_KEY = secrets.token_bytes(32)
MEDIA_TICKET_TTL = 3600


def is_document_path(path: str) -> bool:
    path = path.lower().rstrip('/')
    return (path in {'/api/tree', '/api/read', '/api/save', '/api/convert-pdf', '/api/documents', '/api/drive', '/documents'}
            or path.startswith('/api/documents/') or path.startswith('/api/drive/')
            or path.startswith('/documents/'))


def _canonical_path(path):
    return os.path.normcase(str(Path(path).resolve()))


def issue_media_ticket(path, action, ttl=MEDIA_TICKET_TTL):
    if action not in {'preview', 'download', 'video-preview'}:
        raise HTTPException(400, 'Unsupported media action.')
    body = json.dumps({'path': _canonical_path(path), 'action': action,
                       'exp': int(time.time()) + min(max(int(ttl), 1), MEDIA_TICKET_TTL)},
                      separators=(',', ':')).encode()
    encoded = base64.urlsafe_b64encode(body).decode().rstrip('=')
    signature = hmac.new(_MEDIA_KEY, encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + '.' + signature


def _valid_media_ticket(ticket, path, action):
    if not ticket or len(ticket) > 8192:
        return False
    try:
        encoded, supplied = ticket.rsplit('.', 1)
        expected = hmac.new(_MEDIA_KEY, encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            return False
        claims = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
        return (claims['action'] == action and time.time() < claims['exp']
                and claims['path'] == _canonical_path(path))
    except (ValueError, TypeError, KeyError, OSError):
        return False


def document_request_allowed(request: Request) -> bool:
    key = request.headers.get('x-admin-key', '') or request.headers.get('x-api-key', '')
    if verify_admin_credentials(key, request.headers.get('authorization', '')):
        return True
    route = request.url.path.lower().rstrip('/')
    if request.method not in {'GET', 'HEAD'} or route not in {'/api/drive/preview', '/api/drive/download'}:
        return False
    ticket = request.query_params.get('ticket', '')
    if not ticket:
        return False
    try:
        from routers.shared_drive_router import resolve_safe_path
        path = resolve_safe_path(request.query_params.get('path', ''))
        return _valid_media_ticket(ticket, path, route.rsplit('/', 1)[-1])
    except (HTTPException, OSError, ValueError):
        return False


def require_document_access(request: Request):
    if not document_request_allowed(request):
        raise HTTPException(403, 'Administrator authorization is required for documents and shared-drive access.')


def video_request_allowed(request: Request) -> bool:
    # Existing administrator admission remains distinct from the narrow video link.
    if document_request_allowed(request):
        return True
    route = request.url.path.lower().rstrip('/')
    if request.method not in {'GET', 'HEAD'} or route != '/api/video/stream':
        return False
    ticket = request.query_params.get('ticket', '')
    if not ticket:
        return False
    try:
        from routers.video_router import resolve_video_path
        target = resolve_video_path(request.query_params.get('path', ''))
        return _valid_media_ticket(ticket, target, 'video-preview')
    except (HTTPException, OSError, ValueError):
        return False


def require_video_access(request: Request):
    if not video_request_allowed(request):
        raise HTTPException(403, 'Administrator authorization or a valid file-scoped video link is required.')
