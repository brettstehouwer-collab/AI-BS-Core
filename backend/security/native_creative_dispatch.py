"""Trusted controller-bound RPC to the existing owner-fenced screenplay store.

No HTTP registration or default controller activation. The router argument is a
server-selected service namespace, never decoded from a request. The transport
owner must call close on EOF/timeout and drain I/O before releasing descriptors.
"""
import base64
import hashlib
import json
import threading

from fastapi import HTTPException
from pydantic import ValidationError
from core.personal_memory_scope import bind_memory_principal, reset_memory_principal
from core.chat_pdf_sources import PDFSourceError
from security.native_creative_source import require_native_creative_source
from security.native_creative_adapter import NativeCreativeAdapter
from security.native_creative_peer import OwnedInvocation
from security.native_creative_handoff import HandoffDenied
from native_studio.creative_wire import encode, WireError, MAX_FRAME

_FIELDS = {
    'read': {'project_name'},
    'save': {'project_name', 'content', 'expected_revision', 'expected_workflow_revision',
             'preserve_unchanged_bytes', 'fdx_document'},
    'export_fdx': {'project_name', 'layout', 'expected_revision'},
    'export_pdf': {'project_name', 'layout', 'expected_revision', 'watermark'},
}
_EXPORT_HEADERS = frozenset({'content-type', 'content-disposition', 'x-ai-bs-layout',
    'x-ai-bs-profile', 'x-ai-bs-renderer', 'x-ai-bs-fdx-renderer',
    'x-ai-bs-artifact-sha256', 'x-ai-bs-pdf-page-count'})


class CreativeDispatch:
    """One exact invocation, one redemption and a strictly sequenced RPC stream."""
    def __init__(self, adapter, invocation, router):
        if type(adapter) is not NativeCreativeAdapter or type(invocation) is not OwnedInvocation:
            raise ValueError('An exact controller-owned invocation is required.')
        self._adapter, self._invocation, self._router = adapter, invocation, router
        self._lease = None
        self._next = 1
        self._closed = False
        self._serial = threading.Lock()

    def close(self):
        # Set the terminal flag first. Do not wait for a blocked store operation
        # before revoking its lease. In-flight commit outcomes may be unknown.
        self._closed = True
        self._adapter.unregister(self._invocation)
        self._lease = None

    @staticmethod
    def _refusal(identifier, status):
        return {'version': 1, 'id': identifier, 'status': status,
                'body': {'detail': 'Creative operation was not confirmed. Keep the current draft.'}}

    def dispatch(self, message):
        if not self._serial.acquire(blocking=False):
            raise HandoffDenied()
        try:
            if (self._closed or type(message) is not dict
                    or set(message) != {'version', 'id', 'operation', 'payload'}
                    or type(message['version']) is not int or message['version'] != 1
                    or type(message['id']) is not int or message['id'] != self._next
                    or not 1 <= self._next <= 2147483647
                    or type(message['operation']) is not str
                    or type(message['payload']) is not dict):
                raise HandoffDenied()
            identifier = self._next
            self._next += 1
            operation, payload = message['operation'], message['payload']
            if operation == 'redeem':
                if self._lease is not None or set(payload) != {'grant'}:
                    raise HandoffDenied()
                result = self._adapter.redeem_owned_channel(self._invocation, payload['grant'])
                if self._closed:
                    raise HandoffDenied()
                self._lease = result['lease']
                scope=self._adapter.resolve_owned_channel(self._invocation,self._lease,
                    project=result['project'],operation='read')
                result['recovery_scope']=hashlib.sha256(json.dumps(
                    {'version':1,'owner':scope.owner,'project':scope.project,'source_sha256':scope.source_sha256},
                    sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
                return {'version': 1, 'id': identifier, 'status': 200, 'body': result}
            if (self._lease is None or operation not in _FIELDS
                    or not set(payload).issubset(_FIELDS[operation])
                    or type(payload.get('project_name')) is not str):
                raise HandoffDenied()
            try:
                result = self._execute(operation, payload)
                response = {'version': 1, 'id': identifier, 'status': 200, **result}
                try:
                    encode(response)
                except WireError:
                    return self._refusal(identifier, 413)
                if self._closed:
                    raise HandoffDenied()
                return response
            except (HTTPException, PDFSourceError) as error:
                status = error.status_code if isinstance(error, HTTPException) else error.status
                if status in (401, 403):
                    raise HandoffDenied() from None
                return self._refusal(identifier, status if status in (400,404,409,413,422,428,503) else 503)
            except ValidationError:
                return self._refusal(identifier, 422)
        except HandoffDenied:
            self.close()
            raise
        except Exception:
            self.close()
            raise HandoffDenied() from None
        finally:
            self._serial.release()

    def _execute(self, operation, payload):
        router = self._router
        with router._PROJECT_STORE_LOCK:
            # Resolve AFTER waiting for the store lock, so lease expiry while
            # queued cannot reuse an earlier authorization decision.
            scope = self._adapter.resolve_owned_channel(self._invocation, self._lease,
                project=payload['project_name'], operation=operation)
            token = bind_memory_principal(scope.owner)
            try:
                directory = router._existing_project_directory(scope.project)
                fence = require_native_creative_source(directory)
                if fence.get('source_sha256') != scope.source_sha256:
                    raise HandoffDenied()
                if operation == 'read':
                    return {'body': router.read_screenplay(project_name=scope.project)}
                if operation == 'save':
                    value = router.WriteScreenplayPayload(**payload)
                    return {'body': router.write_screenplay(value)}
                arguments = dict(payload)
                response = (router.export_fdx(**arguments) if operation == 'export_fdx'
                            else router.export_pdf(**arguments))
                body = response.body
                # Leave room for base64 and bounded qualification metadata;
                # oversized exports are refused, never truncated or reformatted.
                if type(body) is not bytes or len(body) > (MAX_FRAME - 65536) * 3 // 4:
                    raise HTTPException(413, 'Export exceeds the channel bound.')
                headers = {key: value for key, value in response.headers.items()
                           if key in _EXPORT_HEADERS}
                if any(len(value) > 4096 for value in headers.values()):
                    raise HTTPException(413, 'Export metadata exceeds the channel bound.')
                return {'body_base64': base64.b64encode(body).decode('ascii'), 'headers': headers}
            finally:
                reset_memory_principal(token)
