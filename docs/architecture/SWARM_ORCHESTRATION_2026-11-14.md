# AI-BS swarm ownership and SQLite concurrency

November 14, 2026. **Source implemented; synthetic qualification passed; live activation pending.** Source baseline is5.329.146, configuration schema1. No new installed/hosted release is claimed.

## Configuration and composition

`config/swarm_orchestration.json` is strict validated JSON with five logical roles, four total slots including at most one lead and three workers, one local GPU job,20GiB advisory model budget and4GiB free headroom. It deliberately contains no claim that Codex runs locally or reserves VRAM. The host supplies a measured model requirement and contemporaneous observed free VRAM; unknown/insufficient values reject local GPU admission. CPU affinity and hardware memory partitions are not implemented.

`backend/core/swarm_runtime.py` composes `SwarmRegistry`, the two named `SQLiteStore` objects and an optional `SwarmBusAdapter`. Construct one runtime per cooperating host, using an isolated task workspace; share its registry across cooperating submitters. Construction validates policy and opens no database, worker, model, account or service. Backend imports use the existing backend module path:

```python
from core.swarm_runtime import SwarmRuntime

# reviewed_workspace is an existing, bounded task working copy.
runtime = SwarmRuntime(reviewed_workspace)
adapter = runtime.attach_native_bus(existing_engine_bus)  # GUI thread
task = adapter.submit(
    'review-001', 'test_runner', ['tests/owned_check.py'],
    reviewed_callable, operation='review-owned-check',
    on_result=show_result, on_error=show_failure,
)
```

The callable accepts `cancel_event`, completes its work synchronously and returns materialized results. Lazy iterators/awaitables are rejected. Existing EngineBus owns the actual pool, bounded queue, queued GUI delivery and native return barriers; no parallel executor was introduced. Ownership acquisition/hash scans and final audits run on that pool's worker, not on the GUI thread. Queued cancellation creates no lease, and task identities/wrappers remain retained through the bus's native barrier. Admission exhaustion is a surfaced task error, not an automatic retry.

## Ownership and lifecycle

The trusted orchestrator grants exact relative file paths per task; directory-wide ownership and direct database-file ownership are rejected. Redirected paths, junction/reparse paths, hard links, traversal, Git internals and database/WAL/SHM paths are rejected. Parallel leases must be disjoint. Resulting workspace content is audited before successful result delivery; peer claims remain recognized across overlapping lease lifetimes even after a peer finishes.

This is **same-account cooperative admission and end-state auditing, not OS isolation**. A callable can bypass the API; transient writes restored before audit and attribution of writes to another concurrently claimed path cannot be proven by snapshots. Changes outside the audited workspace are not monitored. No automatic destructive rollback occurs. Use the existing isolated-worker boundary for untrusted execution; this does not weaken Coding mode's isolated/trusted distinction or authorize original-project application.

Snapshot budgets default to20,000entries/512MiB. Oversized, changing or unverifiable workspaces fail admission/audit. Use small isolated working copies rather than pointing this adapter at the whole live AI-BS tree. Policy limits are per shared registry, not a machine-wide limit on unrelated clients/processes.

An ownership violation stops registry admission and cooperatively cancels peers. The failing task retains its error delivery; previously user-cancelled work remains cancelled. Two consecutive identical operation/error identities halt that operation; an unrelated operation is not globally halted. Task cancellation never forcibly terminates a callable. Host code must keep the runtime/bus alive while close/drain returns false. Default runtime close is nonblocking; optional nonzero waits belong outside the GUI event loop. Existing process/QProcess boundaries remain unchanged.

## Distinct database stores and opt-in rollout

| Name | Existing file | Source reference |
|---|---|---|
| `master` | `C:/AI-BS/backend/aibs_master.db` | Studio/backend master store |
| `cdz_audit` | `C:/AI-BS/database/aibs_master.db` | `backend/database/cdz_audit_db.py` CDZ audit ledger |

No merge, relocation, schema migration or legacy helper replacement was performed. Explicit store activation requires `allow_activation=True`, an existing database, a new backup destination and a consistent SQLite online backup passing `quick_check` **before** changing journal mode. Backup time is bounded. Each store activates separately.

New owned connections use WAL, synchronousFULL,10,000ms busy timeout, cache-8192KiB, mmap0 and auto-checkpoint1000pages. These per-connection settings do not rewrite other connections. Eight read contexts are bounded independently; each owns a fresh connection on its calling thread. One bounded128-entry queue serializes writes on a connection owned by the writer thread. The one-adapter registry is per process; legacy/external writers still rely on SQLite locking, not a new global broker.

Write callbacks receive `(connection, cancel_event)` and must return materialized values without retaining/closing connections or replacing transaction controls. Accidental transaction control is denied. They are trusted application code, not sandboxed code. Queued/running cancellation and commit are arbitrated; cancellation winning before commit rolls back. Failures settle futures and roll back; unusable-connection cleanup failures stop the writer and fail pending work rather than leaving hanging futures. Lock timeouts and queue exhaustion are explicit errors. PASSIVE checkpoint results and WAL byte growth are available through the store API.

Live activation remains a separate rollout: inventory each target caller, capture/verify private backups, qualify the chosen integration and recovery, then activate only that store/caller. Do not apply global PRAGMA changes, replace other databases, delete WAL/SHM files or restart services from this configuration. Credentials/private database snapshots remain local and outside shared source backups.

## Verification and retained evidence

Integrated62checks passed:20policy/ownership,15SQLite,2composition,8native-adapter and17existing EngineBus admission/shutdown regressions. Cases include actual concurrent threads, both peer finish orders, path/link escapes, unknown VRAM admission, two-strike behavior, reader/writer contention, cancellation/rollback, actual SQLITE_FULL, interrupted-process recovery, backup restore integrity, off-GUI hashing, GUI callback delivery and native drain.

The first integrated run passed61/62 and exposed an ownership failure whose cancellation flag suppressed Qt's error delivery. The corrected gate passed62/62. Prior standalone18/20policy checks, initial Qt21checks, the initial SQLite fixture cleanup failure and all relevant logs remain retained. Evidence: `backups/swarm_integration_20261114_v01`, `backups/swarm_orchestration_20261114_v01` and `backups/swarm_sqlite_20261114_v01`.

The production creative manifest remained unchanged throughout the integrated gate; existing `native_studio/engine.py`, legacy database helpers and current service processes were not edited or restarted. No real model calls, live database settings/migrations, deployment or full-release qualification occurred. Local checkpoint/source manifest and any separately verified Drive receipt distinguish their coverage; synthetic passing checks do not assert that live WAL or machine-wide write/VRAM enforcement is enabled.
