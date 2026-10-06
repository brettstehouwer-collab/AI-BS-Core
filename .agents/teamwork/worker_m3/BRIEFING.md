# BRIEFING — 2026-10-06T05:20:00Z

## Mission
Implement MoE 7th Domain (SpecialistDomain.BIOINFORMATICS & SPECIALIST_MATRIX), stehouwer_genomics.Modelfile, and autonomous genomic_discovery_sprint Swarm preset.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: C:\AI-BS\.agents\teamwork\worker_m3
- Original parent: da083096-02cf-43b4-b9c6-1900461cac1b
- Milestone: M3 (MoE 7th Domain & Autonomous Genomic Swarm Pipeline)

## 🔒 Key Constraints
- Exclusive file ownership:
  * backend/core/sovereign_reasoning/moe_specialist_router.py
  * backend/models/stehouwer_genomics.Modelfile
  * backend/core/sovereign_reasoning/swarm_coordinator.py
- DO NOT modify files outside ownership without explicit reason.
- DO NOT CHEAT: All implementations genuine, maintain real state, real behavior.
- Ensure all tests pass: `pytest tests/test_moe_and_agent_harness.py tests/test_swarm_coordinator.py -v`.
- Write handoff.md in working directory and send_message to parent.

## Current Parent
- Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b
- Updated: 2026-10-06T05:20:00Z

## Task Summary
- **What to build**:
  1. SpecialistDomain.BIOINFORMATICS & SPECIALIST_MATRIX expansion in `backend/core/sovereign_reasoning/moe_specialist_router.py`.
  2. `backend/models/stehouwer_genomics.Modelfile` with ChatML, 32k context, temp 0.2, top_p 0.95, repeat_penalty 1.1, stop tokens, and specialized scientific prompt.
  3. `genomic_discovery_sprint` 4-stage preset in `backend/core/sovereign_reasoning/swarm_coordinator.py` using valid AGENT_APPS_CATALOG app_ids (openclaw, deepseek_harness, opencode, hermes_agent).
- **Success criteria**:
  - `pytest tests/test_moe_and_agent_harness.py tests/test_swarm_coordinator.py -v` passes 100% green.
  - Zero regressions across existing tests.
- **Interface contracts**: C:\AI-BS\PROJECT.md
- **Code layout**: C:\AI-BS\PROJECT.md § Code Layout

## Key Decisions Made
- Initializing task workspace and plan.

## Artifact Index
- C:\AI-BS\.agents\teamwork\worker_m3\BRIEFING.md — Situational awareness and state
- C:\AI-BS\.agents\teamwork\worker_m3\progress.md — Liveness heartbeat and milestone tracking
- C:\AI-BS\.agents\teamwork\worker_m3\DISPATCH.md — Assignment instructions
- C:\AI-BS\.agents\teamwork\worker_m3\handoff.md — Final completion handoff report

## Change Tracker
- **Files modified**: None yet
- **Build status**: Pending
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending initial test run
- **Lint status**: Clean
- **Tests added/modified**: Pending

## Loaded Skills
- None
