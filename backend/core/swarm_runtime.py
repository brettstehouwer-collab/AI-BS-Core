"""Explicit, inert composition of reviewed policy and existing-host adapters."""
from pathlib import Path
from core.swarm_orchestration import SwarmRegistry, load_policy
from db.swarm_sqlite import SQLiteStore


class SwarmRuntime:
    """One host-owned runtime shared by its cooperating task submitters.

    Construction validates configuration and allocates no workers/connections.
    Databases activate individually through store.activate after backup. This
    does not retrofit legacy callers or govern external processes/Codex agents.
    """
    def __init__(self, workspace, *, project_root=None, config_path=None):
        root = Path(project_root) if project_root is not None else Path(__file__).resolve().parents[2]
        path = Path(config_path) if config_path is not None else root / 'config/swarm_orchestration.json'
        self.policy = load_policy(path)
        self.registry = SwarmRegistry(workspace, self.policy)
        self.stores = {name: SQLiteStore(root, name) for name in ('master', 'cdz_audit')}
        self._native_adapter = None

    def attach_native_bus(self, bus):
        """Call on the GUI thread; reuse the existing bus and its ownership."""
        if self._native_adapter is not None:
            if self._native_adapter.bus is not bus:
                raise RuntimeError('Runtime already belongs to another EngineBus')
            return self._native_adapter
        from native_studio.swarm_adapter import SwarmBusAdapter
        self._native_adapter = SwarmBusAdapter(bus, self.registry)
        return self._native_adapter

    def request_shutdown(self):
        """Cancel admission cooperatively; host retains all native pool barriers."""
        self.registry.request_shutdown()
        if self._native_adapter is not None:
            self._native_adapter.begin_shutdown()

    def close(self, timeout=0):
        """Bounded polling-style close; default never waits on the GUI thread."""
        import time
        if timeout < 0:
            raise ValueError('Nonnegative timeout required')
        self.request_shutdown()
        deadline = time.monotonic() + timeout
        drained = self.registry.drain(max(0, deadline - time.monotonic()))
        for store in self.stores.values():
            drained = store.close(max(0, deadline - time.monotonic()), cancel_pending=True) and drained
        return drained and (self._native_adapter is None or self._native_adapter.is_drained)
