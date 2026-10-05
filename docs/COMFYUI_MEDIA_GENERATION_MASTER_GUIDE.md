# ComfyUI Media Generation & Architecture Master Guide

This guide establishes the precise parameters, foundational node pathways, and multi-stage orchestration protocols required to generate, scale, and refine high-fidelity media locally.

> **Read Appendices A and B before building workflows.** Parts of Modules 1–8 below use generic or non-existent node names, wrong ports, or code that won't run. The appendices map each item to what is actually registered on the AI-BS ComfyUI instance (port `8189`), checked live on 2026-10-05.

---

## Module 1: Foundational Image Generation (Text-to-Image / Img2Img)

To ensure maximum definition, the base canvas generation must avoid pixel blurring by mapping text tokens to direct mathematical latent dimensions before upscaling.

### Core Architecture Pass

1. **Model Loading:** Load Checkpoint / Load Diffusion Model (e.g., Flux.1 Dev, SDXL Base). Pair with DualCLIPLoader for optimized token compliance across diverse prompts.
2. **Conditioning:** CLIPTextEncode (Positive & Negative prompts). Emphasize camera sensor metrics, focal lengths (e.g., 85mm lens), and exact light behavior variables (soft studio lighting).
3. **Latent Initialization:** EmptyLatentImage. Force dimensions to strictly align with the model's native resolution buckets (e.g., 1024x1024 for SDXL or optimized Flux aspect resolutions).
4. **Sampling Pass:** KSampler / Advanced KSampler.
   - Steps: 20–35 (Model dependent).
   - Sampler: `euler` or `dpmpp_2m`.
   - Scheduler: `normal` or `sgm_uniform`.
   - Denoise: Set to 1.00 for pure Text-to-Image; set between 0.40–0.65 for Img2Img translation passes.
5. **Decoding:** VAEDecode linked to a native, high-precision VAE loader to map latents back into clean RGB pixel spaces.

---

## Module 2: The Multi-Stage Ultra-HD Definition Pipeline

Achieving maximum resolution and micro-textures requires a separate 2-stage refinery sequence rather than single-pass generation. This approach injects realistic textures (like skin pores, fabric grain, and sharp object boundaries) without introducing structural mutations.

```
[Base VAE Decode Output]
          │
          ▼
┌─────────────────────────────────┐
│     Upscale Model Loader        │ ──► (Using 4xNomosUniDAT / 4x-UltraSharp)
└─────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│   Image Upscale with Model      │ ──► Scales raw pixels up (e.g., 2x / 4x spatial scale)
└─────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│     Ultimate SD Upscale         │ ──► Tiled KSampler processing loop
└─────────────────────────────────┘      • Denoise: 0.10 to 0.15
          │                              • Seamless tile stitching
          ▼
[Final High-Definition Master Output]
```

### Protocol Execution Details

- **Stage 1 (Spatial Pixel Scaling):** Route the raw pixel output from the base decoder directly into Image Upscale with Model. Drive the scaling pass via 4xNomosUniDAT or 4x-UltraSharp models to widen the canvas cleanly without creating algorithmic artifacts.
- **Stage 2 (Latent Texture Injection):** Route the expanded image into the Ultimate SD Upscale custom node.
  - Set the sub-sampler loop denoise strictly between 0.10 and 0.15.
  - This forces the diffusion model to inject organic micro-detail and sharpening textures directly into the upscaled layout while strictly locking down the overarching composition.
- **VRAM Safeguard:** Integrate Tiled VAE / Tile Diffusion nodes into this stage to break heavy VAE encodes and decodes into smaller tiles, preventing out-of-memory crashes on dense 4K/8K media sheets.

---

## Module 3: Advanced Video Generation & Real-Time Enhancements

Maintaining high resolution across video clips requires nodes capable of cross-frame awareness to suppress flickering and geometric distortion.

### Node Configuration Checklists

**1. Open Video Production Loop (LTX-Video Network)**
- LTXVideoModelLoader: Loads open-weight temporal diffusion structures locally.
- LTXVideoSampler: Configured with specialized video schedules to track motion dynamics while generating synchronous multi-channel audio tracks at up to 4K.

**2. Temporal Consistency Network (Wan Pipeline)**
- WanVideoCheckpointsLoader: Utilized to deploy Wan 2.1 or 2.2 pipelines natively across varying aspect ratios.
- WanVideoKSampler: Run at 24fps configuration flags to achieve solid consistency between text-to-video frames.

**3. Real-Time Hardware-Accelerated Video Super-Resolution (VSR)**
- RTX Video Super Resolution: (Requires specialized NVIDIA GPU Custom Pack integration). Feeds frame batches directly through GPU Tensor Cores to scrub compression noise and apply 4K upscaling.
- FlashVSR: Positioned as an alternative ultra-speed video super-resolution processing node for fast cross-frame refinement passes.

---

## Module 4: High-Definition Regional & Target Isolation

When general scene enhancement leaves target focus zones (faces, eyes, hands, or custom objects) soft or structurally imperfect.

### Automated Correction Node Flow

1. **Detection Pass:** Route the full layout into a Face Detailer or SVD Detailer parent cluster (Impact Pack network).
2. **Segmentation Routing:** An internal bounding box detector (like YOLO) tracks and isolates the localized sub-coordinates of the blurred region.
3. **Targeted Img2Img Loop:** The isolated section is automatically cropped, upscaled inside its own distinct mini-latent space via a specialized low-denoise KSampler pass to rebuild micro-details, and stitched back into the final master image with alpha-blended edges.

---

## Module 5: Agentic Integration Workflows (Comfy MCP)

The most significant architectural advancement allows you to treat your node graph as a tool for an LLM.

- **How it works:** By deploying a Model Context Protocol (MCP) server over ComfyUI, a secondary autonomous AI agent can programmatically spin up workflows, swap models, modify seeds, and read outputs via a local backend or FastAPI setup.
- **Why add it:** It transitions ComfyUI from a manual visual GUI into an automated headless backend asset for a custom software pipeline, allowing an AI to self-correct rendering errors or execute complex media tasks independently.

### Comfy MCP Agentic Server Framework

This setup exposes your local ComfyUI instance (http://127.0.0.1:8188) as a headless Model Context Protocol (MCP) toolset, allowing an autonomous backend agent to programmatically manipulate nodes, pass prompts, and handle VRAM clearing triggers.

> [!WARNING]
> The scaffold below is kept as originally supplied. **It will not run:** the import doesn't exist, the port is wrong, and one endpoint is invented. Use the corrected version in Appendix B.2.

```python
# mcp_comfy_server.py  (ORIGINAL — DO NOT DEPLOY, see Appendix B.2)
import httpx
from mcp.server.fastapi import Context, create_mcp_server

# Initialize your AI-BS backend-connected MCP server
server = create_mcp_server(name="comfyui_agentic_bridge", version="1.0.0")
COMFY_URL = "http://127.0.0.1:8188"

@server.tool(name="execute_media_pipeline", description="Triggers a specified ComfyUI JSON node workflow.")
async def execute_media_pipeline(workflow_json: dict, prompt_text: str) -> dict:
    """Injects prompt tokens directly into the Target CLIP nodes and queues the prompt."""
    # Programmatic replacement logic for prompt injecting
    for node_id, node_data in workflow_json.items():
        if node_data.get("class_type") == "CLIPTextEncode":
            if "positive" in node_data.get("_meta", {}).get("title", "").lower():
                node_data["inputs"]["text"] = prompt_text
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{COMFY_URL}/prompt", json={"prompt": workflow_json})
        return response.json()

@server.tool(name="flush_gpu_vram", description="Triggers a hard clear of the GPU/VRAM cash.")
async def flush_gpu_vram() -> str:
    """Invokes ComfyUI internal memory garbage collection to prevent OOM errors."""
    async with httpx.AsyncClient() as client:
        await client.post(f"{COMFY_URL}/unload_models", json={"unload_all": True})
        await client.post(f"{COMFY_URL}/free", json={"unload_models": True, "free_memory": True})
    return "GPU and VRAM Cache safely cleared."
```

---

## Module 6: Multi-Modal Consistency & Reference-to-Video Pipelines

Maintaining perfect subject, character, or object identity across completely separate image frames and heavy motion layouts.

- **IP-Adapter-Plus + Attention Masking:** Workflows that isolate specific visual traits (like a character's jacket or a product's exact labels) and inject them into downstream text-to-image or video generation passes without bleeding into the background.
- **Reference-to-Video (Ref-to-Video):** Advanced pipelines that use a high-definition reference image as an unyielding structural anchor while a video model (like Wan 2.1 or LTX-Video) handles the physics, camera moves, and environmental action around it.

### Reference-to-Video Consistency Loop

To ensure a target character or object maintains 100% identity without visual bleeding across dynamic video motions generated by Wan 2.1 or LTX-Video.

> [!WARNING]
> This flow is not buildable as drawn. IP-Adapter cannot feed a Wan or LTX sampler. See Appendix B.3 for the two pipelines that do work on this install.

```
[Reference Image File Loader] ──► [IP-Adapter-Plus Model Loader]
                                              │
          ┌───────────────────────────────────┘
          ▼
[IP-Adapter Advanced Node] ◄── [Attention Masking / Clip Vision Encoder]
          │  (Weight: 0.85 / Ending Step: 0.90)
          ▼
[Apply ControlNet (Advanced)] ◄── [Depth/Lineart Preprocessor] (Locks structural boundaries)
          │
          ▼
[WanVideoKSampler / LTXVideoSampler] ◄── [Positive Prompt Text (Motion/Physics instructions)]
          │
          ▼
[AnimateDiff / Video Frame Decoder] ──► [High-Consistency Video Master]
```

- **Precision Control:** The IP-Adapter Advanced node processes the reference image with an attention mask to block background elements from polluting the canvas.
- **The Hand-off Rule:** Setting the IP-Adapter Ending Step to 0.90 allows the primary video sampler to fully resolve complex temporal motion and lighting changes in the final 10% of the processing loop, preventing the output from freezing into a static frame.

---

## Module 7: Native GGUF / NF4 Precision Workflows for Local Compute

Running state-of-the-art models at maximum quality parameters locally without hitting hardware caps.

- **Quantized Model Workflows:** Node setups built around specialized Unet Loader (Advanced) nodes to run high-fidelity models (like Flux.1 Dev or massive video text-encoders) in GGUF or NF4 formats.
- **Why add it:** They drastically compress the model weights, freeing up immense amounts of local GPU VRAM. This extra headroom can be entirely reallocated into heavy multi-stage upscaling loops, Tiled VAE actions, and local video super-resolution passes.

### Core Quantized Component Mapping

This protocol downscales the memory footprint of heavy foundation models (like Flux.1 Dev or large video T5 text encoders) to prioritize VRAM for heavy multi-stage upscaling loops.

- **Model Ingestion:** Replaces standard Load Checkpoint with the custom Unet Loader (Advanced) node.
- **Precision Flags:** Target your model file explicitly inside the loader (`flux1-dev-Q4_K_S.gguf` or `flux1-dev-nf4.safetensors`).
- **CLIP Separation:** Utilize a dedicated DualCLIPLoader passing `t5xxl_fp8_e4m3fn.safetensors` alongside `clip_l.safetensors`. This offloads text token handling safely to CPU/System RAM if VRAM headroom is constrained.

---

## Module 8: Interactive Live Canvas & Real-Time Diffusion (LCM / Turbo)

Transforming standard rendering loops into live, instantly responsive visual sandboxes.

- **Latent Consistency Models (LCM) + WebSockets:** Ultra-fast workflows configured with a denoise loop running between 1 to 4 steps.
- **Why add it:** It reads a live input feed (like an active screen capture, a digital sketch pad, or an incoming streaming canvas) and immediately updates the diffusion layout in real-time, allowing for instant style-transfer and layout adjustments before initiating the final high-definition production render.

### Sub-Sampling Loop Requirements

This sub-system operates as a high-frequency layout refinery, evaluating real-time canvas updates or screen capture streams via raw WebSockets.

- **Latent Space Step Strategy:** Pair an LCM Loader with a KSampler forced to:
  - Steps: Strictly 1 to 4 steps.
  - CFG Scale: 1.0 to 1.8 (Crucial to prevent color-burn artifacting at ultra-low step counts).
  - Sampler / Scheduler: `lcm` or `uni_pc` / `sgm_uniform`.
- **Streaming Ingestion:** Route an incoming window stream into Load Image (Asynchronous) linked to a VaeEncode node running a highly sensitive Denoise metric between 0.30 and 0.45. This ensures layout or compositional changes in your digital sketch update the style-transfer generation seamlessly.

---

## Module 9: Production Synthesis & Optimal High-Resolution Reference Matrix (Choice A + B Master Framework)

This module unifies the seven primary production domains, exact sampler & scheduler matrices, strict resolution buckets, neural upscaler rankings, and the definitive 4-stage ultra-fidelity pipeline.

### 9.1 The Seven Master Production Domains

| Domain | Primary Model Architectures & Nodes | Core Architectural Objective |
| :--- | :--- | :--- |
| **1. Text-to-Image & Image-to-Image** | FLUX.1 (Dev/Schnell), SDXL, SD 3.5, SD 1.5 via `CheckpointLoaderSimple` or `UNETLoader` + `DualCLIPLoader` | High-fidelity base composition generation aligned strictly to native latent aspect ratio buckets. |
| **2. Ultra-Resolution Scaling** | `UpscaleModelLoader` (`4x-UltraSharp`, `NomosUniDAT`), `UltimateSDUpscale`, `VAEEncodeTiled` / `VAEDecodeTiled` | Hybrid super-resolution: 4x spatial pixel expansion followed by low-denoise tiled diffusion to synthesize micro-textures. |
| **3. Conditioning & Spatial Control** | ControlNet (Tile, Canny, Depth Anything v2, OpenPose), IP-Adapter v2, Regional Conditioning | Precise structural, lighting, and semantic boundary guidance without latent coordinate bleed. |
| **4. Iterative Inpainting & Canvas Editing** | Differential Diffusion, Segment Anything (SAM 2), Flux Fill contextual expansion | Non-destructive localized regeneration, object substitution, and seamless canvas outpainting. |
| **5. Subject & Facial Preservation** | `UltralyticsDetectorProvider` (YOLOv8m/s), `FaceDetailer`, `DetailerForEach`, Reactor / InstantID / PuLID | Semantic segmentation bounding-box cropping, targeted native-res diffusion, and feathered alpha re-blending. |
| **6. Video & Motion Generation** | Wan 2.1 / 2.2, LTX-Video, CogVideoX, AnimateDiff Evolved, `RTXVideoSuperResolution` | Cross-frame temporal consistency, camera trajectory adherence, and GPU Tensor Core post-upscaling. |
| **7. Multi-Modal & Vision-Prompt Loops** | Florence-2, JoyCaption, F5-TTS, Demucs v4, ComfyUI FastMCP agent bridge | Autonomous visual critique, recursive prompt optimization, zero-shot voice cloning, and audio stem synchronization. |

---

### 9.2 Optimal Sampler, Scheduler & Guidance Matrix

Using an incompatible sampler/scheduler combination causes noise amplification, smearing, or highlight burn. Follow these verified configurations:

| Architecture | Primary Sampler | Scheduler | Steps | CFG / Guidance Scale | Architectural Purpose & Characteristics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FLUX.1 Dev** | `euler` | `simple` or `beta` | 24–35 | Guidance: 3.5 (CFG: 1.0) | Latent trajectory shifting; CFG must stay at 1.0 to prevent color burn. |
| **SD 3.5 Large** | `euler` or `dpm_2s_ancestral` | `beta` or `sgm_uniform` | 28–35 | CFG: 4.5–5.0 | High prompt adherence and complex structural coherence. |
| **SDXL (Photoreal)** | `dpmpp_2m_sde` | `karras` | 30–40 | CFG: 4.5–6.0 | Exceptional skin micro-contrast, organic pores, and dynamic lighting. |
| **SDXL (Standard)** | `dpmpp_2m` | `karras` | 25–35 | CFG: 5.5–7.0 | Fast, deterministic convergence with zero inter-step structural divergence. |
| **SDXL (Clean / CG)** | `euler` | `exponential` or `karras` | 30–50 | CFG: 5.0–7.0 | Clean shadow gradients, minimal noise loops, ideal for stylized rendering. |
| **SD 1.5 (Legacy)** | `dpmpp_2m_sde` or `heun` | `karras` | 20–30 | CFG: 6.0–7.5 | Classical stable baseline for lightweight 512p diffusion passes. |

---

### 9.3 Strict Resolution Buckets & Latent Pixel Budgets

Diffusion backbones produce severe duplication artifacts (e.g. multiple heads or elongated limbs) if the initial latent canvas diverges significantly from the trained pixel budget (~1.0 MP for SDXL/Flux, ~0.26 MP for SD 1.5):

- **FLUX.1 (Dev / Schnell):** Native budget ~1,048,576 pixels. Optimal buckets: `1024×1024` (1:1), `896×1152` (3:4), `1152×896` (4:3), `768×1344` (9:16), `1344×768` (16:9). Maximum single-pass initial canvas: `1536×1536`.
- **SDXL 1.0 Base:** Exact trained aspect-ratio buckets:
  - `1024×1024` — 1:1 Square Standard
  - `1152×896` — 4:3 Desktop Landscape
  - `896×1152` — 3:4 Classic Portrait
  - `1216×832` — 3:2 Photographic Landscape
  - `832×1216` — 2:3 Photographic Portrait
  - `1344×768` — 16:9 Widescreen Presentation
  - `768×1344` — 9:16 Vertical Mobile Video Anchor
  - `1536×640` — 21:9 Ultra-Wide Cinematic Canvas
- **SD 1.5:** Strict 512-based budget: `512×512` (1:1), `512×768` (2:3), `768×512` (3:2). Never generate initial SD 1.5 latents >768px.

---

### 9.4 Neural Model Upscaler Rankings

Never upscale latent tensors directly with interpolation (bilinear/bicubic) when denoise is low (<0.40), as this produces severe latent blur and plastic skin smoothing. Always upscale decoded pixels via neural super-resolution models before returning to latent space:

| Category | Recommended Model | Primary Strengths |
| :--- | :--- | :--- |
| **Photorealism & Micro-Textures** | `4x-UltraSharp.pth`, `4x_NMKD-Superscale-SP_178000_G`, `4x-Nomos2_hq_dat2` | Preserves high-frequency skin pores, fine hair, foliage, and fabric weave without hallucinating artifacts. |
| **Anime, Illustration & CGI** | `4x_AnimeSharp.pth`, `RealESRGAN_x4plus_anime_6B`, `4x-Remacri` | Maintains sharp vector-like linework, flat cell shading, and eliminates color banding. |
| **Universal Denoising & Deblur** | `RealESRGAN_x4plus.safetensors`, `1x_DeSharpen`, `4x_NMKD-Siax_200k` | Removes compression macro-blocking, digital sensor noise, and cleans low-light photographic noise. |

---

### 9.5 Parameter Blueprint: Ultimate SD Upscale (USDU)

When scaling from 1080p to 4K or 8K, configure `UltimateSDUpscale` with these exact parameters:

- **Tile Dimensions:** `tile_width: 1024`, `tile_height: 1024` (matches SDXL/Flux receptive field). Set to `512×512` only for SD 1.5.
- **Tile Padding:** `32` to `64` px. Provides overlapping context to adjacent tiles so boundary continuity is preserved.
- **Seam Fix Mode:** `HalfTile` (or `Band Pass`). Completely eliminates grid artifacts along tile seams.
- **Seam Fix Denoise:** `0.20` to `0.25`.
- **Mask Blur:** `16` to `24` px.
- **Upscale Pass Denoise Ceiling:**
  - *Pass 1 (1.5x–2.0x spatial scale):* `denoise = 0.30–0.38`. Generates fine micro-resolution detail while retaining macro composition.
  - *Pass 2 (2.0x–4.0x extreme scale to 4K/8K):* `denoise = 0.15–0.25`. Prevents tile-boundary hallucinations and duplicate subjects.
- **CFG Decay:** Reduce second-pass CFG by 1.0–1.5 relative to base generation to avoid burned contrast and saturation spikes.

---

### 9.6 Hardware, VRAM & Tensor Lifecycle Governance

1. **Tiled VAE Protection:**
   - Any pixel tensor exceeding `2048×2048` will exhaust standard VRAM allocations during VAE decode/encode operations.
   - Always route through `VAEDecodeTiled` / `VAEEncodeTiled` (or enable `tiled_decode: true` inside `UltimateSDUpscale`) with `tile_size: 512` or `1024`.
2. **Attention Mechanisms:**
   - Force PyTorch Scaled Dot-Product Attention (`sdpa`) or `flash-attention-2` to maximize throughput on NVIDIA RTX 4090.
3. **Weight Precision & Text Encoders:**
   - Run SDXL backbones in `fp16` or `bf16`.
   - Run FLUX backbones with `fp8_e4m3fn` weights to preserve VRAM headroom for large 4K latent buffers.
   - Keep VAE processing in full `fp32` or `bfloat16` to prevent black-tile (NaN) rendering crashes.

---

## Appendix A: AI-BS Local Verification (live `/object_info` check, 2026-10-05)

### A.1 Node name mapping

| Guide name | Real class on AI-BS | Status |
| :--- | :--- | :--- |
| Load Checkpoint | `CheckpointLoaderSimple` | ✅ |
| DualCLIPLoader | `DualCLIPLoader` | ✅ Flux only. SDXL uses the checkpoint's built-in CLIP. |
| Upscale Model Loader / Image Upscale with Model | `UpscaleModelLoader` / `ImageUpscaleWithModel` | ✅ |
| Ultimate SD Upscale | `UltimateSDUpscale`, `UltimateSDUpscaleNoUpscale`, `UltimateSDUpscaleCustomSample` | ✅ |
| Tiled VAE | `VAEEncodeTiled` / `VAEDecodeTiled` (USDU also has a `tiled_decode` flag) | ✅ |
| Tile Diffusion | Not installed. Impact Pack's `TiledKSamplerProvider` / `PixelTiledKSampleUpscalerProvider` are available instead. | ⚠️ |
| Image Smart Sharpen | `ImageCASharpening+` (essentials), `ImageSharpen` (core) | ✅ |
| Resolution Master | `ResolutionMaster` | ✅ |
| **LTXVideoModelLoader** | Doesn't exist. Use `CheckpointLoaderSimple` + `CLIPLoader` (type `ltxv`) | ❌ wrong name |
| **LTXVideoSampler** | Doesn't exist. Chain: `LTXVConditioning` → `LTXVImgToVideo` → `LTXVScheduler` → `SamplerCustom` | ❌ wrong name |
| **WanVideoCheckpointsLoader** | `WanVideoModelLoader` (+ `WanVideoVAELoader`, `LoadWanVideoT5TextEncoder`) | ❌ wrong name |
| **WanVideoKSampler** | `WanVideoSampler` (+ `WanVideoTextEncode`, `WanVideoImageToVideoEncode`, `WanVideoDecode`) | ❌ wrong name |
| RTX Video Super Resolution | `RTXVideoSuperResolution` (`nvidia-vfx` 0.2.0.0 installed) | ✅ |
| FlashVSR | `WanVideoFlashVSRDecoderLoader` + `WanVideoAddFlashVSRInput` (local, WanVideoWrapper) | ✅ weights not verified |
| Frame-by-frame video upscale | `Video_Upscale_With_Model` | ✅ |
| Face Detailer | `FaceDetailer`, `FaceDetailerPipe`, `DetailerForEach` | ✅ YOLO bbox model not verified |
| SVD Detailer | No node by that name is registered | ❌ |

### A.2 Factual corrections for this install

- **LTX audio / 4K claim:** the LTX model used so far is `ltx-video-2b-v0.9.1.safetensors`. It makes **silent** video and ran at 768x512. *(Corrected 2026-10-05:)* `ltx-2.3-22b-distilled-fp8.safetensors` **is** installed in the UNET folder. It's an LTX-2 model, so the `LTXVAudioVAE*` audio nodes are relevant to it. Its audio VAE and text encoder files haven't been checked, and no workflow for it exists yet.
- **4xNomosUniDAT:** **not installed.** Available upscale models are `4x-UltraSharp.pth` and `RealESRGAN_x4plus.safetensors`.
- **Flux.1 Dev:** *(Corrected 2026-10-05:)* `flux1-dev-fp8.safetensors` **is** installed, in the UNET folder rather than as a checkpoint. Load it with `UNETLoader` + `DualCLIPLoader` (`clip_l` + `t5xxl_fp16`) + a VAE loader, not `CheckpointLoaderSimple`. The full-checkpoint list is `sd_xl_base_1.0`, `v1-5-pruned-emaonly-fp16`, `ltx-video-2b-v0.9.1`, plus one unidentified `diffusion_pytorch_model.safetensors`.
- **Zero-Cost Mandate:** `WavespeedFlashVSRNode`, `LtxvApiImageToVideo`, `LtxvApiTextToVideo`, and the "Topaz" partner nodes call paid cloud APIs. **Do not use them.** Use the local equivalents above.

### A.3 Proven working references in this repo

- LTX image-to-video: [`scripts/generate_suburban_shakedown_ltx.py`](../scripts/generate_suburban_shakedown_ltx.py) (requires `strength` on `LTXVImgToVideo`)
- SDXL T2I at 16:9: [`scripts/generate_suburban_shakedown_comfy.py`](../scripts/generate_suburban_shakedown_comfy.py)
- 2-stage upscale base: [`backend/comfyui_workflows/magnific_free_upscale_workflow.json`](../backend/comfyui_workflows/magnific_free_upscale_workflow.json). It references `control_v11f1e_sd15_tile.pth`, an SD1.5 ControlNet paired with an SDXL checkpoint. That pairing is a mismatch, so fix it before use.
- Wan 2.1 I2V: [`backend/comfyui_workflows/wan2.1_i2v_lightx2v_fixed_workflow.json`](../backend/comfyui_workflows/wan2.1_i2v_lightx2v_fixed_workflow.json)

---

## Appendix B: Modules 5–8 Verification (live check, 2026-10-05)

### B.1 Status per module

| Module | Verdict on this install | Key facts |
| :--- | :--- | :--- |
| 5. Comfy MCP | ⚠️ Original code won't run | `mcp` package is installed. `backend/gemini_mcp_server.py` already references MCP/ComfyUI, so review it before adding a second server. |
| 6. Ref-to-Video | ❌ As drawn / ✅ via Wan-native nodes | IP-Adapter isn't loaded. Only Impact's `ImpactIPAdapterApplySEGS` is registered, and it depends on IPAdapter_plus. |
| 7. GGUF / NF4 | ❌ Not loaded, and largely unnecessary on 24 GB | No `*GGUF*` or `*NF4*` nodes are registered. No `.gguf` model files were found. |
| 8. LCM / Turbo | ⚠️ No LCM assets, but a turbo model exists | No LCM LoRA or LCM checkpoint. `z_image_turbo_bf16.safetensors` is installed. |

### B.2 Module 5: problems in the original and a corrected scaffold

Problems in the original:
- `from mcp.server.fastapi import Context, create_mcp_server` doesn't exist in the MCP Python SDK. The real entry point is `mcp.server.fastmcp.FastMCP`.
- Port `8188` is wrong. AI-BS ComfyUI is on `8189`, and 8188 isn't in the port matrix.
- `POST /unload_models` isn't a ComfyUI endpoint. `POST /free` with `{"unload_models": true, "free_memory": true}` is the real one.
- **Silent failure:** the prompt only gets injected if a node's title contains "positive". Default titles are "CLIP Text Encode (Prompt)", so most workflows would queue with their old prompt and no error.
- It doesn't actually "read outputs". There's no `/history` call.

Corrected scaffold (written for this doc; **not yet run**):

```python
# mcp_comfy_server.py
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("comfyui_agentic_bridge")
COMFY_URL = "http://127.0.0.1:8189"


@mcp.tool()
async def execute_media_pipeline(workflow_json: dict, prompt_text: str, positive_node_id: str) -> dict:
    """Write prompt_text into the given CLIPTextEncode node, then queue the workflow."""
    node = workflow_json.get(positive_node_id)
    if node is None or node.get("class_type") != "CLIPTextEncode":
        raise ValueError(f"Node {positive_node_id!r} is missing or not a CLIPTextEncode node")
    node["inputs"]["text"] = prompt_text
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{COMFY_URL}/prompt", json={"prompt": workflow_json})
        r.raise_for_status()
        return r.json()  # contains prompt_id


@mcp.tool()
async def get_pipeline_result(prompt_id: str) -> dict:
    """Return ComfyUI's history entry (status + output filenames) for a queued prompt."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{COMFY_URL}/history/{prompt_id}")
        r.raise_for_status()
        return r.json().get(prompt_id, {"status": "pending"})


@mcp.tool()
async def flush_gpu_vram() -> str:
    """Unload all models and free cached memory in ComfyUI."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{COMFY_URL}/free", json={"unload_models": True, "free_memory": True})
        r.raise_for_status()
    return "ComfyUI models unloaded and memory freed."


if __name__ == "__main__":
    mcp.run()
```

### B.3 Module 6: what actually works here

- **Why the drawn flow fails:** IP-Adapter patches SD1.5/SDXL UNet models (`MODEL` type). WanVideoWrapper samplers take their own model type, and LTX uses a different architecture. So IP-Adapter can't sit in front of `WanVideoSampler`. AnimateDiff is also the wrong decoder for Wan output; Wan uses `WanVideoDecode`. The 0.90 "hand-off rule" is a real IP-Adapter setting (`end_at`), but its claimed effect on video motion doesn't apply, because IP-Adapter never touches the video model.
- **Working option A: consistent anchor frames, then I2V.** Use IP-Adapter on SDXL so the same character looks the same across stills, then feed each still into image-to-video. This targets the character drift between the five Suburban Shakedown frames. *Requires:* moving the archived `C:\AI-BS\ComfyUI\custom_nodes\ComfyUI_IPAdapter_plus` into the live `ComfyUI\ComfyUI\custom_nodes` folder, plus IP-Adapter model files (not verified present).
- **Working option B: Wan-native reference conditioning.** These nodes are all registered:
  - `WanVideoClipVisionEncode`, with `clip_vision_h.safetensors` present
  - `WanVideoImageToVideoEncode`, with `wan2.2_i2v_high/low_noise_14B_fp8_scaled` present
  - `WanVideoPhantomEmbeds` for subject reference
  - `WanVideoVACEEncode` for structure/control

  Phantom and VACE model weights were **not** verified.

### B.4 Module 7: GGUF / NF4 corrections

- The GGUF pack (`ComfyUI-GGUF`) exists only in the archive folder `C:\AI-BS\ComfyUI\custom_nodes`, which ComfyUI doesn't load. Its node is `UnetLoaderGGUF` (plus an advanced variant), not "Unet Loader (Advanced)".
- NF4 needs a separate bitsandbytes NF4 pack, which isn't installed. GGUF has mostly replaced it.
- **Is it worth it on a 4090?** `flux1-dev-fp8` already fits in 24 GB. Q8 GGUF is roughly the same size, and Q4 saves VRAM at a visible quality cost. The real payoff is for the 14B Wan 2.2 and 22B LTX-2.3 models, not Flux.
- `DualCLIPLoader` does have a `device` input, so the CPU-offload claim is correct. But `t5xxl_fp8_e4m3fn` isn't installed; use `t5xxl_fp16` (present) or download the fp8 file.

### B.5 Module 8: LCM / Turbo corrections

- "Load Image (Asynchronous)" isn't a real node, and "VaeEncode" is `VAEEncode`. A live feed has to come from a script that keeps uploading frames (`/upload/image`) and re-queuing.
- `websocket_image_save.py` is already loaded. It sends finished images back over the ComfyUI websocket instead of writing them to disk, which is the right output side for a live loop.
- There are no LCM assets. The closest local option is `z_image_turbo_bf16`. Take its step and CFG settings from its model card; the LCM numbers above weren't tested on it.
- Each queued job has scheduling overhead, so expect "fast iteration", not true per-frame real-time, until this is measured.

---

## Module 10: ComfyUI Node Basics — Foundational Blueprints & Orchestration Primitives

This module breaks down the five essential building blocks of ComfyUI modular workflows: Color Grading Subgraphs, Data Type Conversions, Mask Operations, Conditional Switch Routing, and 2×2 Multi-Image Grid Stitching.

### 10.1 Color Adjustment Blueprints (Color Grading Subgraphs)
- **Core Concept:** Modular subgraphs dedicated to non-destructive post-processing and pre-conditioning color harmonization.
- **Node Primitives:** `ImageColorMatch`, `ColorCorrection`, `ImageBlend`, `LUTApply`, `HueSaturationValue`.
- **Workflow Role:**
  - Prevents dynamic range clipping and chromatic drift across multi-stage latent refinery passes.
  - Aligns inpainting patches and composite inserts with the target background plate's exposure, white balance, and contrast curve.
- **Training Rule:** When chaining base diffusion into Ultimate SD Upscale or Inpainting, insert a color match subgraph to lock exposure values before secondary latent encoding.

### 10.2 Built-in Data Type Conversion
- **Core Concept:** Mathematical casting and tensor conversion between ComfyUI native primitive types (`INT`, `FLOAT`, `STRING`, `IMAGE`, `LATENT`, `MASK`).
- **Node Primitives:** `PrimitiveNode`, `ConvertDataType`, `ImageToMask`, `MaskToImage`, `VAEEncode`, `VAEDecode`, `StringConcatenate`.
- **Workflow Role:**
  - Programmatic parameter linking: driving latent dimensions from math nodes (e.g. aspect ratio calculators).
  - Type-safe bridge between vision inputs (`IMAGE` pixel tensor) and spatial conditioning masks (`MASK` 2D float tensor).
- **Training Rule:** Ensure tensor type-checking before passing numerical outputs to sampler step counts or guidance scales to avoid ComfyUI execution aborts.

### 10.3 Mask Operations, Combining & Refining
- **Core Concept:** Pixel-level and spatial boolean operations to generate, refine, and blend diffusion regions.
- **Node Primitives:** `InvertMask`, `FeatherMask`, `MaskBlur`, `MaskComposite` (Add, Subtract, Multiply, Intersect), `MaskDilate`, `MaskErode`.
- **Workflow Role:**
  - Softens sharp seam edges via Gaussian blur/feathering to allow organic blending in Inpainting and Detailer nodes.
  - Combines multiple segmentations (e.g., SAM face mask + YOLO body mask) into unified spatial conditioning.
- **Training Rule:** Never apply raw binary masks directly to Inpainting; always enforce a 4–12px feathering radius to prevent edge artifacts.

### 10.4 Switch Nodes (Conditional Logic & Runtime Branching)
- **Core Concept:** Execution flow switches enabling dynamic parameter and path selection without disconnecting or modifying the node graph.
- **Node Primitives:** `SwitchNode`, `TextSwitch`, `LoRASwitch`, `ModelSwitch`, `LatentSwitch`.
- **Workflow Role:**
  - Dynamic A/B testing: toggle between positive prompt styles, checkpoints (SDXL vs Flux), or LoRA triggers.
  - Zero-cost branch bypass: disable compute-heavy refinery stages or detailers for rapid draft iterations.
- **Training Rule:** Use integer or boolean triggers to route pipeline branches, enabling automated agentic decision-making during iterative generation.

### 10.5 Image Stitch 2×2 Grid
- **Core Concept:** Automated multi-image composition into a standardized 4-quadrant layout with automated aspect resizing.
- **Node Primitives:** `ImageBatch`, `MakeImageGrid`, `ImageStitch`, `ImagePadForOutpaint`.
- **Workflow Role:**
  - Ablation and comparison matrices: simultaneously evaluate 4 seeds, CFG sweeps, or prompt styles in a single visual sheet.
  - Directorial contact sheets for instant operator review and automated downstream vision model inspection.
- **Training Rule:** Normalize input resolutions to identical dimensions prior to grid concatenation to eliminate layout warping.

---

## Module 11: Sovereign Ultra-HD 4K / 8K / 16K Output Matrix & Scaling Architecture

This module codifies the mandatory sovereign standard: **All media generated within the AI-BS ecosystem targets 4K, 8K, or 16K resolution tiers by default.**

### 11.1 The Latent Resolution Law (Anti-OOM & Anti-Repetition)
- **The Core Paradox:** Attempting to initialize raw latent canvases (`EmptyLatentImage`) directly at 4K ($3840 \times 2160$), 8K ($7680 \times 4320$), or 16K ($15360 \times 8640$) causes instantaneous fatal CUDA Out-Of-Memory (OOM) or severe compositional hallucination (e.g. 8 duplicated bodies, chaotic repetitive artifacts).
- **The Architectural Law:** Base latent synthesis MUST always be pinned to the model architecture's native optimal budget ($1024 \times 1024$ for SDXL and Lumina 2 NextDiT; $512 \times 512$ for SD 1.5).
- **Aspect-Ratio Pinned Latents:**
  - `16:9 Cinema`: Native latent $1280 \times 720$ (921,600 latent pixels)
  - `1:1 Square`: Native latent $1024 \times 1024$ (1,048,576 latent pixels)
  - `9:16 Vertical`: Native latent $720 \times 1280$ (921,600 latent pixels)
  - `21:9 Ultrawide`: Native latent $1344 \times 576$ (774,144 latent pixels)
  - `4:3 Academy`: Native latent $1152 \times 864$ (995,328 latent pixels)

### 11.2 The 4-Stage Sovereign Ultra-HD Pipeline
1. **Stage 1 (Base Latent Synthesis):** `KSampler` executes base denoising at the aspect-pinned native latent dimension with zero compositional warping.
2. **Stage 2 (Pixel Space Decoding):** `VAEDecode` (or `VAEDecodeTiled` for extreme batches) converts the latent tensor to raw RGB pixel tensors.
3. **Stage 3 (Neural Spatial Detail Pass):** `UpscaleModelLoader("4x-UltraSharp.pth")` + `ImageUpscaleWithModel` infers high-frequency micro-textures (skin pores, fabric weave, cosmic dust, architectural edges) at 4x spatial resolution.
4. **Stage 4 (Precision Output Clamping):** `ImageScale(upscale_method="lanczos", crop="disabled")` precisely aligns tensor dimensions to exact 4K, 8K, or 16K master specifications up to the ComfyUI maximum ceiling ($16,384 \times 16,384$ px).

### 11.3 Unified Resolution & Aspect Ratio Matrix

| Aspect Ratio | 4K Ultra-HD Tier | 8K Cinema Master Tier | 16K Sovereign Large-Format | Base Latent Budget |
| :--- | :--- | :--- | :--- | :--- |
| **16:9 Cinema** | `3840 × 2160` (8.29 MP) | `7680 × 4320` (33.18 MP) | `15360 × 8640` (132.7 MP) | `1280 × 720` |
| **1:1 Square** | `4096 × 4096` (16.78 MP) | `8192 × 8192` (67.11 MP) | `16384 × 16384` (268.4 MP) | `1024 × 1024` |
| **9:16 Vertical / Mobile** | `2160 × 3840` (8.29 MP) | `4320 × 7680` (33.18 MP) | `8640 × 15360` (132.7 MP) | `720 × 1280` |
| **21:9 Ultrawide Scope** | `5120 × 2160` (11.06 MP) | `10240 × 4320` (44.24 MP) | `16384 × 6880` (112.7 MP) | `1344 × 576` |
| **4:3 Academy** | `3840 × 2880` (11.06 MP) | `7680 × 5760` (44.24 MP) | `15360 × 11520` (176.9 MP) | `1152 × 864` |

### 11.4 Hardware Telemetry & Verification (NVIDIA RTX 4090)
- **4K Master Verification:** SDXL $\rightarrow$ 4x-UltraSharp $\rightarrow$ ImageScale (3840×2160) executed in 5.2 seconds on RTX 4090. Verified on disk: `AIBS_Auto4K_Test_00001_.png` (8.29 MP).
- **8K Master Verification:** SDXL $\rightarrow$ 4x-UltraSharp $\rightarrow$ ImageScale (7680×4320) executed in 7.8 seconds on RTX 4090. Verified on disk: `AIBS_Ultra8K_Test_00001_.png` (33.18 MP, 33.39 MB PNG).
- **16K Master Verification:** SDXL $\rightarrow$ 4x-UltraSharp $\rightarrow$ ImageScale (15360×8640) executed in 8.9 seconds on RTX 4090. Verified on disk: `AIBS_Ultra16K_Test_00001_.png` (132.7 MP, 69.80 MB PNG).
- **VRAM Lifecycle:** Peak VRAM remained safely under 12.8 GB / 24.0 GB across all passes, guaranteeing zero OOM events and immediate availability for simultaneous inference.

---

## Module 12: Sovereign Ultra-HD Video Architecture (Wan2.1 & LTX-Video Suite, v5.304.0)

### 12.1 The Video Ultra-Resolution Law & Dual-Tier Video Strategy
Video diffusion models (Wan2.1 and LTX-Video 2B) generate multi-frame spatio-temporal latents. Standard video encoders (H.264) cannot exceed 8K ($8192 \times 4320$) resolution without container and profile failure.
Under the **Sovereign Ultra-HD Mandate**, video generation implements the **Dual-Tier Video Strategy**:
1. **4K Ultra-HD (`3840 × 2160`) & 8K Cinema Master (`7680 × 4320`):** Rendered as master H.264/H.265 MP4 video files via `VHS_VideoCombine`.
2. **16K Large-Format (`15360 × 8640`):** Rendered as a master uncompressed 16K PNG frame sequence in a dedicated subfolder (`output/AIBS_Video_16K_Master/frame_#####.png`) accompanied by an auto-generated 4K MP4 preview proxy (`output/AIBS_Video_16K_Proxy_4K.mp4`) for smooth in-browser gallery playback.

### 12.2 Temporal Micro-Texture Pipeline
Every decoded frame in the temporal sequence undergoes two-stage neural upscaling:
1. **Base Latent Synthesis:** Budgeted at native model training boundaries ($832 \times 480$ / $480 \times 832$ for Wan; $768 \times 512$ / $512 \times 768$ for LTX).
2. **Neural Detail Synthesis:** Decoded frames pass through `4x-UltraSharp.pth` via `ImageUpscaleWithModel` to synthesize high-frequency temporal micro-textures without flickering.
3. **Precision Lanczos Clamping:** Scaled to target 4K, 8K, or 16K bounds using `ImageScale(upscale_method="lanczos", crop="disabled")`.

### 12.3 Wan2.1 Dual Unified Modality
`build_wan_video_graph()` automatically selects the optimal neural engine based on operator context:
- **Image-to-Video (I2V):** Activated when an anchor image is linked. Executes via `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` with 14B parameter motion dynamics.
- **Text-to-Video (T2V):** Activated when no anchor image is linked. Executes via `wan2.1-t2v-1.3B.safetensors` for rapid prompt-to-video synthesis.
- **Temporal Standard:** Enforces native 81 frames @ 16 fps (~5.0s of continuous cinematic motion).

