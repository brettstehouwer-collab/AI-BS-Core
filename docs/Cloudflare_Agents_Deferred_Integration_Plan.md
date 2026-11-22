# Cloudflare Agents: deferred AI-BS integration plan

**Status: DEFERRED / PLANNING ONLY.**
**Decision date: November 4, 2026 (America/New_York).**
**Requirement: CF-STATUS-PILOT-001.**

The user explicitly selected **Save the plan for later**. This document preserves
the proposal; it does not start implementation, install packages, allocate cloud
resources, expose local services, or authorize deployment. A later user request
is required to start the pilot. This is separate from the pending VM disk-erasure
decision and does not authorize VM removal.

## Purpose and priority

Use Cloudflare selectively for coordination around AI-BS. Start with an optional,
owner-authenticated remote job-status dashboard. Its value is keeping selected
status visible across device disconnects; it does not improve rendering, physics,
model quality, or local execution by itself.

The existing [opening-first priority plan](game_engine/OPENING_FIRST_PRIORITY_PLAN.md)
and [game roadmap](../engine/BUILD_ROADMAP.md) continue to govern game work.
Complete the playable opening before game monitoring, extra development tools,
or the Adam phone companion. Do not divert the active native build/cleanup task.

| Proposed use | Benefit | Deferred decision |
| --- | --- | --- |
| AI-BS job dashboard | View generation, build and validation status from another device | First pilot, when explicitly resumed |
| Background creation workflows | Retain stages, failures and recoverable progress | Add after one real workflow needs it |
| Game development dashboard | Remote build/checkpoint status | Optional, after playable opening |
| Adam phone companion | Selected progression, discoveries and guidance from active PC session | Later, after opening and stable event APIs |
| Cloud-assisted creator proposals | Queue optional generation for native validation and review | Evaluate after demonstrated need |
| Rendering, physics, simulation and saves | Existing native/offline authority | Keep authoritative on PC |

## Existing implementation to reuse

Verified by bounded read-only source review on the decision date:

- [cloudflare-agent/src/index.ts](../cloudflare-agent/src/index.ts), lines 13-40,
  is the existing starting scaffold. It stores client identity, a workload count
  and a telemetry time. It is not a qualified status dashboard.
- Its mutable `recordTelemetry` RPC accepts caller-supplied identity, ignores
  the submitted status and does not maintain workload status. Request/owner
  authentication, a job model, ordering, deduplication, quotas and retention
  remain to be designed and verified.
- [wrangler.jsonc](../cloudflare-agent/wrangler.jsonc) already declares a Durable
  Object binding and SQLite migration. Preserve prior migration history.
  The scaffold directory lacks its own package/lock/TypeScript/test setup.
  Installed SDK compatibility has not been qualified; select and pin a current
  supported version when implementation is resumed. Verify router async/fallback
  behavior against that exact version rather than copying the current expression.
- [read_build_progress](../native_studio/game_build_monitor.py), around line 659,
  already distinguishes missing, unreadable, running, passed, failed, partial
  and stale evidence. [GameBuildView.refresh](../native_studio/game_build_view.py),
  around line 313, consumes it through the worker bus.
- Do not publish the full monitor return value. It includes local source paths,
  inventories, drive/storage information and log tails. Define an explicit
  metadata projection instead of copying these payloads to the cloud.

These findings are current source observations, not proof that the scaffold was
deployed, authenticated, usable from a phone, or tested as a workload dashboard.

## Proposed implementation sequence

1. **Define the status contract.** Allow only owner-scoped project/job identifiers,
   job/attempt identity, stage, optional measured progress, bounded result summary,
   schema/source version and last-seen timestamps. Unknown progress stays unknown.
   Keep logs, paths, prompts, conversations, credentials, family assets and saves
   outside the initial projection. Derive owner scope from verified authentication.
2. **Qualify a local bridge.** Extend the existing scaffold, select/pin a compatible
   SDK and tooling, separate PC publisher permission from read-only viewer access,
   and handle duplicate/delayed messages, producer restarts and bounded reconnects.
   Do not expose terminal commands, start/cancel actions or remote save writes.
3. **Run one optional cloud pilot.** Observe one real local AI-BS job from a remote
   dashboard. Check authentication/owner isolation, reconnect/resync, honest
   failed/unknown/offline states, and bounded event rate, size, retention and cost.
   Cloud outages must not interrupt local AI-BS or make job results look successful.
4. **Expand after demonstrated value.** Add a specific multistep creation workflow
   only when necessary. Game build monitoring and the read-only Adam companion
   remain behind the playable opening and stable PC event contracts.

## Required acceptance before claiming a pilot works

- A real local producer creates status for one real job; a clean remote viewer
  can observe it using owner authentication. No fixture is presented as live data.
- Anonymous, cross-owner and viewer write/RPC/state-change attempts are rejected.
  PC publisher credentials are separately scoped and revocable.
- Idempotent duplicate updates are harmless; conflicting duplicates and older
  updates cannot roll back accepted job state. Producer restart/attempt identity
  is explicit. A terminal result remains recorded after the PC disconnects.
- Job outcome and connection freshness are separate. Use server-received time
  for freshness, and source sequence/attempt evidence for ordering; do not treat
  an untrusted client clock as proof of either success or freshness.
- Reconnect retrieves a bounded current snapshot and necessary missed state.
  Retry/backoff, payload limits, retained history and total cost have explicit bounds.
- A cloud outage leaves local execution, original data and native UI usable.
  No cloud-triggered execution, trading, email dispatch or save mutation is enabled.
- Verify the actual supported SDK API, auth behavior, tooling, pricing and quotas
  at implementation time. Record actual offline and cloud evidence separately.

## PC and game authority

A PC-hosted job still needs the PC/process to remain running. Retaining cloud
status does not continue that process after the PC shuts down. This is a boundary
of the proposed local-producer architecture, not an SDK capability claim.

Gameplay, physics, rendering and durable saves remain local and authoritative.
Simulation pauses/stops with the game; offline play remains available. A future
read-only phone companion pairs to the active PC session and consumes selected,
versioned progression/discovery/map/guidance events with reconnect/resync. It
does not become a second save writer. Any later phone commands require a separate
reviewed contract, request identity, permissions, preconditions and PC acknowledgment.

## Evidence and continuation pointers

- User proposal in this chat and explicit **Save the plan for later** response.
- Current AGENTS contract, relevant directory/integration-ledger pointers,
  engine roadmap/opening-first plan, existing scaffold and build-monitor sources.
- One current turn read from `Plan AI-BS game development`, thread
  `01a19491-7a5c-71e0-a6ba-0dc4a3f58f44`, turn
  `01a1a8bc-4c15-7b80-9abc-2014c14ab911`. Its visible messages retain this
  proposal as later planning while cleanup/native build take priority. This is
  a bounded message review, not a claim to have read all active/archived chats.
- Read-only supplemental review: `/root/cloudflare_pilot_review`; no code changes.
- [Official Cloudflare Agents overview](https://developers.cloudflare.com/agents/)
  retrieved on the decision date. It describes persistent state, live connections,
  scheduling and recoverable work. It does not establish this application's local
  PC bridge, authentication, quotas or production acceptance. Specific APIs and
  package versions are intentionally not frozen by this deferred plan.

**Exact next step on resumption:** re-read the current handoff and roadmap,
confirm the user wants the AI-BS status pilot, inspect the existing scaffold and
one real local job producer, then define and test the smallest authenticated
read-only contract before any optional deployment. Keep live trading disabled.
