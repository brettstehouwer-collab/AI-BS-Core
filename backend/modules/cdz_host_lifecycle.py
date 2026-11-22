"""Explicit, mountable CDZ lifecycle; no default startup/store activation changes."""
import asyncio
import sys
from contextlib import asynccontextmanager


class CDZHostLifecycle:
    """Drains scans and their response readers, not all HTTP query traffic.

    Independent summary/blocks reads retain their SQLiteStore reader lifecycle.
    The outer server still owns HTTP admission and must stop that traffic before
    closing stores. This object never closes or activates a store. Its watcher
    ownership remains reserved after exit, so another caller cannot reopen scan
    admission between a successful drain and the host's store close.
    """
    def __init__(self, watcher, *, poll=False, drain_timeout=2.0):
        if drain_timeout < 0:
            raise ValueError("Nonnegative drain timeout required")
        self.watcher = watcher
        self.poll = poll
        self.drain_timeout = drain_timeout
        self._entered = False
        self._drain_task = None
        self.last_drain_succeeded = None

    @asynccontextmanager
    async def lifespan(self, app):
        store = app.state.swarm_runtime.stores["cdz_audit"]
        if store is None or getattr(store, "name", None) != "cdz_audit" or self.watcher.store is not store:
            raise ValueError("CDZ lifecycle requires the exact host-selected audit store")
        bound = getattr(app.state, "cdz_watcher", None)
        if bound is not None and bound is not self.watcher:
            raise ValueError("CDZ host already has another watcher")
        if self._entered or not self.watcher.bind_host(self):
            raise RuntimeError("CDZ watcher already belongs to an active host")
        if not self.watcher.resume_scans(owner=self):
            raise RuntimeError("Previous CDZ work has not drained")
        self._entered = True
        app.state.cdz_watcher = self.watcher
        try:
            if self.poll and not self.watcher.start():
                raise RuntimeError("CDZ poll worker did not start")
            yield
        finally:
            # Close admission synchronously: executor saturation must not leave
            # a cancelled shutdown's scan epoch open before its drain starts.
            self.watcher.begin_drain(owner=self)
            cancellation = sys.exc_info()[1]
            if not isinstance(cancellation, asyncio.CancelledError):
                cancellation = None
            self.last_drain_succeeded = None
            task = asyncio.create_task(asyncio.to_thread(self.watcher.drain, self.drain_timeout))
            self._drain_task = task
            observed_terminal = False
            try:
                while True:
                    try:
                        drained = await asyncio.shield(task)
                        observed_terminal = True
                        break
                    except asyncio.CancelledError as error:
                        cancellation = error
                        if task.cancelled():
                            # Event-loop teardown or external cancellation of
                            # the private join task cannot prove its worker is
                            # done. Retain ownership/admission closed, fail safe.
                            raise
                        # Repeated lifespan cancellations cannot release the
                        # epoch while its real drain is queued or still running.
                        continue
                    except BaseException:
                        observed_terminal = task.done() and not task.cancelled()
                        raise
                self.last_drain_succeeded = drained
                if cancellation is not None:
                    raise cancellation
                if not drained:
                    # Close only after successful exit, never unconditionally.
                    raise RuntimeError("CDZ work is still draining; keep its store open")
            finally:
                if observed_terminal:
                    self.watcher.finish_host_drain(self)
                    self._drain_task = None
                    self._entered = False
