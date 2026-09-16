# AI-BS Matrix — Image Generation System

## Overview

AI-BS Matrix has a **dual-mode local image generation pipeline** running on your RTX 4090 (24GB VRAM). All image generation is **100% local** — no cloud APIs required.

---

## Architecture

```
User Request → SwarmOrchestrator.delegate_task()
                    │
                    ▼
            HeuristicsDaemon.classify()
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  Standard Image      Advanced Workflow
  (diffusers)         (ComfyUI)
        │                       │
        ▼                       ▼
  CUDA GPU              Custom Nodes
  ~2-5s/image         ControlNet/IP-Adapter
```

---

## Backend Comparison

| Feature | Local_ImageGen (diffusers) | ComfyUI_Agent | ImageGen_Agent (OpenAI) |
|---|---|---|---|
| **Hardware** | RTX 4090 GPU | RTX 4090 GPU | Cloud API |
| **Speed** | ~2-5s/image | ~5-15s/image | ~10-30s/image |
| **Models** | SD 1.5, SDXL, FLUX.1 | Any ComfyUI model | gpt-image-2 |
| **Cost** | Free | Free | Pay-per-use |
| **Privacy** | 100% local | 100% local | Cloud |
| **Advanced** | Basic | ControlNet, IP-Adapter, img2img | Limited |

---

## Quick Start

### Auto-detect (recommended)

```powershell
# Automatically uses CUDA diffusers on RTX 4090
python local_imagegen.py --prompt "A cozy alpine cabin at dawn"
```

### Force specific backend

```powershell
# Use diffusers with SDXL
python local_imagegen.py --prompt "A cozy cabin" --backend diffusers --model sdxl

# Use diffusers with FLUX.1-schnell (fastest)
python local_imagegen.py --prompt "A cozy cabin" --model flux_schnell

# Use diffusers with FLUX.1-dev (highest quality)
python local_imagegen.py --prompt "A cozy cabin" --model flux_dev
```

### SwarmOrchestrator integration

```python
from bullshit_orchestrator import SwarmOrchestrator
import asyncio

swarm = SwarmOrchestrator()

# Automatic routing (contains "image" keyword)
result = await swarm.delegate_task(
    "generate an image of a cozy cabin",
    "Local_ImageGen"
)
print(result["output"])  # → output/imagegen/generated_XXXX.png

# Force ComfyUI for advanced workflows
result = await swarm.delegate_task(
    "img2img: transform this photo into anime style using controlnet",
    "ComfyUI_Agent"
)
```

---

## Available Models (diffusers backend)

| Model ID | Name | Quality | Speed | Use Case |
|---|---|---|---|---|
| `sd15` | Stable Diffusion 1.5 | Good | Fast (~2s) | Quick drafts, thumbnails |
| `sdxl` | Stable Diffusion XL | Very Good | Medium (~4s) | General purpose, high quality |
| `flux_schnell` | FLUX.1-schnell | Excellent | Fastest (~3s) | Production assets, speed |
| `flux_dev` | FLUX.1-dev | Best | Slowest (~8s) | Final output, maximum detail |

---

## ComfyUI Integration

### Prerequisites

1. Install [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
2. Start ComfyUI: `python main.py` (runs on `http://127.0.0.1:8188`)
3. Install custom nodes as needed (ControlNet, IP-Adapter, etc.)

### Triggering ComfyUI workflows

ComfyUI is auto-triggered when your prompt contains these keywords:

- `controlnet` — ControlNet workflow
- `img2img` or `image to image` — Image-to-image workflow
- `ip-adapter` or `style transfer` — IP-Adapter workflow
- `comfyui` — Force ComfyUI
- `inpaint` or `outpaint` — Inpainting workflow
- `custom node` — Custom node workflow

### Example prompts for ComfyUI

```
"controlnet: use depth map to generate a mountain landscape"
"img2img: transform this photo into oil painting style"
"ip-adapter: apply Van Gogh style to this image"
"inpaint: add a cat to the foreground of this scene"
```

---

## Batch Generation

Generate multiple images at once:

```python
from local_imagegen import LocalImageGen, ImageGenConfig
import asyncio

imagegen = LocalImageGen()

prompts = [
    "A cozy cabin in the woods",
    "A futuristic city skyline",
    "A serene lake at sunset",
]

results = await imagegen.generate_batch(
    prompts=prompts,
    backend="diffusers",
    model="flux_schnell",
)

for i, result in enumerate(results):
    print(f"Image {i+1}: {result.output_path} ({result.generation_time_sec:.1f}s)")
```

---

## Environment Setup

### Python 3.12 + CUDA (required for diffusers)

```powershell
# Virtual environment already created at:
C:\Users\footb\AI-BS_Matrix\ai_bs_img_env\

# Activate before using diffusers backend:
ai_bs_img_env\Scripts\activate

# Verify CUDA is working:
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### Ollama (optional, for fallback)

```powershell
# Already pulled:
ollama pull x/z-image-turbo

# Note: x/z-image-turbo uses MLX which only works on macOS.
# On Windows, use diffusers backend instead.
```

---

## Output Location

All generated images are saved to:

```
C:\Users\footb\AI-BS_Matrix\output\imagegen\
```

Files are named with timestamps and hash-based IDs to prevent overwrites.

---

## Troubleshooting

### "CUDA not available"

Your RTX 4090 needs the CUDA-enabled PyTorch build:

```powershell
ai_bs_img_env\Scripts\activate
python -c "import torch; print(torch.cuda.is_available())"
# Should output: True
```

If False, reinstall with:
```powershell
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### "ComfyUI not connected"

Start ComfyUI first:
```powershell
cd path\to\ComfyUI
python main.py
# Should show: "Starting server. To see the GUI go to http://127.0.0.1:8188"
```

### "Model not found"

Models are downloaded automatically on first use from Hugging Face. Ensure you have internet access for initial download, then generation is fully offline.

---

## Performance Benchmarks (RTX 4090)

| Model | Steps | CFG | Time | VRAM |
|---|---|---|---|---|
| SD 1.5 | 20 | 7.5 | ~2s | ~4GB |
| SDXL | 20 | 7.5 | ~4s | ~6GB |
| FLUX.1-schnell | 4 | 3.5 | ~3s | ~8GB |
| FLUX.1-dev | 25 | 3.5 | ~8s | ~10GB |

---

## File Structure

```
AI-BS_Matrix/
├── local_imagegen.py          # Dual-mode image generation (diffusers + Ollama)
├── comfyui_integration.py     # ComfyUI client for advanced workflows
├── imagegen_agent.py          # OpenAI GPT Image API fallback
├── bullshit_orchestrator.py   # SwarmOrchestrator with image routing
├── ai_bs_img_env/             # Python 3.12 + CUDA virtual environment
├── output/imagegen/           # Generated images output directory
└── stehouwer_vector_memory/   # Ollama models (x/z-image-turbo)
```

---

## Agent Routing Summary

When you ask AI-BS to generate an image, here's what happens:

1. **Keyword detection** — SwarmOrchestrator detects image-related keywords
2. **Workflow classification** — Checks for ComfyUI-specific terms (controlnet, img2img, etc.)
3. **Routing**:
   - Advanced workflow detected → `ComfyUI_Agent`
   - Standard generation → `Local_ImageGen` (CUDA diffusers)
   - No local backend available → `ImageGen_Agent` (OpenAI API fallback)

All processing is **local-first** — cloud APIs are only used as a last resort.
