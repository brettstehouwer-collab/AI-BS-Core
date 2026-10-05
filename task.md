# Master Task: Sovereign Agent Apps Hub & Mixture-of-Specialists (MoE) Architecture

## Status: IN PROGRESS (v5.309.0-dev)

- [ ] **Stage 1: Sovereign MoE (Mixture-of-Specialists) Backend Engine**
  - [ ] Implement `backend/core/sovereign_reasoning/moe_specialist_router.py` with intent classification across code, prose, tool, and vision domains.
  - [ ] Map domains to local Ollama weights on Port 11434 (`qwen2.5-coder:latest`, `stehouwer_dolphin:latest`, `stehouwer-hermes:latest`, `qwen3.6:latest`, `llama3.3:70b`).
  - [ ] Mount REST router `/api/v1/moe` in `backend/AI_BS_Backend.py`.
  - [ ] Validate Python AST syntax and route classification accuracy.

- [ ] **Stage 2: Sovereign Agent Harness Execution Adapters**
  - [ ] Implement `backend/modules/agent_harness_runner.py` providing session management and adapters for Terminal coding agents (Aider/Claude Code style), code execution interpreters (OpenCode), and function calling loops (Hermes).
  - [ ] Wire live PowerShell bypass subprocess execution and diff streaming.

- [ ] **Stage 3: 14-App Visual Launcher Workspace & Multi-Mirror Sync**
  - [ ] Author high-aesthetic dark-mode React component `frontend/src/components/SovereignAgentAppsTab.jsx` mirroring the Ollama Apps matrix.
  - [ ] Include active session drawer, terminal console, and specialist model router HUD.
  - [ ] Mount tab `sovereign_apps` into `frontend/App.jsx`.
  - [ ] Synchronize across all 4 mirrors (`frontend/src/components/`, `frontend/components/`, `frontend/src/components/components/`, `frontend/components/components/`) maintaining 100% SHA-256 byte parity.

- [ ] **Stage 4: Automated Verification, Production Build & Cloud Sync**
  - [ ] Run `pytest tests` to assert 0 regressions.
  - [ ] Run `verify-mirror-parity.ps1` to assert 100% SHA-256 byte parity across all mirror files.
  - [ ] Execute Vite production build in `frontend`.
  - [ ] Deploy live to Firebase Hosting (`https://ai-bs-dashboard.web.app`).
  - [ ] Perform Milestone Commit Standard: bump version to `v5.309.0` and update master architectural ledgers.
