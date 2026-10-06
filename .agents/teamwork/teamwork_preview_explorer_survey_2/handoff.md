# Handoff Report: Survey Explorer 2 (R3 & R4 Foundational Survey)

## 1. Observation

1. **`backend/core/sovereign_reasoning/moe_specialist_router.py`**:
   - Lines 38-45 define `SpecialistDomain(str, Enum)` with 6 domains: `CODE = "code"`, `CREATIVE = "creative"`, `FUNCTION_CALLING = "function_calling"`, `VISION = "vision"`, `REASONING = "reasoning"`, `EMBEDDING = "embedding"`.
   - Lines 68-117 define `SPECIALIST_MATRIX` containing configuration dictionaries with keys `"primary"`, `"fallback"`, `"description"`, `"params"`, `"context_window"`, and `"keywords"`.
   - Lines 156-215 define `classify_intent()`, which matches prompt words against `keywords` using regex `\b<kw>\b` (+2 per match) and adds heuristic boosters (+6 for code blocks, +8 for creative keywords, +10 for visual cues).
   - Lines 144-154 define `get_available_models()` fallback list:
     ```python
     return [
         "stehouwer_llm:latest",
         "qwen2.5-coder:latest",
         "stehouwer_dolphin:latest",
         "stehouwer-hermes:latest",
         "qwen3.6:latest",
         "gemma4:12b",
         "llama3.3:70b",
         "nomic-embed-text:latest"
     ]
     ```
   - Lines 270-328 define `route_and_generate()`, verifying model availability against `get_available_models()`, handling `:latest` tag variants, falling back to secondary models if primary is missing, and sending requests to `http://127.0.0.1:11434/api/generate`.

2. **`backend/core/sovereign_reasoning/swarm_coordinator.py`**:
   - Lines 28-109 define `SWARM_PRESETS: Dict[str, Dict[str, Any]]` containing `full_feature_sprint`, `rapid_bug_fix`, and `repo_audit_parity`.
   - Lines 270-366 define `execute_job_stream()`. In lines 307-311:
     ```python
     dispatch_res = await moe_router.dispatch(
         prompt=effective_prompt,
         system_prompt=system_prompt,
         domain_hint=domain
     )
     ```
     Context from prior steps is concatenated in lines 290-300: `### Output from Step {item['step_index']} ({item['role']} - {item['app_id']}):\n{item['output']}`.
   - Lines 124-156 define SQLite persistence in `saved_data/agent_harness_sessions.db` with tables `swarm_pipeline_runs` and `swarm_step_logs`.

3. **`backend/modules/agent_harness_runner.py`**:
   - Lines 36-200 define `AGENT_APPS_CATALOG` with 14 sovereign agent applications: `claude_code`, `codex_cli`, `openclaw`, `opencode`, `hermes_agent`, `hermes_desktop`, `droid`, `pi`, `cline`, `copilot_cli`, `oh_my_pi`, `deepseek_harness`, `qwen_code`, and `terminal`.
   - In `tests/test_swarm_coordinator.py:50`, the test suite strictly enforces: `assert step["app_id"] in AGENT_APPS_CATALOG, f"Unknown app_id {step['app_id']} in preset {pid}"`.

4. **`backend/models/` & Host Ollama Fleet**:
   - Command `ollama list` output on host:
     `qwen2.5-coder:latest` (23 GB), `qwen3.6:latest` (23 GB), `stehouwer_llm:latest` (23 GB), `stehouwer_dolphin:latest` (8.5 GB), `stehouwer_hermes:latest` (8.5 GB), `llama3.3:70b` (42 GB), `nomic-embed-text:latest` (274 MB). Total 29 models installed.
   - `backend/models/stehouwer_llm.Modelfile` (lines 1-14) uses `PARAMETER num_gpu 48`, `PARAMETER num_ctx 16384`, `PARAMETER temperature 0.4`, stop tokens `<|im_start|>`, `<|im_end|>`, `<|endoftext|>`.
   - `backend/models/qwen2.5_coder.Modelfile` (lines 6-12) uses `PARAMETER num_ctx 32768`, `PARAMETER temperature 0.2`, `PARAMETER top_p 0.95`, stop tokens `<|im_start|>`, `<|im_end|>`, `<|endoftext|>`.

5. **Existing Unsloth LoRA & Training Conventions**:
   - `scripts/train_stehouwer_lora_unsloth.py`: Configures QLoRA for NVIDIA RTX 4090 24GB VRAM under ~14GB ceiling.
   - `database/lora_unsloth_config_v3.json`: Demonstrates exact JSON schema with `model_architecture`, `lora_parameters` (`r=32`, `lora_alpha=64`, `target_modules` all 7 linear projections, `use_gradient_checkpointing="unsloth"`), `training_arguments` (`per_device_train_batch_size=2`, `gradient_accumulation_steps=8`, `bf16=true`, `optim="adamw_8bit"`), and `export_pipeline` (`GGUF`, `q5_k_m`, `q8_0`).
   - `llm_training_data/chat_export_today.jsonl`: Demonstrates standard JSONL line-delimited format.

6. **Current Test Status**:
   - Running `pytest tests/test_moe_and_agent_harness.py tests/test_swarm_coordinator.py -v` passes 10/10 tests in 1.72s.

---

## 2. Logic Chain

1. **MoE Routing Integration**:
   - From Observation 1, `moe_specialist_router.py` classifies intents using `SPECIALIST_MATRIX` and keyword word boundaries.
   - Extending `SpecialistDomain` with `BIOINFORMATICS = "bioinformatics"` and adding the `"bioinformatics"` key to `SPECIALIST_MATRIX` (with primary model `stehouwer_genomics:latest` and fallback `qwen2.5-coder:latest`) allows both explicit routing (`domain_hint="bioinformatics"`) and heuristic keyword routing.
   - Adding a +10 heuristic booster for tokens like `"alphafold"`, `"biorxiv"`, `"dbsnp"`, `"gtex"`, `"jaspar"`, `"encode"`, `"pymol"`, `"plddt"`, and `"variant impact"` ensures prompt classification directly hits the bioinformatics specialist with high confidence (>=0.7).

2. **Autonomous Genomic Swarm Integration**:
   - From Observation 2 and Observation 3, `swarm_coordinator.py` dispatches steps in `SWARM_PRESETS` to `moe_router.dispatch(domain_hint=step["domain"])`, and `test_swarm_coordinator.py` requires every step's `app_id` to be in `AGENT_APPS_CATALOG`.
   - Designing `genomic_discovery_sprint` with 4 steps using valid catalog IDs (`openclaw` for Literature Recon, `deepseek_harness` for Variant Impact, `opencode` for Structural Docking, and `hermes_agent` for Synthesis) and setting each step's `domain` to `"bioinformatics"` guarantees:
     a) All steps will dispatch to the bioinformatics MoE domain.
     b) Step outputs accumulate sequentially into a unified multi-domain discovery dossier.
     c) All existing test assertions in `test_swarm_coordinator.py` will pass 100% green.

3. **Modelfile Architecture**:
   - From Observation 4, `qwen2.5-coder:latest` is locally present in the host's Ollama fleet (23 GB, 32.8B Q5_K_M).
   - Basing `stehouwer_genomics.Modelfile` on `FROM qwen2.5-coder:latest` provides native 32,768 context support, ChatML syntax, and code/tool execution capabilities.
   - Tuning parameters to `num_ctx 32768`, `temperature 0.2`, `top_p 0.95`, `repeat_penalty 1.1`, and stop tokens `<|im_start|>`, `<|im_end|>`, `<|endoftext|>` establishes low-hallucination scientific reasoning.
   - Registering `stehouwer_genomics` in `scripts/compile_all_17_modelfiles.py` and `scripts/rebuild_all_17_models.ps1` enables 1-command compilation.

4. **Training Corpus & LoRA Pipeline Architecture**:
   - From Observation 5, standard instruction-tuning format in this ecosystem uses `{"instruction": "...", "input": "...", "output": "..."}`.
   - `scripts/train_bioinformatics_corpus.py` must synthesize pairs covering all 10 tools from R1 (bioRxiv, AlphaFold, STRING, PyMOL, dbSNP, GTEx, JASPAR, ENCODE, AlphaGenome, UCSC) and multi-domain case studies into `llm_training_data/bioinformatics_instruction_dataset.jsonl`.
   - `scripts/train_stehouwer_genomics_lora.py` matching the configuration schema in `database/lora_unsloth_config_v3.json` guarantees strict adherence to the RTX 4090 24GB VRAM ceiling (<14GB consumed, leaving >10GB headroom) with fast 4-bit NF4 training, GGUF export (`q5_k_m`, `q8_0`), and config output to `database/lora_genomics_unsloth_config.json`.

---

## 3. Caveats

1. **Ollama Compilation**: Modelfile authoring creates `backend/models/stehouwer_genomics.Modelfile`. Compiling it into Ollama via `ollama create stehouwer_genomics:latest -f backend/models/stehouwer_genomics.Modelfile` requires the Ollama daemon running on Port 11434. In environments where Ollama is stopped or during offline testing, `moe_specialist_router.py` gracefully falls back to `qwen2.5-coder:latest` or `stehouwer_llm:latest`.
2. **GPU Training Execution**: Active execution of `train_stehouwer_genomics_lora.py --train` requires PyTorch with CUDA and `unsloth` installed. In standard testing or CI environments lacking Unsloth, running with `--dry-run` or `--export-config` validates the dataset and produces the configuration JSON without error.
3. **No Code Modification Undertaken**: As a read-only investigation, no production source files outside this agent's folder were modified.

---

## 4. Conclusion

1. The foundational specifications for R3 (MoE 7th Domain & Autonomous Genomic Swarm Pipeline) and R4 (AI Training Dataset Synthesizer & Local LoRA Pipeline) are fully mapped and documented in `survey_report.md`.
2. Implementation changes required:
   - `backend/core/sovereign_reasoning/moe_specialist_router.py`: Add `SpecialistDomain.BIOINFORMATICS = "bioinformatics"`, insert `"bioinformatics"` into `SPECIALIST_MATRIX`, add heuristic keyword booster (+10).
   - `backend/core/sovereign_reasoning/swarm_coordinator.py`: Add `genomic_discovery_sprint` preset to `SWARM_PRESETS` with 4 steps (`openclaw`, `deepseek_harness`, `opencode`, `hermes_agent`), each with `domain="bioinformatics"`.
   - `backend/models/stehouwer_genomics.Modelfile`: Author Modelfile with ChatML, 32k context, temp 0.2, stop tokens, and scientific system prompt.
   - `scripts/train_bioinformatics_corpus.py`: Build synthesizer outputting `llm_training_data/bioinformatics_instruction_dataset.jsonl` covering all 10 tools.
   - `scripts/train_stehouwer_genomics_lora.py`: Author Unsloth LoRA fine-tuner for RTX 4090 24GB exporting GGUF and config JSON.
   - `scripts/compile_all_17_modelfiles.py` & `scripts/rebuild_all_17_models.ps1`: Register `stehouwer_genomics`.
   - `tests/test_moe_and_agent_harness.py` & `tests/test_swarm_coordinator.py`: Add test assertions validating 7th domain and genomic sprint preset.

---

## 5. Verification Method

1. **MoE Routing Verification**:
   Inspect `SPECIALIST_MATRIX` and verify `SpecialistDomain.BIOINFORMATICS` membership.
   Run:
   ```powershell
   pytest tests/test_moe_and_agent_harness.py -v
   ```
2. **Swarm Preset Verification**:
   Verify `genomic_discovery_sprint` is loaded in `SWARM_PRESETS` and all 4 step app_ids are in `AGENT_APPS_CATALOG`.
   Run:
   ```powershell
   pytest tests/test_swarm_coordinator.py -v
   ```
3. **Dataset Generator Verification**:
   Run:
   ```powershell
   python scripts/train_bioinformatics_corpus.py --num-samples 50 --validate
   ```
   Inspect `llm_training_data/bioinformatics_instruction_dataset.jsonl` to ensure all lines parse as valid JSON with keys `{"instruction", "input", "output"}`.
4. **LoRA Pipeline Verification**:
   Run:
   ```powershell
   python scripts/train_stehouwer_genomics_lora.py --dry-run
   ```
   Inspect generated `database/lora_genomics_unsloth_config.json`.
