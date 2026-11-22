# AI-BS Oracle Hot Standby — Architecture Decision Record (`ADR-HA-OCI-001`)

**Document ID**: `ADR-HA-OCI-001`  
**Status**: Proposed / Stage 1 Offline Implementation Target (Deployment & Cutover Await Operator Authorization)  
**Owner**: Brett Stehouwer  
**Date**: November 19, 2026  

---

## 1. Decision Summary

To guarantee that **at most one entity** can ever submit exchange mutations across the Windows primary host (`AI-BS`) and an Oracle Cloud Infrastructure (`us-chicago-1`, `VM.Standard.A1.Flex`) hot standby, all mutating exchange operations (`CREATE`, `AMEND`, `CANCEL`, `BULK`, `REARM`, `EMERGENCY`) are routed through a single **`ExecutionGateway`** backed by a transactional SQLite WAL **`AuthorityStore`**, using:

1. **Monotonically increasing `authority_epoch` fencing** checked and incremented atomically under `BEGIN IMMEDIATE` + in-process `RLock`.
2. **Pre-network durable intent journaling** (`INTENT -> SUBMITTING -> ACKED | REJECTED | UNKNOWN | RECONCILED | ABORTED`) using string-safe IDs and `Decimal` TEXT accounting.
3. **Dual-key credential isolation**:
   - **Trade Key** (order mutation enabled, **withdrawals disabled**): held strictly inside the `ExecutionGateway` boundary; strategy hosts lose direct trade keys at controlled Stage 1 cutover.
   - **Read-Only Key** (read-only permissions only; trading & withdrawals disabled): used by `agent4_risk_watchdog.py` on Windows and `aibs-standby.service` on OCI ARM64 Linux, paired with code-level enforcement (`PassiveStandbyClient` has zero mutation methods capable of talking to an exchange and unconditionally raises `PassiveAuthorityError`).
4. **Controlled manual promotion in Stage 1** governed by a durable failover state machine (`PASSIVE -> SUSPECT -> VERIFY -> FENCE -> DRAIN_AND_RECONCILE -> RISK_CHECK -> PROMOTE -> ACTIVE`), where manual approval cannot bypass technical reconciliation or risk gates.

---

## 2. Authority Topology & Single-Gateway Dependency Tradeoff

```text
+-----------------------+          +----------------------------------+          +----------------------+
|  Windows AI-BS        |          |  OCI ARM64 VM (or Gateway Host)  |          |  Crypto.com Exchange |
|  structural_dip_engine|  (auth   |  Exclusive Execution Gateway     |  HTTPS   |  Authoritative       |
|  + owner_id + epoch   +--------->+  - Holds Trade Key (no withdraw) +--------->+  Orders, Fills,      |
|                       |  tunnel) |  - SQLite WAL AuthorityStore     |  IPv4    |  Balances            |
|  agent4_risk_watchdog |          |  - Serialized Dispatch Lock      |          +----------+-----------+
|  (Read-Only DPAPI key |          +----------------+-----------------+                     ^
|   + PassiveClient)    |                           | consistent .backup()                  |
+-----------------------+                           v                                       | Read-Only
                                   +----------------------------------+                     | Key Only
                                   |  OCI ARM64 Passive Standby       +---------------------+
                                   |  (PassiveStandbyClient, no trade |
                                   |   key, no GPU/Ollama/UI/Tunnel)  |
                                   +----------------------------------+
```

### Explicit Stage 1 Tradeoff (Single-Gateway Limitation)
For Stage 1 (`AI-BS-HA-OCI-001`), deploying **one** `ExecutionGateway` instance (either co-located on the OCI standby VM with private WireGuard/SSH access from Windows, or on a single designated gateway host) provides strict single-writer serialization and clean fencing **without distributed consensus complexity**.

- **Tradeoff Recorded Plainly**: When hosted on the OCI VM, that OCI VM becomes a runtime execution dependency of the Windows primary trader. If the OCI gateway becomes unreachable, Windows strategy continues observing telemetry/book state safely, while new order mutations pause fail-closed until gateway connectivity recovers or an authorized operator performs documented failover.
- **No False Gateway HA Claims**: Two uncoordinated copies of `ExecutionGateway` are **prohibited**; true multi-node gateway HA requires an external consensus quorum and is a separate future deployment and cost decision.

---

## 3. Datastore, Durability & Replication Boundary

**Datastore**: SQLite 3 with `PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;` and transactional `BEGIN IMMEDIATE` serialization (`C:\AI-BS\scratch\ha_execution_gateway.py`).

### Authoritative Tables
1. `authority_state` (singleton `id = 1`): `owner_id`, `epoch` (monotonic integer), `role` (`PASSIVE | ACTIVE | FENCED | SAFE_HALT | MANUAL_REVIEW`), `state_machine_phase`, `lease_acquired_mono`, `lease_ttl_sec`, `lease_expires_mono`, `last_wall_ts`, `last_mono_ts`, `updated_utc`.
2. `authority_transitions` (append-only audit log): `(seq, from_owner, to_owner, from_epoch, to_epoch, from_phase, to_phase, reason, actor, created_utc)`.
3. `execution_intents`: `(intent_id, client_oid, epoch, owner_id, action, instrument, side, qty_text, price_text, params_json, status, exchange_order_id, error_code, error_detail, created_utc, updated_utc)`.
4. `applied_fills`: `(fill_key, order_id, client_oid, side, qty_text, price_text, fee_text, realized_pnl_text, reserve_delta_text, epoch, applied_utc)` — idempotent deduplication (`INSERT OR IGNORE`) ensuring partial fills during handoff never double-count PnL or the `50%` profit reserve.
5. `journal_meta` (singleton `id = 1`): tracks monotonic `journal_position`, `replication_lag_seconds`, `last_exchange_reconcile_utc`, `last_verified_restore_utc`, `replica_stale`, and `last_error`.

### Replication & Decimal Rules
- All order quantities, prices, fees, realized PnL, and reserve deltas are stored and summed as exact `Decimal` strings (`*_text`), eliminating binary `float` rounding drift.
- Backups and standby snapshots MUST use `sqlite3.Connection.backup()` (`AuthorityStore.create_consistent_backup()`). Copying live `.db`/`.wal` files directly is forbidden.
- **Asynchronous Replication Disclosure**: Async SQLite backup replication to a passive host has non-zero RPO (`replication_lag_seconds > 0`). Zero data loss is **never** claimed across abrupt primary host power loss before snapshot replication completes.
- Restoring any backup (`OPS-03`) initializes authority in **`PASSIVE`** role (`owner_id = NULL`, incremented safety posture) — backups NEVER auto-activate live trading.

---

## 4. Execution Gateway Enforcement Rules (Section 5.2)

1. **Single Admission Path**: Every `CREATE`, `AMEND`, `CANCEL`, `BULK`, `REARM`, and `EMERGENCY` call traverses `ExecutionGateway._execute_mutation()` under `_dispatch_lock` + SQLite `BEGIN IMMEDIATE`.
2. **Pre-Dispatch Revalidation**: Queued commands (`enqueue_command` / `drain_queue`) recheck caller `(owner_id, epoch)` inside `_dispatch_lock` right before network send; any command from an older epoch is marked `ABORTED` and rejected with `StaleEpochError` before touching the exchange.
3. **Fail-Closed Journal & Staleness Barrier**: If the journal DB is unwritable, corrupt, or flagged `replica_stale=1`, mutations raise `JournalDurabilityError` with zero network dispatch.
4. **In-Flight Uncertainty Barrier**: Every mutation writes `INTENT -> SUBMITTING` to durable storage **before** calling `exchange_client`. If the response is lost/times out, the intent transitions to **`UNKNOWN`**. All subsequent non-emergency mutations and standby promotions stay blocked (`UnresolvedIntentError` / `GateBlockedError`) until `reconcile_unresolved_intents()` resolves the intent against authoritative Crypto.com exchange records (`open_orders` / `get_order_detail` / fills).
5. **Credential Isolation Cutover Plan**: Strategy hosts run behind `GatewayExchangeClient` using `(owner_id, epoch)` tokens; passive standbys and Agent 4 watchdog run `PassiveStandbyClient` with the dedicated Read-Only API key. Existing direct DPAPI trade key remains on Windows solely until the operator authorizes Stage 1 gateway cutover.

---

## 5. Failover State Machine, Lease Timing & Clock Discipline (Section 5.3)

### Durable States
`PASSIVE -> SUSPECT -> VERIFY -> FENCE -> DRAIN_AND_RECONCILE -> RISK_CHECK -> PROMOTE -> ACTIVE`  
Failure at any prerequisite transitions immediately to `SAFE_HALT` or `MANUAL_REVIEW`.

### Hard Technical Gates (Manual Approval Cannot Bypass)
Even when `manual_approval_actor` is provided in Stage 1 (`auto_promote_enabled = False`):
1. Previous epoch MUST be fenced (`FENCE` increments `epoch` and invalidates prior leader & queued commands).
2. `DRAIN_AND_RECONCILE` MUST drain stale queued work, achieve `unresolved_intent_count == 0` via authoritative exchange reconciliation, and pass two consecutive consistent exchange read-back checks.
3. `RISK_CHECK` MUST verify `journal_durable == True`, `replica_stale == False`, `clock_anomaly == False`, `market_data_age_sec <= max_market_data_age_sec`, `risk_snapshot.healthy == True`, and `kill_switch_tripped == False`.
4. Only then may `PROMOTE -> ACTIVE` allocate the new exclusive `authority_epoch`.

### Lease Evaluation & Clock Jumps
- Lease expiration (`lease_expires_mono`) is evaluated solely by the authoritative gateway/store using **monotonic elapsed time** (`clock.monotonic()`), never raw cross-host wall-clock comparisons.
- On every store check, delta wall-clock vs delta monotonic elapsed time is compared; divergence exceeding `15.0s` records a `CLOCK_JUMP` anomaly (`ClockAnomalyError`), blocks self-promotion, and requires operator reconciliation.

---

## 6. OCI Provisioning Authority Decision (Section 6)

- **Sole Authority**: Oracle Resource Manager (`POST /20180917/jobs`, operation `APPLY`) against stack `ocid1.ormstack.oc1.us-chicago-1.amaaaaaacuqpksyalu7rlzfn6tci6ml3fxwetdykbjdpifi5sir44tztpyrq`. Direct Compute `LaunchInstance` API calls are permanently removed from automatic claiming.
- **One Instance Lock + Reviewed Plan Policy**: Exclusive host `ControllerLock` prevents concurrent controllers; region (`us-chicago-1`), shape (`VM.Standard.A1.Flex`, `<= 1 OCPU`, `<= 6 GB RAM` approved policy, `<= 2 OCPU / 12 GB` hard cap), compartment, and plan identity are verified prior to `APPLY`.
- **Restart-Safe 20-Minute Capacity Policy**: `POLL_INTERVAL_SECONDS = 1200` minimum wait after confirmed host capacity failure, persisted via `next_attempt_not_before_utc`. Read-only monitoring may poll faster with bounded backoff; unknown `CreateJob` or `GetJob` states block replacement attempts until paginated reconciliation resolves them.

---

## 7. Risk Register

| ID | Risk | Severity | Mitigation / Status |
| --- | --- | --- | --- |
| `R-01` | Stage 1 Single-Gateway on OCI VM becomes dependency for Windows mutations | Medium | Documented plainly; Windows trader halts mutations safely if gateway unreachable; multi-node gateway deferred |
| `R-02` | Always Free Ampere A1 idle reclamation by Oracle or ongoing host capacity exhaustion | Medium | Continuous `MONITOR` mode checks lifecycle state; never claim guaranteed availability from free tier; alert on `OUTAGE_RECOVERY_REQUIRED` |
| `R-03` | Startup-folder boot gap (`Start_24x7_Master_Supervisor.bat` only runs post-sign-in) | High | Migration procedure to authenticated Windows Task Scheduler under user principal prepared in `DEPLOYMENT_AND_ROLLBACK.md` (requires approval) |
| `R-04` | Crypto.com IP allowlist conflicts between dynamic residential primary IP and static OCI egress IP | High | Dual-key separation lets OCI static IP hold Read-Only (and future Gateway) allowlist independently without loosening restrictions |
| `R-05` | Async SQLite `.backup()` snapshot replication has RPO > 0 on sudden Windows power loss | Medium | Track `replication_lag_seconds` and `journal_position`; failback/failover always reconciles directly with Crypto.com exchange first |
| `R-06` | Blanket Defender exclusion on `C:\AI-BS` and `VerifiedAndReputablePolicyState=0` | Medium | Documented for targeted post-verification remediation (narrow exclusions without breaking DPAPI/Python runtimes) |
| `R-07` | Operator pasted `cxakp_...` key prefix in chat during setup | Low | **Not stored** anywhere in repo/docs/logs; operator advised to verify whether prefix/secret should be rotated and load final Read-Only key strictly via local DPAPI (`store_readonly_dpapi.py`) |
