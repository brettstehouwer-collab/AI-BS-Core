# Master Implementation Plan: AI-BS Next-Gen Architectural Upgrade Suite (v5.86.0)

Comprehensive technical specifications and implementation roadmaps across 6 core architectural tracks for the AI-BS ecosystem.

---

## Track 1: Monolithic File Decomposition & Domain Router Architecture
- **Backend Modularization**:
  - Extract route handlers from `backend/AI_BS_Backend.py` into `backend/routers/` (`chat_router.py`, `media_router.py`, `system_router.py`, `trading_router.py`, `memory_router.py`).
  - Keep `AI_BS_Backend.py` as a lightweight FastAPI application mount point.
- **Frontend Modularization**:
  - Extract stateful logic from `BroadcastStudio.jsx` into custom hooks under `frontend/src/components/broadcast/hooks/` (`useCanvasCompositor.js`, `useBroadcastTelemetry.js`, `useAudioMixer.js`).
  - Extract UI panels into modular components (`SourcesDock.jsx`, `AudioMixerDock.jsx`, `StreamlabsOverlayDesigner.jsx`).
  - Split `BullshitKnowledgeSuite.jsx` into dedicated tab sub-components.

## Track 2: Dynamic GPU VRAM Paging, Priority Queue & Live Telemetry
- **Priority GPU Scheduler (`backend/vram_manager.py`)**:
  - Enforce 3-tier VRAM priority queue: NVENC/Audio (P1) > Ollama Chat (P2) > ComfyUI Batch Render (P3).
  - Automate pre-render Ollama eviction and post-render ComfyUI model freeing via `POST /free`.
- **Telemetry UI**:
  - Build `VRAMTelemetryWidget.jsx` displaying real-time allocation across models and encoders.

## Track 3: Unified Type-Safe Event Bus (Go ⇄ Python ⇄ React)
- **Standardized IPC Envelopes**:
  - Enforce strict JSON message format `{topic, event, data, timestamp, source}` across Go Gateway, FastAPI, and WebSocket daemons.
- **Go Gateway Multiplexer**:
  - Route all daemon telemetry through Go Gateway `/ws/matrix` on Port 8000.
- **React Multiplexer Hook**:
  - Build `useMatrixEventBus.js` to manage multi-topic pub/sub over a single persistent WebSocket.

## Track 4: Broadcast Studio WebGL Shader Compositor & WebAudio DSP Rack
- **WebGL2 Offscreen Compositor**:
  - Build `WebGLCompositor.js` with GLSL fragment shaders for real-time Rec.709 LUT color grading, Chroma Key green screen removal, and neon border glow.
- **WebAudio Mastering DSP**:
  - Implement zero-latency brickwall Peak Limiter and Noise Gate AudioWorklet nodes in `audioMasteringChain.js` before audio is pushed to RTMP egress.

## Track 5: Unified SQLite WAL Database Engine & Automated Backup Snapshot Daemon
- **Unified Connection Pool**:
  - Standardize `backend/db/connection_pool.py` configuring WAL mode, 10s busy timeout, and 256MB memory-mapped I/O across all SQLite instances.
- **Automated Backup Daemon**:
  - Implement `backend/database_backup_daemon.py` executing 24-hour non-blocking `VACUUM INTO` snapshots to `E:\AI_BS_Resources\Backups\`.

## Track 6: Automated Matrix Health Check & Diagnostic Suite
- **CLI Diagnostic Tool (`backend/matrix_doctor.py`)**:
  - Pre-flight diagnostic checking port availability, NVML GPU health, SQLite integrity (`PRAGMA quick_check`), and OBS WebSocket handshake.
- **Matrix Doctor UI (`frontend/src/components/MatrixDoctorTab.jsx`)**:
  - 1-Click diagnostic and self-healing dashboard tab with instant repair hooks.
