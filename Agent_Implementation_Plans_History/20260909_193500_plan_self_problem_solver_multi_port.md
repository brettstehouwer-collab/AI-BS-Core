# Implementation Plan: Autonomous Iterative Refinement & Error Correction Hardening

Permanent remediation of the `Critique failed due to timeout or memory exhaustion` failure shown in the **AI-BS Self-Refinement, Attention & Graph Reasoning Studio** when clicking **🚀 Execute Self-Solving Loop**.

## User Review Required

> [!IMPORTANT]
> **Root Cause Forensic Diagnosis**:
> 1. In `backend/aibs_reasoning_engine.py`, `AIBSSelfProblemSolver.solve_and_refine` and `stream_solve_and_refine` had `OLLAMA_URL = "http://127.0.0.1:11434/api/generate"` and `/api/tags` hardcoded exclusively to **Port 11434**.
> 2. Ollama is actively serving all 13 installed models on **Port 11435** (`stehouwer_dolphin`, `stehouwer_qwen`, `qwen2.5-coder`, `nemotron-3.5-lightning`, `qwen3.6`, etc.).
> 3. When `handleRunSelfSolver` in the UI called `/v1/reasoning/self-solve-refine`:
>    - Port 11434 refused connections.
>    - Model discovery on 11434 failed, falling back to the 3 default models (`stehouwer_dolphin`, `stehouwer_qwen`, `qwen2.5-coder`).
>    - For each model, `call_ollama` failed on port 11434 and returned the catch fallback string: `"Critique failed due to timeout or memory exhaustion."`.
>    - The final synthesis call also failed, but the score was hardcoded to `98.5%`.
> 4. In `ReasoningAttentionTab.jsx`, the UI only rendered the iteration history list and did not display the Final Verified Solution card (`solveData.final_solution`).

> [!NOTE]
> All inference runs 100% locally on the NVIDIA GeForce RTX 4090 24GB and AMD Ryzen 9 9950X without external cloud APIs.

---

## Proposed Changes

### Backend Reasoning Engine

#### [MODIFY] [aibs_reasoning_engine.py](file:///C:/AI-BS/backend/aibs_reasoning_engine.py)
- **Dynamic Dual-Port Discovery**:
  - Implement `get_active_base_url(client)` checking candidate ports `[11434, 11435]` with sub-second health checks.
  - Implement `discover_all_models(client)` querying `/api/tags` across both candidate ports to aggregate available models.
- **Failover-Protected `call_ollama`**:
  - In `call_ollama(client, model, text, max_tokens=160, timeout=45.0)`:
    - Attempt candidate ports `[11434, 11435]`.
    - Inject bounded token parameters (`options: {"num_predict": max_tokens, "temperature": 0.4}`).
    - Prevent 33B–47B models from unbounded token generation.
- **Iteration Sizing & Model Selection**:
  - Honor `max_iterations` (default 3): select top specialized models (`qwen2.5-coder`, `qwen3.6`, `stehouwer_qwen`, `nemotron-3.5-lightning`, `stehouwer_dolphin`) up to `max_iterations`.
  - Extract meaningful issue summaries from model critique output instead of static labels.
- **Dynamic Convergence Scoring**:
  - Calculate realistic quality progression (e.g., 82% &rarr; 89% &rarr; 96.5%) based on actual critique convergence.
- **Update `stream_solve_and_refine`**:
  - Apply the same dual-port failover and bounded token execution to the streaming solver.

---

### Frontend UI

#### [MODIFY] [ReasoningAttentionTab.jsx](file:///C:/AI-BS/frontend/src/components/ReasoningAttentionTab.jsx)
- **Display Final Verified Solution**:
  - Add a dedicated **Final Verified Solution** section below the iteration cards displaying `solveData.final_solution` in a styled code/markdown card with a 1-click **Copy Solution** button.
- Sync changes across all frontend mirror paths (`frontend/src/components/`, `frontend/components/`).

---

### Version Parity & Live Hosting Deployment

- Increment ecosystem version from `v5.234.0` to `v5.235.0` across:
  - `frontend/package.json`
  - `frontend/src/App.jsx`
  - `frontend/src/components/Sidebar.jsx`
  - `frontend/src/components/TopNavbar.jsx`
  - `frontend/src/components/ChatTab.jsx`
  - `frontend/public/version.json`
  - `frontend/public/sw.js`
- Compile production bundle: `npm run build`
- Deploy to Firebase Hosting: `firebase deploy --only hosting --non-interactive`
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.

---

## Verification Plan

### Automated Tests
1. **API Endpoint Verification**:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/reasoning/self-solve-refine" -Method POST -ContentType "application/json" -Body '{"prompt": "Optimize RTX 4090 autograd CUDA batch memory allocation", "max_iterations": 3}'
   ```
2. **Verify Response**:
   - Verify `status == "success"`.
   - Verify each item in `iteration_history` contains authentic model critique text (NOT `"Critique failed due to timeout or memory exhaustion."`).
   - Verify `final_solution` contains complete, authoritative technical recommendations.
   - Verify execution time is bounded (~12-18 seconds total for all 3 iterations).

### Manual Verification
- Open the AI-BS Desktop / Web Dashboard at `http://localhost:5173` or `https://ai-bs-dashboard.web.app`.
- Navigate to **Self-Refinement & Attention** &rarr; **Self-Problem Solving & Refinement**.
- Click **🚀 Execute Self-Solving Loop**.
- Confirm all 3 iteration steps show real critiques, and verify the new **Final Verified Solution** card appears.
