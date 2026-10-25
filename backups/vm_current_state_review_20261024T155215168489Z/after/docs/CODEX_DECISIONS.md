# AI-BS — Codex Architectural Decisions & Rationale (`CODEX_DECISIONS.md`)

This document records durable architectural, security, runtime, and persistence decisions for the AI-BS repository (`C:\AI-BS`). Do not overwrite historical entries; append new decisions as development progresses.

---

## ADR-001: Three-Layer Persistent Engineering Memory & Lifecycle Hook Architecture
- **Date:** 2026-10-24
- **Status:** Active / Verified on Codex `v0.164.0-alpha.11.1` (`windows-x86_64`)
- **Context:** Long-running autonomous development across Phases 1–6 experiences context compaction and session restarts. Relying on conversation history alone risks losing checkpoint paths, hash invariants, runtime PID/flag baselines, and deferred scope boundaries.
- **Decision:**
  1. Maintain durable repository truth across:
     - `AGENTS.md` (and `C:\Users\footb\.codex\AGENTS.md`) — Permanent operational instructions and safety invariants.
     - `docs/CODEX_HANDOFF.md` — Authoritative current engineering state and versioned checkpoint records.
     - `docs/CODEX_JOURNAL.md` — Append-only chronological history of checkpoints, lifecycle hook triggers (`SessionStart`, `PreCompact`, `PostCompact`, `Stop`), test results, and diagnostic halts.
     - `docs/CODEX_DECISIONS.md` — Architectural decisions and rationale.
     - `docs/CODEX_TASKS.md` — Outstanding tasks, dependencies, and acceptance criteria.
  2. Configure native Codex `v0.164.0-alpha.11.1` lifecycle hooks in `C:\Users\footb\.codex\hooks.json` (UTF-8 without BOM) with trusted content hashes in `C:\Users\footb\.codex\config.toml` (`[hooks.state.'...']`) invoking `C:\Users\footb\.codex\scripts\codex_lifecycle_hook.py`.
  3. **Non-Interference Invariant:** Hook scripts read `docs/CODEX_HANDOFF.md`, `docs/AI_BS_Autonomy_Implementation_Plan.md`, `docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md`, and `docs/engineering_ledger/cloud_index.json` strictly in **read-only** mode so they never invalidate an in-flight `before_manifest.json` SHA-256 guard during active checkpoint finalization. Hook checkpoints write atomically to `docs/CODEX_JOURNAL.md`, `docs/CODEX_TASKS.md`, and `C:\AI-BS\backups\codex_hook_checkpoints\`.

---

## ADR-002: Preservation of Originals, Private Stores, Models, and Dirty Working Tree
- **Date:** 2026-10-24
- **Status:** Mandatory Invariant
- **Decision:**
  - Never run `git reset`, `git checkout --`, `git clean`, or destructive deletions on `C:\AI-BS`.
  - Preserve all 866 screenplays + 22 selected creative/project documents (888 total) and their retained backup copies byte-for-byte.
  - Preserve SQLite databases (`data/aibs_vault.db`, `aibs_master.db`, `backend/data/personal_ai_profile.db`), model blobs (`C:\AI-BS\models\ollama`), and `Modelfile*` definitions.
  - Export only sanitized engineering ledger summaries to the private Google Drive ledger file after exact byte-readback verification; never export raw source, candidate proposals, personal rows, credentials, or local directory listings.

---

## ADR-003: Loopback-Only Services & Six Disabled Autonomous/External Flags
- **Date:** 2026-10-24
- **Status:** Mandatory Runtime Gate
- **Decision:**
  - Local services (`127.0.0.1:8080` FastAPI backend, `127.0.0.1:8000` Go gateway, `127.0.0.1:11434` Ollama, `127.0.0.1:5173` Vite frontend) must bind strictly to `127.0.0.1`.
  - Keep all six autonomous/outbound flags explicitly `false` (`AIBS_AUTONOMOUS_SWARM`, `AIBS_BACKGROUND_DAEMONS`, `AIBS_OUTBOUND_PUBLISH`, `AIBS_AUTO_APPLY`, `AIBS_CLOUD_SYNC_DAEMON`, `AIBS_UNATTENDED_EXECUTION`).
  - All candidate code proposals remain `Tests not run / Not applied` (`execution_authorized=false`, `apply_authorized=false`) until isolated execution and review/apply gates are explicitly completed.

---

## ADR-004: Explicit Deferral of Windows VM Isolation Steps & Two-Strike Diagnostic Halt
- **Date:** 2026-10-24
- **Status:** Active User Directive
- **Decision:**
  - Per explicit user instruction, Windows VM / Hyper-V / Sandbox isolation setup and VM retry workarounds are deferred while bounded VM-independent tasks in BS-Chat preparation/planning/proposal workflows proceed.
  - Apply a strict two-strike diagnostic halt after two failed corrective attempts on any unexpected runtime or verification failure, recording the exact failure artifact before changing approach.


## ADR-005: Runtime evidence and settings ownership clarification
- Date: 2026-10-24
- Status: Current evidence correction; supersedes conflicting names/claims in earlier notes without removing their history.
- The six actual verified runtime opt-in flags are AI_BS_RECDEBUT_OUTBOUND_ENABLED, AI_BS_RECDEBUT_INBOUND_POLLING_ENABLED, AI_BS_DISCORD_NOTIFICATIONS_ENABLED, AI_BS_BACKEND_MANAGE_DAEMONS, AI_BS_BACKEND_BACKGROUND_ENABLED and AI_BS_ALLOW_DESTRUCTIVE_ACTIONS. They remain false. The AIBS_* names listed in ADR-003 were not established as equivalent controls and must not replace these actual runtime checks.
- Verified personal authority is backend/database/aibs_personal_intelligence.db. Prior preservation checks used the source paths recorded in backups/production_readiness_5_329_33_20261024T054356815Z/backup_report.json, including stehouwer_vault.db and backend/aibs_master.db. Basenames in earlier prose are not proof of a live database path; preserve any additional existing database rather than substituting an empty or similarly named file.
- Five persistent-memory files are now required by the user's replacement instructions. Root AGENTS.md was read and still contains the original project directive; the new memory rules are present in C:/Users/footb/.codex/AGENTS.md. Do not claim the root file already has the addendum or overwrite its existing operational sections.
- Existing config.toml defaults were observed as gpt-6.1-sol, reasoning ultra and priority tier, with approval never, danger-full-access and trusted AI-BS. These are file defaults, not proof of the active chat's effective setting. Recommend Medium and standard/default speed for the requested low-usage workflow. No config was edited by this review.
- Command permissions, Browser/Computer Use controls and app connections are separate. Global browser config already lists localhost5173 as allowed; actual browser-control tools remain unavailable to this session. Root project browser config paths stated in earlier task prose were not found. Do not edit policy files, install workarounds or claim a connector is functional merely because a permission/config/tag exists.
- Antigravity should own only its specifically assigned Codex settings changes while Codex owns the current AI-BS code/runtime task. Avoid concurrent source/version/handoff/ledger edits. Existing routine restart authorization remains valid; an observer's conservative open-connection guard is an implementation issue to diagnose, not a new approval-policy rejection.
- Lifecycle script and hooks.json exist. This review did not execute hooks, validate automatic lifecycle delivery, change their trusted hashes or establish the installed binary version. Preserve hook-written JOURNAL/TASKS changes and keep handoff/plan/cloud-ledger/index outside automatic hook writes.


## ADR-006: Safe user-requested pause during source48 finalization
- Date: 2026-10-24T15:19:26.942391+00:00
- User explicitly requested a pause. Preserve all completed source/test/live evidence and leave existing healthy services running. Final48post-restart preservation, authoritative checkpoint finalization and sanitized cloud sync remain pending. Resume from pause_checkpoint.json without replaying completed actions. VM stays deferred; no new whole-phase completion or external release.


## ADR-007: Resumed full goal with legitimate worker and release boundaries
- Date: 2026-10-24T15:42:20.565050+00:00
- User reauthorized the Windows VM completion scope in the edited objective and requested continuous progress. Earlier pause/VM deferral no longer controls new work.
- Preserve independent worker authentication and accepted guest containment; broad local permissions do not create passwords, guest entitlement, signed packages or empirical verification.
- Retain failed observers and reconcile actual401gateway/403backend denials using fresh observations without restarting healthy services. No host fallback, scheduled-task credential bypass or replay of stale snapshot scripts.
- Root AGENTS.md now has SectionC and was read with SHA256 recorded; the earlier note that its addendum was absent is historical.
- Source48verification is finalized locally with retained manifests; cloud completion requires exact private raw readback. No new platform release or whole phase completion.
