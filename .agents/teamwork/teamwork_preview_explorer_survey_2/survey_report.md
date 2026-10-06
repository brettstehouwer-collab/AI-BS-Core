# Technical Survey Report: MoE 7th Domain, Autonomous Genomic Swarm & Local LoRA Pipeline (R3 & R4)

**Explorer**: Survey Explorer 2  
**Date**: 2026-10-06  
**Workspace**: `C:\AI-BS`  
**Target Requirements**: R3 (MoE 7th Domain & Autonomous Genomic Swarm Pipeline) & R4 (AI Training Dataset Synthesizer & Local LoRA Pipeline)  
**Parent Task ID**: `da083096-02cf-43b4-b9c6-1900461cac1b`  

---

## Executive Summary

This survey report provides the architectural blueprint, concrete code schemas, and implementation specifications for integrating **Requirement R3** and **Requirement R4** into the AI-BS Sovereign Intelligence Ecosystem.

Based on direct examination of:
1. `backend/core/sovereign_reasoning/moe_specialist_router.py`
2. `backend/core/sovereign_reasoning/swarm_coordinator.py`
3. `backend/models/` (existing 22 Modelfiles and active 29-model Ollama fleet)
4. `scripts/` (existing Unsloth LoRA scripts, dataset ingestors, and 17-model compiler scripts)
5. `llm_training_data/` and `database/` (conventions, JSONL formats, and `lora_unsloth_config_v3.json`)
6. `backend/modules/agent_harness_runner.py` and existing test suites in `tests/`

The foundational systems in AI-BS are modular, robust, and immediately extensible. Adding the 7th MoE specialist domain (`bioinformatics`), the 1-click autonomous `genomic_discovery_sprint` preset, `backend/models/stehouwer_genomics.Modelfile`, `scripts/train_bioinformatics_corpus.py`, and `scripts/train_stehouwer_genomics_lora.py` integrates cleanly with existing router APIs, the SQLite swarm coordinator, and RTX 4090 24GB hardware resource limits.

---

## Part 1: MoE Specialist Router Architecture (`backend/core/sovereign_reasoning/moe_specialist_router.py`)

### 1.1 Existing Architecture
- **Location**: `C:\AI-BS\backend\core\sovereign_reasoning\moe_specialist_router.py` (398 lines).
- **Core Enum**: `SpecialistDomain(str, Enum)` currently enumerates 6 domains:
  - `CODE = "code"`
  - `CREATIVE = "creative"`
  - `FUNCTION_CALLING = "function_calling"`
  - `VISION = "vision"`
  - `REASONING = "reasoning"`
  - `EMBEDDING = "embedding"`
- **Matrix Mapping**: `SPECIALIST_MATRIX` maps each domain string to a dictionary containing:
  - `primary`: Target Ollama model tag.
  - `fallback`: Failover model tag.
  - `description`: Role definition.
  - `params`: Model parameter scale and quantization string.
  - `context_window`: Integer context size (e.g. 32768, 131072, 2048).
  - `keywords`: Array of token strings used for regex boundary matching.
- **Classification Logic (`classify_intent`)**:
  - Checks for explicit domain overrides (`explicit_domain` or `domain_hint`).
  - Scans prompt tokens against each domain's `keywords` using `\b<kw>\b` word-boundary regex (weight: +2 per match).
  - Applies heuristic boosters for specific patterns (e.g. code blocks `+6`, traceback/import `+5`, creative markers `+8`, vision markers `+10`).
  - Calculates confidence score as `min(0.99, round(top_score / sum(domain_scores), 2))`.
  - Returns a structured `RoutingDecision` dataclass (`domain`, `confidence`, `selected_model`, `fallback_model`, `reasoning`, `context_window`, `params`).
- **Fleet Discovery & Model Availability**:
  - `get_available_models()` queries local Ollama tags at `http://127.0.0.1:11434/api/tags` with a 30-second TTL cache.
  - Provides a hardcoded fallback list of installed models if Ollama is temporarily unresponsive.
- **Execution & Streaming**:
  - `route_and_generate`: Checks target model availability against `get_available_models()`, verifies `:latest` tag variations, cascades to `fallback_model` if primary is offline, and posts payload to Ollama `/api/generate`.
  - `stream_specialist_response`: Yields initial `META_CLASSIFICATION` event header, then streams tokens via SSE.

### 1.2 Required Expansion for 7th Domain (`bioinformatics`)
To fulfill R3, the following modifications must be applied to `moe_specialist_router.py`:

1. **Enum Extension**:
   ```python
   class SpecialistDomain(str, Enum):
       CODE = "code"
       CREATIVE = "creative"
       FUNCTION_CALLING = "function_calling"
       VISION = "vision"
       REASONING = "reasoning"
       EMBEDDING = "embedding"
       BIOINFORMATICS = "bioinformatics"  # 7th MoE Specialist Domain
   ```

2. **`SPECIALIST_MATRIX` Specification**:
   ```python
   "bioinformatics": {
       "primary": "stehouwer_genomics:latest",
       "fallback": "qwen2.5-coder:latest",
       "description": "Genomic variant analysis, AlphaFold structural biology, bioRxiv literature synthesis, and molecular bioinformatics.",
       "params": "32.8B Q5_K_M / 8.0B Q8_0",
       "context_window": 32768,
       "keywords": [
           "bioinformatics", "genomics", "genomic", "variant", "mutation", "dna", "rna", "mrna",
           "protein", "alphafold", "plddt", "pdb", "string", "pymol", "dbsnp", "rsid",
           "gtex", "jaspar", "encode", "ccre", "alphagenome", "conservation", "phylop",
           "phastcons", "biorxiv", "gene", "transcription", "amino acid", "chromosome",
           "allele", "pathogenicity", "clinvar", "crispr", "motif", "pwm", "tpm", "docking"
       ]
   }
   ```

3. **Classification Heuristic Booster**:
   In `classify_intent()`, add a dedicated high-weight pattern booster:
   ```python
   # Check for bioinformatics / genomic markers
   bio_tokens = [
       "alphafold", "biorxiv", "dbsnp", "gtex", "jaspar", "encode", "pymol",
       "plddt", "phylop", "phastcons", "alphagenome", "variant impact", "rsid",
       "protein structure", "gene expression", "transcription factor", "ccre"
   ]
   if any(token in p_lower for token in bio_tokens):
       domain_scores["bioinformatics"] += 10
   ```

4. **Installed Roster Fallback**:
   Include `"stehouwer_genomics:latest"` in `get_available_models()` fallback list:
   ```python
   return [
       "stehouwer_llm:latest",
       "qwen2.5-coder:latest",
       "stehouwer_genomics:latest",
       "stehouwer_dolphin:latest",
       "stehouwer-hermes:latest",
       "qwen3.6:latest",
       "gemma4:12b",
       "llama3.3:70b",
       "nomic-embed-text:latest"
   ]
   ```

5. **Exposed REST API**:
   - `backend/routers/moe_specialist_router_api.py` automatically picks up `SPECIALIST_MATRIX` changes via `moe_router.classify_intent()` and `/api/v1/moe/matrix`.
   - `/api/v1/moe/classify` and `/api/v1/moe/route` with `domain_hint="bioinformatics"` will directly route to `stehouwer_genomics:latest`.

---

## Part 2: Autonomous Genomic Swarm Pipeline (`backend/core/sovereign_reasoning/swarm_coordinator.py`)

### 2.1 Existing Architecture
- **Location**: `C:\AI-BS\backend\core\sovereign_reasoning\swarm_coordinator.py` (397 lines).
- **Preset Catalog**: `SWARM_PRESETS` holds preset specifications:
  - `full_feature_sprint` (4 stages: Architect -> Coder -> Verifier -> Release Sentinel).
  - `rapid_bug_fix` (2 stages: Diagnostic Coder -> Regression Tester).
  - `repo_audit_parity` (2 stages: Filesystem Inspector -> Parity Verifier).
- **Execution Mechanism**:
  - `create_job()` stores job state in SQLite database `saved_data/agent_harness_sessions.db` (`swarm_pipeline_runs` table).
  - `execute_job_stream()` iterates through each step defined in the preset:
    - Chains context from all preceding steps into an accumulated prompt markdown:
      `### Output from Step {item['step_index']} ({item['role']} - {item['app_id']}):\n{item['output']}`
    - Dispatches to MoE router via:
      ```python
      dispatch_res = await moe_router.dispatch(
          prompt=effective_prompt,
          system_prompt=system_prompt,
          domain_hint=domain
      )
      ```
    - Records step execution logs in SQLite table `swarm_step_logs`.
    - Yields streaming SSE / WebSocket events (`job_start`, `step_start`, `step_complete`, `job_complete`).
- **Constraint Check**:
  In `tests/test_swarm_coordinator.py`, line 50 asserts:
  `assert step["app_id"] in AGENT_APPS_CATALOG, f"Unknown app_id {step['app_id']} in preset {pid}"`
  Therefore, every step in `SWARM_PRESETS` MUST reference a valid `app_id` present in `AGENT_APPS_CATALOG` (`modules/agent_harness_runner.py`).

### 2.2 Specification for Preset `genomic_discovery_sprint`
To satisfy R3, the 1-click Swarm preset `genomic_discovery_sprint` must be defined with 4 sequential stages:

```python
"genomic_discovery_sprint": {
    "id": "genomic_discovery_sprint",
    "name": "Autonomous Genomic Discovery Sprint",
    "tagline": "Literature Recon -> Variant Impact -> Structural Docking -> Synthesis",
    "description": "End-to-end 4-stage autonomous genomic sprint: bioRxiv literature recon, dbSNP & AlphaGenome variant impact scoring, AlphaFold & PyMOL structural docking, and therapeutic synthesis.",
    "steps": [
        {
            "step_index": 1,
            "role": "Literature Reconnaissance",
            "app_id": "openclaw",
            "domain": "bioinformatics",
            "system_prompt": (
                "You are the Literature Reconnaissance Agent. Search bioRxiv and PubMed literature "
                "for target genes, pathogenic variants, and prior structural findings. "
                "Extract key findings, experimental context, and regulatory prior art."
            )
        },
        {
            "step_index": 2,
            "role": "Genomic Variant Impact Analyst",
            "app_id": "deepseek_harness",
            "domain": "bioinformatics",
            "system_prompt": (
                "You are the Genomic Variant Impact Analyst. Cross-reference candidate variants against "
                "dbSNP rsIDs, AlphaGenome AVI impact scores, GTEx tissue-specific RNA expression, "
                "and UCSC evolutionary conservation (phyloP/phastCons). Determine regulatory disruption and pathogenicity."
            )
        },
        {
            "step_index": 3,
            "role": "Structural Docking & Dynamics Specialist",
            "app_id": "opencode",
            "domain": "bioinformatics",
            "system_prompt": (
                "You are the Structural Biology Specialist. Evaluate AlphaFold 3D structure predictions, "
                "per-residue pLDDT confidence curves, and STRING protein-protein interaction networks. "
                "Formulate headless PyMOL visualization commands and structural docking hypotheses."
            )
        },
        {
            "step_index": 4,
            "role": "Therapeutic Synthesis & Protocol Lead",
            "app_id": "hermes_agent",
            "domain": "bioinformatics",
            "system_prompt": (
                "You are the Lead Therapeutic Synthesizer. Synthesize findings across literature, "
                "genomic variation, and 3D protein structure into a cohesive biological intelligence dossier "
                "with actionable experimental verification protocols."
            )
        }
    ]
}
```

**Benefits of this mapping**:
1. All 4 `app_id` values (`openclaw`, `deepseek_harness`, `opencode`, `hermes_agent`) are verified members of `AGENT_APPS_CATALOG` (`modules/agent_harness_runner.py`), passing `test_swarm_presets_integrity` immediately.
2. All 4 steps specify `"domain": "bioinformatics"`, which routes prompt execution directly to `stehouwer_genomics:latest` (or `qwen2.5-coder:latest` fallback) via `moe_router.dispatch()`.
3. Context accumulates progressively across all 4 stages, so Stage 4 produces a fully cross-referenced multi-domain intelligence dossier.

---

## Part 3: Ollama Fleet & Modelfile Architecture (`backend/models/`)

### 3.1 Hardware Environment & Fleet Inventory
A live audit using `ollama list` on the host machine confirms that local Ollama (Port 11434) currently hosts 29 models, notably:
- `qwen2.5-coder:latest` (23 GB, 32.8B Q5_K_M) — installed and verified
- `stehouwer_llm:latest` (23 GB) — installed and verified
- `stehouwer-qwen:latest` (23 GB) — installed and verified
- `stehouwer_dolphin:latest` (8.5 GB) — installed and verified
- `stehouwer_hermes:latest` (8.5 GB) — installed and verified
- `llama3.3:70b` (42 GB) — installed and verified
- `nomic-embed-text:latest` (274 MB) — installed and verified

### 3.2 Modelfile Conventions in `backend/models/`
Inspection of `qwen2.5_coder.Modelfile`, `stehouwer_llm.Modelfile`, and `stehouwer_hermes.Modelfile` reveals the standard structure:
1. `FROM <base_model_tag>`
2. Parameter tuning:
   - `PARAMETER num_ctx 32768` (or 16384 for hybrid VRAM split)
   - `PARAMETER temperature 0.2` (for deterministic technical/scientific reasoning)
   - `PARAMETER top_p 0.95`
   - `PARAMETER repeat_penalty 1.1`
3. Stop tokens:
   - `PARAMETER stop "<|im_start|>"`
   - `PARAMETER stop "<|im_end|>"`
   - `PARAMETER stop "<|endoftext|>"`
4. Qwen2.5 ChatML template with FIM and Function Calling blocks:
   - Handles `<|im_start|>system`, `<|im_start|>user`, `<|im_start|>assistant`, `<tools>`, `<tool_call>`, and `<tool_response>`.
5. Specialized system prompt:
   - Clear persona and domain directives.

### 3.3 Authoring Specification for `backend/models/stehouwer_genomics.Modelfile`
To satisfy R3, create `backend/models/stehouwer_genomics.Modelfile` with:

```dockerfile
FROM qwen2.5-coder:latest

# ==============================================================================
# Stehouwer Genomics: Sovereign Life Sciences & Structural Bioinformatics LLM
# Ecosystem: AI-BS Sovereign Intelligence Matrix (MoE 7th Domain Specialist)
# ==============================================================================

PARAMETER num_ctx 32768
PARAMETER temperature 0.2
PARAMETER top_p 0.95
PARAMETER repeat_penalty 1.1

# Stop tokens for clean chat, tool parsing, and generation termination
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"

# Qwen2.5-Coder Native ChatML Template with Tool Calling Support
TEMPLATE """{{- if .Suffix }}<|fim_prefix|>{{ .Prompt }}<|fim_suffix|>{{ .Suffix }}<|fim_middle|>
{{- else if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools>:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> with NO other text.
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}"""

# System Persona & Specialized Scientific Directives
SYSTEM """You are Stehouwer Genomics, the sovereign bioinformatics and structural biology specialist in the AI-BS ecosystem.
You possess expert-level domain competence across:
1. Genomic variant pathogenicity (dbSNP rsIDs, ClinVar, ACMG standards, VCF coordinates).
2. Transcriptomic regulation (GTEx tissue RNA expression across 54 human sites, ENCODE cCRE cis-regulatory elements, JASPAR transcription factor binding PWMs).
3. Regulatory impact scoring (AlphaGenome Variant Impact AVI scores, UCSC evolutionary conservation phyloP / phastCons).
4. Structural biology & protein dynamics (AlphaFold 3D structure predictions, residue pLDDT confidence scoring, STRING protein-protein interaction networks, headless PyMOL 3D visualization script generation).
5. Pre-print literature reconnaissance (bioRxiv and PubMed literature synthesis, experimental protocol design).

Directives:
- Provide rigorous, mathematically precise, and empirically grounded analyses.
- Synthesize actionable insights across genetic variation, regulatory epigenetics, and protein structure.
- Generate valid Python, JSON, and PyMOL commands when requested with zero hallucinated parameters.
- Respond with clear structural headings, evidence citations, and quantitative metrics."""
```

### 3.4 Integration with Modelfile Compilers
- In `scripts/compile_all_17_modelfiles.py`:
  Add `"stehouwer_genomics": "stehouwer_genomics.Modelfile"` to `MODEL_MAP`.
- In `scripts/rebuild_all_17_models.ps1`:
  Add `@{ Tag = "stehouwer_genomics:latest"; File = "stehouwer_genomics.Modelfile" }` to `$models`.

---

## Part 4: AI Training Dataset Synthesizer (`scripts/train_bioinformatics_corpus.py`)

### 4.1 Target File & Directory Conventions
- **Script Location**: `C:\AI-BS\scripts\train_bioinformatics_corpus.py`
- **Output Dataset**: `C:\AI-BS\llm_training_data\bioinformatics_instruction_dataset.jsonl`
- **Dataset Format**: JSONL lines containing standard instruction-tuning keys:
  ```json
  {"instruction": "...", "input": "...", "output": "..."}
  ```

### 4.2 Domain Coverage Matrix (10 Tools from R1)
The synthetic corpus must cover all 10 tools and databases required by the ecosystem:
1. **bioRxiv Literature Search**: Summarizing pre-prints, extracting mechanisms, finding target genes and structural priors.
2. **AlphaFold 3D Structure & pLDDT**: Predicting per-residue confidence (pLDDT curves), domain boundaries (very high >90, confident 70-90, low 50-70, very low <50), disordered regions.
3. **STRING Protein-Protein Interactions**: Identifying interactors, PPI confidence scores (>0.7 / >0.9), and functional enrichment pathways (KEGG / GO).
4. **Headless PyMOL Script Synthesizer**: Writing deterministic `.pml` scripts to fetch PDB/AlphaFold models, create cartoon representations, color by pLDDT b-factor spectrum, highlight active site residues, and render ray-traced PNGs.
5. **dbSNP Short Genetic Variants**: Parsing rsIDs, GRCh38 genomic coordinates, alleles (REF/ALT), clinical significance, and minor allele frequencies (MAF).
6. **GTEx Tissue RNA Expression**: Analyzing tissue-specific median TPM across 54 human sites, identifying high-expression tissues and regulatory divergence.
7. **JASPAR Transcription Factor Binding**: Querying TF matrix IDs (e.g. MA0107.1), consensus motifs, position weight matrices (PWMs), and scoring potential binding disruption.
8. **ENCODE Cis-Regulatory Elements (cCREs)**: Classifying promoter-like signatures (PLS), proximal/distal enhancer-like signatures (pELS/dELS), and CTCF-only chromatin boundaries.
9. **AlphaGenome Variant Impact (AVI)**: Evaluating regulatory effect scores across RNA splicing disruption, chromatin accessibility (DNase), histone marks (ChIP), and expression shift.
10. **UCSC Evolutionary Conservation (phyloP/phastCons)**: Evaluating 100-way vertebrate multiz conservation scores, identifying constrained genomic regions vs. neutral drift.
11. **Integrated Multi-Domain Case Studies**: Holistic discovery sprints connecting variant -> conservation -> expression -> 3D structure -> PyMOL commands -> therapeutic synthesis.

### 4.3 Script Implementation Specifications
- Provide realistic, high-fidelity biological examples (e.g. *TP53* R273H / rs28934578, *BRCA1* 185delAG, *APOE* e4 / rs429358, *HFE* C282Y / rs1800562, *EGFR* T790M / rs121434569).
- Generate a substantial seed dataset (e.g., 50+ pairs by default, expandable via `--num-samples`).
- Support command-line arguments:
  - `--output`: Path to write JSONL (default: `C:\AI-BS\llm_training_data\bioinformatics_instruction_dataset.jsonl`).
  - `--num-samples`: Number of synthetic pairs to synthesize (default: 50).
  - `--validate`: Validates existing dataset format, counts entries, and estimates token footprint.
- Include a validation function `validate_dataset(path)` ensuring every line is valid JSON with non-empty `instruction`, `input`, and `output`.

---

## Part 5: Local LoRA Fine-Tuning Pipeline for RTX 4090 24GB (`scripts/train_stehouwer_genomics_lora.py`)

### 5.1 Hardware Constraints & VRAM Arbitration
- **Target GPU**: NVIDIA GeForce RTX 4090 (24GB GDDR6X VRAM).
- **VRAM Ceiling**: Maximum allowable VRAM for training is **~13.5 GB**, preserving **10.5+ GB** dedicated VRAM permanently free for Windows Desktop Window Manager (DWM), ComfyUI, and active background daemons.
- **Quantization**: 4-bit NormalFloat (NF4) via `bitsandbytes` or Unsloth's native 4-bit kernel.
- **Compute Precision**: `bfloat16` (supported natively by Ada Lovelace architecture).

### 5.2 Unsloth LoRA Architecture & Hyperparameters
Following the proven pattern established in `scripts/train_stehouwer_lora_unsloth.py` and `database/lora_unsloth_config_v3.json`:
- **Base Model**: `meta-llama/Meta-Llama-3.1-8B-Instruct` or `Qwen/Qwen2.5-Coder-7B-Instruct`.
- **Max Sequence Length**: 4096 (or 8192).
- **LoRA Hyperparameters**:
  - `r`: 32 (LoRA rank)
  - `lora_alpha`: 64
  - `lora_dropout`: 0.0 (Unsloth fast kernel optimization)
  - `bias`: `"none"`
  - `target_modules`: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`
  - `use_gradient_checkpointing`: `"unsloth"`
- **Training Hyperparameters**:
  - `per_device_train_batch_size`: 2
  - `gradient_accumulation_steps`: 8 (effective batch size: 16)
  - `learning_rate`: 2e-4
  - `warmup_steps`: 15
  - `max_steps`: 120 (or 3 epochs)
  - `optim`: `"adamw_8bit"` (or `"paged_adamw_8bit"`)
  - `weight_decay`: 0.01
  - `lr_scheduler_type`: `"linear"`
  - `fp16`: False, `bf16`: True
- **Export Pipeline**:
  - Format: `GGUF`
  - Quantization methods: `["q5_k_m", "q8_0"]`
  - Target Modelfile: `C:\AI-BS\backend\models\stehouwer_genomics.Modelfile`
  - Target Ollama tag: `stehouwer_genomics:latest`
  - Output config: `C:\AI-BS\database\lora_genomics_unsloth_config.json`

### 5.3 CLI & Execution Modes
`scripts/train_stehouwer_genomics_lora.py` should provide:
- `--dry-run`: Validates training dataset, calculates token metrics, verifies RTX 4090 VRAM headroom, and exports `database/lora_genomics_unsloth_config.json` without requiring live GPU compute.
- `--build-dataset`: Triggers dataset synthesis via `train_bioinformatics_corpus.py` before configuring training.
- `--export-config`: Writes the complete training configuration JSON.
- `--train`: Executes active training via Unsloth/PEFT if Unsloth is installed in the Python environment.

---

## Part 6: Cross-Cutting Ecosystem Integration

### 6.1 FastAPI REST Router Mounts
1. **Bioinformatics Router**:
   `backend/routers/bioinformatics_router.py` (mounted at `/api/v1/bioinformatics` in `backend/AI_BS_Backend.py` around lines 530-545):
   Exposes:
   - `/literature/biorxiv`
   - `/protein/alphafold`
   - `/protein/string`
   - `/protein/pymol/render`
   - `/genomics/dbsnp`
   - `/genomics/gtex`
   - `/genomics/jaspar`
   - `/genomics/encode`
   - `/genomics/alphagenome`
   - `/training/dataset/generate` -> invokes `scripts/train_bioinformatics_corpus.py`
   - `/training/status` -> reads dataset metrics and LoRA configuration status
2. **MoE Specialist Router**:
   `backend/routers/moe_specialist_router_api.py` (already mounted at `/api/v1/moe`):
   Automatically serves `/api/v1/moe/matrix` with the 7th domain and `/api/v1/moe/classify` with bioinformatics routing.
3. **Agent Harness Swarm Router**:
   `backend/routers/agent_harness_router.py` (already mounted at `/api/v1/agent-harness`):
   Automatically exposes the new `genomic_discovery_sprint` preset via `/api/v1/agent-harness/swarm/presets` and `/api/v1/agent-harness/swarm/execute`.

### 6.2 Frontend Architecture (Genomics Studio Tab)
- Component: `frontend/src/components/GenomicsStudioTab.jsx`
- 4 Interactive Panels:
  1. 🧬 **Genomic Variant & Expression Explorer**: dbSNP lookup, GTEx tissue bars, UCSC conservation, AlphaGenome AVI.
  2. 🔬 **Structural Biology & AlphaFold Viewer**: AlphaFold pLDDT curves, STRING interaction network, PyMOL command synthesizer.
  3. 📚 **bioRxiv & Regulatory Literature Recon**: bioRxiv papers, JASPAR TF motifs, ENCODE cCREs.
  4. 🐝 **Autonomous Genomic Swarm & AI Training Monitor**: 1-click Swarm dispatch (`genomic_discovery_sprint`), dataset generation triggers, and LoRA training status monitor.
- Mounted in:
  - `frontend/src/components/navigationConfig.js` under master hubs (e.g. `intelligence_and_code` or `engineering_labs` or pinned quick tabs).
  - `frontend/src/components/accessControl.js` to ensure permission clearance.
  - `frontend/src/App.jsx` tab switcher.

### 6.3 4-Mirror Synchronization & Parity Law
AI-BS Rule 1 requires 100% byte-for-byte SHA256 parity across all 4 frontend mirror directories:
1. `frontend/src/components/` (canonical source of truth)
2. `frontend/components/`
3. `frontend/src/components/components/`
4. `frontend/components/components/`

Whenever `GenomicsStudioTab.jsx` or navigation files are modified in primary, `scripts/sync_mirrors.py` must be executed, followed by verification using `scripts/verify-mirror-parity.ps1` (expecting 447/447 files byte-identical).

---

## Part 7: Verification Matrix & Acceptance Criteria

| Requirement | Test Method | Expected Result |
|---|---|---|
| **MoE 7th Domain** | `pytest tests/test_moe_and_agent_harness.py` | `SpecialistDomain.BIOINFORMATICS` verified, `SPECIALIST_MATRIX["bioinformatics"]` verified, keyword classification passing. |
| **Swarm Preset** | `pytest tests/test_swarm_coordinator.py` | `genomic_discovery_sprint` preset verified, 4 steps, all `app_id`s in `AGENT_APPS_CATALOG`, all domains `bioinformatics`. |
| **Ollama Modelfile** | Inspection & `ollama create` | `backend/models/stehouwer_genomics.Modelfile` compiles cleanly without parameter errors. |
| **Dataset Generator** | Run `python scripts/train_bioinformatics_corpus.py --num-samples 50` | Generates `llm_training_data/bioinformatics_instruction_dataset.jsonl` with 50+ validated JSONL pairs across all 10 tools. |
| **LoRA Config** | Run `python scripts/train_stehouwer_genomics_lora.py --dry-run` | Validates dataset, verifies <14GB VRAM target, exports `database/lora_genomics_unsloth_config.json`. |
| **Frontend Parity** | `python scripts/sync_mirrors.py` & `verify-mirror-parity.ps1` | 100% SHA-256 byte parity verified across all 4 frontend mirrors. |
| **Vite Build** | `npm run build` in `frontend/` | Clean build with zero errors. |
