# AI-BS — Codex Tasks, Dependencies & Acceptance Criteria (`CODEX_TASKS.md`)

This file tracks completed checkpoints, active bounded tasks, and remaining Phase 1–6 acceptance criteria. Updated automatically by Codex lifecycle hooks and during checkpoint finalization.

<!-- AUTO_CHECKPOINT_SUMMARY_START -->
## Current Authoritative Checkpoint Summary
- **Last Hook Sync (UTC):** `2026-10-24T15:17:54.269658+00:00` (`SessionStart`)
- **Repository Root:** `C:\AI-BS`
- **Version (`version.txt`):** `v5.329.48`
- **Plan Header:** `Plan revision: 1.61 | Updated: October 24, 2026 | Local application source: v5.329.48`
- **Latest Verified Checkpoint:** `C:\AI-BS\backups\proposal_history_5_329_48_20261024T145341207541Z` (`v5.329.48` / Plan `1.60`, Record `32`)
- **Next Bounded Objective:** Verify fresh standard-worker VM state, then legitimate VM recovery and actual controller acceptance. Source48final verification complete locally; private cloud receipt pending.
- **Active In-Progress Checkpoint:** C:/AI-BS/backups/proposal_history_5_329_48_20261024T145341207541Z/resume_20261024T152738321285Z
- **Authoritative Handoff:** `C:\AI-BS\docs\CODEX_HANDOFF.md` (SHA-256 `94c583bf53f4a87b...`)
<!-- AUTO_CHECKPOINT_SUMMARY_END -->

---

## 1. Completed Bounded Tasks (Trusted-Local Evidence Retained)
- [x] **Phases 1–3 (Historical Trusted-Local Baseline):** Local service bindings (`127.0.0.1:8080`, `8000`, `11434`, `5173`), six disabled activation flags, creative document & personal store preservation, and initial preparation/planning state machine.
- [x] **`v5.329.45` / Plan `1.55` (later diagnostic plan1.57):** Stehouwer planning controls, history and cancellation; generated-code proposals arrived at46, not45.
- [x] **`v5.329.46` / Plan `1.58`:** Live 8080/8000 verification (55 observations) of retained multi-file proposal creation, cancellation, recovery, and 409/422 tamper rejection (`backups/retained_proposal_5_329_46_20261024T141425139154Z`).
- [x] **`v5.329.47` / Plan `1.59`:** BS-Chat `CodingPreparationPanel.jsx` (4 mirrors) and `projectPreparation.js` proposal review controls, Web Crypto SHA-256 verification, same-ID retry, cancellation, and explicit saved-ID inspection/recovery (`backups/proposal_ui_5_329_47_20261024T143740416296Z`).

---

## 2. Active & Next Bounded VM-Independent Tasks
- [ ] **`v5.329.48` / Plan `1.60` — Owner-Scoped Metadata Discovery of Saved Proposal IDs After Reload:**
  - **Dependencies:** `v5.329.46` proposal journal store (`backend/core/coding_preparation_proposals.py`, `backend/routers/coding_preparation_router.py`) and `v5.329.47` panel controls (`frontend/src/utils/projectPreparation.js`, 4 `CodingPreparationPanel.jsx` mirrors).
  - **Acceptance Criteria:**
    1. Paged owner-scoped metadata listing under the authenticated preparation route.
    2. Tests for owner isolation, malformed/corrupt metadata, empty history, pagination bounds, and no-store-initialization behavior.
    3. Client/panel wiring to discover saved proposal IDs after reload without inference replay, automatic execution, or apply.
    4. 100% 4-mirror SHA-256 parity on `CodingPreparationPanel.jsx`, preservation of all 888 documents + personal SQLite rows, and verified checkpoint/ledger receipt.
- [ ] **Next Bounded Preparation/Proposal Tasks (`v5.329.49+`):**
  - Proposal comparison / review-state stale indicator refinement and preparation/plan/proposal lineage navigation in BS-Chat without enabling unisolated host execution.
  - Real signed-in browser UI verification on `http://localhost:5173` now that `.codex/browser/config.toml` and `.codex/browser/sessions/01a16652-3fd9-7750-877a-5b57693481ac.toml` allow `http://localhost:5173` and Chrome (`Default` profile) is active.

---

## 3. Open Larger-Project & Deferred Phase Gates (Do Not Claim Complete Early)
- [ ] **Phase 4 (Explicitly Deferred by User):** Actual Windows VM / Sandbox 14-case isolation, controller enforcement, and transport acceptance.
- [ ] **Phase 5 (Remaining Gates):** Larger-project isolated verification execution, review/apply seal, and atomic rollback verification.
- [ ] **Phase 6 (Remaining Gates):** Browser acceptance, Firebase deployment readiness, native Windows release packaging/signing, rollback drills, confidential-method-safe overview, and measured long-horizon memory/learning benchmarks.


## Source48 current progress correction - 2026-10-24T15:11:09.138002+00:00

- [x]38backend /84client /30offline view /23source observations and four panel parity checks pass.
- [x]Source48metadata backups and selected document/vault/master pre-restart preservation retained.
- [ ]Controlled backend reload and source48actual API/client history verification: pending one diagnosed Codex-app connection; previous attempt changed no processes.
- [ ]Finalize source48/plan1.60 and cloud verification after actual checks pass. Last finalized checkpoint is still47/1.59.
- [ ]Actual Browser tool connection and UI acceptance: pending. Global C:/Users/footb/.codex/browser/config.toml allows localhost5173, but project browser config/session paths in older prose were not found and tool access was not established.

Do not begin the optional49comparison/navigation refinements before48is finalized. VM remains explicitly deferred. See ADR-005 for actual flag and database-path authority corrections.


## User-requested pause - 2026-10-24T15:19:26.942391+00:00

- [x]Source48implementation,38backend/84client/30view/23source checks and26actualAPI/client observations pass.
- [x]Guarded backend reload succeeded after an externally closed connection; new368872/launcher291908, other services unchanged. Original failed observer preserved.
- [x]Paused source/evidence/memory snapshots and SHA256 manifest saved in active48pause_checkpoint.json.
- [ ]Source48post-restart personal/document/DB preservation report and final checkpoint/plan1.60.
- [ ]Sanitized cloud ledger sync for48/pause. Latest cloud receipt remains47/Record31.
- [ ]Resume development only after user resumes. No new side task, VM or publication during pause.


## Current resumed state - 2026-10-24T15:42:20.565050+00:00

- [x] User resumed work; VM completion reauthorized; continue without routine checkpoint pauses.
- [x] Source48hash-bound implementation,38backend/84client/30view/23source checks and prior26actual observations retained. Fresh16API/client/offline-view observations pass after service restoration.
- [x] Post-restoration888document/copy hashes, all retained personal rows and authority DB integrity/schema/count checks passed.
- [x] Current runtime identities/access denials and all six false flags verified; previous failed observers retained.
- [x] Exact private Record33ledger cloud readback:101995bytes; private same-file receipt in resumed checkpoint.
- [ ] Fresh worker VM inspection output, legitimate VM recovery/provisioning and real14-case containment/controller acceptance.
- [ ] Remaining Phase5isolated checks/apply and Phase6release/browser/signing/overview. No new whole-phase completion.


Current source48/plan1.61 resumed checkpoint finalized locally and cloud-verified. Next: fix the newly appeared false-positive Phase4port-only harness while awaiting fresh standard-worker VM state; actual VM/controller acceptance remains incomplete.


## Latest VM inspection confirmed - 2026-10-24T15:52:15.168489+00:00

- [x] Fresh SID1005/nonadmin worker state, actual ABORTEDVM/current77percent snapshot and all8NICsdisabled verified from successful VBoxManage queries.
- [x] Passwordless InteractiveToken dispatch probe was observed not running, then disabled; do not replay or count it as controller acceptance.
- [ ] Narrow existing-worker controller, preserved headless recovery and actual installation/provisioning/containment gates.
- [ ] Newest VM note cloud sync; source48Record33is already privately byte-verified.
