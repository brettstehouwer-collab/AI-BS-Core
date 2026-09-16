# Implementation Plan: BS-Chat UI De-Clutter, Dynamic Artifacts Hub & Autonomous Program Builder

Address UI overlay interference, keep all tool options and workspace artifacts (tasks, plans, media, manuals) synchronized in real-time within BS-Chat, and transform BS-Chat into an autonomous program generation and building workstation.

---

## User Review Required

> [!IMPORTANT]
> **Floating Overlays & Controls De-Clutter:** We are moving the fixed `.team-chat-fab` (the blue floating circle in the bottom right corner) and organizing all top-level tool pills, `@Mentions`, and context gauges into a streamlined, collapsible HUD control dock. This ensures the chat input field, send buttons, and audio controls remain 100% unobstructed.

> [!TIP]
> **Autonomous Program Builder:** When you request the creation of a program, script, or application in BS-Chat, the system will autonomously scaffold the multi-file architecture, write clean source files, execute pre-flight syntax checks, run the program in an isolated sandbox, and present an interactive execution card with file explorer, terminal output, and 1-click export.

---

## Proposed Changes

Grouped by component layer:

### 1. Frontend UI & Layout Architecture (`frontend/src/components/ChatTab.jsx`, `TeamChatDrawer.css`)

#### [MODIFY] [TeamChatDrawer.css](file:///c:/AI-BS/frontend/src/components/TeamChatDrawer.css)
- Adjust `.team-chat-fab` positioning, add z-index containment, and ensure it docks unobtrusively or collapses when the primary BS-Chat workspace is active.

#### [MODIFY] [ChatTab.jsx](file:///c:/AI-BS/frontend/src/components/ChatTab.jsx) & [ChatTab.jsx](file:///c:/AI-BS/frontend/components/ChatTab.jsx)
- **Unified Command Dock:** Consolidate the context budget gauge, active agent tools, `@Tags`, quick presets, and governance triggers into a clean, compact, non-overlapping bottom control strip.
- **Dynamic Artifacts & Tool Sync Drawer:** Add a live "Workspace Artifacts & Tools" panel directly accessible in the chat header/toolbar, displaying:
  - 📋 Active & Archived Tasks (`task.md`, `Agent_Tasks_History`)
  - 📐 Implementation Plans (`implementation_plan.md`, `Agent_Implementation_Plans_History`)
  - 🖼️ Media & Visuals (`saved_data/artifacts/`, screenshots, generated assets)
  - 📖 System Ledgers & Manuals (`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`)
  - 🎛️ Dynamic Tool Toggles (Matrix Doctor, OSINT Recon, Autonomous Program Builder, Audio DSP, etc.)
- **Interactive Program Builder Card:** Render live program execution cards (`ProgramBuilderCard`) when the LLM generates a program, showing the file tree, code viewer, live terminal runner, and export actions.

---

### 2. Backend Autonomous Program Builder & Artifacts API (`backend/core/`, `backend/routers/`)

#### [NEW] [program_builder_engine.py](file:///c:/AI-BS/backend/core/program_builder_engine.py)
- Autonomous software scaffolding engine:
  - Supports Python scripts/modules, React/Vite components, Node.js tools, FastAPI microservices, and shell utilities.
  - Multi-file directory scaffolding under `C:\AI-BS\saved_data\built_programs\<project_name>\`.
  - Sandboxed execution with real-time process monitoring, timeout safety, and stdout/stderr capture.
  - Automated ZIP packaging and export.

#### [NEW] [artifacts_sync_router.py](file:///c:/AI-BS/backend/routers/artifacts_sync_router.py)
- API endpoint `GET /api/artifacts/live` querying live tasks, implementation plans, generated media, system ledgers, and built programs with real-time file modification timestamps.
- API endpoints `POST /api/program_builder/build`, `POST /api/program_builder/run`, `POST /api/program_builder/export`.

#### [MODIFY] [AI_BS_Backend.py](file:///c:/AI-BS/backend/AI_BS_Backend.py) & [real_system_tools.py](file:///c:/AI-BS/backend/core/real_system_tools.py)
- Mount `artifacts_sync_router` and hook the Autonomous Program Builder into tool intent detection in `dispatcher.py` and `real_system_tools.py`.

---

### 3. Master Ledger & Production Synchronization

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///c:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Log `v5.157.0` release entry detailing the UI overlay resolution, live artifact synchronization, and autonomous program builder.

#### [MODIFY] [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///c:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Bump version to `5.157.0` and save versioned manual copy to `saved_data/artifacts/20260902_AI_BS_Master_Ecosystem_Manual.md`.

---

## Verification Plan

### Automated & Backend Tests
- Execute test script validating `GET /api/artifacts/live` returns real workspace tasks, plans, media, and ledgers.
- Execute test script validating `program_builder_engine.py` builds, tests, runs, and exports a sample program (e.g., Python automated lead scraper / utility).

### Manual & UI Verification
- Verify in browser that all floating overlays (`.team-chat-fab`, overlapping badges) are cleanly positioned and never obstruct input fields.
- Verify that the Artifacts Hub displays live files with 1-click preview and insertion.
- Prompt BS-Chat: *"Build an automated price alert script for CRO and BTC with desktop notifications"* and verify that the Autonomous Program Builder card scaffolds files, runs tests, and provides 1-click execution.
- Build frontend and deploy to live Firebase Hosting (`ai-bs-dashboard.web.app`).
