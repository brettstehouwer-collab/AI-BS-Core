# AI-BS — Codex Tasks, Dependencies & Acceptance Criteria (`CODEX_TASKS.md`)

This file tracks completed checkpoints, active bounded tasks, and remaining Phase 1–6 acceptance criteria. Updated automatically by Codex lifecycle hooks and during checkpoint finalization.

<!-- AUTO_CHECKPOINT_SUMMARY_START -->
## Current Authoritative Checkpoint Summary
- **Last Hook Sync (UTC):** `2026-10-24T15:09:45.066663+00:00` (`PostCompact`)
- **Repository Root:** `C:\AI-BS`
- **Version (`version.txt`):** `v5.329.48`
- **Plan Header:** `Plan revision: 1.59 | Updated: October 24, 2026 | Local application source: v5.329.47`
- **Latest Verified Checkpoint:** `C:\AI-BS\backups\proposal_ui_5_329_47_20261024T143740416296Z` (`v5.329.47` / Plan `1.59`, Record `31`)
- **Next Bounded Objective:** Owner-scoped metadata proposal-ID discovery; actual browser/isolated execution/release gates remain open.
- **Active In-Progress Checkpoint:** `C:\AI-BS\backups\proposal_history_5_329_48_20261024T145341207541Z`
- **Authoritative Handoff:** `C:\AI-BS\docs\CODEX_HANDOFF.md` (SHA-256 `3baaeafe6667720d...`)
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
