# Implementation Plan: Workspace Directives, Rules, and Subsystem Configuration Synchronization (v5.259.0)

A comprehensive audit and synchronization to bring the active workspace definitions, IDE workspace configuration, Antigravity rules, agent directives, system topology ports, and master state ledgers into 100% alignment with current ecosystem operations.

---

## User Review Required

> [!IMPORTANT]
> **Explicit Consent & Interactive 'Proceed' Standard:**
> Per ecosystem rules, no changes will execute until you approve them. You may click the interactive **'Proceed'** button in this side-panel or provide confirmation in chat.

> [!NOTE]
> **Zero Breaking Changes to Code:**
> This operation updates configuration, workspace manifest, rules files, port definitions, modular rule catalogs, and master ledgers. No backend application logic or database state will be destructively altered.

---

## Forensic Discrepancy Findings

Our audit identified several critical areas where the workspace had fallen out of sync with recent developments:

1. **`AI-BS.code-workspace` Configuration Lag:**
   - The workspace currently exposes only 4 folders (`AI-BS Ecosystem (Root)`, `Frontend`, `Stehouwer Publishing Server`, `Prestige Mobile Wash App`).
   - Missing major subsystems introduced across v5.243–v5.258:
     - `backend` (FastAPI Core, Tools, Cognitive Reasoning Modules)
     - `go-core` (Go Native Memory Engine, IPC Gateway, Trainer Daemons)
     - `trainer_frontend` (Electron + React BTD6 Memory Trainer)
     - `mobile-app` (React Native Expo Mobile Studio)
     - `game_trainer` (Process Memory Engineering Lab)
     - `screenplay_projects` (Multi-Modal Screenplay Vault)
     - `docs` (Ecosystem Manuals, System Architecture & Records)
   - Missing file exclusion rules for heavy background artifacts (`kaalia.log`, `symbol_graph.json` [252 MB], `py_health_audit.json` [24 MB], `.ollama`, `VRAM_Tensor_Swap`, `Context_Memory_Swap`), causing unnecessary IDE indexing overhead.

2. **`.antigravityrules` Obsolete Content:**
   - `.antigravityrules` still contains legacy C/Go translation directives from `modernc.org/libc` and obsolete `cmd /c` rules instead of the authoritative AI-BS ecosystem directives.

3. **`.agentrules` & `AI-BS_DEVELOPMENT_RULES.md` Port & Rule Gaps:**
   - Both files lack newly integrated ports (Port 8007 Crypto Swarm, Port 8088 Broadcast Kernel/Media Processor, Port 8189 ComfyUI Secondary, etc.).
   - Both lack recent high-priority directives codified in `.agents/AGENTS.md` (e.g., S1/S3/S4 immutable safety lock, Zero-Mock Real Money Rule, Interactive Proceed Button Standard, WSL2 Script Patching, Multi-Tenant Routing).

4. **Modular Rule Catalog Deficiency (`.agents/rules/`):**
   - `.agents/rules/` only contained `FIRE_WRITING_RULE.md`, leaving other strict directives unpartitioned for modular rule loading.

5. **`SAVED_CHECKPOINT.md` Stale Version:**
   - The root checkpoint file was last saved at `v5.242.0` (2026-09-10), lagging 16 major releases behind the active `v5.258.0` state.

---

## Proposed Changes

### Phase 1: IDE Workspace Configuration (`AI-BS.code-workspace`)

#### [MODIFY] [`AI-BS.code-workspace`](file:///C:/AI-BS/AI-BS.code-workspace)
- Add entries for `backend`, `go-core`, `trainer_frontend`, `mobile-app`, `game_trainer`, `screenplay_projects`, and `docs`.
- Update `files.exclude` and `search.exclude` to filter out large binary archives, log caches, and temporary model swap buffers without hiding project source trees.

---

### Phase 2: Antigravity IDE & System Rules Harmonization

#### [MODIFY] [`.antigravityrules`](file:///C:/AI-BS/.antigravityrules)
- Replace obsolete `modernc.org/libc` text with the complete, modern operational directives for Antigravity: Cost Constraints, Safe Command Execution (PowerShell), File Editing Standards, Multi-Tenant Headers, S1/S3/S4 Safety Guarantee, and Continuous Ledger Maintenance.

#### [MODIFY] [`.agentrules`](file:///C:/AI-BS/.agentrules)
- Synchronize port assignments to full 18-port ecosystem matrix.
- Codify the Zero-Mock Real Money Rule, Interactive Proceed Standard, and UI Parity Rule.

#### [MODIFY] [`AI-BS_DEVELOPMENT_RULES.md`](file:///C:/AI-BS/AI-BS_DEVELOPMENT_RULES.md)
- Harmonize ports and operational protocols across all sections.

---

### Phase 3: Modular Rule Definitions (`.agents/rules/`)

#### [NEW] [`.agents/rules/01_COST_CONSTRAINTS.md`](file:///C:/AI-BS/.agents/rules/01_COST_CONSTRAINTS.md)
#### [NEW] [`.agents/rules/02_DEPLOYMENT_STANDARD.md`](file:///C:/AI-BS/.agents/rules/02_DEPLOYMENT_STANDARD.md)
#### [NEW] [`.agents/rules/03_MASTER_LEDGER_MAINTENANCE.md`](file:///C:/AI-BS/.agents/rules/03_MASTER_LEDGER_MAINTENANCE.md)
#### [NEW] [`.agents/rules/04_OBJECTIVE_COMMUNICATION.md`](file:///C:/AI-BS/.agents/rules/04_OBJECTIVE_COMMUNICATION.md)
#### [NEW] [`.agents/rules/05_SAFETY_FILTER_DIRECTIVE.md`](file:///C:/AI-BS/.agents/rules/05_SAFETY_FILTER_DIRECTIVE.md)
#### [NEW] [`.agents/rules/06_ZERO_MOCK_INTEGRITY.md`](file:///C:/AI-BS/.agents/rules/06_ZERO_MOCK_INTEGRITY.md)
#### [NEW] [`.agents/rules/07_INTERACTIVE_PROCEED_STANDARD.md`](file:///C:/AI-BS/.agents/rules/07_INTERACTIVE_PROCEED_STANDARD.md)
#### [NEW] [`.agents/rules/08_IDE_WORKSPACE_INTEGRITY.md`](file:///C:/AI-BS/.agents/rules/08_IDE_WORKSPACE_INTEGRITY.md)
#### [NEW] [`.agents/rules/09_WSL2_SCRIPT_PATCHING.md`](file:///C:/AI-BS/.agents/rules/09_WSL2_SCRIPT_PATCHING.md)
#### [NEW] [`.agents/rules/10_MULTI_TENANT_MEDIA_ROUTING.md`](file:///C:/AI-BS/.agents/rules/10_MULTI_TENANT_MEDIA_ROUTING.md)
#### [NEW] [`.agents/rules/11_UI_VERSION_PARITY.md`](file:///C:/AI-BS/.agents/rules/11_UI_VERSION_PARITY.md)

---

### Phase 4: State Checkpoint & Master Ledger Synchronization

#### [MODIFY] [`SAVED_CHECKPOINT.md`](file:///C:/AI-BS/SAVED_CHECKPOINT.md)
- Bring checkpoint from `v5.242.0` up to `v5.259.0` with full executive summary of releases v5.243 through v5.259.
- Provide unique resume keyword: `RESUME_WORKSPACE_DIRECTIVES_SYNC_V5_259`.

#### [MODIFY] [`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Append timestamped entry for `v5.259.0` detailing workspace, rules, and configuration synchronization.

#### [MODIFY] [`docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Add section for `5.259.0` and bump current ecosystem version to `5.259.0`.
- Persist copy to `saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md`.
- Log lineage entry in `NotebookLM_Records/artifact_history.md`.

#### [MODIFY] Chronologies & Indices
- Synchronize [`MASTER_TASKS_CHRONOLOGY.md`](file:///C:/AI-BS/MASTER_TASKS_CHRONOLOGY.md), [`MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`](file:///C:/AI-BS/MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md), and [`MASTER_HISTORICAL_INDEX.md`](file:///C:/AI-BS/MASTER_HISTORICAL_INDEX.md).

---

### Phase 5: UI Version Parity Sweep & Production Deployment

#### [MODIFY] Version manifests & frontend files
- Update `version.txt`, `frontend/package.json`, `frontend/public/version.json`, `frontend/public/updates/version.json`, `frontend/public/sw.js`.
- Sweep version badges in `frontend/App.jsx`, `TopNavbar.jsx`, `Sidebar.jsx`, `ChatTab.jsx` across all mirror paths to `v5.259.0`.
- Execute `npm run build` and `firebase deploy --only hosting --non-interactive` from `C:\AI-BS\frontend`.

---

## Verification Plan

### Automated Verification
- Verify JSON syntax validity of `AI-BS.code-workspace`.
- Run Python verification script to confirm all ports across `AI-BS_DEVELOPMENT_RULES.md`, `.agentrules`, and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` match 100%.
- Run `npm run build` in `frontend` to verify 0 build errors.

### Manual Verification
- Verify that `AI-BS.code-workspace` loads cleanly with all project folders.
- Verify live Firebase deployment at `https://ai-bs-dashboard.web.app` responds with `v5.259.0`.
