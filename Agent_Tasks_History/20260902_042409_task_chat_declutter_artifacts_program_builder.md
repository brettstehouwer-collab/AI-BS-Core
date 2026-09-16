# Task List: BS-Chat UI De-Clutter, Dynamic Artifacts Hub & Autonomous Program Builder

- [x] **Phase 1: UI De-Clutter & Overlay Cleanup** <!-- id: 0 -->
  - [x] Relocate or suppress intrusive fixed floating buttons (`.team-chat-fab`, overlapping badges) to prevent obstructing input bars and chat controls <!-- id: 1 -->
  - [x] Redesign `ChatTab.jsx` bottom dock: unify `@Mentions`, Context Budget gauge, Tool Toggles, and Quick Presets into an elegant, non-obstructive command strip <!-- id: 2 -->
  - [x] Ensure version badges and governance modal triggers sit cleanly without viewport collision <!-- id: 3 -->

- [x] **Phase 2: Real-Time Dynamic Artifacts & Tool Sync Hub** <!-- id: 4 -->
  - [x] Build backend API endpoint `/api/artifacts/live` querying live workspace artifacts (`task.md`, `implementation_plan.md`, `saved_data/artifacts/`, `Agent_Tasks_History`, `Agent_Implementation_Plans_History`, media files) <!-- id: 5 -->
  - [x] Create real-time Artifacts & Tool Hub panel in `ChatTab.jsx` allowing 1-click inspection, preview, insertion into prompt context, and live synchronization <!-- id: 6 -->
  - [x] Keep tool options and active agent switches dynamically up to date with ecosystem state <!-- id: 7 -->

- [x] **Phase 3: Autonomous Program Builder Engine** <!-- id: 8 -->
  - [x] Build `backend/core/program_builder_engine.py` supporting autonomous project scaffolding, multi-file code generation, live testing/execution in sandbox, error self-correction, and ZIP export to `saved_data/built_programs/` <!-- id: 9 -->
  - [x] Wire `/api/program_builder/build`, `/api/program_builder/run`, and `/api/program_builder/export` routes in FastAPI core backend <!-- id: 10 -->
  - [x] Intercept program creation requests in `real_system_tools.py` and `dispatcher.py` to auto-invoke the Program Builder <!-- id: 11 -->
  - [x] Build interactive `ArtifactsAndToolsModal.jsx` inside `ChatTab.jsx` with file tree explorer, code viewer, live terminal execution console, and 1-click run/export buttons <!-- id: 12 -->

- [x] **Phase 4: Verification, Ledger Updates & Live Production Deployment** <!-- id: 13 -->
  - [x] Test real-time artifact fetching, program building, execution, and UI responsiveness <!-- id: 14 -->
  - [x] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (bump to `v5.157.0`) <!-- id: 15 -->
  - [x] Persist manual artifact and update `NotebookLM_Records/artifact_history.md` and `SAVED_CHECKPOINT.md` <!-- id: 16 -->
  - [x] Build production frontend and deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`) <!-- id: 17 -->
