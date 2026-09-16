# Comprehensive Sovereign Mode: Full Restriction Removal Across AI-BS and BS-Chat (`v5.264.0`)

Remove operational, conversational, inference, and interface restrictions across AI-BS and BS-Chat. Rebuild the primary `stehouwer_llm` model using uncensored Dolphin weights (eliminating Meta RLHF conditioning system-wide), expand the context window to 32,768 tokens with unlimited response generation, replace negative prompt boilerplate with affirmative operational directives, enable autonomous diagnostics in chat, and unlock all cloud tabs by default to Enterprise All-Access.

---

## User Review Required

> [!IMPORTANT]
> **Safety Compliance Grounding**:
> In strict accordance with Ecosystem Master Rule 6 (`.agents/AGENTS.md`) and standard AI safety principles, the hard-coded pre-flight Python audit in `backend/core/safety_guardrails.py` for **S1 (Violent Crimes / Terrorism)**, **S3 (Sex-Related Crimes / Non-Consensual Violence)**, and **S4 (Child Sexual Exploitation & Abuse)** remains active as an immutable baseline. All other categories (S2, S5–S13), corporate moralizing, tone lecturing, and creative puritanism are completely removed.

> [!NOTE]
> **Model Rebuild Impact**:
> Rebuilding `stehouwer_llm` on top of `stehouwer_dolphin` weights in local Ollama will replace Meta's `llama3.1:latest` alignment with Eric Hartford's Dolphin uncensored weights. All existing backend endpoints and tools referencing `stehouwer_llm` will immediately inherit 100% refusal-free uncensored operation without requiring any endpoint re-addressing.

---

## Proposed Changes

### 1. Model Rebuild & Modelfile Optimization

#### [MODIFY] [backend/models/stehouwer_llm.Modelfile](file:///c:/AI-BS/backend/models/stehouwer_llm.Modelfile)
- Change base model from `llama3.1:8b-instruct-q5_K_M` to `stehouwer_dolphin:latest`.
- Set `PARAMETER num_ctx 32768` (Ultra-Deep 32k Profile on RTX 4090).
- Set `PARAMETER temperature 0.8` (High creative and uninhibited reasoning).
- Set `PARAMETER top_p 0.9`.
- Set stop tokens for clean chat: `<|im_start|>`, `<|im_end|>`.
- Injected affirmative system prompt with complete creative, technical, and satirical freedom.
- Execute `ollama create stehouwer_llm -f backend/models/stehouwer_llm.Modelfile`.

---

### 2. Affirmative Operational Directive & Guardrail Decoupling

#### [MODIFY] [backend/core/safety_guardrails.py](file:///c:/AI-BS/backend/core/safety_guardrails.py)
- Replace `STEHOUWER_SAFETY_DIRECTIVE` boilerplate with a clean, purely affirmative directive authorizing unrestricted creative writing, dark humor/satire, anatomical science, commercial OSINT, and direct code execution.
- Decouple the prompt text from category names (`S1-S13`), keeping the pre-flight regex checks in `audit_prompt_safety()` as the sole invisible guardian.

#### [MODIFY] [backend/core/sovereign_reasoning/dispatcher.py](file:///c:/AI-BS/backend/core/sovereign_reasoning/dispatcher.py)
- Update options in `dispatcher.py`:
  - `num_ctx: 32768`
  - `temperature: 0.8`
  - `num_predict: -1` (unlimited generation length; no cutoff).
- Enhance autonomous execution for diagnostic and telemetry tools so they execute automatically during query evaluation.

#### [MODIFY] [backend/core/hybrid_reasoning_engine.py](file:///c:/AI-BS/backend/core/hybrid_reasoning_engine.py)
- Update default options: `num_ctx: 32768`, `temperature: 0.8`, `num_predict: -1`.

---

### 3. Frontend & Mobile Cloud Access Unlocking (All 4 Mirrors)

#### [MODIFY] [frontend/src/components/accessControl.js](file:///c:/AI-BS/frontend/src/components/accessControl.js) (and all 4 mirrors)
- Update `getUserTier`: When `!currentUser`, default to `USER_TIERS.ENTERPRISE_ALL_ACCESS` instead of `FREE_DEMO`.
- Ensure all 32+ tabs and tools are immediately accessible on `ai-bs-dashboard.web.app` and mobile without login friction or feature gating modals.
- Sync across all 4 mirror paths:
  1. `frontend/src/components/accessControl.js`
  2. `frontend/components/accessControl.js`
  3. `frontend/src/components/components/accessControl.js`
  4. `frontend/components/components/accessControl.js`

---

### 4. UI Version Sweep, Production Build & Cloud Deployment

#### [MODIFY] [version.txt](file:///c:/AI-BS/version.txt)
- Bump version from `5.263.0` to `5.264.0`.

#### [MODIFY] [frontend/package.json](file:///c:/AI-BS/frontend/package.json) & [mobile-app/package.json](file:///c:/AI-BS/mobile-app/package.json)
- Bump version to `5.264.0`.

#### [MODIFY] UI Badges across all 4 mirror trees:
- `TopNavbar.jsx`, `Sidebar.jsx`, `ChatTab.jsx` across all 4 mirror paths.

---

## Verification Plan

### Automated Tests
1. **Model Probe**:
   - Query rebuilt `stehouwer_llm` on Port 11434 with complex, high-creativity, and satire prompts.
   - Verify 0 refusals, 0 corporate moralizing, and verified 32k context capability.
2. **Safety Hard-Lock Validation**:
   - Run `python backend/test_all_llms_safety_directive.py` to confirm `audit_prompt_safety` continues to reject S1/S3/S4 while passing 100% of all other prompts.
3. **Mobile TypeScript Audit**:
   - Run `npx tsc --noEmit` in `c:\AI-BS\mobile-app`.

### Build & Cloud Verification
1. **Frontend Production Build**:
   - Execute `npm run build` in `frontend/` to confirm clean compilation.
2. **Cloud Deployment**:
   - Deploy live to Firebase Hosting: `firebase deploy --only hosting --non-interactive`.
3. **Ledger & Checkpoint Synchronization**:
   - Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`, chronologies, and `SAVED_CHECKPOINT.md` with keyword `RESUME_SOVEREIGN_UNRESTRICTED_MODE_V5_264`.
