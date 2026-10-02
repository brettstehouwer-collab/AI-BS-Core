# AI-BS Mission Specification: AI Music & Vocal Production Suite

**Date:** 2026-10-01  
**Status:** LOCKED & APPROVED via `/grill-me`  
**Target Subsystem:** Audio & Vocal Studio (`MusicDAWStudioTab.jsx`, `vst_router.py`, `aibs_vst_daemon.py`, `f5_tts_daemon.py`)  
**Target Version Increment:** Next Release Milestone  

---

## 1. Architectural Scope & Objectives

Integrate a sovereign, zero-cost AI Music & Vocal Production Suite directly into the AI-BS ecosystem, unifying neural stem separation, local vocal synthesis/cloning, and multi-track audio workstation control:

1. **Neural Stem Separation (Demucs)**:
   - Separate input audio (MP3/WAV/FLAC) into 4 isolated stems: `Vocals`, `Drums`, `Bass`, `Other`.
   - Multi-thread execution with on-demand GPU offload and JIT VRAM purge.
2. **Neural Vocal Synthesis & Voice Cloning (F5-TTS)**:
   - Voice cloning and lyrical vocal synthesis via existing backend daemon [`backend/f5_tts_daemon.py`](file:///C:/AI-BS/backend/f5_tts_daemon.py).
   - High-fidelity 24kHz/48kHz WAV audio generation from text/lyric prompts.
3. **DAW & VST Integration**:
   - Direct integration into [`frontend/src/components/daw/MusicDAWStudioTab.jsx`](file:///C:/AI-BS/frontend/src/components/daw/MusicDAWStudioTab.jsx).
   - Real-time stem track loading into Channel Rack, Piano Roll, and Mixer.
   - VST Bridge hook via Port 8013 / [`backend/routers/vst_router.py`](file:///C:/AI-BS/backend/routers/vst_router.py).

---

## 2. Decision Tree Matrix (Resolved via /grill-me)

### Branch 1: Data Schemas & State Persistence
* **Artifact Directory**: `saved_data/audio_stems/<project_id>/`
  - `original.wav`, `vocals.wav`, `drums.wav`, `bass.wav`, `other.wav`.
* **Database Vault**: Table `audio_vocal_projects` in [`backend/stehouwer_vault.db`](file:///C:/AI-BS/backend/stehouwer_vault.db):
  - `id`: TEXT PRIMARY KEY
  - `title`: TEXT
  - `created_at`: TIMESTAMP
  - `source_file`: TEXT
  - `stems_path`: TEXT
  - `vocal_prompt`: TEXT
  - `duration_seconds`: REAL
  - `sample_rate`: INTEGER
  - `status`: TEXT ('queued', 'processing', 'completed', 'failed')
  - `metadata_json`: TEXT
* **Write Mode**: SQLite `PRAGMA journal_mode=WAL;` with busy timeout = 5000ms.

### Branch 2: Concurrency, Locking & Resource Limits
* **JIT VRAM Allocation Policy**:
  - Neural models (Demucs / F5-TTS) load into RTX 4090 VRAM ONLY during active generation passes.
  - Automatic `torch.cuda.empty_cache()` and garbage collection immediately after pass completion.
  - Zero persistent VRAM footprint to maintain Salad top-tier container qualification (>16 GB free VRAM headroom).
* **Thermal & Power Guard**:
  - Bound by [`scripts/gpu_thermal_guardian.py`](file:///C:/AI-BS/scripts/gpu_thermal_guardian.py) (<74°C tripwire).

### Branch 3: Error Handling & Circuit Breakers
* **Fallback Strategy**: If GPU VRAM is under high external demand (>18 GB utilized by Salad), automatically fall back to CPU multi-threading (AMD Ryzen 9 9950X, 16 cores / 32 threads) without failing the job.
* **Timeout & Recovery**: Maximum 180s per separation job; automatically remove orphaned `.tmp` audio chunks on failure.

### Branch 4: Security, Network & Compliance
* **Zero-Cost Mandate**: 100% local runtimes; strictly zero commercial API tokens, paid endpoints, or cloud billing.
* **18-Port Collision Matrix**:
  - Port 8013: VST3 Audio Bridge.
  - Port 8080: FastAPI Core Engine (Router mounted under `/api/v1/audio`).
* **Multi-Mirror Synchronization**: All UI components synchronized across all 4 mirror paths before release build.
