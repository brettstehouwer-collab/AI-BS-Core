# AI-BS Master Directory & File Lookup Index

**Primary Workspaces:**

- **Core Engine & Dashboard:** `C:\AI-BS`
- **Neural Model Storage:** `C:\AI-BS-Models`
- **Publishing & Media Web Portal:** `C:\StehouwerPublishing.com`

---

## 📂 Core Folder Navigation & Quick Reference

### 1. `C:\AI-BS` Directory Structure

| Directory | Description & Key Contents | Usage / Guidelines |
| :--- | :--- | :--- |
| **[`backend/`](file:///C:/AI-BS/backend)** | Central FastAPI cognitive engine, REST API routers, and daemons (`AI_BS_Backend.py`, `drip_trader_daemon.py`, `commercial_gateway/`) | Active production backend code. |
| **[`frontend/`](file:///C:/AI-BS/frontend)** | React + Vite command center web application (`src/App.jsx`, `src/PublicPlaygroundTab.jsx`, `src/PublicCheckoutTab.jsx`) | Modern UI dashboard & storefront deployed to Firebase Hosting (`ai-bs-dashboard.web.app`). |
| **[`go-core/`](file:///C:/AI-BS/go-core)** | High-speed Go Engine binary (`aibs_engine.exe`), reverse proxy gateway, and SHM heartbeat supervisor | Edge proxy & IPC router on Port 8000. |
| **[`obs-core/`](file:///C:/AI-BS/obs-core)** | Portable OBS Studio 30.1.2 installation with WebSocket engine on Port 4455 | DirectX/DXGI hook-based True Game Capture. |
| **[`BroadcastStudioApp/`](file:///C:/AI-BS/BroadcastStudioApp)** | Native Electron broadcast studio application with isolated DirectShow / DXGI game capture | Native desktop studio application. |
| **[`ComfyUI/`](file:///C:/AI-BS/ComfyUI)** | GPU image & WanVideo motion generation server powered by local NVIDIA RTX 4090 VRAM | Accessible on `http://127.0.0.1:8189` / `8188`. |
| **[`rust_master_worker/`](file:///C:/AI-BS/rust_master_worker)** | High-performance Rust multithreaded worker subsystem | Low-overhead background worker. |
| **[`skills/`](file:///C:/AI-BS/skills)** | Agent skills & customized workflows (`agents-sdk`, `cloudflare`, `firebase-firestore`, etc.) | Custom AI agent skill packages. |
| **[`scripts/`](file:///C:/AI-BS/scripts)** | Production automation scripts & utilities (`fix_quotes.py`, `fix_urls.py`, build tools) | Utility & setup scripts. |
| **[`tests/`](file:///C:/AI-BS/tests)** | Automated unit & integration tests (`test_backend_chat.py`, `test_drip_trader.py`) | Automated testing suite. |
| **[`scratch/`](file:///C:/AI-BS/scratch)** | Experimental, exploratory, and one-off test scripts | Safe sandbox zone for temporary code. |
| **[`output/`](file:///C:/AI-BS/output)** | Rendered media outputs (PNG images, MP4 motion clips, stereo WAV tracks) | Output storage location for generated assets. |
| **[`state/`](file:///C:/AI-BS/state)** | Live runtime PID files (`*.pid`), process locks, and daemon supervisor telemetry | System state tracking. |
| **[`InstallerEXE's/`](file:///C:/AI-BS/InstallerEXE's)** | Offline installers, VSIX extensions, binary archives (`cloudflared.exe`, `.apk`, `.zip`) | Standalone tools & installers. |
| **[`Agent_Handoff_Summaries/`](file:///C:/AI-BS/Agent_Handoff_Summaries)** | Historical agent transcripts, session handover notes, and task summaries | Diagnostic & conversation history. |
| **[`stehouwer_vector_memory/`](file:///C:/AI-BS/stehouwer_vector_memory)** | Persistent ChromaDB vector database storing heuristics, past solutions, and knowledge embeddings | Vector memory store. |

---

### 2. `C:\AI-BS-Models` Directory Structure

| Directory | Description & Key Contents |
| :--- | :--- |
| **[`checkpoints/`](file:///C:/AI-BS-Models/checkpoints)** | SDXL and Wan2.2 base model checkpoints (`.safetensors`) |
| **[`diffusion_models/`](file:///C:/AI-BS-Models/diffusion_models)** | High-noise and low-noise WanVideo diffusion UNet weights |
| **[`loras/`](file:///C:/AI-BS-Models/loras)** | Custom LoRA weights for image/video style refinement |
| **[`clip/`](file:///C:/AI-BS-Models/clip)** | Text encoders (`umt5_xxl_fp8`, CLIP ViT-L) |
| **[`vae/`](file:///C:/AI-BS-Models/vae)** | Variational Autoencoders for image/video decoding |

---

### 3. `C:\StehouwerPublishing.com` Directory Structure

| Directory | Description & Key Contents |
| :--- | :--- |
| **[`website-rebuild/`](file:///C:/StehouwerPublishing.com/website-rebuild)** | Active static web pages (`index.html`, `monologs.html`, `library.html`, `guestbook.html`) |
| **[`extracted_assets/`](file:///C:/StehouwerPublishing.com/extracted_assets)** | Downloaded book covers, illustrations, and media assets |
| **[`logs/`](file:///C:/StehouwerPublishing.com/logs)** | Web server access and traffic telemetry logs |

---

## 🛠️ Root Directory Core File Index (`C:\AI-BS`)

- **Configuration & Build Manifests**: [`.env`](file:///C:/AI-BS/.env), [`.gitignore`](file:///C:/AI-BS/.gitignore), [`pyproject.toml`](file:///C:/AI-BS/pyproject.toml), [`requirements.txt`](file:///C:/AI-BS/requirements.txt), [`Dockerfile`](file:///C:/AI-BS/Dockerfile), [`docker-compose.yml`](file:///C:/AI-BS/docker-compose.yml)
- **Primary Control & Launchers**: [`daemon_manager.py`](file:///C:/AI-BS/daemon_manager.py), [`tool_schemas.py`](file:///C:/AI-BS/tool_schemas.py), [`unified_stehouwer_launcher.py`](file:///C:/AI-BS/unified_stehouwer_launcher.py), [`Launch_AI_BS.bat`](file:///C:/AI-BS/Launch_AI_BS.bat), [`Shutdown_AI_BS.bat`](file:///C:/AI-BS/Shutdown_AI_BS.bat), [`rebuild_frontend.bat`](file:///C:/AI-BS/rebuild_frontend.bat)
- **Master Documentation**: [`AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`](file:///C:/AI-BS/AI_BS_MASTER_ARCHITECTURAL_LEDGER.md), [`README.md`](file:///C:/AI-BS/README.md), [`LICENSE`](file:///C:/AI-BS/LICENSE)
- **Active Backend Module Dependencies**: [`cleanup.py`](file:///C:/AI-BS/cleanup.py), [`sandbox_executor.py`](file:///C:/AI-BS/sandbox_executor.py), [`health_check.py`](file:///C:/AI-BS/health_check.py), [`heuristic_filter.py`](file:///C:/AI-BS/heuristic_filter.py), [`imagegen_agent.py`](file:///C:/AI-BS/imagegen_agent.py), [`local_imagegen.py`](file:///C:/AI-BS/local_imagegen.py), [`memory_service.py`](file:///C:/AI-BS/memory_service.py), [`orchestrator_config.py`](file:///C:/AI-BS/orchestrator_config.py), [`token_budget_estimator.py`](file:///C:/AI-BS/token_budget_estimator.py), [`tool_result.py`](file:///C:/AI-BS/tool_result.py)
