"""Explicit stdin-v2 child bootstrap and inherited-pipe resource ownership.

The sole trusted launch packet supplies handles, never a URL, path or PID.
Parsing itself claims no handles. Adoption begins only after both handles pass
the Windows pipe/inheritance/stdio checks in single-threaded startup.
"""
import ctypes
from ctypes import wintypes
import json
import os
import threading

from native_studio.creative_session import (
    Bootstrap, CreativeSession, CreativeSessionError, MAX_PACKET,
    _read_bootstrap_bytes, decode_bootstrap, silence_native_bootstrap_output,
)
from native_studio.creative_pipe_io import PipeEndpoint


class PipeBootstrapError(CreativeSessionError):
    def __init__(self, *, resources=None, cleanup_complete=True):
        super().__init__()
        # The holder contains no grant/document bytes. Retain unresolved resources
        # so an embedding caller can retry cleanup rather than closing live I/O.
        self.resources = resources
        self.cleanup_complete = cleanup_complete


def decode_pipe_bootstrap(raw):
    """Validate a complete bounded v2 envelope without touching native handles."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result
    try:
        if type(raw) is not bytes or not 1 <= len(raw) <= MAX_PACKET:
            raise ValueError()
        envelope = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
        if (type(envelope) is not dict or set(envelope) != {'version','bootstrap','channel'}
                or type(envelope['version']) is not int or envelope['version'] != 2
                or type(envelope['bootstrap']) is not dict or type(envelope['channel']) is not dict
                or set(envelope['channel']) != {'read_handle','write_handle'}):
            raise ValueError()
        packet = decode_bootstrap(json.dumps(envelope['bootstrap'],ensure_ascii=False,
                                            allow_nan=False).encode('utf-8'))
        handles = tuple(envelope['channel'][key] for key in ('read_handle','write_handle'))
        maximum = (1 << (ctypes.sizeof(ctypes.c_void_p)*8)) - 1
        if (any(type(handle) is not int or not 0 < handle < maximum for handle in handles)
                or handles[0] == handles[1]):
            raise ValueError()
        return packet, handles
    except (ValueError,TypeError,UnicodeError,RecursionError):
        raise PipeBootstrapError() from None


def _kernel32():
    api = ctypes.WinDLL('kernel32',use_last_error=True)
    api.GetFileType.argtypes = [wintypes.HANDLE]
    api.GetFileType.restype = wintypes.DWORD
    api.GetStdHandle.argtypes = [wintypes.DWORD]
    api.GetStdHandle.restype = wintypes.HANDLE
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    return api


class OwnedPipeResources:
    """Own only the fully validated pair; transfer each handle to one CRT fd.

    close() never releases descriptors until endpoint cancellation is complete.
    Failed releases remain recorded for a later close(), with no success claim.
    """
    def __init__(self, handles):
        if (os.name != 'nt' or threading.current_thread() is not threading.main_thread()
                or threading.active_count() != 1 or type(handles) is not tuple or len(handles) != 2):
            raise PipeBootstrapError()
        import msvcrt
        api = _kernel32()
        maximum = (1 << (ctypes.sizeof(ctypes.c_void_p)*8)) - 1
        standard = {api.GetStdHandle(value & 0xffffffff) for value in (-10,-11,-12)}
        for descriptor in (0,1,2):
            try:
                standard.add(msvcrt.get_osfhandle(descriptor))
            except OSError:
                pass
        try:
            if (any(type(handle) is not int or not 0 < handle < maximum
                    or handle in standard or api.GetFileType(handle) != 3
                    or not os.get_handle_inheritable(handle) for handle in handles)
                    or handles[0] == handles[1]):
                raise ValueError()
        except (OSError,ValueError):
            # Neither numeric input has been claimed; never close arbitrary
            # values from a malformed, invalid or aliased envelope.
            raise PipeBootstrapError() from None
        self._api = api
        self._lock = threading.Lock()
        self._raw_handles = set(handles)
        self._fds = set()
        self._endpoint = None
        try:
            descriptors = []
            for handle, flags in zip(handles,(os.O_RDONLY|os.O_BINARY,os.O_WRONLY|os.O_BINARY)):
                os.set_handle_inheritable(handle,False)
                descriptor = msvcrt.open_osfhandle(handle,flags)
                self._raw_handles.remove(handle)
                self._fds.add(descriptor)
                descriptors.append(descriptor)
            self._endpoint = PipeEndpoint(*descriptors)
        except BaseException:
            complete = self.close()
            raise PipeBootstrapError(resources=self,cleanup_complete=complete) from None

    @property
    def endpoint(self):
        if self._endpoint is None:
            raise PipeBootstrapError(resources=self,cleanup_complete=not self._fds and not self._raw_handles)
        return self._endpoint

    def close(self):
        with self._lock:
            if self._endpoint is not None:
                try:
                    if self._endpoint.close() is not True:
                        return False
                except Exception:
                    return False
            complete = True
            for descriptor in tuple(self._fds):
                try:
                    os.close(descriptor)
                    self._fds.remove(descriptor)
                except OSError:
                    complete = False
            for handle in tuple(self._raw_handles):
                if self._api.CloseHandle(handle):
                    self._raw_handles.remove(handle)
                else:
                    complete = False
            return complete and not self._fds and not self._raw_handles

    def __repr__(self):
        return '<OwnedPipeResources>'


def bootstrap_pipe_session(stream, *, session_factory=CreativeSession):
    """Prepare exact normal session/packet types before any editor startup."""
    resources = None
    session = None
    try:
        packet, handles = decode_pipe_bootstrap(_read_bootstrap_bytes(stream))
        resources = OwnedPipeResources(handles)
        silence_native_bootstrap_output()
        session = session_factory(endpoint=resources.endpoint)
        if type(session) is not CreativeSession:
            raise PipeBootstrapError()
        session._attach_bootstrap_resources(resources)
        session.redeem(packet)
        return session, packet
    except BaseException as error:
        complete = True
        if session is not None:
            try:
                complete = session.close() is True
            except Exception:
                complete = False
        if resources is not None:
            complete = resources.close() and complete
        elif isinstance(error,PipeBootstrapError) and error.resources is not None:
            resources = error.resources
            complete = error.cleanup_complete
        if not isinstance(error,Exception):
            raise
        raise PipeBootstrapError(resources=resources,cleanup_complete=complete) from None
