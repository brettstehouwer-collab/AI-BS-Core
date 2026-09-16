# Implementation Plan: Sovereign Swarm Gauntlet Multi-Port Failover & Connection Hardening

Permanent remediation of the `Error in sovereign reasoning matrix: All connection attempts failed` exception shown in the AI-BS UI chat, establishing resilient dual-port discovery across Ollama Port 11434 (C-Drive Primary) and Port 11435 (E-Drive Secondary).

## User Review Required

> [!IMPORTANT]
> **Root Cause Identified**: 
> 1. In `swarm_gauntlet.py`, `OLLAMA_URL` was hardcoded exclusively to `http://127.0.0.1:11434/api/generate`.
> 2. When Ollama was active on Port 11435 (where all 13 models including `stehouwer_llm`, `stehouwer_dolphin`, `stehouwer_qwen`, and `nemotron-3.5-lightning` are located) while Port 11434 was inactive, the individual swarm passes caught the connection failure and fell back to `"Model convergence passed with baseline consistency."`.
> 3. When reaching the final multi-model backpropagation synthesis stream, line 124 executed an unguarded `client.stream("POST", cls.OLLAMA_URL, json=payload)` against Port 11434 without failover to Port 11435. This caused `httpx.ConnectError: All connection attempts failed` to bubble up to `hybrid_reasoning_engine.py` and display on the chat interface.

> [!NOTE]
> All changes use 100% local resources on your RTX 4090 and AMD Ryzen 9 9950X, requiring zero external cloud dependencies or paid APIs.

---

## Proposed Changes

### Core Sovereign Reasoning Engine

#### [MODIFY] [swarm_gauntlet.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/swarm_gauntlet.py)
- **Dynamic Multi-Port Detection**: Replace static `OLLAMA_URL` with dynamic candidate list `[11434, 11435]`.
- **Active Endpoint Resolver (`get_active_endpoint`)**: Probe `127.0.0.1:11434` and `127.0.0.1:11435` with sub-second health checks; automatically fallback to the active port.
- **Model Fleet Aggregator**: Query `api/tags` from the active endpoint (or aggregate both if both are running), populating `installed_models` dynamically rather than failing to the 2-model static fallback.
- **Resilient Single-Model Calling**: In `call_single_model`, attempt primary port and automatically retry on secondary port if connection fails.
- **Failover-Protected Final Synthesis**: Wrap `client.stream(...)` in a dual-port failover loop. If the primary port drops mid-flight or is unreachable, failover to the secondary port or trigger self-healing auto-start, guaranteeing uninterrupted streaming.

```python
# Conceptual Architecture in swarm_gauntlet.py:
OLLAMA_PORTS = [11434, 11435]

@classmethod
async def get_active_base_url(cls, client: httpx.AsyncClient) -> str:
    for port in cls.OLLAMA_PORTS:
        try:
            r = await client.get(f"http://127.0.0.1:{port}/api/tags", timeout=1.0)
            if r.status_code == 200:
                return f"http://127.0.0.1:{port}"
        except Exception:
            continue
    # If neither is responding, trigger self-healing
    from .dispatcher import ensure_ollama_running
    ensure_ollama_running()
    await asyncio.sleep(2.0)
    return "http://127.0.0.1:11434"
```

#### [MODIFY] [dispatcher.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/dispatcher.py)
- Update `ensure_ollama_running()` to inspect **both** Port 11434 and Port 11435.
- If neither port is active, launch Ollama with proper environment variables (`OLLAMA_HOST=0.0.0.0:11434`, `OLLAMA_MODELS=C:\AI-BS\.ollama\models`).
- Ensure `ensure_ollama_running` is callable from `swarm_gauntlet.py`.

---

### Startup & Orchestration

#### [MODIFY] [Launch_AI_BS.bat](file:///C:/AI-BS/Launch_AI_BS.bat)
- Enhance the startup sequence for Ollama:
  - Verify Port 11434 binding with a 2-second stabilization window before triggering the secondary Port 11435 process.
  - Log status explicitly during boot.

---

### Frontend UI & Version Parity

#### [MODIFY] Multiple Frontend Components & Ledgers
- Increment system version from `v5.233.0` to `v5.234.0` across:
  - `frontend/package.json`
  - `frontend/src/App.jsx`
  - `frontend/src/components/Sidebar.jsx`
  - `frontend/src/components/TopNavbar.jsx`
  - `frontend/src/components/ChatTab.jsx`
- Rebuild production bundle: `npm run build`
- Deploy to Firebase Hosting: `firebase deploy --only hosting --non-interactive`
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.

---

## Verification Plan

### Automated Tests
1. **Port Check**: Verify TCP listeners on 11434 and 11435:
   ```powershell
   Get-NetTCPConnection -LocalPort 11434, 11435 -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, OwningProcess, State
   ```
2. **Model Availability**: Verify tags on both ports:
   ```powershell
   (Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags').models.name
   (Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/tags').models.name
   ```
3. **Live Swarm Gauntlet Stream Execution**:
   - Send test payload to `POST http://127.0.0.1:8000/api/chat/stream` or `/api/v1/hybrid-chat/stream` with prompt: `run deep gauntlet test connectivity and multi-model consensus`.
   - Verify that:
     - Thought blocks stream in real-time.
     - Swarm passes load and run against actual models.
     - Final synthesis streams tokens smoothly without the `All connection attempts failed` exception.

### Manual Verification
- Open BS-CHAT in the web dashboard or local browser (`http://localhost:5173` or `https://ai-bs-dashboard.web.app`).
- Submit a query with `run deep gauntlet ...` and observe the live streaming execution cards and completion snippet.
