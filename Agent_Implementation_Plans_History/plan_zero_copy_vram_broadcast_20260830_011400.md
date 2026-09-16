# Implementation Plan: Pure VRAM Zero-Copy D3D11 / CUDA Hardware Surface & Ultra-Low Latency NVENC Engine

Implement a pure VRAM, zero-copy video processing and hardware encoding pipeline for **AI-BS Broadcast Studio**. This completely eliminates the PCIe Double-Hop Stall (capturing D3D11 textures to host RAM and piping raw byte buffers back to VRAM) by passing hardware surface pointers directly between DirectX 11/DXGI capture, CUDA interop, and on-chip NVENC ASIC encoders with sub-16ms local loopback and SRT network transport.

---

## User Review Required

> [!IMPORTANT]
> **Zero-Latency Parameters Standardized Across Pipelines:**
> 1. **NVENC Hardware Preset:** `p1` (fastest single-pass on-chip encoding).
> 2. **Lookahead / B-Frames:** Disabled (`-bf 0`, `-tune ull`, `-zerolatency 1`, `-delay 0`) to eliminate temporal buffer lag.
> 3. **Strict Constant Bitrate (CBR):** Buffer sizing enforced at `bufsize = (bitrate / fps) * 2` (e.g. 283 KB buffer at 8500 kbps @ 60 FPS) to prevent rate-control queue bloat.
> 4. **Transport Protocols:** Support for SRT (UDP `srt://`) with configurable latency buffers (< 120ms) alongside standard RTMP and local WebRTC / IPC loopback for the Electron UI viewport.

---

## Proposed Changes

### Backend Core & Hardware Acceleration Layer

#### [NEW] [aibs_d3d11_cuda_bridge.py](file:///C:/AI-BS/backend/aibs_d3d11_cuda_bridge.py)
* Creates a pure Python/ctypes/CUDA hardware surface bridge (`CUDADirectXBridge`).
* Implements `cudaGraphicsD3D11RegisterResource`, `cudaGraphicsMapResources`, and `cudaGraphicsSubResourceGetMappedArray` / pointer extraction.
* Manages D3D11 device creation with multi-thread protection (`ID3D11Multithread`) and shared handle registration (`ID3D11Resource::GetSharedHandle`).
* Provides zero-copy VRAM surface pointers directly to libavcodec hardware frame contexts (`AVHWFramesContext`).

#### [MODIFY] [aibs_broadcast_kernel.py](file:///C:/AI-BS/backend/aibs_broadcast_kernel.py)
* Upgrade `DirectXZeroCopyEngine` to initialize `d3d11va` hardware contexts and register NVENC `ull` (Ultra-Low Latency) parameter presets.
* Replace CPU `gdigrab` with zero-copy hardware capture inputs (`d3d11va` / `ddagrab` / `d3d11` surface pipeline with automatic fallback and elevated permissions handling).
* Add native **SRT (Secure Reliable Transport)** and **WebRTC WHIP / loopback** streaming endpoints alongside RTMP.
* Update `start_stream()` and `start_recording()` to apply zero-latency flags:
  ```python
  "-preset", "p1",
  "-tune", "ull",
  "-zerolatency", "1",
  "-bf", "0",
  "-rc", "cbr",
  "-bufsize", f"{int(bitrate_kbps / fps * 2)}k",
  "-g", str(fps),
  "-forced-idr", "1"
  ```
* Expose `/api/kernel/d3d11_cuda/status` and `/api/kernel/stream/srt/start` endpoints for the UI.

#### [MODIFY] [aibs_broadcast_daemon.py](file:///C:/AI-BS/backend/aibs_broadcast_daemon.py)
* Align daemon encoding flag builders (`build_encoder_flags`) with `p1`, `ull`, zero-latency CBR, and SRT protocol handling.
* Add D3D11VA hardware device flags (`-hwaccel d3d11va -hwaccel_output_format d3d11`).

---

### Broadcast Studio Electron UI

#### [MODIFY] [BroadcastStudio.jsx](file:///C:/AI-BS/BroadcastStudioApp/src/components/BroadcastStudio.jsx)
* Add protocol toggle (RTMP vs. SRT vs. WebRTC Loopback) in the Stream Settings panel.
* Add real-time VRAM telemetry badge showing Pure VRAM Zero-Copy status, active hardware frame context (D3D11VA / CUDA), and sub-16ms latency metrics.
* Wire instant SRT start/stop actions and update performance stats dock.

---

### Documentation & Master Ledgers

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
* Log development entry detailing the Pure VRAM Zero-Copy D3D11 / CUDA Hardware Context architecture and low-latency parameters.

#### [MODIFY] [AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md)
* Bump manual version and document operating procedures for zero-copy streaming, SRT ingestion, and CUDA-D3D11 interop.

---

## Verification Plan

### Automated Tests
* **Hardware Surface & Context Probe:**
  ```powershell
  python -c "from aibs_d3d11_cuda_bridge import CUDADirectXBridge; bridge = CUDADirectXBridge(); print(bridge.probe_hardware())"
  ```
* **Low-Latency FFmpeg Pipeline Verification:**
  ```powershell
  ffmpeg -y -init_hw_device d3d11va -f lavfi -i nullsrc=s=1920x1080:r=60:d=1 -c:v h264_nvenc -preset p1 -tune ull -zerolatency 1 -bf 0 -b:v 8500k -bufsize 283k -f null -
  ```
* **Kernel REST & Telemetry Endpoints:**
  ```powershell
  powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8088/api/kernel/status'"
  ```

### Manual Verification
* Start the AI-BS Broadcast Kernel (`python aibs_broadcast_kernel.py`).
* Verify UI telemetry in Broadcast Studio shows `d3d11_zero_copy: true`, `preset: p1`, `tune: ull`, `latency: <16ms`.
* Test live stream initiation to local/remote SRT and RTMP endpoints.
