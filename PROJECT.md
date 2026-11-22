# Project: AI-BS Platform Integration & End-to-End Verification

## Architecture
The AI-BS platform integrates native real-time C++20 DX12 simulation with Python Qt/PyQt6 Studio authoring, high-throughput distributed ML training (PySpark / PyTorch / GCP Dataproc Serverless), cloud-synced asset vector memory (ChromaDB / Ollama), a high-concurrency FastAPI cognitive backend, ComfyUI RTX 4090 generative pipelines, and a modern Vite/React frontend dashboard.

```
                                  +---------------------------+
                                  |     Vite Frontend (5173)  |
                                  +-------------+-------------+
                                                |
                                                v
+-------------------------------+  HTTP   +---------------------------+  Proxy  +---------------------------+
| Native Studio / Viewport      | <-----> |   FastAPI Backend (8080)  | ------> | ComfyUI Bridge (8188/8189)|
| - aibs_creator_viewport.exe   |         +-------------+-------------+         | - RTX 4090 (24GB VRAM)    |
| - Sheltered Hub Stations (3)  |                       |                       +---------------------------+
| - Spatial Trigger Volumes (7) |                       v
| - Adam Blend Trees (2201)     |         +---------------------------+
| - Legacy DX Fallback Engine   |         | ChromaDB Vector Memory    |
+-------------------------------+         | - 177 Synced Drive Assets |
                                          | - 7 Cloud Categories      |
                                          +---------------------------+
                                                        ^
+-------------------------------+                       |
| Distributed Training Pipeline | ----------------------+
| - PyTorch 16->64->2 & MLlib   |
| - Local multi-core validation |
| - GCP Dataproc Serverless     |
+-------------------------------+
```

## Feature Inventory
Every Survey feature assigned a milestone (none unassigned).
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Sheltered Hub Stations (3) | Writing Desk, Memory Shelves, and Shared Play stations with state contracts and SQLite schemas | M1 | Survey 1 & ORIGINAL_REQUEST R1 |
| 2 | Spatial Trigger Zones (7) | Containment math and audio cue triggers across 7 zones from awakening to pencil room | M1 | Survey 1 & ORIGINAL_REQUEST R1 |
| 3 | Adam Blend Tree Animations | Adam guide character 2201 likeness verification checks, animation blend trees, and podium tracking | M1 | Survey 1 & ORIGINAL_REQUEST R1 |
| 4 | Native DX12 Viewport Session | C++20 DirectX 12 native viewport rendering, offscreen capture, UUID picking, telemetry JSON, and BMP output | M1 | Survey 1 & ORIGINAL_REQUEST R1 |
| 5 | Legacy DirectX 8/9/10 Fallbacks | Optional fallback compatibility via D3D feature levels (FL 10_0, FL 9_3), D3D11on12, WARP, or translation bridges (DXVK/d8vk/d9vk) | M2 | Survey 1 & ORIGINAL_REQUEST R2 |
| 6 | Engine Graphics Configuration | Selectable renderer configuration via `graphics_pipeline.json`, environment variables, and CLI options | M2 | Survey 1 & ORIGINAL_REQUEST R2 |
| 7 | Local ML Training Pipeline | High-throughput multi-core ML training script with feature-correlated signal and 8-point assertion suite | M3 | Survey 2 & ORIGINAL_REQUEST R3 |
| 8 | Distributed Training Driver | PySpark MLlib and PyTorch/TorchDistributor dual-framework training engine | M3 | Survey 2 & ORIGINAL_REQUEST R3 |
| 9 | Dataproc Serverless Template | Schema-validated GCP Dataproc Serverless batch session template and compute configs | M3 | Survey 2 & ORIGINAL_REQUEST R3 |
| 10 | Dataproc Batch Deployment Script | Deployment automation script with `--validate` schema verification and serverless Terraform generation | M3 | Survey 2 & ORIGINAL_REQUEST R3 |
| 11 | Synced Drive Assets 177 Files | 177 files across 7 categories and 31 subdirectories verified on disk with 0 I/O errors | M4 | Survey 3 & ORIGINAL_REQUEST R4 |
| 12 | ChromaDB Vector Ingestion | Document chunking, vector embedding, and insertion of all 177 files into ChromaDB collections without data loss | M4 | Survey 3 & ORIGINAL_REQUEST R4 |
| 13 | Microservice Vector Retrieval | Backend microservice endpoints (`/api/rag/query`, `/api/omnidrive/search`) querying indexed asset collections | M4 | Survey 3 & ORIGINAL_REQUEST R4 |
| 14 | Chapter Creator & Native Studio Audit | Native GPU and unit tests passing with 0 errors across 130 CTest targets | M5 | Survey 3 & ORIGINAL_REQUEST R5 |
| 15 | FastAPI Master Engine Audit | Central cognitive backend listening on port 8080 responding 200 OK on health endpoints | M5 | Survey 3 & ORIGINAL_REQUEST R5 |
| 16 | ComfyUI RTX 4090 Bridge Audit | Dual-port ComfyUI bridge (primary proxy 8188 and highvram 8189) reporting active RTX 4090 GPU status | M5 | Survey 3 & ORIGINAL_REQUEST R5 |
| 17 | Vite Frontend Build & Dev Audit | Vite development server on port 5173 responding 200 OK and production build compiling with 0 errors | M5 | Survey 3 & ORIGINAL_REQUEST R5 |
| 18 | Opaque-Box E2E Test Suite | Comprehensive multi-tier test suite (Tiers 1-4) validating all platform features independently | E2E | Dual Track E2E |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Viewport & Native Studio Integration | Fix Sheltered Hub viewport session probe target and verification assertions, verify 3 stations, 7 spatial trigger zones, and Adam blend trees in C++20 DX12 runtime | none | COMPLETE |
| M2 | Legacy DirectX Fallback Compatibility | Implement engine graphics configuration (`graphics_pipeline.json`), renderer abstraction for D3D feature level fallbacks (10_0, 9_3), D3D11on12, WARP, and translation bridge options | none | COMPLETE |
| M3 | Distributed Training & Serverless Spark | Upgrade `test_local_ml_pipeline.py` with 8-point assertions and feature correlation, add PyTorch/TorchDistributor dual-framework support, implement `--validate` in `deploy_serverless_spark.py` | none | COMPLETE |
| M4 | Drive Assets ChromaDB Vectorization | Implement ingestion pipeline for all 177 synced cloud files in `synced_drive_assets` into ChromaDB, map to microservice retrieval endpoints (`/api/rag/query`, `/api/omnidrive/search`) | none | COMPLETE |
| M5 | Full System Audit & Subsystem Verification | Execute automated health checks, native C++ tests, FastAPI `/health`, ComfyUI 8188/8189 proxies, and Vite frontend build | M1, M2, M3, M4 | COMPLETE |
| M6 | Final Acceptance: E2E Suite Pass & Hardening | Execute 100% of E2E tests published in `TEST_READY.md` (Tiers 1-4, 275 tests passed), followed by Tier 5 adversarial coverage hardening | M5, TEST_READY.md | COMPLETE |

## Interface Contracts

### Native Viewport ↔ Studio Telemetry Contract
- Protocol: Windows offscreen process execution with file-based IPC.
- Input: `.aibv` binary snapshot packet containing entities, spatial bounds, UUIDs, and camera probe parameters.
- Output: `viewport.json` (keys: `nonbackground_pixels: int > 0`, `debug_errors: int == 0`, `debug_warnings: int`, `selected_uuid: str`, `status: "passed"`), `viewport.bmp` (24-bit RGB bitmap).

### Engine Graphics Backend ↔ Pipeline Configuration Contract
- Schema: `C:\AI-BS\engine\config\graphics_pipeline.json`
- Fields:
  - `primary_backend`: `"DirectX12"`
  - `fallback_chain`: `["DirectX11On12", "DirectX11_FeatureLevel_10_0", "DirectX11_FeatureLevel_9_3", "WARP_Software", "DXVK_Bridge"]`
  - `feature_level_requested`: string (e.g. `"11_0"`, `"12_0"`)
  - `minimum_feature_level`: string (e.g. `"9_3"`, `"10_0"`)
  - `allow_software_warp`: boolean
- Environment Overrides: `AIBS_GRAPHICS_BACKEND`, `AIBS_D3D_FEATURE_LEVEL`.

### Distributed Training ↔ Dataproc Serverless Contract
- Artifact Export: `C:\AI-BS\distributed_training\local_models\rf_model_<timestamp>.pkl` containing serialized model, scaler, and verified metrics (`auc >= 0.70`, `acc >= 0.50`).
- Session Template Schema: Valid against Google Cloud Dataproc v1 `SessionTemplate` REST schema.
- Driver Interface: `python distributed_training_driver.py --framework [mllib|pytorch|both]`.
- Batch Validator Interface: `python deploy_serverless_spark.py --validate` exits 0 on valid configuration.

### Cloud Assets ↔ ChromaDB Microservice Contract
- Collection Names: `ai_bs_synced_drive_assets` or per-category collections (`synced_01_engineering`, ..., `synced_07_legal`).
- Document Metadata Schema:
  - `file_path`: Relative or absolute path in `synced_drive_assets`
  - `category`: Top-level folder name (1 of 7)
  - `subcategory`: Subdirectory name (1 of 31)
  - `file_name`: Basename of file
  - `file_size_bytes`: Integer size
  - `file_extension`: Extension (.md, .txt, .csv, etc.)
- Endpoint Query Interface: `POST http://localhost:8080/api/rag/query` with JSON `{"query": str, "top_k": int, "collection": str}`.

### Subsystem Verification API Contracts
- FastAPI: `GET http://localhost:8080/health` -> HTTP 200, `status: "online"`, `gpu_accelerated: true`.
- ComfyUI Primary Proxy: `GET http://localhost:8188/health` -> HTTP 200, `service: "ComfyUI Primary Service"`.
- ComfyUI Worker: `GET http://localhost:8189/system_stats` -> HTTP 200, `devices[0].name: "NVIDIA GeForce RTX 4090"`.
- Vite Frontend: `GET http://localhost:5173/` -> HTTP 200 (`<!doctype html>`).

## Code Layout
- Native Studio / Viewport: `C:\AI-BS\native_studio\`
- Graphics Engine & Shaders: `C:\AI-BS\engine\`
- Distributed Training: `C:\AI-BS\distributed_training\`
- Synced Cloud Assets: `C:\AI-BS\synced_drive_assets\`
- Documentation & Inventory: `C:\AI-BS\docs\`
- FastAPI Cognitive Backend: `C:\AI-BS\backend\` and `C:\AI-BS\AI_BS_Backend.py`
- ComfyUI RTX 4090 Bridge: `C:\AI-BS\ComfyUI\` and `C:\AI-BS\backend\comfy_primary_proxy_8188.py`
- Vite Frontend Dashboard: `C:\AI-BS\frontend\`
