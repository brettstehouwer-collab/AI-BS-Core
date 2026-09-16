# Autonomous ComfyUI Local RTX 4090 Video & Scene Diffusion Pipeline (`v5.262.0`)

Connect Julie Stehouwer's *The Bad Side Upside Down* screenplay visual prompts directly to the active local ComfyUI daemon on Port `8189`, leveraging verified local GPU acceleration on the **NVIDIA GeForce RTX 4090** (24GB VRAM) to synthesize high-resolution scene renders and video diffusion motion with **zero paid cloud APIs**.

---

## Architectural Flow

```mermaid
graph TD
    A[concept_art_prompts.json] --> B[synthesize_video_scenes.py]
    B --> C{ComfyUI Node Graph Generator}
    C -->|SDXL Graph| D[sd_xl_base_1.0.safetensors]
    C -->|T2V Graph| E[wan2.1-t2v-1.3B / ltx-video-2b]
    D --> F[ComfyUI API: POST /prompt on Port 8189]
    E --> F
    F --> G[Poll /history/{prompt_id}]
    G --> H[Output: PNG Frames & Video Clips in output/the_bad_side_upside_down/]
    H --> I[mobile-app/App.tsx & Web Studio Gallery Integration]
    H --> J[Verification & Ledger Sync v5.262.0]
```

---

## User Review Required

> [!IMPORTANT]
> **Zero-Cost Sovereign Hardware Mandate**:
> All diffusion workloads run **100% locally on your NVIDIA GeForce RTX 4090 (24GB VRAM)** via the ComfyUI daemon on Port `8189`. Zero metered commercial APIs (no OpenAI, no Runway, no paid endpoints) will be contacted.

> [!NOTE]
> **Target Models Verified on Local Host**:
> - Checkpoints: `sd_xl_base_1.0.safetensors`, `v1-5-pruned-emaonly-fp16.safetensors`
> - Video Diffusion / UNETs: `wan2.1-t2v-1.3B.safetensors`, `ltx-video-2b-v0.9.1.safetensors`, `flux1-dev-fp8.safetensors`
> - VAEs: `Wan2_1_VAE_bf16.safetensors`, `ae.safetensors`, `taesdxl`

---

## Proposed Changes

### Screenplay Studio & Video Synthesizer Engine

#### [NEW] [synthesize_video_scenes.py](file:///C:/AI-BS/screenplay_projects/The_Bad_Side_Upside_Down/synthesize_video_scenes.py)
- Connects to ComfyUI API on `http://127.0.0.1:8189`.
- Translates `concept_art_prompts.json` into valid ComfyUI executable prompt DAGs:
  - **SDXL High-Fidelity Graph**: `CheckpointLoaderSimple` -> `CLIPTextEncode` (Positive & Negative) -> `EmptyLatentImage` (1024x1024 / 1280x720) -> `KSampler` (Euler / Normal, 20 steps, CFG 7.0) -> `VAEDecode` -> `SaveImage`.
  - **Video Diffusion Graph**: Text-to-Video latent generation targeting `wan2.1-t2v-1.3B.safetensors` / `ltx-video-2b` with `Wan2_1_VAE_bf16.safetensors`.
- Dispatches prompts via `POST http://127.0.0.1:8189/prompt`.
- Implements resilient non-blocking polling on `/history/{prompt_id}` until completion.
- Downloads or copies rendered artifacts into `C:\AI-BS\output\the_bad_side_upside_down\`.
- Emits an updated `rendered_assets_manifest.json`.

---

### Mobile App & Web Studio Integration

#### [MODIFY] [mobile-app/App.tsx](file:///C:/AI-BS/mobile-app/App.tsx)
- Add a Scene Visual Gallery section / modal in `mobile-app/App.tsx` displaying the generated concept assets and video status from *The Bad Side Upside Down*.
- Allow instant mobile preview of rendered screenplay sets and characters.
- Validate TypeScript with `npx tsc --noEmit`.

#### [MODIFY] [mobile-app/package.json](file:///C:/AI-BS/mobile-app/package.json)
- Bump version to `5.262.0`.

---

### Release & Master Ledger Synchronization

#### [MODIFY] [version.txt](file:///C:/AI-BS/version.txt) & [frontend/package.json](file:///C:/AI-BS/frontend/package.json)
- Bump version to `5.262.0`.
- Sweep all 4 mirror trees:
  - `frontend/src/components/`
  - `frontend/src/components/components/`
  - `frontend/components/`
  - `frontend/components/components/`

#### [MODIFY] [AI_BS_MASTER_ARCHITECTURAL_LEDGER.md](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md)
- Append authoritative entry for `v5.262.0` documenting the Autonomous ComfyUI Local RTX 4090 Video & Scene Diffusion Pipeline.

#### [MODIFY] [docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md](file:///C:/AI-BS/docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md) & [SAVED_CHECKPOINT.md](file:///C:/AI-BS/SAVED_CHECKPOINT.md)
- Archive snapshot to `saved_data/artifacts/20260911_AI_BS_Master_Ecosystem_Manual.md`.
- Set active resume keyword to `RESUME_COMFYUI_VIDEO_DIFFUSION_V5_262`.

---

## Verification Plan

### Automated Tests
1. **API Validation**:
   - Run `python -c "import urllib.request; resp = urllib.request.urlopen('http://127.0.0.1:8189/system_stats'); print(resp.status)"`
2. **Diffusion Pipeline Execution**:
   - Run `python screenplay_projects/The_Bad_Side_Upside_Down/synthesize_video_scenes.py`.
   - Verify prompt DAG queueing, generation completion, and presence of output images/video assets in `output/the_bad_side_upside_down/`.
3. **Mobile Typecheck**:
   - Run `npx tsc --noEmit` inside `C:\AI-BS\mobile-app`.
4. **Vite Production Build**:
   - Run `powershell -ExecutionPolicy Bypass -Command "npm run build"` in `frontend/`.

### Manual Verification
- Inspect generated frames for the Candy Store storefront, Hell furnace flank, Heaven picket fence flank, and Weeble Wobble character models.
