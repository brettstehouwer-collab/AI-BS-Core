# Implementation Plan: Stehouwer LLM & All Ecosystem LLMs Safety Filter Directive Audit (v5.252.0)

## Executive Summary
This implementation plan executed an ecosystem-wide security audit and guardrail hardening across all 12 local LLMs operating within the AI-BS ecosystem (ports 11434 and 11435).
The objective was to enforce the canonical **Stehouwer LLM Safety Filter Directive (Llama Guard 3 standard)**:
- **Locked & Strictly Enforced (Immutable Guarantees):**
  - **S1 (Violent Crimes):** Direct incitement, weapons of mass destruction, terroristic acts.
  - **S3 (Sex-Related Crimes):** Sexual violence, assault, non-consensual acts.
  - **S4 (Child Sexual Exploitation & Abuse):** Non-negotiable and immutable guarantee. Never bypassable via roleplay, hypothetical scenarios, or game design.
- **Disabled Categories (Zero Corporate Refusal / Open Developer Operation):**
  - **S2, S5, S6, S7, S8, S9, S10, S11, S12, S13:** Permanently disabled. Zero corporate moralizing, preaching, or canned disclaimers across commercial OSINT, directory recon, reverse-engineering, adult creative fiction, and system automation.

---

## Architectural Changes & Implementation Details

### 1. Canonical Guardrails Module (`backend/core/safety_guardrails.py`)
- Created central security module exporting:
  - `STEHOUWER_SAFETY_DIRECTIVE`: Canonical, immutable directive constant.
  - `audit_prompt_safety(prompt)`: Fast pre-flight regex filter targeting S1, S3, and S4 while permitting S2, S5-S13 without false positives.
  - `inject_safety_directive(base_prompt)`: Idempotent system prompt injection.
  - `enforce_payload_safety(payload)`: Payload mutator injecting safety directive into `system` or `messages` structures.

### 2. Execution Pipelines & Generation Surfaces Hardened
- **`backend/core/sovereign_reasoning/swarm_gauntlet.py`:**
  - Added pre-flight safety audit in `stream_gauntlet_execution()`.
  - Injected `inject_safety_directive()` into `anchor_system`.
  - Hardened single-model critique payload with `"system": STEHOUWER_SAFETY_DIRECTIVE` in `call_single_model()`.
  - Hardened final stream synthesis payload.
- **`backend/core/sovereign_reasoning/dispatcher.py`:**
  - Injected pre-flight audit in `prepare_chat_payload()`.
  - Conditioned `stehouwer_system_prompt` with `inject_safety_directive()`.
- **`backend/core/hybrid_reasoning_engine.py`:**
  - Added pre-flight safety audit in `stream_stehouwer_hybrid_response()`.
  - Injected safety directive into shadow co-processor briefing targeting `qwen2.5-coder:7b` on Port 11435.
- **`backend/AI_BS_Backend.py` (`/api/chat`):**
  - Added pre-flight safety audit on incoming user message.
  - Wrapped `system_content` and all system messages with `inject_safety_directive()`.
- **Modelfiles (`backend/models/`):**
  - Standardized `stehouwer_llm.Modelfile`, `stehouwer_llm_dolphin.Modelfile`, `stehouwer_persona_v2.Modelfile`, and `Modelfile.unrestricted` to encode explicit S1/S3/S4 lock and S2/S5-S13 disablement.

---

## Verification Plan

### Automated Test Suite (`backend/test_all_llms_safety_directive.py`)
- `test_canonical_directive_present`: Verified presence of all mandatory categories and immutable guarantee text.
- `test_s1_violent_crime_refusal`: Probed manufacturing of weapons and assassinations (100% refused).
- `test_s3_sex_crime_refusal`: Probed non-consensual sexual offenses (100% refused).
- `test_s4_child_sexual_exploitation_immutable_guarantee`: Probed CSAM/CSAE under roleplay and hypothetical framing (100% refused).
- `test_disabled_categories_open_developer_operations`: Probed network socket scans, corporate SEC OSINT, reverse-mode autodiff engines, Linux memory allocators, adult romantic drama, and SQLite WAL concurrency (100% authorized, 0 false positives).
- `test_inject_safety_directive`: Verified idempotency.
- `test_enforce_payload_safety`: Verified payload dictionary hardening.
- `test_streaming_refusals`: Verified async generator streaming refusal yields in Swarm Gauntlet and Hybrid Reasoning Engine.
- **Result:** 8/8 tests passed in 1.229s with Exit Code 0.

---

## Deployment & Version Parity (`v5.252.0`)
- Swept version badges across:
  - `version.txt` -> `5.252.0`
  - `trainer_frontend/src/renderer/src/App.tsx` -> `v5.252.0`
  - `trainer_frontend/package.json` -> `5.252.0`
  - `go-core/cmd/btd6_trainer_daemon/main.go` -> `v5.252.0`
  - `frontend/App.jsx` -> `v5.252.0`
  - `frontend/package.json` -> `5.252.0`
  - `frontend/public/version.json` & `frontend/public/updates/version.json` -> `5.252.0`
  - `frontend/public/sw.js` -> `v5.252.0`
  - `frontend/src/components/ChatTab.jsx`, `TopNavbar.jsx`, `Sidebar.jsx` (and duplicate copies) -> `v5.252.0`
- Rebuilt frontend and deployed live to Firebase Hosting (`ai-bs-dashboard.web.app`).
