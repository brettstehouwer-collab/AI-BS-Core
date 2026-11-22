"""Trusted, source-only native creative launch controller. No routes or defaults.

No caller selects a path, argv, environment or candidate digest. A server-owned
reviewed spec pins only its explicitly listed files, not a whole Python/DLL import
closure. A reviewed child must consume its exact v1/v2 stdin contract and redirect
CRT/Win32 stdout and stderr to NUL before redeeming; editable GUI startup remains gated until redemption
acknowledges the owned lifetime. This module does not select a production candidate.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
import hashlib
import inspect
import json
import math
import ntpath
import os
from pathlib import Path
import re
import threading
import time

from security.firebase_auth import VerifiedFirebaseContext
from security.native_creative_adapter import NativeCreativeAdapter
from security.native_creative_handoff import CreativeHandoffs, CreativeScope
from security.native_creative_lifetime import NativeCreativeLifetime
from security.native_creative_channel import CreativePipes
from security.native_creative_dispatch import CreativeDispatch
from native_studio.creative_pipe_io import PipeEndpoint

BOOTSTRAP_CONTRACT = 'stdin-v1;crt-win32-nul-before-redeem;gui-after-redeem-v1'
PIPE_BOOTSTRAP_CONTRACT = 'stdin-v2;owned-pipe-rpc-v1;crt-win32-nul-before-redeem;gui-after-redeem-v1'
MAX_PACKET = 4096
DELIVERY_SECONDS = 5.0
ACK_SECONDS = 20.0
_ENV_KEYS = frozenset({'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP',
    'PYTHONNOUSERSITE', 'PYTHONDONTWRITEBYTECODE', 'PYTHONUTF8',
    'QT_QPA_PLATFORM_PLUGIN_PATH', 'QT_PLUGIN_PATH'})


class NativeControllerError(RuntimeError):
    def __init__(self):
        super().__init__('Native creative launch or authorization was not confirmed.')


def _local_path(value):
    if (type(value) is not str or not 3 <= len(value) <= 1024
            or not re.match(r'^[A-Za-z]:[\\/]', value)
            or any(ord(c) < 32 for c in value) or ':' in value[2:]):
        raise ValueError('A fixed local Windows path is required.')
    normalized = ntpath.normpath(value)
    if normalized != value.replace('/', '\\'):
        raise ValueError('A normalized server-owned path is required.')
    return normalized


@dataclass(frozen=True, repr=False)
class ReviewedFile:
    path: str
    sha256: str

    def __post_init__(self):
        _local_path(self.path)
        if type(self.sha256) is not str or not re.fullmatch(r'[a-f0-9]{64}', self.sha256):
            raise ValueError('A reviewed file digest is required.')


@dataclass(frozen=True, repr=False)
class ReviewedCandidate:
    executable: ReviewedFile
    arguments: tuple
    cwd: str
    environment: tuple
    dependencies: tuple
    contract: str

    def __post_init__(self):
        if (type(self.executable) is not ReviewedFile or type(self.arguments) is not tuple
                or len(self.arguments) > 32 or type(self.dependencies) is not tuple
                or len(self.dependencies) > 63
                or any(type(pin) is not ReviewedFile for pin in self.dependencies)
                or self.contract not in (BOOTSTRAP_CONTRACT, PIPE_BOOTSTRAP_CONTRACT)
                or type(self.environment) is not tuple or len(self.environment) > 16):
            raise ValueError('An explicit reviewed candidate spec is required.')
        if self.contract == PIPE_BOOTSTRAP_CONTRACT and self.arguments.count('--native-creative-pipe-bootstrap') != 1:
            raise ValueError('The reviewed pipe bootstrap requires its fixed explicit flag.')
        _local_path(self.cwd)
        for argument in self.arguments:
            if (type(argument) is not str or len(argument) > 4096
                    or any(ord(c) < 32 for c in argument)):
                raise ValueError('Only fixed candidate arguments are allowed.')
        names = set()
        for pair in self.environment:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError('A fixed noncredential environment is required.')
            name, value = pair
            if (type(name) is not str or name.upper() not in _ENV_KEYS or name.upper() in names
                    or type(value) is not str or len(value) > 8192
                    or any(ord(c) < 32 for c in value)):
                raise ValueError('A fixed noncredential environment is required.')
            names.add(name.upper())
        paths = [ntpath.normcase(_local_path(pin.path)) for pin in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError('Duplicate reviewed file pins are not allowed.')

    @property
    def files(self):
        return (self.executable,) + self.dependencies

    @property
    def sha256(self):
        # This identifies this exact LIMITED manifest, not an unlisted bundle.
        value = dict(executable=(self.executable.path, self.executable.sha256),
            arguments=self.arguments, cwd=self.cwd, environment=self.environment,
            dependencies=tuple((p.path, p.sha256) for p in self.dependencies), contract=self.contract)
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
            ensure_ascii=True).encode('ascii')).hexdigest()


class _FileInfo(ctypes.Structure):
    _fields_ = [('attributes', wintypes.DWORD), ('created', wintypes.FILETIME),
        ('accessed', wintypes.FILETIME), ('written', wintypes.FILETIME),
        ('volume', wintypes.DWORD), ('size_high', wintypes.DWORD),
        ('size_low', wintypes.DWORD), ('links', wintypes.DWORD),
        ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD)]


class _PinnedFiles:
    """Open/verify listed local files; retain no-write/no-delete file handles.

    Ancestor directories are held without DELETE sharing and reparse points are
    refused. This narrows pathname substitution; it is not an OS security sandbox
    or protection from privileged handle/memory manipulation and unlisted imports.
    """
    def __init__(self, candidate):
        self.handles = []
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
            ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        api.CreateFileW.restype = wintypes.HANDLE
        api.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.POINTER(_FileInfo)]
        api.GetFileInformationByHandle.restype = wintypes.BOOL
        api.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
            wintypes.DWORD, wintypes.DWORD]
        api.GetFinalPathNameByHandleW.restype = wintypes.DWORD
        api.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
        api.ReadFile.restype = wintypes.BOOL
        api.CloseHandle.argtypes = [wintypes.HANDLE]; api.CloseHandle.restype = wintypes.BOOL
        self.api = api
        try:
            directories = {Path(candidate.cwd)}
            for pin in candidate.files:
                directories.update(Path(pin.path).parents)
            directories.update(Path(candidate.cwd).parents)
            if len(directories) > 256:
                raise NativeControllerError()
            for directory in sorted(directories, key=lambda p: len(p.parts)):
                self._open(str(directory), directory=True)
            for pin in candidate.files:
                handle, info = self._open(pin.path, directory=False)
                size = info.size_low | info.size_high << 32
                if size > 512 * 1024 * 1024:
                    raise NativeControllerError()
                digest = hashlib.sha256(); total = 0
                buffer = ctypes.create_string_buffer(65536)
                while True:
                    count = wintypes.DWORD()
                    if not api.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
                        raise NativeControllerError()
                    if not count.value:
                        break
                    total += count.value
                    if total > size:
                        raise NativeControllerError()
                    digest.update(buffer.raw[:count.value])
                if total != size or digest.hexdigest() != pin.sha256:
                    raise NativeControllerError()
        except BaseException:
            self.close()
            raise

    def _open(self, path, *, directory):
        access = 0x80 if directory else 0x80000000
        share = 3 if directory else 1  # No DELETE, and file pins also deny WRITE.
        flags = 0x00200000 | (0x02000000 if directory else 0x80)
        handle = self.api.CreateFileW(path, access, share, None, 3, flags, None)
        if handle in (None, ctypes.c_void_p(-1).value):
            raise NativeControllerError()
        self.handles.append(handle)
        info = _FileInfo(); final = ctypes.create_unicode_buffer(2048)
        length = self.api.GetFinalPathNameByHandleW(handle, final, len(final), 0)
        if (not self.api.GetFileInformationByHandle(handle, ctypes.byref(info))
                or info.attributes & 0x400 or bool(info.attributes & 0x10) != directory
                or not 0 < length < len(final)):
            raise NativeControllerError()
        actual = final.value
        if actual.startswith('\\\\?\\'):
            actual = actual[4:]
        if ntpath.normcase(ntpath.normpath(actual)) != ntpath.normcase(ntpath.normpath(path)):
            raise NativeControllerError()
        return handle, info

    def close(self):
        remaining = []
        for handle in reversed(self.handles):
            if not self.api.CloseHandle(handle):
                remaining.append(handle)
        self.handles = list(reversed(remaining))
        if remaining:
            raise NativeControllerError()


class _Drain:
    """Discard fixed-size blocks without logging/storing child output."""
    def __init__(self, stream):
        self.done = threading.Event()
        self.failed = False
        self.bytes_discarded = 0
        def run():
            try:
                while True:
                    block = stream.read(16384)
                    if not block:
                        break
                    # Saturating metadata only; memory never grows with output.
                    self.bytes_discarded = min(16 * 1024 * 1024, self.bytes_discarded + len(block))
            except (OSError, ValueError):
                self.failed = True
            finally:
                self.done.set()
        self.thread = threading.Thread(target=run, name='native-output-discard', daemon=True)
        self.thread.start()


@dataclass(eq=False, repr=False)
class OwnedLaunch:
    _controller: object
    _lifetime: object
    _pins: object
    _expected: CreativeScope
    _drains: tuple
    _delivery: threading.Event = field(default_factory=threading.Event)
    _acked: threading.Event = field(default_factory=threading.Event)
    _delivery_ok: bool = False
    _failed: bool = False
    _writer: object = None
    _result: object = None
    _closing: threading.Lock = field(default_factory=threading.Lock)
    _transition: threading.Lock = field(default_factory=threading.Lock)
    _stopping: bool = False
    _pipes: object = None
    _endpoint: object = None
    _dispatcher: object = None
    _service: object = None
    _service_done: threading.Event = field(default_factory=threading.Event)
    _cleanup_worker: object = None
    _rpc_ack_deadline: float = 0

    @property
    def invocation(self): return self._lifetime.invocation
    @property
    def pid(self): return self._lifetime.process.pid
    @property
    def acknowledged(self): return self._lifetime.acknowledged


class NativeCreativeController:
    """One fixed reviewed candidate; trusted caller supplies verified scope only.

    preflight is the server's existing owner/source/revision-checked grant issuer,
    never an HTTP-supplied function. The adapter's trusted post-redemption hook
    must call acknowledge_redeemed(invocation, lease) before a successful reply.
    Neither grant nor packet is kept in records, files, argv, environment or logs.
    """
    def __init__(self, candidate, grants, adapter, preflight, *, capacity=4, services=None):
        if (os.name != 'nt' or type(candidate) is not ReviewedCandidate
                or type(grants) is not CreativeHandoffs or type(adapter) is not NativeCreativeAdapter
                or adapter._grants is not grants or not callable(preflight)
                or not callable(adapter._on_redeemed)
                or inspect.iscoroutinefunction(preflight)
                or type(capacity) is not int or not 1 <= capacity <= 8):
            raise ValueError('Trusted fixed candidate, grant store, registry and preflight are required.')
        self._candidate = candidate
        if candidate.contract == PIPE_BOOTSTRAP_CONTRACT and services is None:
            raise ValueError('Pipe mode requires trusted screenplay services.')
        self._services = services
        self._grants, self._adapter, self._preflight = grants, adapter, preflight
        self._capacity = capacity
        self._records = {}
        self._retained_cleanup = {}
        self._retained_pipes = {}
        self._cleanup_failed = False
        self._pending = 0
        self._shutdown = False
        self._lock = threading.Lock()
        self._unpublished_cleanup_lock = threading.Lock()

    @classmethod
    def create(cls, candidate, grants, preflight, *, peer_resolver=None, capacity=4, services=None):
        """Trusted factory wires acknowledgement before any launch is possible."""
        controller = None
        def acknowledged(invocation, lease):
            if controller is None:
                raise NativeControllerError()
            return controller.acknowledge_redeemed(invocation, lease)
        adapter = NativeCreativeAdapter(grants, peer_resolver=peer_resolver,
            on_redeemed=acknowledged)
        controller = cls(candidate, grants, adapter, preflight, capacity=capacity, services=services)
        return controller

    @property
    def candidate(self): return self._candidate

    @property
    def adapter(self): return self._adapter

    @property
    def cleanup_failed(self):
        """Sticky metadata only; never claim cleanup succeeded after a failure."""
        with self._lock: return self._cleanup_failed

    def _close_unpublished(self, life, pins):
        # Multiple prune snapshots can contain the same retained resources.
        # Serialize CloseHandle attempts, including the map update, so a second
        # snapshot observes idempotently emptied resources rather than reuse.
        with self._unpublished_cleanup_lock:
            success = True
            for resource in (life, pins):
                if resource is not None:
                    try:
                        result = resource.close()
                        if resource is life and result.job_drained is False:
                            success = False
                    except Exception:
                        success = False
            with self._lock:
                key = (id(life), id(pins))
                if success:
                    self._retained_cleanup.pop(key, None)
                else:
                    self._cleanup_failed = True
                    self._retained_cleanup[key] = (life, pins)
            return success

    def launch(self, context, *, project, revision, source_sha256):
        """No argv/path/env/PID/token fields accepted at this boundary."""
        record = None; pins = None; life = None; pipes = None
        reserved = False; completed = False
        try:
            if (type(context) is not VerifiedFirebaseContext
                    or type(context.valid_until_monotonic) not in (int, float)
                    or not math.isfinite(context.valid_until_monotonic)
                    or context.valid_until_monotonic <= time.monotonic()):
                raise NativeControllerError()
            expected = CreativeScope(context.principal, project, revision, source_sha256, self.candidate.sha256)
            self.prune()
            with self._lock:
                if self._shutdown:
                    raise NativeControllerError()
                if len(self._records) + len(self._retained_cleanup) + len(self._retained_pipes) + self._pending >= self._capacity:
                    raise NativeControllerError()
                self._pending += 1
                reserved = True
            try:
                pins = _PinnedFiles(self.candidate)
                handles = None
                if self.candidate.contract == PIPE_BOOTSTRAP_CONTRACT:
                    pipes = CreativePipes()
                    handles = pipes.child_handles
                launch_options = {'pipes': pipes} if pipes is not None else {}
                life = NativeCreativeLifetime([self.candidate.executable.path, *self.candidate.arguments],
                    self.candidate.cwd, dict(self.candidate.environment), candidate_sha256=self.candidate.sha256,
                    revoke_invocation=self._grants.revoke_invocation, **launch_options)
                drains = (_Drain(life.process.stdout), _Drain(life.process.stderr))
                record = OwnedLaunch(self, life, pins, expected, drains)
                record._pipes = pipes
                with self._lock:
                    if self._shutdown:
                        raise NativeControllerError()
                    self._records[record.invocation] = record
                self._adapter.register(record.invocation)
                grant = self._preflight(context, record.invocation, self.candidate.sha256,
                    project_name=project, expected_revision=revision,
                    expected_source_sha256=source_sha256, grants=self._grants)
                if record._stopping or record._result is not None or not record.invocation.alive():
                    raise NativeControllerError()
                if type(grant) is not str or not re.fullmatch(r'nch_g_[A-Za-z0-9_-]{43}', grant):
                    raise NativeControllerError()
                payload = dict(version=1, grant=grant, project=project, revision=revision,
                    source_sha256=source_sha256, candidate_sha256=self.candidate.sha256)
                if pipes is not None:
                    record._endpoint = PipeEndpoint(*pipes.parent_fds, receive_timeout_limit=300)
                    record._dispatcher = CreativeDispatch(self._adapter, record.invocation, self._services)
                    payload = dict(version=2, bootstrap=payload,
                        channel=dict(read_handle=handles[0], write_handle=handles[1]))
                packet = json.dumps(payload,
                    separators=(',', ':'), ensure_ascii=False).encode('utf-8')
                if not 0 < len(packet) <= MAX_PACKET:
                    raise NativeControllerError()
                if pipes is not None:
                    self._start_pipe_service(record)
                self._deliver(record, packet)
                del grant, packet, payload
                if not record._delivery.wait(DELIVERY_SECONDS) or not record._delivery_ok:
                    raise NativeControllerError()
                def expire():
                    if not record._acked.wait(ACK_SECONDS):
                        try: self.close(record)
                        except Exception: record._failed = True
                threading.Thread(target=expire, name='native-handoff-deadline', daemon=True).start()
                completed = True
                return record
            finally:
                if completed:
                    with self._lock:
                        self._pending -= 1
                    reserved = False
        except BaseException as error:
            if record is not None:
                # Preflight may finish AFTER a concurrent close/prune revoked
                # its earlier state. Revoke any newly issued pending authority
                # even when close(record) already has a cached result.
                try: self._grants.revoke_invocation(record.invocation)
                except Exception:
                    with self._lock: self._cleanup_failed = True
                try: self.close(record)
                except Exception: record._failed = True
            else:
                self._close_unpublished(life, pins)
                if pipes is not None:
                    self._close_unpublished_pipes(pipes)
            if reserved:
                # Retain failure resources before freeing their reservation.
                with self._lock:
                    self._pending -= 1
            if not isinstance(error, Exception):
                raise
            raise NativeControllerError() from None

    @staticmethod
    def _deliver(record, packet):
        def write():
            stream = record._lifetime.process.stdin
            try:
                record._delivery_ok = stream.write(packet) == len(packet)
            except (OSError, ValueError, AttributeError):
                record._delivery_ok = False
            finally:
                try: stream.close()
                except (OSError, ValueError, AttributeError): record._delivery_ok = False
                record._delivery.set()
        record._writer = threading.Thread(target=write, name='native-bootstrap-delivery', daemon=True)
        record._writer.start()

    def acknowledge_redeemed(self, invocation, lease):
        """Trusted registry hook only, after one-use redemption; no unregister here.

        Store authorization proves a redeemed lease and exact scope. Output EOF
        proves the child closed both inherited output pipes before disarming the
        job. Lock order avoids calling the registry from inside lifetime.close.
        """
        try:
            with self._lock:
                if self._shutdown:
                    raise NativeControllerError()
                record = self._records.get(invocation)
            if record is None or record._failed or record._result is not None:
                raise NativeControllerError()
            deadline = time.monotonic() + DELIVERY_SECONDS
            if not record._delivery.wait(max(0, deadline-time.monotonic())) or not record._delivery_ok:
                raise NativeControllerError()
            for drain in record._drains:
                if not drain.done.wait(max(0, deadline-time.monotonic())) or drain.failed:
                    raise NativeControllerError()
            with record._transition:
                if self._shutdown or record._stopping:
                    raise NativeControllerError()
                authorized = self._grants.authorize(lease, invocation,
                    project=record._expected.project, operation='read')
                if authorized != record._expected:
                    raise NativeControllerError()
                record._lifetime.acknowledge_handoff(invocation)
                record._acked.set()
        except Exception:
            # The registry owns removal/revocation while its redeem lock is held.
            # A close here could recursively acquire that lock and destroy a GUI.
            raise NativeControllerError() from None

    def close(self, record):
        if type(record) is not OwnedLaunch or record._controller is not self:
            raise NativeControllerError()
        with record._closing:
            if record._result is not None:
                return record._result
            with record._transition:
                record._stopping = True
            if record._pipes is not None:
                self._drain_pipe_resources(record)
            result = record._lifetime.close()  # Revoke store FIRST; no registry lock.
            self._adapter.unregister(record.invocation)
            for worker in (record._writer, *(d.thread for d in record._drains)):
                if worker is not None:
                    worker.join(timeout=3)
                    if worker.is_alive():
                        record._failed = True
                        raise NativeControllerError()
            record._pins.close()
            record._result = result
            record._acked.set()  # End the pre-ack deadline after any explicit close.
            with self._lock:
                self._records.pop(record.invocation, None)
            if result.job_drained is False:
                raise NativeControllerError()
            return result

    def _drain_pipe_resources(self, record):
        try:
            self._grants.revoke_invocation(record.invocation)
            if record._endpoint is not None and not record._endpoint.close():
                record._failed = True
                raise NativeControllerError()
            if record._service is not None:
                if record._service is threading.current_thread():
                    record._failed = True
                    raise NativeControllerError()
                record._service.join(timeout=3)
                if record._service.is_alive():
                    record._failed = True
                    raise NativeControllerError()
            if record._dispatcher is not None:
                record._dispatcher.close()
            record._pipes.close()
        except Exception:
            record._failed = True
            with self._lock:
                self._cleanup_failed = True
            raise NativeControllerError() from None

    def shutdown(self):
        """Stop admissions and revoke/drain only this controller's resources.

        Acknowledged editors retain their independent lifetime. Incomplete
        cleanup remains retained and is reported for an explicit later retry.
        """
        with self._lock:
            self._shutdown = True
            records = tuple(self._records.values())
            retained = tuple(self._retained_cleanup.values())
            retained_pipes = tuple(self._retained_pipes.values())
        for record in records:
            try:
                self.close(record)
            except Exception:
                with self._lock:
                    self._cleanup_failed = True
        for life, pins in retained:
            self._close_unpublished(life, pins)
        for pipes in retained_pipes:
            self._close_unpublished_pipes(pipes)
        with self._lock:
            remaining = len(self._records) + len(self._retained_cleanup) + len(self._retained_pipes)
            return {'complete': remaining == 0 and self._pending == 0,
                    'retained_resources': remaining, 'pending_launches': self._pending,
                    'cleanup_failure_observed': self._cleanup_failed}

    def prune(self):
        with self._lock:
            records = tuple(self._records.values())
            retained = tuple(self._retained_cleanup.values())
            retained_pipes = tuple(self._retained_pipes.values())
        for life, pins in retained:
            self._close_unpublished(life, pins)
        for pipes in retained_pipes:
            self._close_unpublished_pipes(pipes)
        for record in records:
            if record._failed or not record.invocation.alive():
                self.close(record)

    def _close_unpublished_pipes(self, pipes):
        with self._unpublished_cleanup_lock:
            try:
                pipes.close()
            except Exception:
                with self._lock:
                    self._cleanup_failed = True
                    self._retained_pipes[id(pipes)] = pipes
                return False
            with self._lock:
                self._retained_pipes.pop(id(pipes), None)
            return True

    def _start_pipe_service(self, record):
        record._rpc_ack_deadline = time.monotonic() + ACK_SECONDS + DELIVERY_SECONDS
        def service():
            try:
                while not record._stopping:
                    lease = record._dispatcher._lease
                    if lease is None:
                        remaining = record._rpc_ack_deadline - time.monotonic()
                    else:
                        scope, remaining = self._grants.authorize_with_lifetime(lease,
                            record.invocation, project=record._expected.project, operation='read')
                        if scope != record._expected or not record.invocation.alive():
                            raise NativeControllerError()
                    if not 0 < remaining <= 300:
                        raise NativeControllerError()
                    request = record._endpoint.receive(timeout=remaining)
                    response = record._dispatcher.dispatch(request)
                    record._endpoint.send(response, timeout=10)
            except BaseException:
                record._failed = True
            finally:
                self._grants.revoke_invocation(record.invocation)
                record._service_done.set()
                # Never join this service from itself. The owned record remains
                # registered/counted until the separate cleanup completes.
                def cleanup():
                    try:
                        self.close(record)
                    except Exception:
                        record._failed = True
                        with self._lock:
                            self._cleanup_failed = True
                record._cleanup_worker = threading.Thread(target=cleanup,
                    name='native-pipe-cleanup', daemon=True)
                record._cleanup_worker.start()
        record._service = threading.Thread(target=service, name='native-pipe-service', daemon=True)
        record._service.start()
