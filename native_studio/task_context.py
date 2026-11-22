"""Opt-in bounded task events over EngineBus; no pool or authority of its own.

Bindings are caller-provided freshness fences, never authentication or write
permission. Only cooperative, JSON-input/output callables opt into this adapter.
Terminal delivery waits for the existing global pool barrier, which can delay a
completed task behind unrelated legacy work. Threads are never forcibly killed.
"""
from collections import deque
from dataclasses import asdict, dataclass, field
import inspect
import json
import math
import re
import threading
import time
import uuid
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

MAX_PAYLOAD = 65536
STAGES = frozenset(('queued', 'reading', 'parsing', 'processing', 'complete'))


def _json_bytes(value):
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > 4096 or depth > 32:
            raise ValueError('Task payload structure exceeds its bound')
        kind = type(item)
        if kind is dict:
            if len(item) > 4096 or any(type(key) is not str for key in item):
                raise ValueError('JSON object keys must be strings')
            stack.extend((part, depth + 1) for pair in item.items() for part in pair)
        elif kind in (list, tuple):
            if len(item) > 4096:
                raise ValueError('Task array exceeds its bound')
            stack.extend((part, depth + 1) for part in item)
        elif kind is str:
            if len(item) > MAX_PAYLOAD:
                raise ValueError('Task string exceeds its bound')
        elif kind not in (type(None), bool, int, float):
            raise ValueError('Only JSON task payloads are supported')
    raw = json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(',', ':')).encode('utf-8')
    if len(raw) > MAX_PAYLOAD:
        raise ValueError('Task payload exceeds its bound')
    return raw


@dataclass(frozen=True)
class Binding:
    workspace: str
    owner: str
    generation: int
    revision_sha256: str
    operation: str
    resource: str = 'io'

    def __post_init__(self):
        for value in (self.workspace, self.owner, self.operation):
            if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
                raise ValueError('Opaque bounded task identity required')
        if type(self.generation) is not int or not 0 <= self.generation <= 2**53 - 1:
            raise ValueError('Bounded task generation required')
        if type(self.revision_sha256) is not str or not re.fullmatch(r'[a-f0-9]{64}', self.revision_sha256):
            raise ValueError('Expected revision digest required')
        if self.resource not in ('io', 'cpu'):
            raise ValueError('Provider/GPU admission is outside this adapter')


class _Stop(Exception):
    def __init__(self, reason):
        self.reason = reason


@dataclass
class _Job:
    task_id: str
    binding: Binding
    deadline: float
    stop: threading.Event = field(default_factory=threading.Event)
    lock: object = field(default_factory=threading.Lock)
    reason: str | None = None
    outcome: tuple | None = None
    progress: dict | None = None
    sequence: int = 0
    sent_sequence: int = 0
    last_progress: float = 0
    started: bool = False
    task: object = None


class WorkContext:
    def __init__(self, adapter, job):
        self._adapter, self._job = adapter, job

    @property
    def task_id(self):
        return self._job.task_id

    @property
    def binding(self):
        return self._job.binding

    @property
    def cancel_event(self):
        return self._job.stop

    def check_cancelled(self):
        reason = self._adapter._reason(self._job)
        if reason:
            raise _Stop(reason)

    def progress(self, stage, completed, total=None):
        self.check_cancelled()
        if (stage not in STAGES or type(completed) is not int or not 0 <= completed <= 10**9
                or total is not None and (type(total) is not int or not completed <= total <= 10**9)):
            raise ValueError('Bounded progress units required')
        job = self._job
        with job.lock:
            old = job.progress
            if old and old['stage'] == stage and (completed < old['completed'] or total != old['total']):
                raise ValueError('Progress cannot regress within its stage')
            job.sequence += 1
            job.progress = {'sequence': job.sequence, 'stage': stage, 'completed': completed, 'total': total}


class TaskContextAdapter(QObject):
    # Immutable JSON bytes prevent a receiver from mutating another's event.
    task_event = pyqtSignal(bytes)
    drained = pyqtSignal()

    def __init__(self, bus):
        super().__init__(bus)
        self.bus = bus
        self._bindings = {}
        self._binding_lock = threading.Lock()
        self._jobs = {}
        self._history = deque(maxlen=64)
        self._closed = False
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)
        bus.drained.connect(self._tick)

    def _gui(self):
        if QThread.currentThread() is not self.thread():
            raise RuntimeError('Task context controls belong to the GUI thread')

    def bind(self, binding):
        self._gui()
        if type(binding) is not Binding or self._closed:
            raise ValueError('Open adapter and validated binding required')
        with self._binding_lock:
            old = self._bindings.get(binding.workspace)
            if old and (binding.generation < old.generation or
                        binding.generation == old.generation and self._fence(binding) != self._fence(old)):
                raise ValueError('A changed workspace binding needs a newer generation')
            if binding.workspace not in self._bindings and len(self._bindings) >= 128:
                raise ValueError('Workspace binding limit reached')
            self._bindings[binding.workspace] = binding

    @staticmethod
    def _fence(binding):
        return (binding.owner, binding.generation, binding.revision_sha256)

    def _current(self, binding):
        with self._binding_lock:
            current = self._bindings.get(binding.workspace)
            return current is not None and self._fence(current) == self._fence(binding)

    def _reason(self, job, *, deadline=True):
        with job.lock:
            reason = job.reason
        if reason:
            return reason
        if job.task is not None and job.task.cancel_event.is_set():
            return 'cancelled'
        if not self._current(job.binding):
            return 'superseded'
        if deadline and time.monotonic() >= job.deadline:
            return 'timed_out'
        if job.stop.is_set():
            return 'cancelled'
        return None

    def submit(self, binding, fn, *args, deadline_seconds=60, **kwargs):
        self._gui()
        if (self._closed or len(self._jobs) >= 128 or type(binding) is not Binding
                or not self._current(binding)):
            raise ValueError('Current bound context and available task slot required')
        if (type(deadline_seconds) not in (int, float) or not math.isfinite(deadline_seconds)
                or not 0 < deadline_seconds <= 3600):
            raise ValueError('Bounded deadline required')
        signature = inspect.signature(fn)
        parameter = signature.parameters.get('task_context')
        if (parameter is None or parameter.kind not in (parameter.KEYWORD_ONLY, parameter.POSITIONAL_OR_KEYWORD)
                or 'task_context' in kwargs):
            raise ValueError('Callable must explicitly opt into task_context')
        signature.bind(*args, task_context=None, **kwargs)
        packed = _json_bytes({'args': args, 'kwargs': kwargs})
        job = _Job(uuid.uuid4().hex, binding, time.monotonic() + deadline_seconds)
        context = WorkContext(self, job)

        def work():
            outcome = ('failed', {'type': 'Exception'})
            try:
                context.check_cancelled()
                with job.lock:
                    job.started = True
                payload = json.loads(packed)
                value = fn(*payload['args'], task_context=context, **payload['kwargs'])
                context.check_cancelled()
                outcome = ('succeeded', _json_bytes(value))
            except _Stop as error:
                outcome = (error.reason, None)
            except BaseException as error:
                # No raw message, traceback, locals or source in public events.
                name = type(error).__name__
                outcome = ('failed', {'type': name if name in ('ValueError', 'TypeError', 'OSError', 'RuntimeError', 'RecursionError') else 'Exception'})
            finally:
                with job.lock:
                    job.outcome = outcome

        self._jobs[job.task_id] = job
        try:
            job.task = self.bus.submit(work)
        except Exception:
            del self._jobs[job.task_id]
            raise
        self._timer.start()
        return job.task_id

    def cancel(self, task_id):
        self._gui()
        job = self._jobs.get(task_id)
        if job is None:
            return False
        with job.lock:
            job.reason = 'cancelled'
            job.stop.set()
        return True

    def shutdown(self):
        self._gui()
        self._closed = True
        for task_id in tuple(self._jobs):
            self.cancel(task_id)
        self._tick()

    @property
    def is_drained(self):
        return not self._jobs

    def snapshot(self):
        self._gui()
        return {'closed': self._closed, 'active': len(self._jobs), 'retained_terminals': list(self._history)}

    def _emit(self, job, kind, data):
        if not self._closed:
            self.task_event.emit(json.dumps({'schema': 1, 'task_id': job.task_id,
                'binding': asdict(job.binding), 'kind': kind, 'data': data},
                allow_nan=False, separators=(',', ':')).encode('utf-8'))

    @pyqtSlot()
    def _tick(self):
        self._gui()
        joined = self.bus.pool.waitForDone(0)
        had_jobs = bool(self._jobs)
        for job in tuple(self._jobs.values()):
            with job.lock:
                outcome = job.outcome
            reason = self._reason(job, deadline=outcome is None)
            if reason:
                with job.lock:
                    job.reason = reason
                    job.stop.set()
            if outcome is None and (self.bus.is_drained or
                    reason == 'cancelled' and job.task is not None
                    and job.task.cancel_event.is_set() and self.bus.active_count == 0 and joined):
                outcome = ('cancelled', None)  # queued work withdrawn by bus shutdown
            if not reason:
                with job.lock:
                    progress = dict(job.progress) if job.progress else None
                if (progress and progress['sequence'] > job.sent_sequence
                        and time.monotonic() - job.last_progress >= .1):
                    job.sent_sequence = progress['sequence']
                    job.last_progress = time.monotonic()
                    self._emit(job, 'progress', progress)
            if outcome is None or not joined:
                continue
            state, payload = outcome
            state = reason or state
            del self._jobs[job.task_id]
            self._history.append({'task_id': job.task_id, 'status': state})
            if state == 'succeeded':
                self._emit(job, 'result', json.loads(payload))
            elif state == 'failed':
                self._emit(job, 'error', {**payload, 'message': 'Background task failed; no result was applied.'})
            self._emit(job, 'finished', {'status': state, 'native_pool_joined': True})
            job.task = None
        if not self._jobs:
            self._timer.stop()
            if had_jobs:
                self.drained.emit()
