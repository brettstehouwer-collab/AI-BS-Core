# Implementation Plan: RTX 4090 Wan 2.1 Video Generation Pipeline Recovery & Timeout Remediation

Resolution of the 10-minute generation hang and destructive "Server returned HTTP Connection Offline" failover during local Wan 2.1 video synthesis on NVIDIA RTX 4090 (Port 8189).

---

## 1. Root Cause Forensic Analysis

| Defect Layer | Mechanism | Manifestation |
| :--- | :--- | :--- |
| **ComfyUI Worker Deadlock** | Prior image prompt failed with `torch.AcceleratorError: CUDA error: unknown error in torch.cuda.synchronize()`. The ComfyUI web server stayed alive on Port 8189, but its execution worker thread died. | 8 prompts accumulated in `queue_pending` with `queue_running = 0`. All new video jobs queued indefinitely. |
| **Unbounded Frame Count Math** | `generate_comfy_video` defaulted to `duration_seconds = max(7, min(15, dur_raw))` with default 10s. The formula `k_val = max(20, round((duration_seconds * fps - 1) / 4))` forced $k=40$, generating **161 frames** at 10 steps. | 161 frames requires ~650 seconds on RTX 4090 (Wan 1.3B t2v VAE tiling and sampling), exceeding standard HTTP timeouts. |
| **Dimension Divisibility Constraint** | Wan 2.1 patch embed module requires `width` and `height` to be strict multiples of 16. Arbitrary resolutions (e.g. 640x360) cause immediate node failure. | Node exceptions were thrown when non-aligned dimensions were supplied. |
| **Client-Side Timeout Expiration** | `MobileStehouwerChat.jsx` enforced `AbortSignal.timeout(600000)` (600s = 10 min). | At 585s–600s, the browser aborted the fetch stream. |
| **Destructive Non-Streaming Failover** | In `MobileStehouwerChat.jsx` and `ChatTab.jsx`, when the streaming fetch reader threw an abort/network exception, `streamingSucceeded` remained `false`. The client fell back to non-streaming `/api/chat`. | Because the backend was still blocked in synchronous execution, the non-streaming fetch failed and overwrote the chat with `❌ Connection Notice: Server returned HTTP Connection Offline`. |
| **Hazardous SDXL Fallback Latent Batch** | In `backend/tools/tool_registry.py` line 1907, the fallback SDXL workflow set `batch_size: min(num_frames, 64)`. | Generating 64 SDXL latents at once exhausted VRAM and froze the GPU driver. |

---

## 2. Benchmark Verification (RTX 4090 Port 8189)

We verified the recovered ComfyUI instance with native Wan 2.1 weights:
- **Weights Verified**: `umt5_xxl_fp16.safetensors` (10.59 GB), `wan2.1-t2v-1.3B.safetensors` (1.37 GB), `Wan2_1_VAE_bf16.safetensors` (0.24 GB).
- **Benchmark Run**: 49 frames ($k=12$, $4 \times 12 + 1 = 49$), 832x480 resolution, 8 steps UniPC scheduler, 16 fps.
- **Execution Latency**: **55.1 seconds total** (WanVideoTextEncode: 4s, WanVideoSampler: 28s, WanVideoDecode: 20s, VHS_VideoCombine: 3s).
- **Generated Artifact**: `C:\AI-BS\ComfyUI\ComfyUI\output\Cyberpunk_Matrix_Flight_00001.mp4` (2,557,677 bytes / 2.55 MB). Verified HTTP 200 streaming via `/api/comfy/media`.

---

## 3. Proposed Code Modifications

### A. Backend Video Pipeline Optimization (`backend/tools/tool_registry.py`)
1. **Calibrate Duration & Frame Math**:
   - Parse `duration_seconds` defaulting to 3s (constrained between 3 and 8s).
   - Compute `k_val = max(12, min(32, round((duration_seconds * fps - 1) / 4)))`.
   - Default $k=12$ yields 49 frames (~3.06s @ 16fps), completing in ~55s on RTX 4090.
2. **Enforce 16-Pixel Dimension Divisibility**:
   - `width = max(512, min(960, (raw_w // 16) * 16))`
   - `height = max(384, min(544, (raw_h // 16) * 16))`
   - `steps = max(6, min(14, int(arguments.get("steps", 8))))`
3. **Safe Fallback Latent Batch**:
   - Set `"batch_size": min(num_frames, 8)` to prevent GPU OOM crashes during fallback.

### B. Frontend Streaming Resilience (`MobileStehouwerChat.jsx`, `ChatTab.jsx`, `MobileGeminiChat.jsx`)
1. **Preserve Stream Progress**:
   - Scope accumulated message text outside the inner try block.
   - If `accumulated.trim().length > 0`, mark `streamingSucceeded = true` so an abort or network glitch does NOT fall through to wipe the UI with an offline error.
2. **Increase Media Timeout Ceiling**:
   - Increase `mediaTimeout` from 600,000 ms to 900,000 ms (15 min).
3. **Mirror Path Synchronization**:
   - Apply identical fixes across `frontend/src/components/` and `frontend/components/`.

### C. Build & Deployment
1. Execute `powershell -ExecutionPolicy Bypass -Command "npm run build; firebase deploy --only hosting --non-interactive"` from `C:\AI-BS\frontend`.
2. Mirror updated `dist` to `C:\Program Files\AI-BS Sovereign Studio\frontend_dist`.
3. Restart FastAPI backend on Port 8080.

---

## 4. Verification Plan

### Automated / Programmatic
- Execute test script queuing and awaiting a 49-frame Wan 2.1 video via Port 8189 and verifying output media URL.
- Test `/api/comfy/media` endpoint with range requests.

### Manual / Operator
- Verify generated video playback in chat UI.
- Verify that stream progress indicator transitions smoothly to `<video>` player upon completion.
