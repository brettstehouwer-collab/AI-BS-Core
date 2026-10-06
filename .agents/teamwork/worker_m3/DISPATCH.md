# Dispatch: Worker M3 (MoE 7th Domain & Autonomous Genomic Swarm Pipeline)

## Identity
- Archetype: teamwork_preview_worker
- Working directory: C:\AI-BS\.agents\teamwork\worker_m3
- Parent Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b

## Objective
Implement R3: MoE 7th Domain (`SpecialistDomain.BIOINFORMATICS`), `stehouwer_genomics.Modelfile`, and the autonomous `genomic_discovery_sprint` Swarm preset as specified in `C:\AI-BS\PROJECT.md`, `C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md`, and `C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_2\survey_report.md`.

## Exclusive File Ownership
- `backend/core/sovereign_reasoning/moe_specialist_router.py`
- `backend/models/stehouwer_genomics.Modelfile`
- `backend/core/sovereign_reasoning/swarm_coordinator.py`
- (Optionally registers in `scripts/compile_all_17_modelfiles.py` and `scripts/rebuild_all_17_models.ps1`)
(DO NOT modify files outside your ownership)

## Implementation Requirements
1. **MoE 7th Domain Expansion (`moe_specialist_router.py`)**:
   - Add `BIOINFORMATICS = "bioinformatics"` to `SpecialistDomain(str, Enum)`.
   - Add `"bioinformatics"` entry to `SPECIALIST_MATRIX`:
     * `"primary"`: `"stehouwer_genomics:latest"`
     * `"fallback"`: `["qwen2.5-coder:latest", "llama3.3:70b"]`
     * `"description"`: `"Genomic variant interpretation, structural biology, protein design, and bioRxiv literature reasoning"`
     * `"params"`: `{"temperature": 0.2, "top_p": 0.95, "num_ctx": 32768, "repeat_penalty": 1.1}`
     * `"context_window"`: 32768
     * `"keywords"`: comprehensive list of bioinformatics keywords (e.g., `["alphafold", "biorxiv", "dbsnp", "gtex", "jaspar", "encode", "pymol", "foldseek", "plddt", "variant", "mutation", "protein", "dna", "rna", "transcription factor", "ccre", "genomic", "uniprot", "pdb", "gene expression"]`)
   - Add +10 heuristic booster in `classify_intent()` for strong bioinformatics signals.
   - Include `"stehouwer_genomics:latest"` in fallback candidate lists where appropriate.
2. **Modelfile Authoring (`backend/models/stehouwer_genomics.Modelfile`)**:
   - Base model: `FROM qwen2.5-coder:latest` (or `FROM stehouwer_llm:latest`)
   - Parameters:
     * `PARAMETER num_ctx 32768`
     * `PARAMETER temperature 0.2`
     * `PARAMETER top_p 0.95`
     * `PARAMETER repeat_penalty 1.1`
     * Stop tokens: `<|im_start|>`, `<|im_end|>`, `<|endoftext|>`
   - Specialized scientific system prompt incorporating multi-omic clinical and structural analysis guidelines.
3. **Autonomous Genomic Swarm Preset (`swarm_coordinator.py`)**:
   - Add `genomic_discovery_sprint` preset to `SWARM_PRESETS`:
     * `name`: `"Genomic Discovery & Multi-Omic Synthesis Sprint"`
     * `description`: `"Autonomous 4-stage pipeline: Literature Recon -> Variant Impact -> Structural Docking & Homology -> Final Synthesis Dossier"`
     * `steps`:
       1. `step_index: 1`, `role: "Literature & Prior Art Recon"`, `app_id: "openclaw"`, `domain: "bioinformatics"`, prompt targeting bioRxiv & regulatory literature.
       2. `step_index: 2`, `role: "Genomic Variant & Expression Analysis"`, `app_id: "deepseek_harness"`, `domain: "bioinformatics"`, prompt targeting dbSNP, GTEx, AlphaGenome AVI, UCSC conservation.
       3. `step_index: 3`, `role: "Structural Biology & Homology Docking"`, `app_id: "opencode"`, `domain: "bioinformatics"`, prompt targeting AlphaFold pLDDT, STRING, PyMOL, Foldseek.
       4. `step_index: 4`, `role: "Sovereign Synthesis & Actionable Report"`, `app_id: "hermes_agent"`, `domain: "bioinformatics"`, prompt synthesizing prior outputs into a clinical/research dossier.
     *(Note: All `app_id` values MUST be members of `AGENT_APPS_CATALOG` in `backend/modules/agent_harness_runner.py`)*.
4. **Verification**:
   - Run `pytest tests/test_moe_and_agent_harness.py tests/test_swarm_coordinator.py -v`.
   - Ensure all existing tests pass 100% green without regressions.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Completion Criteria
- Run tests and verify zero regressions.
- Deliver `handoff.md` in your working directory and message parent.


## 2026-10-06T05:19:48Z
[Message] timestamp=2026-10-06T05:19:48Z sender=da083096-02cf-43b4-b9c6-1900461cac1b priority=MESSAGE_PRIORITY_HIGH content=You are Worker M3 (MoE 7th Domain & Swarm Pipeline).
Your working directory is: C:\AI-BS\.agents\teamwork\worker_m3
Read C:\AI-BS\.agents\teamwork\worker_m3\DISPATCH.md, C:\AI-BS\PROJECT.md, and C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md.
Implement:
1. SpecialistDomain.BIOINFORMATICS & SPECIALIST_MATRIX expansion in backend/core/sovereign_reasoning/moe_specialist_router.py.
2. backend/models/stehouwer_genomics.Modelfile with ChatML, 32k context, temp 0.2, stop tokens, and scientific prompt.
3. genomic_discovery_sprint 4-stage preset in backend/core/sovereign_reasoning/swarm_coordinator.py (using valid AGENT_APPS_CATALOG app_ids).
Exclusive file ownership: backend/core/sovereign_reasoning/moe_specialist_router.py, backend/models/stehouwer_genomics.Modelfile, backend/core/sovereign_reasoning/swarm_coordinator.py.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Run pytest tests/test_moe_and_agent_harness.py tests/test_swarm_coordinator.py -v, write handoff.md, and send a message to parent da083096-02cf-43b4-b9c6-1900461cac1b.
