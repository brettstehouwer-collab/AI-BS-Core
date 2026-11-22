"""Private RPC client for an explicitly inherited, controller-owned endpoint.

No credential lookup, network client, reconnect or request replay. Descriptor
ownership remains with the bootstrap; close must drain before descriptor release.
"""
import base64
import hashlib
import threading
import httpx
from native_studio.creative_pipe_io import PipeEndpoint
from native_studio.creative_wire import MAX_FRAME

OPERATIONS = {('GET','/api/screenwriting/read'):'read',
    ('POST','/api/screenwriting/write'):'save',
    ('GET','/api/screenwriting/export/fdx'):'export_fdx',
    ('GET','/api/screenwriting/export/pdf'):'export_pdf'}
_HEADERS = frozenset({'content-type','content-disposition','x-ai-bs-layout',
    'x-ai-bs-profile','x-ai-bs-renderer','x-ai-bs-fdx-renderer',
    'x-ai-bs-artifact-sha256','x-ai-bs-pdf-page-count'})


class CreativePipeTransport:
    def __init__(self, endpoint):
        if type(endpoint) is not PipeEndpoint:
            raise ValueError('An exact owned pipe endpoint is required.')
        self._endpoint = endpoint
        self._sequence = 0
        self._redeemed = False
        self._terminal = False
        self._busy = threading.Lock()

    def close(self):
        self._terminal = True
        return self._endpoint.close()

    def request(self, operation, payload):
        from native_studio.creative_session import CreativeSessionError
        if not self._busy.acquire(blocking=False):
            raise CreativeSessionError()
        try:
            if (self._terminal or type(payload) is not dict
                    or operation not in {'redeem', *OPERATIONS.values()}
                    or operation=='redeem' and self._redeemed
                    or operation!='redeem' and not self._redeemed):
                raise ValueError()
            self._sequence += 1
            if self._sequence > 2147483647:
                raise ValueError()
            identifier = self._sequence
            response = self._endpoint.exchange({'version':1,'id':identifier,
                'operation':operation,'payload':payload},timeout=10)
            if (self._terminal or type(response) is not dict
                    or type(response.get('version')) is not int or response['version']!=1
                    or type(response.get('id')) is not int or response['id']!=identifier
                    or type(response.get('status')) is not int
                    or response['status'] not in (200,400,403,404,409,413,422,428,503)):
                raise ValueError()
            status = response['status']
            if status==403:
                raise ValueError()
            if operation in {'export_fdx','export_pdf'} and status==200:
                if (set(response)!={'version','id','status','body_base64','headers'}
                        or type(response['body_base64']) is not str
                        or len(response['body_base64'])>MAX_FRAME
                        or type(response['headers']) is not dict
                        or not set(response['headers']).issubset(_HEADERS)
                        or any(type(v) is not str or len(v)>4096 for v in response['headers'].values())):
                    raise ValueError()
                body=base64.b64decode(response['body_base64'],validate=True)
                if response['headers'].get('x-ai-bs-artifact-sha256')!=hashlib.sha256(body).hexdigest():
                    raise ValueError()
                result=httpx.Response(200,content=body,headers=response['headers'])
            else:
                if set(response)!={'version','id','status','body'} or type(response['body']) is not dict:
                    raise ValueError()
                result=httpx.Response(status,json=response['body'])
            if operation=='redeem':
                if status!=200:
                    raise ValueError()
                self._redeemed=True
            return result
        except BaseException as error:
            self.close()
            if isinstance(error,Exception):
                raise CreativeSessionError() from None
            raise
        finally:
            self._busy.release()
