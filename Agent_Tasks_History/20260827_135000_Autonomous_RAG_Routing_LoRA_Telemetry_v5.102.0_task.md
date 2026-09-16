# AI-BS 4-Phase Autonomous RAG, Routing, LoRA & Telemetry Tracker

## Phase I: Vectorized Retrieval-Augmented Generation (ChromaDB + FDX/Manuscript Ingestion)
- [x] **Step 1.1**: Upgrade `backend/core/project_rag.py` to parse Final Draft XML (`.fdx`) in addition to Fountain/Text, extracting scene headings, characters, and dialogue.
- [x] **Step 1.2**: Create `backend/scripts/ingest_manuscripts_chroma.py` to index *The Judge Made Him Go!* / *Echoes Within* and *THE BOOK- The Sagal's* into ChromaDB collections with `nomic-embed-text`.
- [x] **Step 1.3**: Validate ChromaDB queries and test retrieval accuracy with test scripts (1,080+ documents across all 7 projects indexed).

## Phase II: AI-BS Multi-Agent Gateway Routing (FastAPI + Castor-RT + Parameter Isolation)
- [x] **Step 2.1**: Create `backend/routers/agent_routing.py` with dedicated endpoints (`/api/agent/draft`, `/api/agent/compile`, `/api/agent/noco`, `/api/agent/profiles`).
- [x] **Step 2.2**: Register `agent_routing` in `backend/main.py` and `backend/AI_BS_Backend.py`.
- [x] **Step 2.3**: Verify multi-agent routing responses and parameter isolation ($T=0.75$ creative vs $T=0.10$ code).

## Phase III: Structural LoRA Fine-Tuning Pipeline (Unsloth/PEFT on 6,414 Turns + NoCo + Suno)
- [x] **Step 3.1**: Create `scripts/train_stehouwer_lora_unsloth.py` configuring 4-bit NF4 QLoRA for RTX 4090 (24GB VRAM).
- [x] **Step 3.2**: Ingest and format dialogue turns from `database/Stehouwer_Persona_Dataset.jsonl`, NoCo microgrid parameters, and Suno AI prompts into `database/Unified_Stehouwer_Persona_v3.jsonl` (6,421 turns).
- [x] **Step 3.3**: Validate dry-run training pass, batch tokenization, and GGUF quantization export path.

## Phase IV: Visual Node & Telemetry Dashboard Expansion (ComfyUI + Real-Time VRAM/GPU Telemetry)
- [x] **Step 4.1**: Expose `GET /api/system/gpu-telemetry` in `backend/routers/system_router.py` reading real VRAM allocation and GPU thermals.
- [x] **Step 4.2**: Integrate real-time VRAM allocation and ComfyUI status into `frontend/components/SystemHealthTab.jsx` adhering to Core Rule 4.
- [x] **Step 4.3**: Recompile frontend with `npm run build` and deploy to Firebase Hosting (`ai-bs-dashboard.web.app`).
- [x] **Step 4.4**: Update master architectural ledgers (`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, chronologies).
