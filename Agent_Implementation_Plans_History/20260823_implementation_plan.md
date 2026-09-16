# Apply AI-BS Ecosystem Upgrades to Production

This plan outlines the steps required to transition the successfully tested Sandbox Simulation Upgrades (Phase 2 & 3) directly into the live `C:\AI-BS` production ecosystem.

## User Review Required
> [!IMPORTANT]
> The changes below will modify the core live services (`AI_BS_Backend.py`). Please review the injection points to ensure they align with the current operational requirements before I proceed with the execution.

## Proposed Changes

### Backend Integrations (Live Production)

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- **VRAM Arbitration**: Import and initialize `vram_orchestrator` from `vram_manager`. Integrate it into the lifecycle events (e.g., ComfyUI trigger endpoints) to actively request and release GPU budget.
- **High-Performance DB Connection**: Replace existing standard `sqlite3.connect` initializations with the hardened `get_sqlite_connection` imported from `db_manager.py` to ensure zero-lock WAL mode concurrency is active across all endpoints.
- **Event Bus Integration**: Import `aibs_event_bus` from `core.aibs_event_bus`. Hook it into the FastAPI lifecycle (`@app.on_event("startup")` or `lifespan` context manager).
- **Daemon Engine**: Wire the background daemon polling into `consolidated_daemon_engine.py`'s `asyncio.TaskGroup` to cut idle Python memory footprint and prevent thread contention.

### Architectural Master Ledger Updates

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Append a timestamped Development Entry & AI Rationale detailing the rollout of the Sandbox Simulation Upgrades (Phase 1-4).
- Update Technical Specifications to reflect the newly integrated IPC ring, VRAM arbiter, and SQLite WAL pragmas.

#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
- Update step-by-step operational guides for the new Event Bus triggers.
- Bump system version number and persist an artifact copy to `saved_data/artifacts/YYYYMMDD_AI_BS_Master_Ecosystem_Manual.md`.

## Verification Plan

### Automated Tests
- The sandbox tests have already successfully passed in the previous phase. 

### Manual Verification
- Start the live AI-BS ecosystem (`Launch_AI_BS.bat`).
- Trigger a ComfyUI generation job to verify VRAM offloading via `nvidia-smi`.
- Verify cross-program event dispatch (e.g., from Prestige Mobile Wash to Master Accounting).
