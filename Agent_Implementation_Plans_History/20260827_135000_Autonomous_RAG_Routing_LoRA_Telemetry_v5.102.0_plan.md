# Implementation Plan: Autonomous RAG, Multi-Agent Routing, LoRA Fine-Tuning & GPU Telemetry Suite (v5.102.0)

## Overview
Comprehensive 4-Phase autonomous AI expansion capitalizing on the RTX 4090 24GB hardware surplus:
1. **Phase I: Vectorized Retrieval-Augmented Generation (RAG):**
   - Upgraded `backend/core/project_rag.py` to parse Final Draft XML (`.fdx`) in addition to Fountain/Text.
   - Built and ran `backend/scripts/ingest_manuscripts_chroma.py`, indexing 1,080+ documents across all 7 projects into ChromaDB using `nomic-embed-text`.
2. **Phase II: AI-BS Multi-Agent Gateway Routing:**
   - Created `backend/routers/agent_routing.py` with isolated parameter profiles (`/api/agent/draft`, `/api/agent/compile`, `/api/agent/noco`, `/api/agent/route`).
   - Registered router into `backend/main.py` and `backend/AI_BS_Backend.py`.
3. **Phase III: Structural LoRA Fine-Tuning Pipeline:**
   - Built `scripts/train_stehouwer_lora_unsloth.py` merging 6,421 dialogue turns across base persona, Project NoCo biomimetics, and Suno AI prompting schemas into `database/Unified_Stehouwer_Persona_v3.jsonl` with 4-bit NF4 QLoRA export config.
4. **Phase IV: GPU Telemetry & ComfyUI Expansion:**
   - Exposed `GET /api/system/gpu-telemetry` in `backend/routers/system_router.py` reading live RTX 4090 VRAM allocations, GPU temperatures, and utilization.
   - Integrated real-time VRAM allocation meter into `frontend/components/SystemHealthTab.jsx` adhering to Core Rule 4.
