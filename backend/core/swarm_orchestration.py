"""Opt-in task admission and end-state ownership auditing, not an OS sandbox.

No executor, GPU reservation, process launch or database connection is created here.
Use a bounded isolated workspace: shared-account tasks can bypass this API, and
end-state hashes cannot detect a transient write restored before the final audit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import threading
import time
from typing import Sequence

ROLES = ('lead_orchestrator', 'test_runner', 'frontend_ui_worker',
         'native_ui_worker', 'database_state_worker')
MIB = 1024 * 1024


class AdmissionError(RuntimeError):
    pass


class OwnershipViolation(AdmissionError):
    pass


@dataclass(frozen=True)
class Policy:
    max_active_agents: int = 4
    max_active_workers: int = 3
    max_local_gpu_jobs: int = 1
    gpu_advisory_budget_bytes: int = 20 * 1024**3
    gpu_headroom_bytes: int = 4 * 1024**3
    failure_threshold: int = 2
    max_snapshot_entries: int = 20000
    max_snapshot_bytes: int = 512 * 1024**2

    def __post_init__(self):
        for key, value in self.__dict__.items():
            if type(value) is not int or value <= 0:
                raise ValueError('Policy values must be positive integers: ' + key)
        if self.max_active_agents > 4 or self.max_active_workers > 3:
            raise ValueError('This client permits at most four agents and three workers')
        if self.max_active_workers >= self.max_active_agents or self.max_local_gpu_jobs != 1:
            raise ValueError('Reserve the lead slot; one local GPU job is supported')
        if self.failure_threshold != 2:
            raise ValueError('The two-strike threshold is fixed')


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate configuration key: ' + key)
        obj[key] = value
    return obj


def _keys(obj, expected):
    if type(obj) is not dict or set(obj) != set(expected):
        raise ValueError('Unexpected configuration fields')


def load_policy(path) -> Policy:
    """Validate the exact inert configuration schema without touching databases."""
    raw = Path(path).read_bytes()
    if len(raw) > 65536:
        raise ValueError('Configuration exceeds bound')
    value = json.loads(raw, object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite number')))
    _keys(value, ('schema_version', 'source_baseline', 'classification', 'activation',
                  'roles', 'admission', 'databases', 'sqlite', 'enforcement'))
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Unsupported schema')
    if value['source_baseline'] != '5.329.146' or value['classification'] != 'SOURCE_IMPLEMENTED_LIVE_ACTIVATION_PENDING':
        raise ValueError('Unexpected baseline/classification')
    _keys(value['activation'], ('automatic_start', 'live_database_changes', 'provider_calls'))
    if any(type(v) is not bool for v in value['activation'].values()):
        raise ValueError('Activation flags must be booleans')
    if value['activation']['provider_calls']:
        raise ValueError('Provider calls must remain explicitly disabled')
    if value['roles'] != list(ROLES):
        raise ValueError('Expected five logical roles')
    _keys(value['admission'], Policy.__dataclass_fields__)
    policy = Policy(**value['admission'])
    _keys(value['databases'], ('master', 'cdz_audit'))
    if value['databases'] != {'master': 'C:/AI-BS/backend/aibs_master.db',
                              'cdz_audit': 'C:/AI-BS/database/aibs_master.db'}:
        raise ValueError('Database identities must remain distinct')
    expected_sqlite = {'journal_mode': 'WAL', 'synchronous': 'FULL', 'busy_timeout_ms': 10000,
                       'cache_size_kib': 8192, 'mmap_size_bytes': 0,
                       'wal_autocheckpoint_pages': 1000,
                       'max_read_connections_per_database': 8,
                       'max_concurrent_writers_per_database': 1}
    _keys(value['sqlite'], expected_sqlite)
    if any(type(value['sqlite'][k]) is not type(v) or value['sqlite'][k] != v for k, v in expected_sqlite.items()):
        raise ValueError('Unexpected authoritative database defaults')
    expected_enforcement = {'exact_task_paths': True, 'same_account_not_os_sandbox': True,
                            'gpu_budget_is_advisory': True, 'cpu_affinity_enforced': False,
                            'cross_boundary_action': 'stop_admission_and_cooperative_cancel'}
    _keys(value['enforcement'], expected_enforcement)
    if any(type(value['enforcement'][k]) is not type(v) or value['enforcement'][k] != v for k, v in expected_enforcement.items()):
        raise ValueError('Invalid enforcement claims')
    return policy


@dataclass(eq=False, frozen=True)
class Lease:
    task_id: str
    role: str
    paths: tuple[str, ...]
    operation: str
    gpu_required_bytes: int | None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _before: dict = field(default_factory=dict, repr=False)
    _peer_paths: set = field(default_factory=set, repr=False)


class SwarmRegistry:
    """Thread-safe admission adapter for existing schedulers; leases own no threads."""

    def __init__(self, workspace, policy: Policy | None = None):
        raw = Path(workspace).absolute()
        self.policy = policy or Policy()
        self._reject_redirects(raw)
        self.workspace = raw.resolve(strict=True)
        if not self.workspace.is_dir() or self.workspace.parent == self.workspace:
            raise ValueError('A non-root workspace directory is required')
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._active = {}
        self._paused = self._stopping = False
        self._failures = {}

    @staticmethod
    def _reject_redirects(path):
        for part in (path, *path.parents):
            try:
                info = part.lstat()
            except FileNotFoundError:
                continue
            if part.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise OwnershipViolation('Redirected path rejected')
            if part.is_file() and info.st_nlink != 1:
                raise OwnershipViolation('Hard-linked file rejected')

    def _path(self, name):
        if type(name) is not str or not name or '\\' in name or ':' in name:
            raise OwnershipViolation('Use an exact relative forward-slash path')
        p = Path(name)
        parts = name.split('/')
        reserved = {'con', 'prn', 'aux', 'nul', *('com' + str(n) for n in range(1, 10)), *('lpt' + str(n) for n in range(1, 10))}
        if p.is_absolute() or PureWindowsPath(name).is_absolute() or any(x.casefold() in {'', '.', '..', '.git'} or x.split('.')[0].casefold() in reserved or x.endswith((' ', '.')) for x in parts) or any(x in name for x in '*?[]'):
            raise OwnershipViolation('Unsafe or non-exact path')
        if p.suffix.lower() in {'.db', '.sqlite', '.sqlite3'} or name.lower().endswith(('-wal', '-shm')):
            raise OwnershipViolation('Database files are owned by service interfaces')
        target = self.workspace / p
        self._reject_redirects(target)
        if not target.resolve().is_relative_to(self.workspace):
            raise OwnershipViolation('Path escapes workspace')
        if target.is_dir():
            raise OwnershipViolation('Directory ownership is not supported')
        return p.as_posix().casefold() if os.name == 'nt' else p.as_posix()

    def _snapshot(self):
        result, total = {}, 0
        for base, dirs, files in os.walk(self.workspace, followlinks=False):
            for name in dirs + files:
                path = Path(base) / name
                self._reject_redirects(path)
                info = path.lstat()
                key = path.relative_to(self.workspace).as_posix()
                if os.name == 'nt':
                    key = key.casefold()
                if len(result) >= self.policy.max_snapshot_entries:
                    raise AdmissionError('Workspace snapshot entry budget exceeded')
                if path.is_dir():
                    result[key] = ('directory',)
                elif path.is_file():
                    total += info.st_size
                    if total > self.policy.max_snapshot_bytes:
                        raise AdmissionError('Workspace snapshot byte budget exceeded')
                    with path.open('rb') as source:
                        digest = hashlib.file_digest(source, 'sha256').hexdigest()
                    after = path.stat()
                    if (info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
                        raise AdmissionError('Workspace changed during snapshot')
                    result[key] = ('file', digest)
                else:
                    raise OwnershipViolation('Unsupported filesystem object')
        return result

    def acquire(self, task_id, role, paths: Sequence[str], operation=None,
                gpu_required_bytes=None, free_vram_bytes=None, cancel_event=None) -> Lease:
        with self._lock:
            if cancel_event is not None and not isinstance(cancel_event, threading.Event):
                raise AdmissionError('A threading.Event cancellation signal is required')
            event = cancel_event if cancel_event is not None else threading.Event()
            if event.is_set():
                raise AdmissionError('Task cancelled before admission')
            if self._paused or self._stopping:
                raise AdmissionError('Admission paused or shutting down')
            if type(task_id) is not str or not task_id or task_id in self._active or role not in ROLES:
                raise AdmissionError('Invalid or duplicate task identity')
            operation = operation or task_id
            if type(operation) is not str or not operation:
                raise AdmissionError('Invalid operation identity')
            if self._failures.get(operation, (None, 0))[1] >= self.policy.failure_threshold:
                raise AdmissionError('Operation halted by two-strike circuit breaker')
            if len(self._active) >= self.policy.max_active_agents:
                raise AdmissionError('Agent capacity reached')
            if role == 'lead_orchestrator' and any(l.role == role for l in self._active.values()):
                raise AdmissionError('Only one lead is permitted')
            if role != 'lead_orchestrator' and sum(l.role != 'lead_orchestrator' for l in self._active.values()) >= self.policy.max_active_workers:
                raise AdmissionError('Worker capacity reached')
            if isinstance(paths, (str, bytes)):
                raise OwnershipViolation('Path sequence required')
            exact = tuple(self._path(p) for p in paths)
            if len(exact) != len(set(exact)):
                raise OwnershipViolation('Duplicate task paths')
            if any(set(exact) & set(l.paths) for l in self._active.values()):
                raise OwnershipViolation('Another task owns a requested path')
            if gpu_required_bytes is not None:
                if type(gpu_required_bytes) is not int or gpu_required_bytes <= 0 or type(free_vram_bytes) is not int:
                    raise AdmissionError('Measured model requirement and observed free VRAM required')
                if (gpu_required_bytes > self.policy.gpu_advisory_budget_bytes or
                    free_vram_bytes < gpu_required_bytes + self.policy.gpu_headroom_bytes or
                    any(l.gpu_required_bytes is not None for l in self._active.values())):
                    raise AdmissionError('Local GPU admission unavailable')
            before = self._snapshot()
            if event.is_set():
                raise AdmissionError('Task cancelled during admission')
            lease = Lease(task_id, role, exact, operation, gpu_required_bytes,
                          cancel_event=event, _before=before)
            for peer in self._active.values():
                peer._peer_paths.update(exact)
                lease._peer_paths.update(peer.paths)
            self._active[task_id] = lease
            return lease

    def check(self, lease):
        with self._lock:
            if self._active.get(lease.task_id) is not lease or lease.cancel_event.is_set() or self._stopping:
                raise AdmissionError('Task retired, cancelled or stopped')
            for path in lease.paths:
                self._path(path)
            return True

    def finish(self, lease, error_identity=None):
        with self._condition:
            if self._active.get(lease.task_id) is not lease:
                raise AdmissionError('Unknown task lease')
            failure = error_identity
            try:
                after = self._snapshot()
                changed = {p for p in lease._before.keys() | after.keys() if lease._before.get(p) != after.get(p)}
                # Other active tasks own disjoint files and may legitimately change them.
                allowed = set(lease.paths) | lease._peer_paths
                allowed_dirs = {parent.as_posix() for p in allowed for parent in Path(p).parents if parent.as_posix() != '.'}
                bad = {p for p in changed if p not in allowed and not (p in allowed_dirs and after.get(p, lease._before.get(p)) == ('directory',))}
                if bad:
                    raise OwnershipViolation('Unowned resulting changes: ' + ', '.join(sorted(bad)[:8]))
                return tuple(sorted(changed & set(lease.paths)))
            except (OwnershipViolation, AdmissionError, OSError) as error:
                failure = type(error).__name__
                self._stopping = True
                for active in self._active.values():
                    # Preserve delivery of the failing task's audit exception.
                    # Existing EngineBus suppresses callbacks for cancelled jobs.
                    if active is not lease:
                        active.cancel_event.set()
                raise
            finally:
                self._active.pop(lease.task_id, None)
                if failure is None and not lease.cancel_event.is_set():
                    self._failures.pop(lease.operation, None)
                elif failure is not None:
                    previous, count = self._failures.get(lease.operation, (None, 0))
                    self._failures[lease.operation] = (str(failure), count + 1 if previous == str(failure) else 1)
                self._condition.notify_all()

    def cancel(self, task_id):
        with self._lock:
            if task_id in self._active:
                self._active[task_id].cancel_event.set()

    def pause(self):
        with self._lock:
            self._paused = True

    def resume(self):
        with self._lock:
            if self._stopping:
                raise AdmissionError('Registry is shutting down')
            self._paused = False

    def request_shutdown(self):
        with self._lock:
            self._stopping = True
            for lease in self._active.values():
                lease.cancel_event.set()

    def is_drained(self):
        with self._lock:
            return not self._active

    def drain(self, timeout=0):
        deadline = time.monotonic() + max(0, timeout)
        with self._condition:
            while self._active:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def snapshot(self):
        with self._lock:
            return {'active': len(self._active), 'workers': sum(l.role != 'lead_orchestrator' for l in self._active.values()),
                    'paused': self._paused, 'stopping': self._stopping,
                    'local_gpu_jobs': sum(l.gpu_required_bytes is not None for l in self._active.values()),
                    'enforcement': 'cooperative admission and bounded end-state audit; not an OS sandbox'}
