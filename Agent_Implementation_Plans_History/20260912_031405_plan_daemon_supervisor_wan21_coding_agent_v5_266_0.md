# Implementation Plan: Centralized Daemon Supervisor, Unified /ws/telemetry Event Hub, Wan2.1 49-Frame Video Diffusion & Mobile Interactive Telemetry Deck (`v5.266.0`)

Elevate the AI-BS ecosystem with a unified, high-performance operational backbone: (1) Wire `backend/core/daemon_manager.py` into `AI_BS_Backend.py` with hybrid static + JIT VRAM-aware supervision across the 18 collision-free ports; (2) Mount a high-throughput `/ws/telemetry` WebSocket endpoint on Port 8080 broadcasting real-time process health, latency, CPU/VRAM metrics, and video render progress; (3) Build the autonomous Wan2.1 49-frame RTX 4090 video diffusion pipeline on Port 8189 with Weeble Wobble physics for *The Bad Side Upside Down*; (4) Transform the Mobile App's 18-Port Topology Modal into an interactive control deck with live WebSocket streaming and 1-tap daemon actions; (5) Bridge ecosystem telemetry to Firebase Cloud Firestore (`ecosystem_telemetry/live_status`) for off-LAN mobile fallback.

---

## User Review Required

> [!IMPORTANT]
> - **Port Matrix Adherence:** All socket allocations strictly preserve the immutable 18-port collision matrix (FastAPI on 8080, ComfyUI on 8189, Ollama on 11434, Go Gateway on 8000, ChromaDB on 8002, Broadcast on 8005, SHM on 8010).
> - **Zero-Cost Mandate:** All compute, LLM inference, video diffusion, and telemetry run 100% locally or on free open-source infrastructure; zero commercial metered APIs.
> - **Multi-Mirror Synchronization Law:** All updates to frontend components (`ChatTab.jsx`, `TopNavbar.jsx`, `Sidebar.jsx`, `firebase.js`, etc.) must synchronize across all 4 mirror directory trees simultaneously with 100% hash parity.

---

## Proposed Changes

### Backend Core & Daemon Supervision

#### [MODIFY] [daemon_manager.py](file:///C:/AI-BS/backend/core/daemon_manager.py)
- Enhance `DaemonManager` to support hybrid static vs. JIT registration categories.
- Integrate thermal throttle checking and VRAM awareness (`check_hardware_thermal_throttle()`).
- Add authoritative status serialization method `get_full_ecosystem_status()` returning structured port, PID, status (`ONLINE`/`OFFLINE`), memory, CPU, and uptime for all 18 collision-free ports.
- Provide thread-safe hooks for WebSocket broadcasting upon state transitions.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Wire `daemon_supervisor` into FastAPI `lifespan` with pre-flight port sweeps and graceful shutdown hooks.
- Mount `@app.websocket("/ws/telemetry")` broadcasting live process metrics, daemon states, and active Wan2.1 render job events at a 1 Hz heartbeat or upon state changes.
- Provide `GET /api/executive/daemons` and `POST /api/executive/daemon-action` (`start`, `stop`, `restart`) connected directly to `daemon_supervisor`.
- Wire periodic background sync to Firestore document `ecosystem_telemetry/live_status`.

---

### Wan2.1 Video Diffusion Pipeline (RTX 4090 / Port 8189)

#### [MODIFY] [wan_media_router.py](file:///C:/AI-BS/backend/routers/wan_media_router.py)
- Expand router to support the 49-frame Wan2.1 text-to-video / image-to-video generation passes (`/api/v1/wan-media/t2v/generate`).
- Implement asynchronous worker queue with ComfyUI Port 8189 JSON workflow dispatching.
- Inject Weeble Wobble physics parameters (`center_of_mass_offset: -35cm`, `oscillation_hz: 1.2`) into video metadata.
- Broadcast real-time diffusion step progress and node execution milestones over `/ws/telemetry`.
- Update `output/the_bad_side_upside_down/rendered_assets_manifest.json` upon completion and serve rendered media via `/api/comfy/media`.

#### [NEW] [test_daemon_supervisor.py](file:///C:/AI-BS/backend/test_daemon_supervisor.py)
- Unit test suite verifying daemon registration, port reclamation, status serialization, and process restart logic.

#### [NEW] [test_wan_video_pipeline.py](file:///C:/AI-BS/backend/test_wan_video_pipeline.py)
- Automated test validating Wan2.1 prompt injection, workflow formatting, WebSocket notification dispatch, and manifest synchronization.

---

### Mobile App Telemetry Deck & Control Console

#### [MODIFY] [App.tsx](file:///C:/AI-BS/mobile-app/App.tsx)
- Connect 18-Port Topology Modal to `ws://{activeGateway}/ws/telemetry` with fallback to Cloud Firestore `onSnapshot` when off-LAN.
- Replace static status badges with live dynamic indicators (real-time ping latency in ms, CPU/VRAM usage bars).
- Add interactive 1-tap `[Restart]` and `[Stop/Start]` action buttons per port calling `POST /api/executive/daemon-action`.
- Add live Wan2.1 diffusion progress indicator card showing active scene rendering status, prompt ID, and frame count.
- Update app version to `v5.266.0`.

---

### Frontend & Cloud Synchronization

#### [MODIFY] [firebase.js](file:///C:/AI-BS/frontend/firebase.js) (and all 4 mirrors)
- Add utility helpers `subscribeToEcosystemStatus(callback)` and `syncLocalTelemetryToCloud(statusPayload)` using Firestore `ecosystem_telemetry/live_status`.

#### [MODIFY] [ChatTab.jsx](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx) (and all 4 mirrors)
- Add `/daemon` and `/topology` slash commands to inspect and control daemons directly from chat.
- Add live WebSocket connection indicator badge in the executive drawer.

#### [MODIFY] [TopNavbar.jsx](file:///C:/AI-BS/frontend/src/components/TopNavbar.jsx) (and all 4 mirrors)
- Update version badge to `v5.266.0`.

#### [MODIFY] [Sidebar.jsx](file:///C:/AI-BS/frontend/src/components/Sidebar.jsx) (and all 4 mirrors)
- Update version badge to `v5.266.0`.

#### [MODIFY] Version Authority Files
- `version.txt`: increment to `v5.266.0`.
- `frontend/package.json`: increment to `5.266.0`.
- `mobile-app/package.json`: increment to `5.266.0`.
- `frontend/public/version.json`: increment to `5.266.0`.
- `frontend/public/sw.js`: increment cache version to `v5.266.0`.

---

## Verification Plan

### Automated Test Suites
- Run `python backend/test_daemon_supervisor.py` to verify daemon registration, status reporting, and lifecycle control.
- Run `python backend/test_wan_video_pipeline.py` to verify Wan2.1 workflow composition and WebSocket event routing.
- Run `npx tsc --noEmit` in `c:\AI-BS\mobile-app` to guarantee 0 TypeScript errors.

### Multi-Mirror Parity Verification
- Compute SHA256 hashes of all 4 mirror trees of `ChatTab.jsx`, `TopNavbar.jsx`, `Sidebar.jsx`, `firebase.js` to ensure 100% hash parity.

### Production Build & Deployment
- Execute `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"` in `frontend/`.
- Verify live cloud deployment at `https://ai-bs-dashboard.web.app`.

### Master Ledger Synchronization
- Append comprehensive milestone entry to `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`.
- Update `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` and archive snapshot.
- Archive task and plan to history folders and update chronologies.
- Update `SAVED_CHECKPOINT.md` with active resume keyword `RESUME_DAEMON_SUPERVISOR_WAN21_TELEMETRY_V5_266`.
