"""Server-only live transport/process identity for the native creative adapter.

Not a route, launcher, authentication substitute or PID attachment API. The
future reviewed-candidate controller supplies an exact owned Windows job; OS
socket ownership joins that retained process handle to each direct HTTP request.
Uvicorn proxy rewriting is tolerated only by rejecting every forwarding header
before consulting the scope. Never use this through a forwarding gateway.
"""
from __future__ import annotations
import ctypes
import os
import re
import socket
from ctypes import wintypes
import psutil
from core.opencode_worker import _WinProcess
from security.native_creative_process import CreativeProcess
from security.native_creative_handoff import HandoffDenied


class OwnedInvocation:
    """Retain the controller's actual process object/handle, not a caller PID.

    Reuses the qualified suspended-create/JobObject/resume implementation. It
    does not invoke OpenCode, use a provider, or alter worker configuration.
    Candidate review/hash locking and bounded stdin delivery remain controller
    responsibilities before any grant can be issued to this identity.
    """
    def __init__(self, process, *, candidate_sha256):
        if (os.name!='nt' or type(process) not in (_WinProcess, CreativeProcess)
                or not isinstance(candidate_sha256,str)
                or not re.fullmatch(r'[a-f0-9]{64}',candidate_sha256)):
            raise HandoffDenied()
        self._process=process
        self._handle=process.hp
        self._pid=process.pid
        self._candidate_sha256=candidate_sha256
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.GetProcessId.argtypes=[wintypes.HANDLE];api.GetProcessId.restype=wintypes.DWORD
        api.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
        api.GetProcessTimes.restype=wintypes.BOOL
        self._api=api
        self._birth=self._identity()
        if self._birth is None:raise HandoffDenied()

    @property
    def candidate_sha256(self):return self._candidate_sha256

    def _identity(self):
        try:
            if (not self._handle or self._process.hp!=self._handle
                    or self._process.pid!=self._pid or self._process.poll() is not None
                    or self._api.GetProcessId(self._handle)!=self._pid):
                return None
            times=[wintypes.FILETIME() for _ in range(4)]
            if not self._api.GetProcessTimes(self._handle,*[ctypes.byref(t) for t in times]):
                return None
            return times[0].dwLowDateTime | times[0].dwHighDateTime<<32
        except (OSError,ValueError,TypeError):
            return None

    def alive(self):
        return self._birth is not None and self._identity()==self._birth


class NativePeerResolver:
    """Fail closed on proxy metadata, unavailable ownership, ambiguity or exit.

    endpoint is trusted server configuration, never request/query/JSON data.
    Only IPv4 loopback is supported by this fixed native transport. Both the
    accepted server-side socket (current backend PID) and client-side socket
    (exact live owned process PID) must match, twice. No forwarding header or
    request PID can supply the process identity. This is a sampled OS ownership
    check, not protection against code injection by an already privileged user.
    """
    def __init__(self, *, endpoint=('127.0.0.1',8080)):
        if (type(endpoint) is not tuple or len(endpoint)!=2 or endpoint[0]!='127.0.0.1'
                or type(endpoint[1]) is not int or not 1<=endpoint[1]<=65535):
            raise ValueError('A fixed IPv4 loopback endpoint is required.')
        self.endpoint=endpoint

    def _peer(self, scope):
        try:
            if scope['type']!='http':raise HandoffDenied()
            for name,value in scope['headers']:
                if not isinstance(name,bytes) or not isinstance(value,bytes):raise HandoffDenied()
                name=name.lower()
                if name==b'forwarded' or name.startswith(b'x-forwarded-'):
                    raise HandoffDenied()
            host,port=scope['client'];server_host,server_port=scope['server']
            if (host!='127.0.0.1' or type(port) is not int or not 1<=port<=65535
                    or server_host not in ('127.0.0.1','0.0.0.0')
                    or type(server_port) is not int or server_port!=self.endpoint[1]):
                raise HandoffDenied()
            return host,port
        except (KeyError,TypeError,ValueError):
            raise HandoffDenied() from None

    def _owner(self, peer):
        try:
            rows=psutil.net_connections(kind='tcp4')
            clients=set();servers=set()
            for row in rows:
                if (row.family!=socket.AF_INET or row.type!=socket.SOCK_STREAM
                        or row.status!=psutil.CONN_ESTABLISHED):continue
                local,remote=tuple(row.laddr),tuple(row.raddr)
                if local==peer and remote==self.endpoint:clients.add(row.pid)
                if local==self.endpoint and remote==peer:servers.add(row.pid)
            if (servers!={os.getpid()} or len(clients)!=1
                    or type(next(iter(clients))) is not int):raise HandoffDenied()
            return next(iter(clients))
        except (psutil.Error,OSError,ValueError,TypeError):
            raise HandoffDenied() from None

    def resolve(self, scope, invocations):
        peer=self._peer(scope)
        if (type(invocations) not in (tuple,list) or not 1<=len(invocations)<=64
                or any(type(x) is not OwnedInvocation for x in invocations)):
            raise HandoffDenied()
        owner=self._owner(peer)
        matches=[x for x in invocations if x._pid==owner and x.alive()]
        if len(matches)!=1:raise HandoffDenied()
        invocation=matches[0]
        if self._owner(peer)!=owner or not invocation.alive():raise HandoffDenied()
        return invocation
