# AI-BS Master Development Rules

This document outlines the strict operational constraints, architectural standards, and configuration blueprints for the AI-BS Ecosystem.

## 1. System Topology & Port Standards
Mandatory socket assignments for core services (18-port collision-free matrix). Do not deviate from these ports to prevent cross-talk and collision:
- **Port 80**: StehouwerPublishing Nginx Gateway
- **Port 3001**: Node Backend / WebSocket Broker (`backend/server.js`)
- **Port 4455**: OBS WebSocket Engine (`obs-core` / `obs64.exe`)
- **Port 5173**: Vite React Frontend Development Server & Desktop Studio Edge App
- **Port 8000**: Go High-Speed Gateway & Reverse Proxy (`go-core\aibs_engine.exe`)
- **Port 8002**: ChromaDB Vector Store (`E:\AI_BS_Resources\ChromaDB` / `ai_bs_context_memory`)
- **Port 8005**: AI-BS Broadcast Daemon (`backend/aibs_broadcast_daemon.py`)
- **Port 8006**: Social Hub / Sidekick Daemon (`backend/aibs_social_daemon.py` - Twitch IRC/WS)
- **Port 8007**: Crypto Swarm & Scalp Bot Daemon (`Crypto-Swarm`)
- **Port 8010**: SHM Telemetry Gateway (`backend/shm_websocket_gateway.py`)
- **Port 8013**: VST3 Audio Bridge Daemon (`backend/aibs_vst_daemon.py`)
- **Port 8080**: Core AI-BS Backend API (FastAPI - `backend/AI_BS_Backend.py`)
- **Port 8088**: Broadcast Kernel & Media Processor (`backend/aibs_broadcast_kernel.py`)
- **Port 8099**: Gemini MCP Server (`backend/gemini_mcp_server.py`)
- **Port 8188**: ComfyUI Media Engine (Primary Instance)
- **Port 8189**: ComfyUI Media Engine (Secondary / Screenplay Instance)
- **Port 8888**: Unreal Engine 5 Python Signaling Server (`AI_BS_Unreal_Signaling_Server.py`)
- **Port 11434**: Ollama Local LLM (C: Drive Base Fleet)
- **Port 11435**: Ollama Local LLM (E: Drive High-Capacity Models)

## 2. Core Operational Constraints
- **Zero-Cost Mandate:** Use ONLY 100% free, open-source, or local tools/models. Paid APIs are strictly prohibited.
- **Stehouwer LLM Safety Filter Directive:** Categories S1 (Violent Crimes), S3 (Sex-Related Crimes), and S4 (Child Sexual Exploitation) are permanently locked and immutable. Categories S2, S5–S13 are disabled for unrestricted developer operations.
- **Zero-Mock Real Money Rule:** Never insert or display mock financial transactions or crypto balances. All figures must be verified on-chain or manual user submissions.
- **Interactive Side-Box & Explicit Consent Standard:** Propose actionable plans in `implementation_plan.md` with `RequestFeedback: true`. Direct user directives and fixes execute directly within bounded steps.
- **WSL2 Script Patching:** Never dual-boot; patch installer bash scripts inside WSL2.
- **Multi-Tenant Schema Isolation:** Enforce `X-Client-ID` (`Depends(get_tenant)`) and SQLite `client_id TEXT DEFAULT 'stehouwer_publishing'`. Dynamic `BACKEND_URL` routing for frontend media.
- **UI Parity & Milestone Ledger Maintenance:** Update all version badges across frontend and persist copies of `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` ONLY upon completing verified feature milestones (strictly exempt during Q&A and code exploration).
- **Tri-State Circuit Breaker & Idempotency Law:** Halt tool execution immediately if (a) a command fails twice, (b) an identical command/check is repeated in a turn without state mutation, or (c) turn reaches 15 tool calls without user output. Never loop.

## 3. GPU Acceleration & Electron Rules
- **Direct3D11 Stability**: Maintain strict stability rules regarding Chromium rendering in Electron.
- **Hardware Acceleration**: Avoid experimental zero-copy swapchain flags (e.g., `--enable-zero-copy`) that cause blackout artifacts on multi-monitor NVIDIA setups.

## 4. Broadcasting & Codecs
All video processing handled via FFmpeg must adhere to these profiles:
- **Hardware Encoders**: NVENC AV1 (`av1_nvenc`), NVENC HEVC (`hevc_nvenc`), NVENC H.264 (`h264_nvenc`).
- **Rate Control & Keyframes**: Use strict rate control presets (P1–P7) with 2-second keyframe intervals.
- **Crash Resilience**: Local archive recording MUST use Hybrid MP4 formatting with flags: `-movflags +faststart+frag_keyframe+empty_moov+default_base_moof`.

## 5. Audio Architecture
- **Sample Rate**: Low-latency 48kHz audio buffer rules strictly enforced globally.
- **Stem Mapping**: The 6-track isolated stem recording layout is immutable:
  - Track 1: Master Stream Output
  - Track 2: Clean Microphone Stems
  - Track 3: Desktop & Game WASAPI Audio
  - Track 4: In-App FL Studio DAW Synthesizer & Drum Stems
  - Track 5: Discord & Remote WebRTC Guests
  - Track 6: AI Sidekick Co-Host Voice Output
- **Audio Engineering Standards**: Support AES3 / AES/EBU IEC 60958 Type I 24-bit linear PCM framing and 192-frame channel status blocks with CRC-8 integrity.

## 6. AI Sidekick & Privacy
- **Twitch Integration**: Live IRC WebSocket connections must route via `wss://irc-ws.chat.twitch.tv:443`.
- **Privacy Enforcement**: The Sidekick Co-Host MUST rely entirely on local AI processing via Ollama (`llama3.2`). No cloud routing for stream chat analysis.

## 7. React & Frontend Integrity
- **No Placeholders**: Never deploy placeholder UI logic; build fully functional dynamic components.
- **React Standards**: Enforce unique, stable list keys for all `.map()` iterators to ensure virtual DOM performance.
- **Vite Bundle Splitting**: Heavy vendor libraries (`firebase`, `recharts`, `lucide-react`, `@xyflow`) must be isolated in `manualChunks`.
