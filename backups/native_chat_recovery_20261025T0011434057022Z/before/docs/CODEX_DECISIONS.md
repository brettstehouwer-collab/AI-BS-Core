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

## ADR-008: Fixed worker recovery preserves current containment and disk
- Date:2026-10-24T16:05Z
- Recover the actual aborted worker disk, preserving it with a NEW cold snapshot; never restore historical installer snapshot hardware that includes NAT.
- Require existing worker SID1005/nonadministrator/medium integrity; no cross-account dispatch workaround. Local permissions do not establish an authenticated worker execution channel.
- Allow only fixed VBox state/snapshot/medium/boot/screenshot/save operations. Bound observation to45seconds before saving; one-shot evidence prevents automatic replay. Failure leaves state requiring fresh inspection rather than guessed cleanup.
- Replace the old port-only controller readiness claim with explicit worker preflight/recovery and AutoApprove rejection. Offline guards are not actual Phase4acceptance.
- Budget a full64GiB child disk,8GiB saved RAM and64GiB host headroom (136GiB). This is a new launcher resource policy, not a modification of the historical launch scripts.

## ADR-009: Optional display evidence cannot skip VM-state preservation
- Date:2026-10-24T16:11Z
- The first live recovery captured before firmware initialized video and returned0x0. Never equate failed screenshot evidence with a failed boot; retain both boot and observation outcomes.
- Stop optional screenshot collection on its first failure and independently query/validate/save the same isolated VM. A validation failure still halts control operations.
- Continue this running child/snapshot through one fixed worker-only -ObserveRunning action, never replay boot or restore the old snapshot. Actual saved state must be observed, not inferred from tests.

## ADR-010: Temporary setup UI channel is separate from generated-task transport
- Date:2026-10-24
- Require manual existing-worker launch once, then accept only bounded fixed VM controls and screenshot-bound navigation; preserve independent authentication without repeated command launch handoffs.
- Use protected local channel ACL, exclusive lease, live PID/creation/SID verification, unique sessions, strict monotonic sequence and durable intents. Never equate a status file with a live worker or replay ambiguous requests.
- Independently save/verify the exact isolated guest on ordinary idle/stop/error. Abrupt process death and real task cancellation require separate acceptance; do not describe setup polling as proven Phase4containment.
- Preserve the saved OOBE disk/snapshot. No text/password/F10, generated commands, network/sharing changes or snapshot restoration. A license/credential boundary is not routine navigation permission.

## ADR-011: Preserve status reader snapshots and release lease on report failure
- Date:2026-10-24
- Use File.Replace with PowerShell NullString for a true null backup argument; ordinary $null was converted to an invalid empty path. Initial publication uses File.Move.
- Do not copy over an existing status inode: actual reader tests demonstrated that this changes a previously opened reader's view. Publication failure must leave prior status readable.
- Always dispose the exclusive controller lease even if final status reporting fails. VM preservation remains independently queried/attempted before terminal reporting.
- Keep the confirmed second agent on offline-media/Phase5fixture work; this chat coordinates live VM and five-file memory updates.

## ADR-012: Pivot to immutable status records after live replacement denial
- Date:2026-10-24
- Preserve both binding/removal failures; do not repeat failed status replacement. Publish new numbered flushed records with unique rename, retaining earlier bytes and ignoring incomplete pending files.
- Highest corrupt publication fails closed; never turn stale READYinto liveness. Preserve live PID/creation/SID/session checks in the client.
- Candidate remains separate until concurrent edits to the shared controller stop. Source-owner reconciliation is required before promotion, not a new permission to bypass worker authentication.

## ADR-013: Narrow measurement and artifact evidence cannot complete broader workflow gates
- Date:2026-10-24
- Count the ten warm synthetic model requests only under their exact repeated-prompt condition; retain the failed60second initialization separately from the diagnosed180second-budget retry. One cold observation is not a cold distribution or proof of general offline/model quality.
- Accept the independently parsed seven-file offline ISO as a media artifact; require real guest provisioning, compatibility/licensing/credential exclusion and controller acceptance separately.
- Treat the other agent's three passing tests as contracts/staging/simulation. Placeholder assertions and hand-written copy/rollback do not prove React behavior or production reviewed application/recovery; request stronger fixtures before Phase5acceptance.
- Operator's provided agent scope report plus no live lease/stable source permits main VM-control promotion within existing authorization; no exact confirmation phrase is required when the actual ownership ambiguity has been resolved by evidence.

## ADR-014: Normalize client timestamps without relaxing worker identity or freshness
- Date:2026-10-24
- PowerShell7may deserialize ISOtimestamps as DateTime, while Windows PowerShell keeps strings and casts can create local times. Compare UTC ticks for process creation and UTC-normalized age for heartbeat/frame windows.
- Keep exact SID/PID/creation, session/sequence and visible-frame gates.15actual-condition regressions on both PowerShell versions prove valid representations pass and stale/mismatched values reject.
- Missing live guest/controller and an unfinished local account require user/state progress; stale files and repeated prompts cannot prove a running job or desktop. Preserve successful ten-operation OOBE checkpoint separately from its next human handoff.

## ADR-015: Preserve desktop identity transitions and reject expired task bases
- Date:2026-10-24
- A completed desktop/snapshot/media transition changes the pinned current snapshot, child disk and optical UUID. Historical recovery guards must reject it until a reviewed exact transition is implemented; do not weaken guards or restore snapshot hardware blindly.
- An expired-license watermark is a prerequisite failure requiring legitimate guest activation/licensing verification before task admission. Desktop access and runtime provisioning cannot establish eligibility or extend evaluation rights.
- Keep runtime-install consent separate from results: operator explicitly approved Node24.22.1/Python3.13.17guest installation; retain that approval, while requiring observed completion/exact runtime verification and human handling of mandatory security/authentication prompts.
## ADR-016: Provisioning guard tests and runtime installation do not grant task authority
- Date:2026-10-24
- Reject actual host/wrong-VM identity before imports or writes. Pin helper/media bytes, require offline optical media and actual guest facts, preserve exact native failure evidence and version checks.
- Bound provisioning processes/output but quarantine on uncertain installer descendants; MSI service execution is not proven contained by killing its initiating parent. Keep all generated-task acceptance and task authority disabled.
- Native VirtualBox soft keyboard may navigate ordinary guest GUI when capture blocks injected input. It must never be used to bypass the Computer Use restrictions on terminal commands, authentication or security/privacy permission prompts.
## ADR-017: Retain provisioning intent and independently verify media before delivery
- Date:2026-10-24
- An exclusive lease alone cannot prevent replay after process termination. Flush an immutable attempt intent before native installation, reject any retained/partial intent after lease release, and require reviewed recovery instead of deleting history or automatically retrying.
- Preserve v1 media and agent source. Stage a separate exact-file-set bundle, independently parse its actual directory/extents and compare every byte, verify helper pins and final artifact hash, and grant the worker read-only access. Media construction is separate from guest execution/task acceptance.
- A user-reported finished installer or closed wizard is not an exact runtime/exit-code observation. Reconcile actual installed paths and preserve security-prompt/manual-input handoffs before continuing.
## ADR-018: Keep desktop profile validation separate from controller adoption
- Date:2026-10-24
- Validate the exact new desktop snapshot/disk/v1DVD tuple in a separate pure candidate. Preserve historical recovery code, reject unreviewed optical identities and require an explicit observed operation state; do not rewrite observations to satisfy an older profile.
- Synthetic VM-info and persisted XML establish predicate/configuration evidence only. Actual authenticated worker state, media/ancestry checks, licensing, runtimes and all behavioral containment cases remain necessary before dispatch or task admission.
## ADR-019: Replace unavailable clipboard workflows with explicit offline diagnostics
- Date:2026-10-24
- Do not require a long paste while the approved isolation profile disables host/guest clipboard. Identify the actual displayed application before interpreting an internet prompt; the observed app was Power Automate.
- Deliver a reviewed, fixed-function native read-only diagnostic through exact-file-set read-back media. The operator manually launches it; no tool injects terminal commands or bypasses authentication, security warnings or policy. Keep actual guest results separate from host infrastructure tests and artifact construction.
- Preserve originals and fail-closed historical profiles across optical-media changes. No diagnostic result itself authorizes generated-task execution or completes containment.
## ADR-020: Preserve PS/2 isolation while recovering pointer integration
- Date:2026-10-24
- Use matching reviewed local Oracle Guest Additions for PS/2 mouse integration; do not enable a USB tablet/controller or sharing/networking as a shortcut. Full Guest Additions installs broader drivers/services, so installation does not itself establish accepted protected transport or containment.
- Verify current direct Machine/Hardware separately from historical snapshots. Preserve externally observed drift as evidence, restore current approved disabled sharing, and never infer that restoring snapshot hardware retains isolation.
- Snapshot before driver changes; verify actual graph/state file and read-only exact media identity. Stop repeated ineffective guest inputs and distinguish responsive host controls/vCPU activity from actual guest responsiveness or completed installation.

## ADR-021: Fixed wheel remedy commits durable outcomes separately from GUI closure
- Date:2026-10-24
- Retain actual failed imports even when a human reports a completed install; remedy only the two pinned offline wheels in the already verified current guest interpreter, without broader installer replay or runtime bootstrap.
- Flush bounded native step evidence before validating or advancing. Retain one exclusive intent and all uncertain/failed history; do not infer success from GUI closure or delete history to retry.
- Use a shared cancellation-versus-durable-VERIFIED commit boundary. Accepted cancellation before that boundary prevents VERIFIED; a completed durable success precedes any later closure. Only verified GUI completion returns0; identity-only diagnostics have a separate documented status.
- Keep actual host refusal, media/source/test evidence, human guest launch and actual guest package acceptance distinct. Neither the remedy nor a powered-off guest establishes task transport/containment; revalidate exact worker/VM graph after any lifecycle change.

## ADR-022: Operator reorders publication/deployment ahead of VM completion
- Date:2026-10-24
- On explicit operator instruction, preserve the powered-off VM and return to its completion after publication/deployment. Withdraw pending worker-Manager/guest-install actions; the full six-phase objective stays open.
- Advance nonVM Phase5workflow/session readiness and Phase6browser/build/release/deployment gates against existing targets. Keep the unavailable VM provider and its dependent isolated workflow claims disabled in releases.
- Preserve the reviewed read-only preflight and its actual limits: pure/fixture/host-refusal checks establish no actual worker adoption, guest transport, runtime/licensing acceptance or any of the14containment cases. Verify those after returning to the VM.
- Treat release source, staged/dist artifacts, secret/signing material and actual deployed version as separate evidence; the reordering does not turn stale builds or simulated workflow results into accepted releases.

## ADR-023: Web deployment precedes a Windows build matching its actual capabilities
- Date:2026-10-24
- The operator replaced the active goal: deploy the existing Firebase web app first, then build the matching Windows native application. Preserve the broader roadmap's open gates without treating it as the current goal or claiming it complete.
- Use the actual deployed web release as the native parity baseline. Native packaging/build/signing and deferred VM work do not precede completion of web deployment under this order.
- Automatic approval covers routine work within the stated release scope. Keep publication artifacts separate from source/private stores; verify a fresh build and actual hosted behavior, retaining rollback evidence and disabled unavailable execution features.


## ADR-024: Bind native parity to a verified web artifact and restore only the existing API route
- Date:2026-10-24
- Build current web source with public-directory copying disabled, explicit reviewed assets, exact upload/live hash manifests and retained immutable rollback identity. Preserve original hosting exclusions; an inline reference alone does not override an existing private-file exclusion.
- Treat Firebase Hosting deployment, anonymous browser rendering, authenticated workflows and native capability acceptance separately. The live189file proof completes web publication; it does not certify every feature, mobile layout, signed-in flow or global TypeScript cleanliness.
- Restore the existing API hostname through its existing tunnel with a separate narrow configuration, explicit closed legacy routes and default404. Preserve DNS, unrelated healthy service, broad original configuration, credentials, loopback listeners and disabled activation flags. Session connector liveness is not durable autostart; record PID/creation/config identity for exact rollback.
- Begin Windows packaging only after actual live hash/version verification, using that web artifact as the baseline. Preserve unavailable isolated task providers and private documents/databases/models; never include stale dist, plaintext signing credentials or unrelated archive stores.


## ADR-025: Use a source-bound pure Qt parity candidate and verify actual embedded code
- Date:2026-10-24
- Continue the existing native_studio PyQt6 application for native parity. A web wrapper and historical line-count/navigation reports do not certify native behavior.
- Freeze the literal native import closure with a deployed-web baseline, exclude backend/private stores/signers/stale binaries and request standard-user execution. Restrict dependency discovery to reviewed Python/Windows/frozen roots, handling compiler namespace metadata and public CA/stdlib archives explicitly.
- Verify actual PE/version/manifest, complete output hashes and embedded native code against frozen source without launching the application. Keep an unsigned prototype distinct from a functional, signed, publishable release.
- Native startup must not initialize server-owned databases, perform remote updates or open audio automatically. Explicit Play/audition remains functional; failed audition activation retains diagnostics and drops obsolete notes.
- Before packaged acceptance, replace frozen source-repository update/version behavior and verify actual workflow parity; self-issued stored certificates do not establish public publisher trust. Keep unavailable execution/VM gates and six disabled host activation flags.


## ADR-026: Retire observed chat sessions without bypassing ownership or storage gates
- Date:2026-10-24
- Track observed backend/UID notification epochs, including sameUID logout/login hidden by React batching. Old bindings remain retired even when the scalar identity returns.
- Capture previous owned state once before a different actor can mutate the shared store; fence deferred configuration/history effects before restoring or admitting a session. Normalize backend equality through one existing URL policy.
- Repair readiness through verified reconfiguration; preserve durable outbox, identity, ownership confirmation and conflict protections. An offline/auth/storage failure is not permission to display old history or claim saved data.
- Separate controlled source regression proof and actual deployment hashes from real-user typing acceptance. A user-stopped UI session is not bypassed by another control path; obtain a fresh safe observation or the operator's result.
- Frozen native updates report bundled version and require a new installer; they never alter the developer repository or claim a source Git change updated an existing binary.


## ADR-027: Verify browser Firebase ID tokens with their own signing-key family
- Date:2026-10-24
- Use Google's securetoken X509 endpoint for SDK ID tokens; identitytoolkit/relyingparty keys are for session cookies. Preserve signature/issuer/audience/expiry/verified-email/admin checks and the original upstream subject credential.
- Test a cold key fetch as well as cache-seeded claim fixtures, retaining cache/max-age and forged-signature denial. An administrator-key health probe alone does not verify the user's Firebase flow.
- Require actual browser identity/history responses and editable-input proof for the hosted typing symptom. Record unsent typing separately from message/model execution and save workflows; reload without clearing site data or conversation history.


## ADR-028: Native clients use explicit service boundaries; Unreal signaling is session-owned
- Date:2026-10-24
- Bind Windows builds to exact reviewed web manifests and complete LIVE readbacks. Static code/package equivalence does not certify runtime dependencies or capabilities.
- Replace native FE Express server imports/SQLite access with established service routes and worker snapshots; require explicit action confirmation and do not auto-retry uncertain mutations. Preserve manual booking approval and keep credentials out of packages.
- Cold client imports must not initialize backend singletons. Defer legacy source-development engines to their legacy views; packaged service-adapter/auth and real Swarm/DAG functionality remain required before claiming parity.
- Unreal signaling is off by default and started only for an explicit Pixel Streaming session. The dedicated controller owns its signaling process and cleans up by exact identity after engine exit. Preserve occupied ports and reused PIDs; no general ecosystem autostart or blanket taskkill.
- User-stopped computer control ends UI actions for that turn. Preserve the launched process identity and pending verification instead of treating missing UI observations as a crash or retry permission.


## ADR-029: Render real native pattern audio without consuming live playback state
- Export an immutable accepted-control snapshot through a fresh CPU-only engine; keep all callback/device methods and the live ring untouched.
- Validate actual PCM/header/frame data and disk readback before atomic no-overwrite publication. Preserve failed staging evidence and honor cancellation without false saved claims.
- State current-pattern scope honestly; complete playlist/media mixing, MP4 and hardware recording/output remain separate parity requirements.
- Private native local use must connect automatically without user API-key entry; hosted security remains enforced and developer credentials are never packaged.


## ADR-030: Automatic local Windows connection retains backend authorization
- Private native users do not enter API keys. The owned backend publishes one application-scoped current-user/local-machine Windows credential only after binding the exact loopback listener.
- Resolve it at request time with listener PID/creation/executable/owner/origin validation; preserve remote auth, redirect/proxy protections and writer revision/CAS controls. No credential enumeration or developer-secret packaging.
- Own/cancel the bounded publication task in backend lifespan without activating autonomous services. Respect actual pywin32 Unicode-write/UTF16LE-read semantics and stored-byte size limits.
- Keep current-source client proof, packaged GUI proof and standalone recipient companion/bootstrap separate; signing/installer and full parity remain release gates.
