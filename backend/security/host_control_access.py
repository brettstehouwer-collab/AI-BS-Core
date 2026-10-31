"""Verified administrator admission for private host-control API routes."""

import asyncio
from collections.abc import Callable, Coroutine, Mapping
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocket

from security.firebase_auth import get_admin_principal


HOST_CONTROL_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization, X-Admin-Key, X-Api-Key",
}
HOST_UPLOAD_REQUEST_MAX_BYTES = 33 * 1024 * 1024
HOST_UPLOAD_PATHS = frozenset({
    "/documents/upload",
    "/api/v1/media/upload",
    "/api/v1/audio/demucs/upload_and_separate",
})


def _private_headers(existing: Mapping[str, str] | None = None) -> dict[str, str]:
    """Retain response metadata while enforcing private authorization variants."""
    headers = dict(existing or {})
    vary = []
    for name in list(headers):
        if name.lower() == "cache-control":
            del headers[name]
        elif name.lower() == "vary":
            vary.extend(part.strip() for part in headers.pop(name).split(",") if part.strip())
    variants = {part.lower() for part in vary}
    for part in HOST_CONTROL_PRIVATE_HEADERS["Vary"].split(", "):
        if part.lower() not in variants:
            vary.append(part)
            variants.add(part.lower())
    headers.update(HOST_CONTROL_PRIVATE_HEADERS)
    headers["Vary"] = ", ".join(vary)
    return headers


async def require_host_admin(request: Request) -> str:
    """Resolve configured local or SDK-verified Firebase administration off-thread."""
    key = request.headers.get("x-admin-key", "") or request.headers.get("x-api-key", "")
    authorization = request.headers.get("authorization", "")
    try:
        principal = await asyncio.to_thread(get_admin_principal, key, authorization)
    except Exception:
        principal = None
    if not isinstance(principal, str) or not principal.strip():
        raise HTTPException(
            status_code=403,
            detail="Verified administrator authorization is required for host controls.",
            headers=dict(HOST_CONTROL_PRIVATE_HEADERS),
        )
    return principal


class AdminWebSocketBoundaryMiddleware:
    """Verify private host sockets before a handler can accept or read frames.

    HTTP middleware does not run for WebSockets. Credentials use the same
    verified headers as host HTTP controls; URL query strings are never tokens.
    Browser clients need an authenticated socket adapter before using this API.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            await self.app(scope, receive, send)
            return
        socket = WebSocket(scope, receive, send)
        try:
            await require_host_admin(socket)
        except HTTPException:
            await socket.close(code=1008, reason='Verified administrator authorization is required.')
            return
        await self.app(scope, receive, send)


async def limit_host_upload(request: Request) -> None:
    """Bound upload requests before multipart parsing, with 1 MiB envelope overhead.

    Admission must precede this call. Check each received chunk before retaining
    it, then replay a bounded body cache through Starlette's normal parser. This
    avoids partial multipart spool files when the request exceeds its budget and
    leaves the request receive/close callables unchanged.
    """
    path = request.url.path.lower().rstrip("/")
    multipart = request.headers.get("content-type", "").split(";", 1)[0].strip().lower() == "multipart/form-data"
    if request.method not in {"POST", "PUT", "PATCH"} or (path not in HOST_UPLOAD_PATHS and not multipart):
        return

    limit = HOST_UPLOAD_REQUEST_MAX_BYTES

    def deny(status: int, detail: str) -> HTTPException:
        return HTTPException(status, detail, headers=dict(HOST_CONTROL_PRIVATE_HEADERS))

    lengths = set()
    for value in request.headers.getlist("content-length"):
        for item in value.split(","):
            item = item.strip()
            if not item or not item.isascii() or not item.isdecimal():
                raise deny(400, "Invalid upload content length.")
            if len(item) > 20:
                raise deny(413, "Upload request exceeds the permitted size.")
            length = int(item)
            if length > limit:
                raise deny(413, "Upload request exceeds the permitted size.")
            lengths.add(length)
    if len(lengths) > 1:
        raise deny(400, "Conflicting upload content lengths.")

    cached = getattr(request, "_body", None)
    if cached is not None:
        if len(cached) > limit:
            raise deny(413, "Upload request exceeds the permitted size.")
        return

    body = bytearray()
    received = 0
    async for block in request.stream():
        received += len(block)
        if received > limit:
            raise deny(413, "Upload request exceeds the permitted size.")
        body.extend(block)
    request._body = bytes(body)


class AdminHostControlRoute(APIRoute):
    """Admit administrators before body parsing and keep all route responses private."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            try:
                await require_host_admin(request)
                await limit_host_upload(request)
                response = await handler(request)
            except StarletteHTTPException as exc:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=exc.detail,
                    headers=_private_headers(exc.headers),
                ) from None
            except RequestValidationError:
                raise HTTPException(
                    status_code=422,
                    detail="Invalid host-control request.",
                    headers=dict(HOST_CONTROL_PRIVATE_HEADERS),
                ) from None
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Host-control request failed.",
                    headers=dict(HOST_CONTROL_PRIVATE_HEADERS),
                ) from None
            private = _private_headers({"Vary": ", ".join(response.headers.getlist("vary"))})
            for name in HOST_CONTROL_PRIVATE_HEADERS:
                response.headers[name] = private[name]
            return response

        return guarded
