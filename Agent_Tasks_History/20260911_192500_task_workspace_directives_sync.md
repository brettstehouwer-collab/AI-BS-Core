# Master Task Plan: Workspace Directives, Rules, and Subsystem Configuration Synchronization (v5.259.0)

## Status: PENDING USER APPROVAL

- [ ] **Phase 1: IDE Workspace Configuration (`AI-BS.code-workspace`)** <!-- id: 1 -->
  - [ ] Add missing active subsystems to workspace folders: `backend`, `go-core`, `trainer_frontend`, `mobile-app`, `game_trainer`, `screenplay_projects`, `docs`
  - [ ] Enhance `files.exclude` and `search.exclude` to prevent IDE performance degradation from massive cache and model swap files
  - [ ] Validate JSON syntax of `AI-BS.code-workspace`
- [ ] **Phase 2: Antigravity IDE & System Rules Harmonization** <!-- id: 2 -->
  - [ ] Replace obsolete `modernc.org/libc` directives in `.antigravityrules` with current ecosystem rules
  - [ ] Synchronize `.agentrules` with the complete 18-port ecosystem assignments and core mandates
  - [ ] Update `AI-BS_DEVELOPMENT_RULES.md` with full topology and operational directives
- [ ] **Phase 3: Modular Rule Definitions (`.agents/rules/`)** <!-- id: 3 -->
  - [ ] Create discrete markdown rule definitions in `.agents/rules/` for Cost Constraints, Deployment, Master Ledgers, Safety Filter Directive (S1/S3/S4), Zero-Mock Real Money, Interactive Proceed Standard, IDE Workspace Integrity, WSL2 Script Patching, Multi-Tenant Media Routing, and UI Version Parity
- [ ] **Phase 4: State Checkpoint & Master Ledger Synchronization** <!-- id: 4 -->
  - [ ] Update `SAVED_CHECKPOINT.md` from stale v5.242.0 to current state v5.259.0 with complete release summary and resume keyword `RESUME_WORKSPACE_DIRECTIVES_SYNC_V5_259`
  - [ ] Log entry in `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` for v5.259.0
  - [ ] Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` to v5.259.0, copy artifact to `saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md`, and log in `NotebookLM_Records/artifact_history.md`
  - [ ] Synchronize `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`
- [ ] **Phase 5: UI Version Parity Sweep & Production Deployment** <!-- id: 5 -->
  - [ ] Bump version to `5.259.0` across `version.txt`, `package.json`, `version.json`, `sw.js`
  - [ ] Sweep frontend UI badges in `App.jsx`, `TopNavbar.jsx`, `Sidebar.jsx`, `ChatTab.jsx` across all mirror paths
  - [ ] Compile production bundle (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`)
