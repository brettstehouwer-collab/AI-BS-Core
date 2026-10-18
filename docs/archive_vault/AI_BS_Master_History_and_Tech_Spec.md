# 🌌 AI-BS Master Technical Specification, Architectural Manual & Creation History

**System Name:** Autonomous Intelligence & Build System (**AI-BS**)  
**Creator & Architect:** Brett Adam Stehouwer  
**Primary Intelligence Engine:** `stehouwer_llm` (Local Ollama Llama 3.1 8k / RTX 4090 GPU Accelerated)  
**Host Hardware Infrastructure:** AMD Ryzen 9 9950X / 64GB DDR5 RAM / NVIDIA GeForce RTX 4090 24GB VRAM  
**Production Endpoints:**  
- Web Dashboard: https://ai-bs-dashboard.web.app (Firebase Hosting)  
- Local Backend API Gateway: `http://localhost:8000` (FastAPI / Uvicorn)  
- ComfyUI API Loopback Bridge: `http://127.0.0.1:8188`  

---

## 📖 1. Executive Summary & System Identity

The Autonomous Intelligence & Build System (**AI-BS**) is a sovereign, self-contained, multi-agent AI engineering and creation ecosystem architected by **Brett Adam Stehouwer**. Operating 100% free of paid third-party API dependencies, AI-BS integrates:
- High-throughput local neural LLM inference (`stehouwer_llm`).
- Automated image and video generation workflows via a custom ComfyUI Loopback Bridge.
- Asynchronous background daemons for heuristic log parsing, continuous knowledge harvesting, memory offloading, and self-healing.
- An interactive web application featuring Creation Suite, Writing Studio, Video Studio, Visual Scripting, Monaco Code IDE, and Real-time Telemetry.

---

## 🏛️ 2. System Architecture & Component Specification

### A. Central Cognitive Engine (`c:\AI-BS\backend\AI_BS_Backend.py`)
- **FastAPI / Uvicorn Server:** Runs on port 8000. Serves as the central API gateway for client connections, prompt routing, and tool execution.
- **Memory Manager (`bullshit_memory.py`):** Operates SSD offloading with a 2048MB RAM threshold and background garbage collection.
- **Monolithic Background Daemons:**
  - **Heuristics Daemon:** Continuously monitors execution logs to capture and embed pipeline failure heuristics into the Vector Vault.
  - **Sponge Daemon:** Autonomous web/repository scraper that forage for domain knowledge and updates vector embeddings.
  - **Trainer Daemon:** Asynchronous background poller leveraging Watchdog event loops.
  - **Sensory & Medic Daemons:** Monitors system telemetry, GPU VRAM, CPU utilization, and executes emergency process restarts if health checks fail.

### B. ComfyUI API Loopback Bridge (`c:\AI-BS\backend\comfy_bridge.py`)
- **Asynchronous Execution Engine:** Built with `aiohttp.ClientSession` to dispatch workflow prompt DAGs without blocking the main event loop.
- **Non-Blocking Queueing & Polling:**
  - `queue_comfyui_workflow(prompt)`: Generates UUID `client_id` and queues prompts to `127.0.0.1:8188/prompt`.
  - `await_generation_result(prompt_id)`: Asynchronously checks `/history/{prompt_id}` until completion.
  - `extract_output_media(history)`: Extracts media objects from `images`, `videos`, and `gifs` (`VHS_VideoCombine`) outputs and builds absolute `/view` URLs.

### C. Creation Suite & Web Application (`c:\AI-BS\frontend`)
- **Framework & Libraries:** React 18, Vite 5, Vanilla CSS design tokens, Monaco Editor, `@xyflow/react`.
- **Key Modules:**
  - **Command Center:** Live system status, model selection dropdown, background daemon controls.
  - **Writing Studio:** Document Editor with cryptographic digital canvas signature modal and PDF export.
  - **Screenwriting Studio:** Fountain/FDX screenplay parser, scene beat analyzer, and sprint tracker.
  - **Video Studio & Visual Scripting:** Interactive node-based logic canvas (`VisualScriptingTab.jsx`).
  - **Interactive Chat Interface:** Custom Markdown renderer with native HTML5 `<video>` auto-play support for rendered ComfyUI `.mp4` and `.webm` media.

---

## 📜 3. Verified Historical Documents & Tech Spec Catalog

Below is the compiled inventory of historical technical reports, specifications, and handover logs discovered across the AI-BS storage drives:

1. **[AI-BS Technical Architecture Report (Original)](file:///C:/AI-BS/_archive_v1/AI-BS_Documents_Archive/AI-BS%20Technical%20Architecture%20Report%20%E2%80%94%20Brett%20Adam%20Stehouwer.md)**  
   *Comprehensive technical blueprint outlining the initial sovereign compute infrastructure, model quantization, and agent swarms.*
2. **[AI-BS Technical Architecture Report v1.2](file:///C:/AI-BS/_archive_v1/AI-BS_Documents_Archive/AI-BS_Technical_Architecture_Report_v1.2.md)**  
   *Updated system specification covering Dual-CCD topology and memory threshold offloading.*
3. **[AI-BS Master Archive & Architecture Note](file:///C:/AI-BS/_archive_v1/AI-BS_Documents_Archive/AI-BS_Master_Archive_&_Architectura.MD)**  
   *Archival index detailing project directory structures, sandbox isolation, and database schemas.*
4. **[AI-BS Session Handover Summary](file:///C:/AI-BS/AI_BS_Handover.md)**  
   *Operational status log summarizing system hardware, active endpoints, and ongoing refinement tasks.*
5. **[Stehouwer LLM Upgrade Study Guide](file:///C:/AI-BS/Stehouwer_LLM_Upgrade_Study_Guide.md)**  
   *Fine-tuning guide detailing Ollama Modelfile parameters, tool registration, and prompt formatting rules for `stehouwer_llm`.*
6. **[Full Chat Transcript (July 22, 2026)](file:///C:/AI-BS/Full_Chat_Transcript_2026-07-22.md)**  
   *Complete transcript archive documenting full-stack feature development and debugging sessions.*
7. **[Session History Archive JSON](file:///C:/AI-BS/session_history_archive.json)**  
   *Raw JSON database containing historical user prompts, tool calls, and model outputs.*

---

## 🛠️ 4. Tool Registry & Declarations (`tool_registry.py`)

AI-BS provides native tool execution capabilities registered directly in `stehouwer_llm`:

| Tool Name | Purpose / Function |
| :--- | :--- |
| `read_sandbox_file` | Inspects file contents inside the isolated backend sandbox environment. |
| `write_sandbox_file` | Safely creates or edits code/config files inside the sandbox. |
| `query_sqlite` | Performs schema inspection and executes custom SQL queries on local SQLite databases. |
| `generate_comfy_image` | Dispatches image/video generation requests to local ComfyUI via `comfy_bridge`. |
| `create_comfy_workflow` | Generates, saves, and dispatches custom JSON workflow graphs to ComfyUI. |

---

*Document compiled and master-indexed for Brett Adam Stehouwer.*
