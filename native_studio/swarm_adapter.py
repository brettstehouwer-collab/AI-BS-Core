"""Opt-in swarm admission over the existing EngineBus, not another executor.

Same-account callables are cooperative, not sandboxed. Use a reviewed isolated
workspace for ownership auditing. The application continues to own EngineBus
shutdown and must retain it until its existing native pool barrier completes.
"""
from __future__ import annotations

import threading
from collections.abc import AsyncIterator, Iterator
import inspect
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot


class SwarmBusAdapter(QObject):
    drained = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, bus, registry):
        if QThread.currentThread() != bus.thread():
            raise RuntimeError('Swarm adapter must be created on the bus GUI thread')
        super().__init__(bus)
        self.bus = bus
        self.registry = registry
        self._tasks = {}
        self._stopping = False
        self._announced = False
        self._timer = QTimer(self)
        self._timer.setInterval(20)
        self._timer.timeout.connect(self._collect)

    def _gui(self):
        if QThread.currentThread() != self.thread():
            raise RuntimeError('Swarm admission must run on its owning GUI thread')

    def submit(self, task_id, role, paths, fn, *args, operation=None,
               gpu_required_bytes=None, free_vram_bytes=None,
               on_result=None, on_error=None, **kwargs):
        """Submit a callable accepting cancel_event; audit before result delivery.

        Admission and workspace hashing run on the existing bus worker. Slot
        exhaustion is delivered through on_error; the bus owns its bounded queue.
        Passing a GPU estimate requires a contemporaneous observed-free value.
        Neither estimate is a hardware reservation or provider configuration.
        """
        self._gui()
        if self._stopping:
            raise RuntimeError('Swarm adapter is shutting down')
        if task_id in self._tasks:
            raise ValueError('Task identity is retained until native drain')
        if 'cancel_event' in kwargs:
            raise ValueError('Cancellation event is owned by the task lease')
        cancel_event = threading.Event()
        completed = threading.Event()

        def work():
            error = None
            lease = None
            try:
                if cancel_event.is_set():
                    return None
                lease = self.registry.acquire(task_id, role, paths, operation=operation,
                    gpu_required_bytes=gpu_required_bytes, free_vram_bytes=free_vram_bytes,
                    cancel_event=cancel_event)
                self.registry.check(lease)
                result = fn(*args, cancel_event=cancel_event, **kwargs)
                if inspect.isawaitable(result) or isinstance(result, (Iterator, AsyncIterator)):
                    if inspect.iscoroutine(result):
                        result.close()
                    raise TypeError('Owned work must complete synchronously and return materialized values')
                return result
            except Exception as exc:
                error = type(exc).__name__
                raise
            finally:
                try:
                    if lease is not None:
                        self.registry.finish(lease, error_identity=error)
                finally:
                    completed.set()

        try:
            task = self.bus.submit(work, on_result=on_result, on_error=on_error)
        except BaseException:
            cancel_event.set()
            raise
        # GUI-thread submission cannot interleave a GUI shutdown before this
        # assignment. Both the bus fence and cooperative callable see one event.
        task.cancel_event = cancel_event
        self._tasks[task_id] = (task, cancel_event, completed)
        self._timer.start()
        return task

    def cancel(self, task_id):
        self._gui()
        entry = self._tasks.get(task_id)
        if entry is not None:
            entry[1].set()

    @pyqtSlot()
    def _collect(self):
        self._gui()
        # A queued task can be cleared without work() or a lease ever starting.
        # Retain its wrapper until the existing bus's native join releases it.
        for task_id, (task, cancel_event, completed) in list(self._tasks.items()):
            if task not in self.bus._owned:
                self._tasks.pop(task_id, None)
        if not self._tasks:
            self._timer.stop()
            if self._stopping and not self._announced:
                self._announced = True
                self.drained.emit()

    def begin_shutdown(self):
        """Cancel only this adapter's tasks; never stop unrelated bus callers."""
        self._gui()
        self._stopping = True
        for _, cancel_event, _ in self._tasks.values():
            cancel_event.set()
        self._collect()

    @property
    def is_drained(self):
        return not self._tasks
