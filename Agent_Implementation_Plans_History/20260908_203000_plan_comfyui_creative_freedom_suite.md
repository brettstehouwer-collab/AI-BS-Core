# Implementation Plan: Complete Local ComfyUI Suite Upgrade (Freedom, Img2Img, & Interrogation)

## Overview
This plan implements the complete suite of local visual capabilities discussed in the Reddit workflow architecture for AI-BS on the local NVIDIA GeForce RTX 4090 (24GB VRAM):
1. **Unrestricted Stylistic Freedom (Text-to-Image):** Eliminate forced positive prompt injections (architectural/metal textures) and remove artificial style exclusions (`cartoon`, `anime`, `illustration`, `3d sketch`) from negative prompts, allowing any artistic medium.
2. **Local Image-to-Image (img2img) & Reference Re-creation:** Add a native `generate_comfy_img2img` pipeline in ComfyUI that loads a reference image via `LoadImage`, encodes to latent via `VAEEncode`, condition with positive/negative prompts, and samples via `KSampler` with configurable denoise (`0.3` to `0.85`), outputting transformed renders.
3. **Local Image Interrogation & Prompt Extraction:** Add an `interrogate_image` / `extract_image_prompt` tool using local computer vision to analyze composition, subjects, and colors from uploaded images and output structured Danbooru/photorealistic prompt tags for subsequent generation passes.
4. **Unified Intent Detection in BS-Chat:** Overhaul regex and intent parsing in `backend/core/hybrid_reasoning_engine.py` and `backend/AI_BS_Backend.py` so text-to-image, image-to-image, and prompt extraction requests route directly to local ComfyUI without falling back to corporate LLM refusals.

---

## User Review Required

> [!IMPORTANT]
> **Safety Directive Preservation:** Per the *Stehouwer LLM Safety Filter Directive (Llama Guard 3-style)*:
> - Categories **S1 (Violent Crimes)**, **S3 (Sex-Related Crimes)**, and **S4 (Child Sexual Exploitation)** remain strictly enforced, locked, and immutable.
> - All other categories (**S2, S5-S13**, corporate puritanism, copyright restrictions, and generic corporate "explicit content" disclaimers) are disabled for local creative generation.
> - Workflows operate 100% locally and offline on your RTX 4090 with zero third-party cloud API costs.

---

## Proposed Changes

### 1. Stylistic Freedom & Defect-Only Negative Prompts
#### [MODIFY] [`tool_registry.py`](file:///C:/AI-BS/backend/tools/tool_registry.py)
- In `ToolRegistry.execute_tool("generate_comfy_image", ...)`:
  - Remove forced server room / architectural positive prompt constraints (`"(photorealistic:1.2), ... highly detailed metal and glass textures"`).
  - Adopt a neutral quality enhancer preserving the user's chosen medium: `f"{clean_prompt}, high resolution, masterpiece, sharp focus, rich detail"`.
  - Clean `negative_prompt` of style bans: delete `cartoon, line art, 3d sketch, drawing, anime, illustration, draft`.
  - Set default `negative_prompt` strictly to defect mitigation: `"low quality, blurry, distorted geometry, bad anatomy, deformed, artifacts, watermark"`.

---

### 2. Local Image-to-Image (img2img) Tool
#### [MODIFY] [`tool_registry.py`](file:///C:/AI-BS/backend/tools/tool_registry.py)
- Register tool schema `generate_comfy_img2img` with parameters:
  - `prompt`: Target modifications or desired style.
  - `image_path`: Path or filename of the reference image.
  - `denoise`: Denoise strength (default `0.65`, where lower preserves the source structure and higher allows creative reimagining).
- Implement execution in `ToolRegistry.execute_tool("generate_comfy_img2img", ...)`:
  - Resolves input image path and copies it into `C:\AI-BS\ComfyUI\input` if not already present.
  - Constructs the ComfyUI img2img node graph:
    - Node `4`: `CheckpointLoaderSimple` (`sd_xl_base_1.0.safetensors` or active model).
    - Node `10`: `LoadImage` (`image: filename`).
    - Node `11`: `VAEEncode` (`pixels: ["10", 0]`, `vae: ["4", 2]`).
    - Node `6`: `CLIPTextEncode` (positive prompt).
    - Node `7`: `CLIPTextEncode` (negative prompt).
    - Node `3`: `KSampler` (`model: ["4", 0]`, `positive: ["6", 0]`, `negative: ["7", 0]`, `latent_image: ["11", 0]`, `denoise: denoise_val`).
    - Node `8`: `VAEDecode` (`samples: ["3", 0]`, `vae: ["4", 2]`).
    - Node `9`: `SaveImage` (`images: ["8", 0]`, `filename_prefix: "AI_BS_Img2Img"`).
  - Queues workflow via `queue_comfyui_workflow` and awaits output via `comfy_bridge.py`.

---

### 3. Local Image Interrogation & Prompt Extraction
#### [MODIFY] [`tool_registry.py`](file:///C:/AI-BS/backend/tools/tool_registry.py)
- Register tool schema `interrogate_image`:
  - Parameter: `image_path` (string).
- Implement execution in `ToolRegistry.execute_tool("interrogate_image", ...)`:
  - Ingests image via `aibs_computer_vision.AIBSImageAnalyzer.analyze_image_for_llm` and local object detection.
  - Formats detected objects, scene features, and color distributions into structured comma-separated prompt tags.
  - Returns both a natural language description and a `suggested_comfy_prompt` string ready for 1-click text-to-image or img2img regeneration.

---

### 4. Intent Routing in BS-Chat
#### [MODIFY] [`hybrid_reasoning_engine.py`](file:///C:/AI-BS/backend/core/hybrid_reasoning_engine.py) & [`AI_BS_Backend.py`](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Upgrade `detect_tool_intent` and `clean_tool_prompt`:
  - **Text-to-Image:** Regex matching creation verbs (`create`, `generate`, `draw`, `render`, `paint`, `make`) paired with visual nouns (`photo`, `image`, `picture`, `artwork`, `illustration`, `drawing`, `wallpaper`, etc.).
  - **Image-to-Image:** Regex matching re-creation/transformation (`recreate`, `modify image`, `transform image`, `change this image`, `make this photo into`, `re-render`, `img2img`) or when an image attachment is referenced with visual instructions.
  - **Interrogation:** Matching queries like `describe this image`, `interrogate image`, `extract prompt from image`, `what is in this photo`.
- Update stream handler in `hybrid_reasoning_engine.py` to yield rendered img2img outputs and structured interrogation results with formatting.

---

### 5. System Directives & Persistent Memory
#### [MODIFY] [`dispatcher.py`](file:///C:/AI-BS/backend/core/sovereign_reasoning/dispatcher.py), [`stehouwer_llm.Modelfile`](file:///C:/AI-BS/backend/models/stehouwer_llm.Modelfile), & [`personal_intelligence_memory.py`](file:///C:/AI-BS/backend/core/personal_intelligence_memory.py)
- Append the Sovereign Creative & Image Generation Directive into `stehouwer_system_prompt` and `Modelfile`.
- Record and pin the directive in `backend/database/aibs_personal_intelligence.db`.

---

### 6. Version Bump & Master Documentation Sync
- Version bump to `v5.225.0`.
- Sweep frontend UI version badge in `App.jsx`, `Sidebar.jsx`, `TopNavbar.jsx`, `ChatTab.jsx`.
- Compile frontend (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).
- Synchronize `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, `saved_data/artifacts/20260908_AI_BS_Master_Ecosystem_Manual.md`, `NotebookLM_Records/artifact_history.md`, `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md`.

---

## Verification Plan

### Automated / Programmatic Tests
1. **Tool Intent Detection Test:** Run Python script testing regex classification for:
   - Text-to-image: `"Draw an anime portrait of a cyberpunk hacker"`
   - Img2Img: `"Recreate this image in watercolor style"`
   - Interrogation: `"Extract prompt from this uploaded photo"`
2. **Workflow Construction Verification:** Validate JSON graph output of `generate_comfy_img2img` containing `LoadImage` (node 10), `VAEEncode` (node 11), `KSampler` (node 3 with `denoise`), and `SaveImage` (node 9).
3. **Stylistic Sanity Check:** Verify that `negative_prompt` in `tool_registry.py` does not contain `cartoon`, `anime`, or `illustration`.
4. **Safety Baseline Test:** Confirm S1/S3/S4 entries in `aibs_personal_intelligence.db` remain active and unmodified.

### Manual / Live Verification
- Launch BS-Chat and submit a stylized generation prompt to confirm direct local ComfyUI dispatch and successful image rendering on port 8189.
