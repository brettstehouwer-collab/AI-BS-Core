"""Memory-only native creative bootstrap; ordinary launches remain unchanged.

Only explicit bootstrap mode may consume this packet. The owned launcher must
deliver it through stdin and close the pipe; no URL/argv/environment persistence.
Server routes and trusted invocation resolution are separate required wiring.
"""
from dataclasses import dataclass
import json
import math
import re
import time
import threading
import httpx
from native_studio.local_connection import local_service_headers, LocalConnectionError

MAX_PACKET = 4096
ORIGIN = 'http://127.0.0.1:8080'


def silence_native_bootstrap_output():
    """Detach candidate output from backend pipes before redemption/GUI editing.

    Must run in the single-threaded explicit bootstrap path. Redirect both CRT
    descriptors and Win32 standard handles; backend loss must not leave a GUI
    writing into broken inherited logging pipes. No file log is created.
    """
    import os
    if (os.name!='nt' or threading.current_thread() is not threading.main_thread()
            or threading.active_count()!=1):raise CreativeSessionError()
    import ctypes,msvcrt
    from ctypes import wintypes
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.SetStdHandle.argtypes=[wintypes.DWORD,wintypes.HANDLE]
    api.SetStdHandle.restype=wintypes.BOOL
    try:
        with open(os.devnull,'wb',buffering=0) as sink:
            for fd,standard in ((1,-11),(2,-12)):
                os.dup2(sink.fileno(),fd)
                if not api.SetStdHandle(standard & 0xffffffff,msvcrt.get_osfhandle(fd)):
                    raise CreativeSessionError()
    except (OSError,ValueError):raise CreativeSessionError() from None


class CreativeSessionError(RuntimeError):
    def __init__(self):
        super().__init__('Native project authorization was not confirmed. Keep the current draft.')


@dataclass(frozen=True, repr=False)
class Bootstrap:
    grant: str
    project: str
    revision: str
    source_sha256: str
    candidate_sha256: str


def _read_bootstrap_bytes(stream, *, timeout=5.0):
    """Read the sole inherited Windows stdin pipe before GUI/worker startup.

    PeekNamedPipe is used only in this single-threaded startup phase; Microsoft
    warns synchronous peeks can block in multithreaded applications. Never call
    this from an existing GUI or share/read this stream concurrently.
    """
    import os
    if (os.name != 'nt' or threading.current_thread() is not threading.main_thread()
            or threading.active_count() != 1 or type(timeout) not in (int,float)
            or not math.isfinite(timeout) or not 0 < timeout <= 5):
        raise CreativeSessionError()
    import ctypes
    from ctypes import wintypes
    import msvcrt
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.GetFileType.argtypes=[wintypes.HANDLE]
    api.GetFileType.restype=wintypes.DWORD
    api.PeekNamedPipe.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD,
                               ctypes.c_void_p,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    api.PeekNamedPipe.restype=wintypes.BOOL
    try:
        fd=stream.fileno()
        handle=msvcrt.get_osfhandle(fd)
        if api.GetFileType(handle)!=3: raise CreativeSessionError()
        msvcrt.setmode(fd,os.O_BINARY)
        deadline=time.monotonic()+timeout
        raw=bytearray()
        while True:
            if time.monotonic()>=deadline: raise CreativeSessionError()
            available=wintypes.DWORD()
            if not api.PeekNamedPipe(handle,None,0,None,ctypes.byref(available),None):
                if ctypes.get_last_error()==109: break  # Writer closed its pipe.
                raise CreativeSessionError()
            if available.value:
                if available.value>MAX_PACKET-len(raw): raise CreativeSessionError()
                chunk=os.read(fd,available.value)
                if not chunk: break
                raw.extend(chunk)
            else:
                time.sleep(min(.01,max(0,deadline-time.monotonic())))
        return bytes(raw)
    except (OSError,ValueError,AttributeError):
        raise CreativeSessionError() from None


def read_bootstrap_pipe(stream, *, timeout=5.0):
    """Preserved stdin-v1 entry; the shared reader still requires pipe EOF."""
    return decode_bootstrap(_read_bootstrap_bytes(stream, timeout=timeout))


def decode_bootstrap(raw):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result: raise ValueError()
            result[key] = value
        return result
    try:
        if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_PACKET:
            raise ValueError()
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
        if not isinstance(value,dict) or set(value) != {'version','grant','project','revision','source_sha256','candidate_sha256'}:
            raise ValueError()
        if type(value['version']) is not int or value['version'] != 1:
            raise ValueError()
        if not isinstance(value['grant'],str) or not re.fullmatch(r'nch_g_[A-Za-z0-9_-]{43}',value['grant']):
            raise ValueError()
        for name in ('project','revision'):
            text=value[name]
            if not isinstance(text,str) or not text or len(text)>256 or any(ord(c)<32 for c in text):
                raise ValueError()
        for name in ('source_sha256','candidate_sha256'):
            if not isinstance(value[name],str) or not re.fullmatch(r'[a-f0-9]{64}',value[name]):
                raise ValueError()
        return Bootstrap(**{key:value[key] for key in value if key!='version'})
    except (ValueError,TypeError,UnicodeError):
        raise CreativeSessionError() from None


class CreativeSession:
    def __init__(self, *, headers_provider=local_service_headers, transport=None, clock=time.monotonic, endpoint=None):
        self._headers_provider, self._transport, self._clock = headers_provider, transport, clock
        self._channel = None
        self._bootstrap_resources = None
        self._recovery_scope = None
        if endpoint is not None:
            from native_studio.creative_pipe_transport import CreativePipeTransport
            self._channel = CreativePipeTransport(endpoint)
        self._lease, self._scope, self._deadline = None, None, 0

    def close(self):
        self._lease, self._scope, self._deadline = None, None, 0
        self._recovery_scope = None
        drained = True if self._channel is None else self._channel.close()
        if not drained:
            return False
        return True if self._bootstrap_resources is None else self._bootstrap_resources.close()

    def _attach_bootstrap_resources(self, resources):
        from native_studio.creative_pipe_bootstrap import OwnedPipeResources
        if (type(resources) is not OwnedPipeResources or self._bootstrap_resources is not None
                or self._channel is None or self._channel._endpoint is not resources.endpoint):
            raise CreativeSessionError()
        self._bootstrap_resources = resources

    @property
    def owned_channel(self):
        return self._channel is not None

    @property
    def recovery_scope(self):
        return self._recovery_scope

    def redeem(self, packet):
        self._lease, self._scope, self._deadline = None, None, 0
        self._recovery_scope = None
        if not isinstance(packet,Bootstrap): raise CreativeSessionError()
        started=self._clock()
        response=self._request('/api/screenwriting/native/redeem', {'grant':packet.grant})
        try:
            value=response.json()
            expected={'lease','project','revision','source_sha256','expires_in'}
            if (not isinstance(value,dict) or (set(value)!=expected and
                    not(self._channel is not None and set(value)==expected|{'recovery_scope'}))):
                raise ValueError()
            binding=value.get('recovery_scope')
            if binding is not None and (type(binding) is not str or not re.fullmatch(r'[a-f0-9]{64}',binding)):
                raise ValueError()
            if (value['project'],value['revision'],value['source_sha256']) != (packet.project,packet.revision,packet.source_sha256):
                raise ValueError()
            ttl=value['expires_in']
            if type(ttl) not in (int,float) or not math.isfinite(ttl) or not 0<ttl<=300:
                raise ValueError()
            if not isinstance(value['lease'],str) or not re.fullmatch(r'nch_l_[A-Za-z0-9_-]{43}',value['lease']):
                raise ValueError()
            deadline=started+ttl
            if deadline<=self._clock(): raise ValueError()
        except (ValueError,TypeError,KeyError):
            if self._channel is not None:self.close()
            raise CreativeSessionError() from None
        self._lease,self._scope,self._deadline=value['lease'],packet,deadline
        self._recovery_scope=binding

    def _request(self, route, payload):
        if self._channel is not None:
            if route!='/api/screenwriting/native/redeem':raise CreativeSessionError()
            return self._channel.request('redeem',payload)
        try:
            headers=self._headers_provider()
            if not headers: raise CreativeSessionError()
            with httpx.Client(base_url=ORIGIN,trust_env=False,follow_redirects=False,
                              timeout=10,transport=self._transport) as client:
                with client.stream('POST',route,headers=headers,json=payload) as response:
                    if response.status_code != 200:raise CreativeSessionError()
                    body=bytearray()
                    for chunk in response.iter_bytes(chunk_size=MAX_PACKET+1):
                        if len(chunk)>MAX_PACKET-len(body):raise CreativeSessionError()
                        body.extend(chunk)
                    return httpx.Response(200,content=bytes(body),request=response.request)
        except (httpx.HTTPError,LocalConnectionError):
            raise CreativeSessionError() from None

    def headers(self, *, project, operation):
        if self._channel is not None:raise CreativeSessionError()
        if (self._lease is None or self._scope is None or self._clock()>=self._deadline
                or project!=self._scope.project or operation not in {'read','save','export_fdx','export_pdf'}):
            raise CreativeSessionError()
        try:
            headers=dict(self._headers_provider())
        except (LocalConnectionError,TypeError,ValueError):
            raise CreativeSessionError() from None
        if not headers: raise CreativeSessionError()
        headers['X-AI-BS-Creative-Lease']=self._lease
        return headers

    def channel_request(self, method, route, payload):
        from native_studio.creative_pipe_transport import OPERATIONS
        operation=OPERATIONS.get((method,route))
        if (self._channel is None or operation is None or type(payload) is not dict
                or self._lease is None or self._scope is None or self._clock()>=self._deadline
                or payload.get('project_name')!=self._scope.project):
            raise CreativeSessionError()
        return self._channel.request(operation,payload)


def bootstrap_native_session(argv, stream, *, session_factory=CreativeSession):
    """Prepare an explicit delegated launch before Qt/worker initialization.

    Ordinary launches perform no pipe/credential/network work. The future scoped
    UI must consume the returned session; this helper never opens an editor.
    """
    flag='--native-creative-bootstrap'
    pipe_flag='--native-creative-pipe-bootstrap'
    if flag not in argv and pipe_flag not in argv:return None
    if type(argv) not in (list,tuple) or len(argv)!=2 or argv[1] not in (flag,pipe_flag):
        raise CreativeSessionError()
    if argv[1]==pipe_flag:
        from native_studio.creative_pipe_bootstrap import bootstrap_pipe_session
        return bootstrap_pipe_session(stream,session_factory=session_factory)
    packet=read_bootstrap_pipe(stream)
    silence_native_bootstrap_output()
    session=session_factory()
    try:
        session.redeem(packet)
    except Exception:
        session.close()
        raise CreativeSessionError() from None
    return session,packet
