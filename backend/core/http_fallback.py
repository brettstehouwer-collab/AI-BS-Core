"""Inert HTTP fallback helpers; no startup, execution or inference side effects."""
from pathlib import Path, PureWindowsPath

from fastapi.responses import FileResponse, JSONResponse
from starlette.routing import Match


def compatibility_target(full_path: str, method: str):
    """Only documented canonical endpoints can enter legacy compatibility code."""
    if full_path == 'v1/chat/completions' and method == 'POST':
        return 'chat'
    if full_path in {'models', 'api/models', 'v1/models'} and method in {'GET', 'HEAD'}:
        return 'models'
    return None


def fallback_method_response(request):
    """Recover actual prior route methods hidden by a final full-path route."""
    methods = set()
    current = request.scope.get('route')
    for route in _effective_routes(request.app.routes):
        if getattr(route, 'original_route', route) is current:
            break
        match, _ = route.matches(request.scope)
        if match == Match.PARTIAL:
            methods.update(getattr(route, 'methods', ()) or ())
    if methods:
        return JSONResponse(status_code=405, content={'detail': 'Method Not Allowed'},
                            headers={'Allow': ', '.join(sorted(methods))})
    return None


def _effective_routes(routes):
    for route in routes:
        # Recent FastAPI keeps includes lazy. Its effective contexts preserve
        # nested include prefixes and methods; flattened versions use routes.
        expand = getattr(route, 'effective_route_contexts', None)
        if callable(expand):
            yield from expand()
        else:
            yield route


def _not_found():
    return JSONResponse(status_code=404, content={'detail': 'Not Found'})


def _public_parts(full_path):
    if not isinstance(full_path, str) or full_path.startswith('/'):
        raise ValueError('Invalid public path')
    if any(ord(ch) < 32 or ord(ch) == 127 or ch in '\\:<>"|?*' for ch in full_path):
        raise ValueError('Invalid Windows path')
    parts = tuple(full_path.split('/')) if full_path else ()
    for index, part in enumerate(parts):
        if (not part or part in {'.', '..'} or part.endswith((' ', '.'))
                or PureWindowsPath(part).is_reserved()
                or (part.startswith('.') and not (index == 0 and part == '.well-known'))):
            raise ValueError('Non-public path component')
    return parts


def _public_file(workspace, base, parts):
    resolved_base = base.resolve()
    if not resolved_base.is_relative_to(workspace):
        raise ValueError('Public root escaped workspace')
    candidate = base.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_base):
        raise ValueError('File escaped public root')
    return candidate if candidate.is_file() else None


def static_fallback_response(workspace_root, full_path, method):
    """Serve declared public files/SPA only; resolved paths never leave the root."""
    if method not in {'GET', 'HEAD'}:
        return None
    try:
        parts = _public_parts(full_path)
        if parts and parts[0].lower() in {'api', 'v1'}:
            return None
        workspace = Path(workspace_root).resolve()
        dist = workspace / 'frontend/dist'
        public = workspace / 'frontend/public'
        if not parts or parts == ('index.html',):
            index = _public_file(workspace, dist, ('index.html',))
            if index is not None:
                return FileResponse(index, media_type='text/html')
        for base in (dist, public):
            candidate = _public_file(workspace, base, parts)
            if candidate is not None:
                media_type = 'application/vnd.android.package-archive' if full_path.lower().endswith('.apk') else None
                return FileResponse(candidate, media_type=media_type, filename=candidate.name)
        index = _public_file(workspace, dist, ('index.html',))
        if index is not None:
            return FileResponse(index, media_type='text/html')
    except (OSError, ValueError, RuntimeError):
        return _not_found()
    return None
