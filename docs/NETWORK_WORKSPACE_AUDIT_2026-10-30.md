# Network workspace audit — Record194

Audited 2026-10-30 against source v5.329.73 and the running localhost UI. **Two critical source risks remain unresolved: unauthenticated network payouts and potential disclosure of administrator headers through network telemetry.** The existing crypto trading hold does not protect these separate payout handlers. No application fixes or deployments were performed in this audit.

## Route and observed behavior

The supplied `http://localhost:5173/?tab=unified_creation&subtab=network` reached the Universal Creation Suite password gate. That component accepts only `playwright`, `video`, `comfyui` and `visual`; unsupported `network` falls back to Writing Studio. Its renderer has no Network case. Evidence: `frontend/components/UniversalCreationSuite.jsx:93`, `:129`; app mapping `frontend/App.jsx:260`.

The actual GPU Network panel is `http://localhost:5173/?tab=unified_crypto&subtab=network`, mapped by `frontend/components/UnifiedCryptoHub.jsx:95` to `GpuNetworkTab.jsx`.

Before navigating to the actual panel, browser request blocking was enabled for `/v1/network/*` and `/api/network-telemetry/*`. The earnings and treasury requests to `http://127.0.0.1:8000` failed with browser `blockedReason=inspector`. Despite this, the panel showed **$12.93 available, $12.93 total earned, $0.55/hr and “IDLE & COMPUTING”**, with a52°C GPU card. The page header independently showed28°C. The treasury remained “Connecting to Polygon Web3 Node...”. The renter view exposed a code/prompt field, budget and submit control. Neither submit nor payout was clicked. The agent-created audit tab was then closed; the temporary request blocking did not remain in a user tab.

These displayed monetary values are not verified balances or earnings. They are observations of a failure-mode UI, not financial records.

## Critical / high findings

### N1 — Critical: network payout dispatch has no verified caller boundary

`backend/commercial_gateway/gpu_network_router.py:51` defines `/v1/network` without authentication dependencies; the payout handler at`:339` likewise has no owner/admin dependency. The router is mounted at `backend/AI_BS_Backend.py:3073`, and the global admin middleware's sensitive prefix list at`:1773` omits this family.

The handler contains live PayPal OAuth/payout and chain signing/broadcast branches (`gpu_network_router.py:375`, `:419`, `:516`). It does not check the shared crypto trading hold. Recipients are configured/server-controlled; this is not a claim that a caller can select any destination. An unauthenticated caller can nevertheless request privileged financial activity if this source is loaded and the applicable provider credentials/funds exist. Provider readiness, actual transfer success, remote ingress and deployed handler identity were not exercised.

**Priority remediation:** hold payout dispatch before provider access; require verified owner/admin identity and owner-bound balances. Release it only after durable reservations, idempotency, verified fees/payment provenance and unknown-outcome recovery exist. Hiding the UI button or relying on the exchange trading hold is insufficient.

### N2 — Critical: adjacent network telemetry can expose administrator credentials

`backend/modules/network_telemetry.py:102` redacts Authorization and X-API-Key but omits X-Admin-Key and X-Local-Token. The header loop at`:863` retains unrecognized headers. The middleware is globally registered at `backend/AI_BS_Backend.py:1891`.

`backend/routers/network_telemetry_router.py:93` and`:243` expose captured traffic/stream data. Their `get_tenant` dependency at`:21` is only a caller-provided label, not authentication or owner filtering. The global admin prefix list also omits `/api/network-telemetry`.

A bounded probe executed only the actual extracted header-sanitizing loop with synthetic sentinels: Authorization was redacted; X-Admin-Key and X-Local-Token were retained. No application module, real credential, runtime traffic record or telemetry endpoint was used. This demonstrates the source-level leakage path, not an observed credential compromise.

**Priority remediation:** protect all telemetry reads/streams/controls using verified identity, enforce ownership, redact internal credential headers before storage, and prefer an explicit safe-header allowlist. Assess existing retained records after containment; rotate affected administrator credentials if exposure is confirmed or cannot reasonably be excluded. Do not export raw traffic to the history archive.

### N3 — High: synthetic and caller-controlled balances can reach real payouts

Registration seeds demonstration earnings (`gpu_network_router.py:112`); heartbeat credits caller-supplied compute seconds (`:142`). The unknown-node earnings GET at`:255` creates a shared in-memory ledger entry and reads a global monetary file with a synthetic fallback (`:215`). It is not a harmless read-only authentication probe and was deliberately not called.

The Crypto.com payout branch reports completion without performing the described transfer (`:575`), and unrecognized payout methods can fall through to success/accounting updates (`:597`). Monetary state uses floats and nontransactional shared state/JSON, without per-owner reconciliation. The user-facing initial balances and five-second accrual timer are independently fabricated (`GpuNetworkTab.jsx:19`, `:29`, `:92`).

**Remediation:** separate explicit test fixtures from live paths; remove demo credits and client accrual; show Unavailable until verified owned records exist. Enforce method enums and positive bounded exact amounts. Book only verified compute/payment/payout events with integer minor units or Decimal, fees and durable reconciliation.

### N4 — High: payout concurrency and unknown outcomes lack durable recovery

Balance checks precede awaited provider work (`gpu_network_router.py:343`). There is no durable reservation, stable request idempotency or dispatch journal before payment. Concurrent requests or retries following an unknown outcome can repeat financial activity. PayPal requests have no explicit short timeout; a chain confirmation timeout is not proof that a transfer failed.

**Remediation:** persist an owner-scoped intent and reserve funds atomically before dispatch, use provider idempotency where supported, reconcile unknown references rather than resending, and settle only from verified outcomes.

### N5 — High: unauthenticated code can poison the shared compute queue

`gpu_network_router.py:186` accepts arbitrary `prompt_or_code`, a caller-provided renter ID and budget, then appends to a shared queue. A later compute-agent handoff selects queued work and runs its code in WSL Docker with GPU access and a writable host output mount (`backend/compute_orchestrator_agent.py:40`, `:109`; handoff `backend/bullshit_orchestrator.py:842`). The container command does include network/capability/resource restrictions; this finding is not a claim of a demonstrated container escape or immediate bare-host code execution. Submission alone does not execute the job.

**Remediation:** hold untrusted job dispatch, bind submissions to verified owners and paid/reserved budgets, and require a versioned workload schema plus the approved isolated execution boundary. Separate prompts from executable code and remove caller budget claims as scheduling/payment proof.

### N6 — High: idle-only safety and financial identity are unsupported UI claims

The “Windows Idle-Only Task Execution” toggle only changes React state (`GpuNetworkTab.jsx:297`). It sends no backend command and does not control the `isIdleActive` accrual effect, despite promising automatic pauses for mouse/keyboard/gaming activity. The component ignores the signed-in identity, sends unauthenticated fetches and uses a fixed renter label (`:15`, `:110`, `:137`). Private state is not reset on owner changes.

**Remediation:** expose a truthful unavailable/held state until an authenticated worker acknowledges an enforced idle policy; key private sessions to verified identity, cancel old requests and clear state on account changes. Never infer execution safety from a local toggle.

## Medium / low findings

- **Medium — stale/failing reads:** earnings/treasury polling ignores HTTP status and has no timeout, cancellation, overlap/generation guard or freshness metadata. Errors go to the console and retain stale/demo values (`GpuNetworkTab.jsx:54`).
- **Medium — duplicate work and unsupported completion labels:** job submission has no pending lock, idempotency or visible failure state; the UI labels queued work “Node Assigned” although the server only appends to a queue (`GpuNetworkTab.jsx:135`, `:679`). Second-resolution job IDs can collide (`gpu_network_router.py:189`).
- **Medium — browser-only studio gate:** the supplied page's gate uses a bundled password constant, sessionStorage and a broad name-substring identity rule (`UniversalCreationSuite.jsx:47`, `:77`). Password contents are omitted from this report. This is not proof of bypassing the separate backend screenwriting/document controls.
- **Medium — route mismatch:** validate or redirect stale/unknown subtabs explicitly; preserve a clear route identity instead of silently opening Writing Studio.
- **Low — clipboard state:** copy controls claim success before clipboard completion and lack rejection feedback (`GpuNetworkTab.jsx:456`).

## Proposed containment code — not applied

The immediate source change should retire unsafe payout/job admission before provider/process side effects, then add verified authentication and ownership to all remaining network/telemetry paths. For example, the first executable statement in the payout and job handlers can be:

```python
raise HTTPException(
    status_code=503,
    detail="Network financial and code dispatch is held pending verified ownership and reconciliation.",
)
```

This snippet requires the normal `HTTPException` import. It is a containment proposal, not a sufficient financial coordinator or execution sandbox. Telemetry credential redaction and access controls must be fixed at the same priority; do not test those fixes using actual administrator secrets against the current logger.

## Verification and limits

- Actual UI inspected at the supplied URL; actual GPU panel inspected with its network API requests blocked before navigation. No password was entered or bypassed. No payout/job/capture/fan/treasury control was activated.
- Six Python owning files parsed successfully; three component sets have exact four-mirror parity. The extracted sanitizer probe reproduced failed security expectations; these are **not passing security tests**. No broad application test suite or app imports ran.
- Four protected crypto safety/control/monetary files match the earlier protected baseline. This audit does not establish that network payouts are held; they are a distinct unresolved dispatch path.
- Source findings are confirmed in inspected code. Loaded backend route identity, anonymous runtime exploitation, provider credentials/balances, actual credential compromise and container isolation acceptance remain UNVERIFIED.
- No app source, environment, credentials, version, service, financial records, activation flags or deployment changed. Only the audit report, continuity entries, evidence and authorized history upload were added. Version remains v5.329.73.

Local evidence: `backups/creation_network_audit_20261030T214149Z`, including source snapshots, source fingerprints, the synthetic probe result and browser observations. History export contains reports/ledgers/manifest and sanitized audit metadata, never raw traffic, credentials or source backups.

Next executable remediation: contain network payouts/job dispatch and protect/redact telemetry, with temporary-store and fake-transport tests proving denial occurs before any provider, ledger, capture or process side effect; then replace fabricated metrics and wire a real acknowledged idle policy.
