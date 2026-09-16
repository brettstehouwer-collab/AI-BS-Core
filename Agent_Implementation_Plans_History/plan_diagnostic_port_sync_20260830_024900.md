# Diagnostic & Port Synchronization Fix (v5.146.0)

Resolve browser console errors across the AI-BS ecosystem:
1. **Port 8088 Connection Refused (`/api/windows`, `/ws/telemetry`, `/api/audio/search`):** AI-BS Broadcast Kernel (`backend/aibs_broadcast_kernel.py`) is not active in the background and was omitted from the background process spawn block in `Launch_AI_BS.bat`.
2. **Port 8006 HTTP 404 (`/api/social/status`):** Social Daemon (`backend/aibs_social_daemon.py`) is missing the `/api/social/status` and `/status` route handler probed by `BroadcastStudioApp`.
3. **Port 8002 HTTP 410 Gone (`/api/v1/heartbeat`):** ChromaDB v0.5+ deprecated `/api/v1/heartbeat` in favor of `/api/v2/heartbeat`.
4. **Tone.js AudioContext Suspension:** Standard browser policy warning requiring user gesture before starting Web Audio graph.

## Proposed Changes

### Backend Daemons & System Scripts

#### [MODIFY] [aibs_social_daemon.py](file:///C:/AI-BS/backend/aibs_social_daemon.py)
- Add `@app.get("/api/social/status")` and `@app.get("/status")` returning daemon state, active Twitch channel, connection status, and client count.

#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
- Add background startup for `aibs_broadcast_kernel.py` on Port 8088 in section `[2/9]`.

#### [MODIFY] [verify_boot_health.py](file:///C:/AI-BS/scripts/verify_boot_health.py)
- Update ChromaDB heartbeat endpoint from `/api/v1/heartbeat` to `/api/v2/heartbeat`.
- Add validation probes for `http://127.0.0.1:8088/api/windows` and `http://127.0.0.1:8006/api/social/status`.

---

### Desktop & Web Frontend Suites

#### [MODIFY] [App.jsx](file:///C:/AI-BS/BroadcastStudioApp/src/App.jsx)
- Update localhost service list: ChromaDB vector store heartbeat to `/api/v2/heartbeat`, and Broadcast Stream Engine to port 8088 Broadcast Kernel.
- Enhance Tone.js interaction triggers to safely start audio context on pointer/keyboard interactions.

#### [MODIFY] UI Version Badges (`v5.146.0`)
- Update version strings in `frontend/App.jsx`, `frontend/components/Sidebar.jsx`, `frontend/components/TopNavbar.jsx`, `frontend/components/ChatTab.jsx`, `frontend/components/SyndicationTab.jsx`, `frontend/src/components/BroadcastStudio.jsx`, `frontend/src/components/EcosystemBlueprintTab.jsx`, `BroadcastStudioApp/src/components/BroadcastStudio.jsx`, `BroadcastStudioApp/src/components/SyndicationTab.jsx`.

---

### Master Ledgers & Documentation

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
#### [NEW] [20260830_AI_BS_Master_Ecosystem_Manual.md](file:///C:/AI-BS/saved_data/artifacts/20260830_AI_BS_Master_Ecosystem_Manual.md)
#### [MODIFY] [artifact_history.md](file:///C:/AI-BS/NotebookLM_Records/artifact_history.md)
#### [MODIFY] [MASTER_HISTORICAL_INDEX.md](file:///C:/AI-BS/MASTER_HISTORICAL_INDEX.md)
#### [MODIFY] [MASTER_TASKS_CHRONOLOGY.md](file:///C:/AI-BS/MASTER_TASKS_CHRONOLOGY.md)
#### [MODIFY] [MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md](file:///C:/AI-BS/MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md)

## Verification Plan

### Automated Tests
- Run `python scripts/verify_boot_health.py` to probe all ports (8080, 8088, 8006, 8002, 11434).
- Execute `curl http://127.0.0.1:8088/api/windows` and `curl http://127.0.0.1:8088/api/audio/stats`.
- Execute `curl http://127.0.0.1:8006/api/social/status`.
- Execute `curl http://127.0.0.1:8002/api/v2/heartbeat`.

### Manual & Build Verification
- Compile `frontend` and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Compile `BroadcastStudioApp` production bundle (`npm run build`).
- Verify no `ERR_CONNECTION_REFUSED`, `404`, or `410` in dev console.
