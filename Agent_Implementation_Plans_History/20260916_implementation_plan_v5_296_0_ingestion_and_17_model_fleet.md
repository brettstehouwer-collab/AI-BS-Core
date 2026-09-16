# Implementation Plan: Stehouwer LLM 17-Model Unrestricted Fleet, 175-Session Brain Ingestion (139,512 Vault Items / 67,748 ChromaDB Vectors) & Port 8080 Lifespan Stabilization (v5.296.0)

**Version:** `v5.296.0`  
**Date:** 2026-09-16  
**Status:** Executed & Verified  

---

## 1. Technical Architecture & Design
- **Brain Ingestion:** Recursive JSONL parsing of 175 historical sessions from `C:\Users\footb\OneDrive\Desktop\ingest folder`, extracting conversation turns, subagent tasks, implementation plans, and walkthroughs into `backend/stehouwer_vault.db` and ChromaDB `stehouwer_llm_memory`.
- **ChromaDB Provider Pinning:** Bind ONNX embedding session to `CPUExecutionProvider` in `backend/core/memory_bank.py` to prevent missing CUDA 13 DLL load crashes on Windows host.
- **Model Compilation:** Update all 17 Ollama Modelfiles on `E:\AI_BS_Resources\Ollama` with affirmative uncensored sovereign directive, 81-121 tool declarations, and Flash Attention (`OLLAMA_FLASH_ATTENTION=1`).
- **Vision Matting Startup Optimization:** Pre-download and cache `birefnet-general` in `C:\AI-BS\models\rembg` to eliminate blocking synchronous downloads during FastAPI startup lifespan.
- **Version Tracking & Mirror Parity:** Sweep all frontend UI badges across 4 mirrors to `v5.296.0`, verify 100% SHA256 parity, and deploy to Firebase Hosting.

---

## 2. Verification Results
- Ingestion passed in 7.89s (139,512 Vault rows, 67,748 vector embeddings).
- All 17 Ollama models verified on `E:\AI_BS_Resources\Ollama`.
- Direct FastAPI (`http://127.0.0.1:8080/api/chat`) and Go Gateway (`http://127.0.0.1:8000/api/chat`) confirmed 100% operational with sub-second token generation on NVIDIA RTX 4090.
- Vite build completed (27.32s) and deployed live to Firebase Hosting (`https://ai-bs-dashboard.web.app`).
