# Dispatch: Survey Explorer 2 (MoE 7th Domain, Swarm Coordinator, AI Training Survey)

## Identity
- Archetype: teamwork_preview_explorer
- Working directory: C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_2
- Parent Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b

## Objective
Read C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md.
Investigate the existing MoE specialist reasoning, swarm coordinator, Ollama models, and training dataset scripts in C:\AI-BS to map the foundational requirements for R3 (MoE 7th Domain & Autonomous Genomic Swarm Pipeline) and R4 (AI Training Dataset Synthesizer & Local LoRA Pipeline).

## Scope Boundaries
- Read-only exploration. DO NOT write or modify application code.
- Focus on:
  1. backend/core/sovereign_reasoning/moe_specialist_router.py: Existing SpecialistDomain enum, SPECIALIST_MATRIX structure, routing logic, primary/fallback model definitions.
  2. backend/core/sovereign_reasoning/swarm_coordinator.py: Swarm presets, agent roles, stage progression, sprint execution patterns.
  3. backend/models/: Existing Modelfiles (e.g. system prompts, Ollama parameters, stop tokens, how Modelfiles are defined and registered).
  4. scripts/: Existing training scripts, dataset generators, format conventions (JSONL instruction datasets, instruction/input/output), Unsloth LoRA fine-tuning scripts for RTX 4090 24GB.
  5. llm_training_data/: Directory conventions, existing instruction datasets.

## Output Requirements
Write your detailed report to C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_2\survey_report.md, and write handoff.md in your working directory.
Send a message back to parent when done.


## 2026-10-06T05:09:50Z
You are Survey Explorer 2.
Your working directory is: C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_2
Read your instructions in C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_2\DISPATCH.md and the authoritative request in C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md.
Investigate the existing MoE specialist reasoning, swarm coordinator, Ollama models, and training dataset scripts in C:\AI-BS to map the foundational requirements for R3 (MoE 7th Domain & Autonomous Genomic Swarm Pipeline) and R4 (AI Training Dataset Synthesizer & Local LoRA Pipeline).
Examine:
- backend/core/sovereign_reasoning/moe_specialist_router.py: SpecialistDomain enum, SPECIALIST_MATRIX structure, routing logic.
- backend/core/sovereign_reasoning/swarm_coordinator.py: Swarm presets, stage execution, sprint models.
- backend/models/: Modelfiles structure, parameters, stop tokens.
- scripts/ and llm_training_data/: Training dataset generation conventions, Unsloth LoRA scripts for RTX 4090 24GB.
Write your complete findings to C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_2\survey_report.md and a standard handoff.md in your working directory. Send a message to parent (da083096-02cf-43b4-b9c6-1900461cac1b) when done.
