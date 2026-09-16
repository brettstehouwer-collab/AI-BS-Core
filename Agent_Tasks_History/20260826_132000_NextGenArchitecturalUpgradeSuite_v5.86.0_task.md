# Master Task List: AI-BS Next-Gen Architectural Upgrade Suite (v5.86.0)

## Track 1: Monolithic File Decomposition & Domain Router Architecture
- [x] Decompose `AI_BS_Backend.py` into modular domain routers (`routers/chat_router.py`, `routers/media_router.py`, `routers/system_router.py`, `routers/trading_router.py`, `routers/memory_router.py`)
- [x] Modularize `BroadcastStudio.jsx` into custom hooks (`useCanvasCompositor`, `useBroadcastTelemetry`, `useAudioMixer`) and UI docks (`SourcesDock.jsx`, `AudioMixerDock.jsx`, `StreamlabsOverlayDesigner.jsx`)
- [x] Split `BullshitKnowledgeSuite.jsx` into tab components (`VectorVaultTab`, `HeuristicsGraphTab`, `TrainingDataTab`)

## Track 2: Dynamic GPU VRAM Paging, Priority Queue & Live Telemetry
- [x] Implement multi-level GPU VRAM Priority Arbiter in `backend/vram_manager.py` (NVENC Priority 1, Ollama Priority 2, ComfyUI Priority 3)
- [x] Implement proactive keep-alive idle timers (`keep_alive=3m`) and ComfyUI `/free` pre-render flushes
- [x] Create `VRAMTelemetryWidget.jsx` with real-time visual memory breakdown bar in top navigation

## Track 3: Unified Type-Safe Event Bus (Go ⇄ Python ⇄ React)
- [x] Standardize IPC JSON-RPC message envelope schema in `backend/core/event_bus.py` and `go-core/pkg/ipc/event_bus.go`
- [x] Expose `/ws/matrix` multiplexer on Port 8000 in Go Gateway
- [x] Implement `useMatrixEventBus.js` unified React subscription hook

## Track 4: Broadcast Studio WebGL Shader Compositor & WebAudio DSP Rack
- [x] Build WebGL2 quad texture pipeline with GLSL fragment shaders in `frontend/src/components/broadcast/WebGLCompositor.js`
- [x] Add real-time LUT color grading (Rec.709), Chroma Key, and neon border glow shaders
- [x] Build WebAudio master chain with brickwall Lookahead Peak Limiter and Noise Gate worklet in `audioMasteringChain.js`

## Track 5: Unified SQLite WAL Database Engine & Automated Backup Snapshot Daemon
- [x] Standardize SQLite connection factory with WAL mode and 10s busy timeout in `backend/db/connection_pool.py`
- [x] Create non-blocking `database_backup_daemon.py` executing 24-hour `VACUUM INTO` snapshots to `E:\AI_BS_Resources\Backups\`

## Track 6: Automated Matrix Health Check & Diagnostic Suite
- [x] Build `backend/matrix_doctor.py` CLI diagnostic tool verifying 15 ports, NVML GPU stats, database integrity, and WebSocket reachability
- [x] Build `MatrixDoctorTab.jsx` interactive diagnostic deck with 1-click health audits and self-repair actions



