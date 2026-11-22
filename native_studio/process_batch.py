"""Native admission controls for trusted, registered local process jobs.

This is a process lifetime boundary, not a filesystem/network sandbox. No shell,
provider, source-edit or application action is selected by this module. Windows
children enter an existing kill-on-close JobObject before their first instruction.
The GUI never waits for native process or pipe drains.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import math
import os
from pathlib import Path
import queue
import threading
import time

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal


@dataclass(frozen=True)
class BatchLimits:
    workers: int = 1
    batch_size: int = 8
    start_interval_ms: int = 100
    batch_cooldown_ms: int = 250
    max_jobs: int = 512
    output_limit_bytes: int = 65536

    def __post_init__(self):
        bounds = {'workers': (1, 8), 'batch_size': (1, 128),
                  'start_interval_ms': (0, 3600000), 'batch_cooldown_ms': (0, 3600000),
                  'max_jobs': (1, 4096), 'output_limit_bytes': (1024, 1048576)}
        for name, (lower, upper) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(f'{name} is outside its bounded range')


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    executable: str
    arguments: tuple[str, ...]
    cwd: str
    timeout_seconds: float = 60
    environment: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if (not isinstance(self.job_id, str) or not self.job_id or len(self.job_id) > 128
                or any(ord(c) < 32 for c in self.job_id)):
            raise ValueError('A bounded job identifier is required')
        if not Path(self.executable).is_absolute() or not Path(self.executable).is_file():
            raise ValueError('An existing absolute executable is required')
        if not Path(self.cwd).is_absolute() or not Path(self.cwd).is_dir():
            raise ValueError('An existing absolute working directory is required')
        if (type(self.arguments) is not tuple or len(self.arguments) > 256
                or any(not isinstance(arg, str) or '\0' in arg for arg in self.arguments)
                or sum(map(len, self.arguments)) > 30000):
            raise ValueError('A bounded explicit argument tuple is required')
        if (type(self.timeout_seconds) not in (int, float)
                or not math.isfinite(self.timeout_seconds) or not 0 < self.timeout_seconds <= 3600):
            raise ValueError('A finite bounded job deadline is required')
        if type(self.environment) is not tuple or len(self.environment) > 128:
            raise ValueError('Bounded environment overrides are required')
        for item in self.environment:
            if (type(item) is not tuple or len(item) != 2
                    or any(not isinstance(x, str) or '\0' in x for x in item)
                    or not item[0] or '=' in item[0]):
                raise ValueError('Invalid environment override')
        if sum(len(key) + len(value) for key, value in self.environment) > 131072:
            raise ValueError('Environment overrides exceed their bounded size')


class ProcessBatchController(QObject):
    changed = pyqtSignal(object)
    job_event = pyqtSignal(object)
    log = pyqtSignal(str)
    drained = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.limits = BatchLimits()
        self._pending = deque()
        self._active = {}
        self._rows = {}
        self._updates = queue.Queue(maxsize=8192)
        self._paused = False
        self._closing = False
        self._next_start = 0.0
        self._batch_started = 0
        self._batch_wait = False
        self._last_drained = True
        self._drain_failed = False
        self._failure_halted = False
        self._last_error_code = None
        self._same_error_count = 0
        self._timer = QTimer(self)
        self._timer.setInterval(15)
        self._timer.timeout.connect(self._tick)

    def _gui(self):
        if QThread.currentThread() is not self.thread():
            raise RuntimeError('Batch controls must run on their owning GUI thread')

    @property
    def is_drained(self):
        return not self._pending and not self._active and not self._drain_failed

    def snapshot(self):
        return {'limits': asdict(self.limits), 'paused': self._paused,
                'closing': self._closing, 'queued': len(self._pending),
                'running': len(self._active), 'is_drained': self.is_drained,
                'drain_failed': self._drain_failed,
                'failure_halted': self._failure_halted,
                'last_error_code': self._last_error_code,
                'same_error_count': self._same_error_count,
                'jobs': [dict(row) for row in self._rows.values()]}

    def _changed(self):
        self.changed.emit(self.snapshot())

    def configure(self, limits):
        self._gui()
        if type(limits) is not BatchLimits:
            raise ValueError('Validated BatchLimits required')
        self.limits = limits
        # A reduced cap only affects future admission, never active children.
        self._changed()

    def submit(self, jobs):
        self._gui()
        if self._closing or not self.is_drained:
            raise RuntimeError('The previous batch must drain before submission')
        if self._failure_halted:
            raise RuntimeError('Repeated failure halted this queue; diagnose and reset before starting another batch')
        if type(jobs) not in (list, tuple) or not 1 <= len(jobs) <= self.limits.max_jobs:
            raise ValueError('A bounded nonempty job batch is required')
        if any(type(job) is not JobSpec for job in jobs) or len({j.job_id for j in jobs}) != len(jobs):
            raise ValueError('Unique registered job specifications required')
        if os.name != 'nt':
            raise RuntimeError('This contained native process runner requires Windows')
        self._pending = deque(jobs)
        self._rows = {j.job_id: {'job_id': j.job_id, 'state': 'queued', 'pid': None,
                                'output': '', 'output_bytes': 0, 'output_truncated': False}
                      for j in jobs}
        self._paused = False
        self._last_error_code = None
        self._same_error_count = 0
        self._batch_started = 0
        self._batch_wait = False
        self._next_start = 0.0
        self._last_drained = False
        self._timer.start()
        self._changed()

    def pause(self):
        self._gui()
        self._paused = True
        self._changed()

    def resume(self):
        self._gui()
        if not self._closing and not self._failure_halted:
            self._paused = False
            if not self.is_drained:
                self._timer.start()
        self._changed()

    def reset_failure_halt(self):
        self._gui()
        if self._active:
            raise RuntimeError('Wait for active owned jobs before resetting the failure halt')
        self._failure_halted = False
        self._last_error_code = None
        self._same_error_count = 0
        # Reset does not restart work. Resume remains an explicit control.
        self._changed()

    def cancel(self):
        self._gui()
        while self._pending:
            self._rows[self._pending.popleft().job_id]['state'] = 'cancelled'
        for state in self._active.values():
            state['cancel'].set()
        # MainWindow stops child timers before calling shutdown; restart here.
        self._timer.start()
        self._changed()

    def shutdown(self):
        self._gui()
        self._closing = True
        self.cancel()

    def _worker(self, spec, stop, output_limit):
        process = None
        readers = []
        chunks = []
        byte_count = 0
        retained = 0
        lock = threading.Lock()
        terminal = {'state': 'failed', 'exit_code': None, 'job_drained': False}

        def read(stream):
            nonlocal byte_count, retained
            while True:
                try:
                    data = stream.read(4096)
                except (OSError, ValueError):
                    break
                if not data:
                    break
                with lock:
                    byte_count += len(data)
                    room = max(0, output_limit - retained)
                    if room:
                        chunks.append(data[:room])
                        retained += min(room, len(data))

        try:
            from native_studio.owned_process import OwnedProcess
            if stop.is_set():
                terminal['state'] = 'cancelled'
                terminal['job_drained'] = True
                return
            environment = dict(os.environ)
            environment.update(spec.environment)
            process = OwnedProcess((spec.executable, *spec.arguments), spec.cwd, environment)
            process.stdin.close()
            process.stdin = None
            started = time.monotonic()
            self._updates.put(('started', spec.job_id, {'pid': process.pid, 'started_at': started}))
            for stream in (process.stdout, process.stderr):
                thread = threading.Thread(target=read, args=(stream,), daemon=False)
                readers.append(thread)
                thread.start()
            while True:
                code = process.poll()
                if code is not None:
                    terminal.update(state='passed' if code == 0 else 'failed', exit_code=code)
                    break
                if stop.is_set():
                    terminal['state'] = 'cancelled'
                    break
                if time.monotonic() - started >= spec.timeout_seconds:
                    terminal['state'] = 'timed_out'
                    break
                stop.wait(.02)
        except Exception as exc:
            # No command/environment/token details in public launch errors.
            terminal['error'] = type(exc).__name__
        finally:
            if process is not None:
                try:
                    terminal['job_drained'] = process.close()
                except Exception as exc:
                    terminal['error'] = type(exc).__name__
            for thread in readers:
                thread.join()
            if not terminal['job_drained'] and process is not None:
                terminal['state'] = 'cleanup_failed'
            terminal.update(finished_at=time.monotonic(), output=b''.join(chunks).decode('utf-8', 'replace'),
                            output_bytes=byte_count, output_truncated=byte_count > output_limit)
            self._updates.put(('finished', spec.job_id, terminal))

    def _tick(self):
        while True:
            try:
                kind, job_id, data = self._updates.get_nowait()
            except queue.Empty:
                break
            row = self._rows[job_id]
            row.update(data)
            if kind == 'finished' and data.get('state') == 'cleanup_failed':
                # Failed cleanup is not proof of drain. Retain the UI/evidence;
                # do not authorize destruction or launch a replacement batch.
                self._drain_failed = True
            if kind == 'started':
                row['state'] = 'running'
            elif kind == 'finished' and not self._failure_halted:
                code = data.get('exit_code')
                if data.get('state') == 'passed':
                    self._last_error_code = None
                    self._same_error_count = 0
                elif data.get('state') == 'failed' and type(code) is int and code != 0:
                    self._same_error_count = self._same_error_count + 1 if code == self._last_error_code else 1
                    self._last_error_code = code
                    if self._same_error_count >= 2:
                        self._failure_halted = True
                        self._paused = True
                        self.log.emit(f'Batch halted after two consecutive failures with exit code {code}. Diagnose before resetting.')
            self.job_event.emit({'kind': kind, **dict(row)})
        for job_id, state in list(self._active.items()):
            if (not state['thread'].is_alive()
                    and self._rows[job_id]['state'] not in ('starting', 'running')):
                state['thread'].join(0)
                del self._active[job_id]
        now = time.monotonic()
        if self._batch_wait and not self._active:
            self._batch_wait = False
            self._batch_started = 0
            self._next_start = max(self._next_start, now + self.limits.batch_cooldown_ms / 1000)
        if (self._pending and not self._paused and not self._closing
                and not self._batch_wait and len(self._active) < self.limits.workers
                and now >= self._next_start):
            spec = self._pending.popleft()
            stop = threading.Event()
            thread = threading.Thread(target=self._worker,
                                      args=(spec, stop, self.limits.output_limit_bytes), daemon=False)
            self._rows[spec.job_id]['state'] = 'starting'
            self._rows[spec.job_id]['admitted_at'] = now
            self._active[spec.job_id] = {'thread': thread, 'cancel': stop}
            self._batch_started += 1
            self._next_start = now + self.limits.start_interval_ms / 1000
            if self._batch_started >= self.limits.batch_size:
                self._batch_wait = True
            try:
                thread.start()
            except RuntimeError as exc:
                del self._active[spec.job_id]
                self._rows[spec.job_id].update(state='failed', error=type(exc).__name__,
                                              job_drained=True, finished_at=time.monotonic())
        self._changed()
        if self.is_drained:
            self._timer.stop()
            if not self._last_drained:
                self._last_drained = True
                self.drained.emit()
