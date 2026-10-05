# AI-BS Mission Specification: Interactive ComfyUI Workstation & Node Inspector

**Mission ID:** MISSION-COMFYUI-WORKSTATION-8189  
**Status:** LOCKED & APPROVED  
**Target Subsystem:** Frontend Workspace & ComfyUI Runtime Interface  
**Ecosystem Baseline:** AI-BS v5.305.0 | Windows 11 Pro | RTX 4090 (24GB VRAM)  
**Port Reservation:** Port 8189 (ComfyUI RTX 4090 Native)  

---

## 1. Executive Summary & Intent
Deliver a fully interactive, locally hosted ComfyUI workstation featuring:
1. One-click tool and workflow execution.
2. Dynamic workflow preset catalog pre-loaded with verified local RTX 4090 pipelines.
3. Live WebSocket execution telemetry, active node tracking, and step progress.
4. Searchable node registry inspector parsing all 1,365 installed nodes from `/object_info`.
5. Dual display bridging an embedded native canvas iframe and a live output gallery.
6. Seamless integration within `ComfyWorkspaceTab.jsx` as a top-level Dual-Engine mode toggle.

---

## 2. Architectural Decisions (Grill Session Resolution)

### Branch 1: Data Schemas & State Persistence
- **Node Registry Schema:** Caches full `/object_info` dictionary containing node inputs, outputs, types, and categories.
- **Workflow DAG Format:** Standard ComfyUI prompt API JSON format.
- **Output Gallery Persistence:** Captured image/video URLs streamed via WebSocket (`executed` event) and rendered into the gallery grid with direct download capabilities.

### Branch 2: Concurrency, Locking & Resource Limits
- **Port Authority:** Bound strictly to `http://127.0.0.1:8189` and `ws://127.0.0.1:8189/ws` (Port 8189 static reservation).
- **GPU Compute Allocation:** Operates on the NVIDIA RTX 4090 (24GB VRAM). VRAM resource arbiter coordination prevents contention with local Ollama models on Port 11434.

### Branch 3: Error Handling & Boundary Recovery
- **Dynamic Hybrid Endpoint Resolver:** Automatically detects execution context (localhost vs remote dashboard). Allows operator endpoint override in the top control bar with Go Gateway fallback (`/api/comfyui`).
- **WebSocket Reconnection:** Graceful disconnect handling and state tracking (`isConnected` boolean indicator).

### Branch 4: Preset Catalog Matrix (RTX 4090 Verified)
Pre-loads 5 sovereign workflows grounded in active disk models and installed nodes:
1. **SDXL 4K Master Cinema + 4x-UltraSharp:** `sd_xl_base_1.0.safetensors` + `4x-UltraSharp.pth` (28 steps, CFG 7.5, DPM++ 2M SDE GPU / Karras).
2. **Wan2.1 Neural Motion Video:** `WanVideoWrapper` + `Wan2_1_VAE_bf16.safetensors` + `qwen3vl_4b_fp8_scaled.safetensors` + `Video Helper Suite` (VHS VideoCombine).
3. **LTX-Video 2B Real-Time Motion:** `ltx-video-2b-v0.9.1.safetensors`.
4. **ImpactPack FaceDetailer & ControlNet Depth:** `ImpactPack` + `ControlNet Preprocessors` + `v1-5-pruned-emaonly-fp16.safetensors`.
5. **4x-UltraSharp Direct Super-Resolution:** Direct model-based image upscaling.

---

## 3. Implementation Targets & Multi-Mirror Parity
- Hook: `frontend/src/components/useComfyWorkspace.js`
- Component: `frontend/src/components/ComfyStation.jsx`
- Styling: `frontend/src/components/ComfyStation.css`
- Integration: `frontend/src/components/ComfyWorkspaceTab.jsx`
- Mirror Synchronization: Synchronize all 4 frontend directory trees:
  1. `frontend/src/components/`
  2. `frontend/components/`
  3. `frontend/src/components/components/`
  4. `frontend/components/components/`
- Verification: 100% SHA-256 byte parity confirmed via `scripts/verify-mirror-parity.ps1`.
- Deployment: Production build (`npm run build`) and Firebase Hosting release.
