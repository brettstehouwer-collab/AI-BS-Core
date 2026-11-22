"""Authenticated evidence-only API factory; deliberately absent from live startup.

Callers must admit a protected dedicated registry/store and a local embedding
adapter. Mounting requires independent concurrency/rate limits and store
ACL acceptance. This factory does not enable theatrical Performance Mode, model
generation, chat/history/tools, fallback, or execution of supplied source text.
"""
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request as BoundedRequest
from starlette.responses import JSONResponse
from typing import Annotated

from .firebase_auth import get_admin_principal
from .theatrical_corpus_boundary import CorpusBoundaryError
from .theatrical_corpus_registry import MAX_SOURCE_BYTES


Identifier = Annotated[StrictStr, Field(min_length=1, max_length=128,
                                       pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')]
Revision = Annotated[StrictStr, Field(min_length=64, max_length=64,
                                     pattern=r'^[0-9a-f]{64}$')]
MAX_REQUEST_BYTES = 12 * 1024 * 1024


class _StrictBody(BaseModel):
    model_config = ConfigDict(extra='forbid')


class _Source(_StrictBody):
    source_id: Identifier
    text: Annotated[StrictStr, Field(min_length=1, max_length=MAX_SOURCE_BYTES)]


class _Ingest(_StrictBody):
    sources: Annotated[list[_Source], Field(min_length=1, max_length=32)]


class _Query(_StrictBody):
    query: Annotated[StrictStr, Field(min_length=1, max_length=4096)]
    limit: Annotated[StrictInt, Field(ge=1, le=10)] = 3


class _Deactivate(_StrictBody):
    expected_revision: Revision


def _principal(request: Request):
    try:
        principal = get_admin_principal(
            request.headers.get('X-Admin-Key') or request.headers.get('X-API-Key', ''),
            request.headers.get('Authorization', ''))
    except Exception:
        principal = None
    if not principal:
        raise HTTPException(403, 'CORPUS_AUTH_REQUIRED')
    return principal


class _CorpusRoute(APIRoute):
    """Bound bytes before parsing; do not echo manuscript input in 422 errors."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def guarded(request: Request):
            # Authentication precedes even malformed JSON or oversized payloads.
            await run_in_threadpool(_principal, request)
            length = request.headers.get('Content-Length')
            if length is not None:
                if not re.fullmatch(r'[0-9]{1,10}', length):
                    raise HTTPException(400, 'INVALID_CORPUS_REQUEST')
                if int(length) > MAX_REQUEST_BYTES:
                    raise HTTPException(413, 'CORPUS_REQUEST_TOO_LARGE')
            received = 0

            async def bounded_receive():
                nonlocal received
                message = await request.receive()
                if message['type'] == 'http.request':
                    received += len(message.get('body', b''))
                    if received > MAX_REQUEST_BYTES:
                        raise HTTPException(413, 'CORPUS_REQUEST_TOO_LARGE')
                return message

            try:
                response = await handler(BoundedRequest(request.scope, receive=bounded_receive))
            except RequestValidationError:
                response = JSONResponse({'detail': 'INVALID_CORPUS_REQUEST'}, status_code=422)
            response.headers['Cache-Control'] = 'no-store'
            return response

        return guarded


def _public_failure(error):
    """Never return provider exceptions, raw content or authentication material."""
    code = str(error) if isinstance(error, CorpusBoundaryError) else 'CORPUS_UNAVAILABLE'
    if not re.fullmatch(r'[A-Z_]{1,64}', code):
        code = 'CORPUS_UNAVAILABLE'
    status = 503
    if code == 'CORPUS_NOT_AVAILABLE':
        status = 404
    elif code in ('CORPUS_REVISION_CONFLICT', 'CORPUS_REVISION_EXISTS'):
        status = 409
    elif code in ('INVALID_CORPUS_INPUT', 'INVALID_CORPUS_ENCODING',
                  'CORPUS_SIZE_LIMIT', 'REGISTRY_SIZE_LIMIT'):
        status = 422
    return HTTPException(status, code)


def _description(record):
    manifest = json.loads(record.manifest_json)  # Already verified by registry.resolve.
    return dict(capability='evidence_only', model_execution=False,
                performance_mode_enabled=False, corpus_id=record.scope.corpus_id,
                revision=record.scope.revision, generation=record.generation,
                source_count=len(manifest['sources']),
                chunk_count=sum(len(source['chunks']) for source in manifest['sources']))


def create_theatrical_corpus_router(registry, store, embedder, *, embedding_profile, dimensions):
    """Return an unmounted router; all dependencies are admitted server config.

    Sync handlers use FastAPI's thread pool. The dedicated SQLite connection must
    permit this use; CorpusRegistry serializes its transactions and uses a head
    generation comparison for changes spanning external store calls.
    """
    if (type(embedding_profile) is not str
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', embedding_profile)
            or type(dimensions) is not int or not 1 <= dimensions <= 4096):
        raise ValueError('INVALID_EMBEDDING_PROFILE')
    router = APIRouter(prefix='/api/theatrical/corpora', tags=['theatrical-evidence'],
                       route_class=_CorpusRoute)

    @router.post('/{corpus_id}/ingest', status_code=201)
    def ingest(corpus_id: Identifier, body: _Ingest, principal=Depends(_principal)):
        try:
            sources = [(source.source_id, source.text.encode('utf-8', errors='strict'))
                       for source in body.sources]
            scope = registry.ingest(principal, corpus_id, sources, store,
                embedder.embed_documents, embedding_profile=embedding_profile, dimensions=dimensions)
            record = registry.resolve(principal, corpus_id)
            if record.scope != scope:
                raise CorpusBoundaryError('CORPUS_REVISION_CONFLICT')
            return _description(record)
        except UnicodeError:
            raise HTTPException(422, 'INVALID_CORPUS_ENCODING') from None
        except Exception as error:
            raise _public_failure(error) from None

    @router.post('/{corpus_id}/evidence')
    def evidence(corpus_id: Identifier, body: _Query, principal=Depends(_principal)):
        try:
            record = registry.resolve(principal, corpus_id)  # Reject absent/foreign before embedding.
            manifest = json.loads(record.manifest_json)
            if (manifest['embedding_profile'] != embedding_profile
                    or manifest['dimensions'] != dimensions):
                raise CorpusBoundaryError('CORPUS_EMBEDDING_PROFILE_MISMATCH')
            vector = embedder.embed_query(body.query)
            result = registry.retrieve(principal, corpus_id, store, vector,
                                      embedding_profile=embedding_profile, limit=body.limit)
            if result.scope != record.scope or registry.resolve(principal, corpus_id) != record:
                raise CorpusBoundaryError('CORPUS_REVISION_CONFLICT')
            provenance = {chunk['id']: dict(source_id=source['source_id'],
                source_sha256=source['sha256'], start_byte=chunk['start_byte'],
                end_byte=chunk['end_byte'], chunk_sha256=chunk['sha256'])
                for source in manifest['sources'] for chunk in source['chunks']}
            return dict(_description(record), evidence=[dict(chunk_id=key, text=text,
                **provenance[key]) for key, text in zip(result.ids, result.documents)])
        except Exception as error:
            raise _public_failure(error) from None

    @router.get('/{corpus_id}/status')
    def status(corpus_id: Identifier, principal=Depends(_principal)):
        try:
            return _description(registry.resolve(principal, corpus_id))
        except Exception as error:
            raise _public_failure(error) from None

    @router.post('/{corpus_id}/deactivate')
    def deactivate(corpus_id: Identifier, body: _Deactivate, principal=Depends(_principal)):
        try:
            registry.deactivate(principal, corpus_id, expected_revision=body.expected_revision)
            return dict(capability='evidence_only', model_execution=False,
                        performance_mode_enabled=False, corpus_id=corpus_id,
                        deactivated_revision=body.expected_revision, active=False)
        except Exception as error:
            raise _public_failure(error) from None

    return router
