# OpenCode AI-BS Project Context & System Guide

Welcome to **AI-BS** in OpenCode. This document provides local LLM orchestrators and coding agents with complete architectural awareness and working rules.

---

## 1. System Ecosystem Overview

- **Frontend**: Vite + React SPA (`C:\AI-BS\frontend\`)
  - Running on `http://localhost:5173/`
  - Unified Crypto Tab: `http://localhost:5173/?tab=unified_crypto&subtab=livestream`
  - Real-time components: [CryptoLiveStreamTab.jsx](file:///C:/AI-BS/frontend/src/components/CryptoLiveStreamTab.jsx), [CodingPreparationPanel.jsx](file:///C:/AI-BS/frontend/src/components/CodingPreparationPanel.jsx)

- **Main Backend**: FastAPI (`C:\AI-BS\backend\AI_BS_Backend.py`)
  - Running on `http://127.0.0.1:8000`
  - Serves hybrid reasoning, sovereign chat, matrix telemetry, and sandbox executors.

- **Live Crypto Scalp Engine**: Independent Service (`C:\AI-BS\scratch\live_cro_usdt_trader.py`)
  - Running on `http://127.0.0.1:8007` (Endpoint: `/api/live-telemetry`)
  - Live trading `CRO/USDT` limit-bracket scalp cycle on Crypto.com Exchange.
  - DPAPI credential protection: Loads API key pair in memory only.

---

## 2. Critical Safety Directives & Working Rules

1. **Codex Preflight Pin Protection**:
   - Codex has active SHA-256 preflight checks across `888` source files in `backend/` and `backups/`.
   - **DO NOT** edit backend files (`C:\AI-BS\backend\...`) or backup records (`C:\AI-BS\backups\...`) directly without verifying hash pins.
   - For new functionality, use adapter layers, `scratch/`, or dedicated microservice endpoints.

2. **Crypto & Financial Safety**:
   - Never log API secrets or private keys in plaintext.
   - Respect Crypto.com Exchange rate limits: Keep REST polling intervals at $\ge 2.0$ seconds to prevent HTTP 429 IP bans.
   - Bound credential preparation registry is located at: `C:\AI-BS\saved_data\crypto_credential_preparation_registry`.

3. **Multi-Agent Protocol**:
   - Consult [AGENTS.md](file:///C:/AI-BS/AGENTS.md) and [PROJECT.md](file:///C:/AI-BS/PROJECT.md) for handoff notes and source release versions.

---

## 3. Active Agent Roles

| Role | Model | Purpose |
| :--- | :--- | :--- |
| **`build`** | `ollama/qwen2.5-coder:latest` | Primary code editor and implementation agent. |
| **`plan`** | `ollama/llama3.3:70b` | High-level system architect and workflow designer. |
| **`general`** | `ollama/qwen2.5-coder:latest` | Stehouwer authentic core voice & assistant. |
| **`explore`** | `ollama/llama3.1-tools:latest` | Fast repository grep, inspection, and context briefing. |

