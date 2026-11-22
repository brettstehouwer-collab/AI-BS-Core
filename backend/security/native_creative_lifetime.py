"""Server-owned GUI lifetime; no route, candidate selection or authority grant.

The reviewed controller supplies fixed argv/environment and retains this object.
Until a trusted handoff acknowledgement, the existing suspended-create job owns
launch-failure cleanup. Acknowledgement clears only KILL_ON_JOB_CLOSE so a later
backend loss cannot destroy an editor's unsaved draft. This does not break the
process out of its job, grant filesystem/network isolation, or qualify a GUI.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import inspect
import os
import re
import threading

from core.opencode_worker import _WinProcess
from security.native_creative_process import CreativeProcess
from security.native_creative_channel import CreativePipes
from security.native_creative_peer import OwnedInvocation

_EXTENDED_LIMIT_INFORMATION = 9
_KILL_ON_JOB_CLOSE = 0x2000


class NativeLifetimeError(RuntimeError):
    """A local lifetime transition failed; contains no launch or document data."""


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ('PerProcessUserTimeLimit', ctypes.c_int64),
        ('PerJobUserTimeLimit', ctypes.c_int64),
        ('LimitFlags', wintypes.DWORD),
        ('MinimumWorkingSetSize', ctypes.c_size_t),
        ('MaximumWorkingSetSize', ctypes.c_size_t),
        ('ActiveProcessLimit', wintypes.DWORD),
        ('Affinity', ctypes.c_size_t),
        ('PriorityClass', wintypes.DWORD),
        ('SchedulingClass', wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        'ReadOperationCount', 'WriteOperationCount', 'OtherOperationCount',
        'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ('BasicLimitInformation', _BasicLimits), ('IoInfo', _IoCounters),
        ('ProcessMemoryLimit', ctypes.c_size_t),
        ('JobMemoryLimit', ctypes.c_size_t),
        ('PeakProcessMemoryUsed', ctypes.c_size_t),
        ('PeakJobMemoryUsed', ctypes.c_size_t),
    ]


@dataclass(frozen=True)
class CloseResult:
    acknowledged: bool
    termination_requested: bool
    job_drained: bool | None


class NativeCreativeLifetime:
    """Create one exact owned process and serialize its lifetime transitions.

    ``revoke_invocation`` is a synchronous trusted callback (normally the store's
    revoke_invocation method). It must complete before close touches OS resources
    and must not reenter this object. If it raises, no release/termination occurs;
    the controller can repair/retry revocation. Do not silently swallow that error.

    Only the trusted controller may call acknowledge_handoff after the exact live
    invocation has completed its reviewed handoff. A request boolean/PID/path must
    never call it directly. Keep editable GUI state gated until this succeeds:
    backend loss before acknowledgement intentionally terminates the launch job.
    Existing process stdout/stderr require bounded drains
    by the controller; close releases these pipes and they are not a GUI lifetime
    channel. After acknowledgement, close/expiry/restart must not use the borrowed
    _WinProcess.close(), which deliberately terminates worker jobs.
    """
    def __init__(self, argv, cwd, env, *, candidate_sha256, revoke_invocation, pipes=None):
        if (os.name != 'nt' or type(argv) not in (tuple, list) or not argv
                or not callable(revoke_invocation)
                or inspect.iscoroutinefunction(revoke_invocation)
                or not isinstance(candidate_sha256, str)
                or not re.fullmatch(r'[a-f0-9]{64}', candidate_sha256)):
            raise ValueError('A trusted Windows invocation and synchronous revoker are required.')
        self._lock = threading.RLock()
        self._revoking = False
        self._revoked = False
        self._acknowledged = False
        self._result = None
        self._revoke = revoke_invocation
        if pipes is not None and type(pipes) is not CreativePipes:
            raise ValueError('An owned creative pipe resource is required.')
        self._process = (_WinProcess(argv, cwd, env) if pipes is None
                         else CreativeProcess(argv, cwd, env, pipes))
        try:
            self._invocation = OwnedInvocation(self._process, candidate_sha256=candidate_sha256)
            self._job = self._process.job
            self._handle = self._process.hp
            api = ctypes.WinDLL('kernel32', use_last_error=True)
            api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
            api.QueryInformationJobObject.restype = wintypes.BOOL
            api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                ctypes.c_void_p, wintypes.DWORD]
            api.SetInformationJobObject.restype = wintypes.BOOL
            api.CloseHandle.argtypes = [wintypes.HANDLE]
            api.CloseHandle.restype = wintypes.BOOL
            self._api = api
            if not self._query_limits().BasicLimitInformation.LimitFlags & _KILL_ON_JOB_CLOSE:
                raise NativeLifetimeError('Launch containment is unavailable.')
        except BaseException:
            # No invocation has escaped this constructor or received authority.
            self._process.close()
            raise

    @property
    def invocation(self):
        return self._invocation

    @property
    def process(self):
        """Borrowed controller IO/liveness; never independently close this job."""
        return self._process

    @property
    def acknowledged(self):
        with self._lock:
            return self._acknowledged

    @property
    def closed(self):
        with self._lock:
            return self._result is not None

    def _query_limits(self):
        limits = _ExtendedLimits()
        size = wintypes.DWORD()
        if (not self._job or self._process.job != self._job
                or not self._api.QueryInformationJobObject(self._job,
                    _EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits),
                    ctypes.sizeof(limits), ctypes.byref(size))
                or size.value != ctypes.sizeof(limits)):
            raise NativeLifetimeError('Owned job limits are unavailable.')
        return limits

    def acknowledge_handoff(self, invocation):
        """Disarm backend-close termination, retaining exact peer handles.

        Query/modify/set preserves other limits as Microsoft specifies; a second
        query verifies the flag was removed. Failures remain unacknowledged and
        the caller must close the failed launch. No request-supplied identity is
        accepted, and no process/job membership or permissions are broadened.
        """
        with self._lock:
            if (self._result is not None or self._revoking or self._revoked
                    or invocation is not self._invocation or not invocation.alive()):
                raise NativeLifetimeError('The live owned handoff is unavailable.')
            if self._acknowledged:
                return
            limits = self._query_limits()
            limits.BasicLimitInformation.LimitFlags &= ~_KILL_ON_JOB_CLOSE
            if not self._api.SetInformationJobObject(self._job,
                    _EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise NativeLifetimeError('Owned job handoff failed.')
            if self._query_limits().BasicLimitInformation.LimitFlags & _KILL_ON_JOB_CLOSE:
                raise NativeLifetimeError('Owned job handoff was not confirmed.')
            self._acknowledged = True

    def _revoke_first(self):
        if self._revoked:
            return
        if self._revoking:
            raise NativeLifetimeError('Revocation may not reenter lifetime transitions.')
        self._revoking = True
        try:
            result = self._revoke(self._invocation)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise NativeLifetimeError('Revocation must complete synchronously.')
            self._revoked = True
        finally:
            self._revoking = False

    def close(self):
        """Revoke then abort a failed launch, or release a surviving editor.

        A released editor is not reported as drained. Repeated successful close
        returns the same immutable result and never invokes the revoker twice.
        """
        with self._lock:
            if self._result is not None:
                return self._result
            self._revoke_first()
            if not self._acknowledged:
                if self._process.job != self._job or self._process.hp != self._handle:
                    raise NativeLifetimeError('Owned launch handles changed.')
                drained = self._process.close()
                self._job = None
                self._result = CloseResult(False, True, drained)
                return self._result
            # No TerminateJobObject/WaitForSingleObject: acknowledged GUI work
            # survives backend loss. Keep failed handles for an explicit retry.
            for name in ('stdin', 'stdout', 'stderr'):
                stream = getattr(self._process, name, None)
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
                    setattr(self._process, name, None)
            if self._process.job is not None:
                if self._process.job != self._job or not self._api.CloseHandle(self._job):
                    raise NativeLifetimeError('Owned job handle release failed.')
                self._process.job = None
                self._job = None
            if self._process.hp is not None:
                if self._process.hp != self._handle or not self._api.CloseHandle(self._handle):
                    raise NativeLifetimeError('Owned process handle release failed.')
                self._process.hp = None
            self._result = CloseResult(True, False, None)
            return self._result
