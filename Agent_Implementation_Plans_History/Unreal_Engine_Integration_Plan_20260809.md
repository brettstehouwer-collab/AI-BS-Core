# Unreal Engine 3D Environment Integration

Currently, the Unreal Engine integration is localized to specific demo endpoints (like the Noto Banquet Architect) and isolated scripts (`fountain_unreal.py`). To make 3D environments work seamlessly across **all tools** in AI-BS, we need to standardize the bridge between the AI agents, the backend, and the active Unreal Engine instance.

## User Review Required

> [!WARNING]
> **Performance Impact:** Running Unreal Engine locally alongside the local LLMs (Ollama) and background daemons is extremely resource-intensive. We must ensure the AI-BS ecosystem doesn't crash the system due to VRAM/RAM limits when Unreal Engine is loaded. We may need to verify if the machine has enough resources or if we need to offload LLM tasks when the 3D environment is active.

## Open Questions

> [!IMPORTANT]
> 1. **Pixel Streaming vs. Headless:** Should the Unreal Engine run headlessly (invisible) and just stream the video feed to the AI-BS frontend via Pixel Streaming (port 8888), or will you have the Unreal Editor visibly open on a second monitor while working?
> 2. **Asset Library:** The database `unreal_assets.db` maps keywords to Unreal package paths. Do we have the actual 3D assets imported into `AI_BS_Hub.uproject`, or do we need to build a pipeline to auto-import them?
> 3. **Remote Control Plugin:** Is the "Web Remote Control" plugin fully enabled in your Unreal Project and bound to port 30010?

## Proposed Changes

---

### Backend Core Engine

#### [MODIFY] `c:\AI-BS\backend\routers\unreal_bridge_new.py`
- Refactor to act as the global Unreal API router for the entire ecosystem.
- Implement robust endpoints for:
  - `POST /unreal/spawn_asset`: Spawns a 3D asset using its package path.
  - `POST /unreal/set_environment`: Changes lighting, time of day, and post-processing.
  - `POST /unreal/execute_script`: Pipes generated Python scripts directly into Unreal via the Remote Control API or command-line execution.

#### [MODIFY] `c:\AI-BS\backend\tools\tool_registry.py`
- Register new universal tools for the LLM agents:
  - `spawn_3d_object`: Allows any agent to place objects in the 3D world.
  - `update_3d_lighting`: Allows agents to adjust the mood/lighting based on user requests.
  - `generate_unreal_cinematic`: Hooks into `fountain_unreal.py` to auto-generate and execute camera fly-throughs.

---

### Frontend Dashboard

#### [NEW] `c:\AI-BS\frontend\src\components\UnrealViewport.jsx`
- Create a reusable React component that connects to the WebRTC Signaling Server (`ws://localhost:8888`).
- Embeds the Unreal Engine Pixel Streaming video feed directly into the dashboard.

#### [MODIFY] `c:\AI-BS\frontend\src\App.jsx` (or main layout)
- Add a global toggle switch: **"2D Mode / 3D Mode"**.
- When switched to 3D Mode, the `UnrealViewport` renders, allowing real-time visual feedback for whatever the AI is building.

---

### Daemon & Infrastructure

#### [MODIFY] `c:\AI-BS\Launch_AI_BS.bat`
- Ensure the `AI_BS_Unreal_Signaling_Server.py` boots reliably.
- Add health checks for port `30010` (Unreal Remote Control) and port `8888` (Pixel Streaming) to verify the 3D engine is fully hooked into the AI-BS matrix.

## Verification Plan

### Automated Tests
- Send mock JSON payloads to the `/unreal-remote-control` endpoint to verify the backend correctly formats the REST calls.
- Verify the WebRTC signaling server accepts WebSocket connections on port 8888.

### Manual Verification
1. Launch `AI_BS_Hub.uproject` in Unreal Engine.
2. Ask any AI agent in the AI-BS dashboard to "Spawn a table in the 3D environment and set the lighting to evening."
3. Visually verify in the Unreal Editor (or via Pixel Streaming in the browser) that the table appears and lighting changes instantly.
