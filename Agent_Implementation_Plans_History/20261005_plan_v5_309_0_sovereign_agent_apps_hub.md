# Implementation Plan: Sovereign Agent Apps Hub & Mixture-of-Specialists (MoE) Routing Architecture

## Overview
Based on the forensic audit of your local 29-model Ollama fleet (Port 11434/11435) and the 14-tool agent launcher matrix (Claude Code, Codex CLI, OpenClaw, OpenCode, Hermes Agent, Hermes Desktop, Droid, Pi, Cline, Copilot CLI, Oh My Pi, DeepSeek Harness, Qwen Code, Terminal), this implementation plan unites these capabilities into a **native, 100% sovereign Agentic Suite** directly inside AI-BS.

---

## Architectural Blueprint

```
                     ┌──────────────────────────────────────────────────────────┐
                     │     SOVEREIGN AGENT APPS HUB (14-TOOL LAUNCHER)          │
                     │  (Claude Code, Codex, OpenCode, Hermes, Cline, Terminal) │
                     └────────────────────────────┬─────────────────────────────┘
                                                  │
                                                  ▼
                     ┌──────────────────────────────────────────────────────────┐
                     │      SOVEREIGN MoE SPECIALIST ROUTER (Port 8080)         │
                     │         (backend/core/moe_specialist_router.py)          │
                     └──────┬─────────────────────┬──────────────────────┬──────┘
                            │                     │                      │
         [Deterministic Code / Tools]   [Unrestricted Dialogue]   [Vision / Perception]
                    ▼                             ▼                      ▼
         qwen2.5-coder:latest          stehouwer_dolphin:8b         qwen3.6 / gemma4
              (32.8B Q5_K_M)                 (8.0B Q8_0)             (262k Context)
```

---

## Proposed Changes

### Phase 1: Sovereign MoE (Mixture of Specialists) Routing Engine
#### [backend/core/sovereign_reasoning/moe_specialist_router.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/moe_specialist_router.py)
- Create dynamic task-classifier and multi-model router:
  - **Code, Polyglot, Refactoring & AST Tasks** ➔ Dispatches to `qwen2.5-coder:latest` / `stehouwer_llm:latest` (32.8B).
  - **Creative Writing, Narrative Prose, Dialogue & Fire Writing** ➔ Dispatches to `stehouwer_dolphin:latest` (8.0B unfiltered).
  - **Tool-Use, JSON Schema & Function Calling** ➔ Dispatches to `stehouwer-hermes:latest` (8.0B ChatML).
  - **Vision, Layout Analysis & Image Multimodal Tasks** ➔ Dispatches to `qwen3.6:latest` / `gemma4:12b` (262k context).
  - **Deep Philosophical Verification & Reasoning** ➔ Dispatches to `llama3.3:70b` (70.6B).
  - **Vector Embedding & RAG Context** ➔ Dispatches to `nomic-embed-text:latest`.
- Mount REST endpoints in `backend/AI_BS_Backend.py` under `/api/v1/moe/route` and `/api/v1/moe/models`.

### Phase 2: Sovereign Agent Tools & Harness Runner
#### [backend/modules/agent_harness_runner.py](file:///C:/AI-BS/backend/modules/agent_harness_runner.py)
- Create execution adapters for the 14 agent types:
  1. **Claude Code / Codex CLI / Qwen Code / DeepSeek Harness**: Terminal-based autonomous coding harness streaming diffs and terminal commands.
  2. **OpenClaw / OpenCode**: Autonomous Python/Shell sandbox execution engine with live stdio streaming.
  3. **Hermes Agent / Hermes Desktop**: Structured JSON tool-calling agent loop.
  4. **Droid / Pi / Oh My Pi**: Lightweight persona & task assistants.
  5. **Cline / Copilot CLI**: In-browser split-pane diff editor and file tree inspector.
  6. **Terminal**: Direct interactive PowerShell host shell with execution policy bypass.

### Phase 3: High-Aesthetic 14-App Launcher Tab
#### [frontend/src/components/SovereignAgentAppsTab.jsx](file:///C:/AI-BS/frontend/src/components/SovereignAgentAppsTab.jsx)
- Build high-aesthetic dark-mode interactive workspace tab:
  - **14-App Visual Grid**: Direct launcher cards matching the Ollama Apps matrix with custom icons, operational status indicators, and active model tags.
  - **Active Session Workspace**: Split-view panel displaying live session chat, terminal runner, and file patch inspector.
  - **Specialist Router Switcher**: Live HUD showing which model is handling the active task with real-time VRAM allocation and token streaming stats.
- **Rule 1 Multi-Mirror Law**: Synchronize across all 4 frontend mirrors with 100% SHA-256 byte parity.
- Register `sovereign_apps` tab in `frontend/App.jsx`.

### Phase 4: Verification & Production Release
- Verify Python AST syntax with `py_compile`.
- Test MoE endpoint classification and model streaming over Port 11434.
- Assert 100% SHA-256 byte parity across all 4 mirrors (`verify-mirror-parity.ps1`).
- Compile Vite production bundle and deploy live to Firebase Hosting.
- Bump version to `v5.309.0` and synchronize master ledgers.

---

## Verification Plan

### Automated Tests
1. **MoE Router Classification Test**: Verify query "Write a binary search tree in C++" routes to `qwen2.5-coder`, and "Write an emotional dialogue" routes to `stehouwer_dolphin`.
2. **Mirror Parity**: Run `verify-mirror-parity.ps1` to assert 100% byte match.
3. **Pytest Suite**: Execute `pytest tests` to guarantee zero regressions.
4. **Vite Production Build**: `npm run build` cleanly in `frontend`.
