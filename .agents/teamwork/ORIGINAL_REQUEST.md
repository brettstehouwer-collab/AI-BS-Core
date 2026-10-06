# Original User Request

## Initial Request — 2026-10-06T05:07:27Z

Integrate a complete life sciences, genomic variant analysis, structural biology, and bioRxiv literature intelligence suite into the AI-BS Sovereign Intelligence Ecosystem with multi-system AI training, 7th MoE specialist domain, autonomous genomic swarm pipeline, and dedicated studio workspace.

Working directory: C:\AI-BS
Integrity mode: development

## Requirements

### R1. Unified Core Bioinformatics & Structural Intelligence Service
Build backend/core/bioinformatics_service.py wrapping the 10 scientific databases and visualization tools:
- bioRxiv literature search and summary extraction
- AlphaFold 3D structure prediction metrics (pLDDT curves, domain boundaries)
- STRING database protein-protein interaction networks and functional enrichments
- Headless PyMOL script synthesizer and command dispatcher
- dbSNP short genetic variant & rsID lookup with clinical annotations
- GTEx tissue-specific RNA quantitative expression across 54 human tissues
- JASPAR transcription factor binding profiles and position weight matrices (PWMs)
- ENCODE Registry of cis-Regulatory Elements (cCREs)
- AlphaGenome Variant Impact (AVI) scoring and regulatory prediction
- UCSC Genome Browser evolutionary conservation (phyloP/phastCons) and TFBS
All queries must support local SQLite caching in saved_data/bioinformatics_cache.db for offline resilience.

### R2. FastAPI REST Router on Port 8080
Create backend/routers/bioinformatics_router.py mounted at /api/v1/bioinformatics in backend/AI_BS_Backend.py exposing:
- /literature/biorxiv
- /protein/alphafold
- /protein/string
- /protein/pymol/render
- /genomics/dbsnp
- /genomics/gtex
- /genomics/jaspar
- /genomics/encode
- /genomics/alphagenome
- /training/dataset/generate
- /training/status

### R3. MoE 7th Domain & Autonomous Genomic Swarm Pipeline
- Expand SpecialistDomain and SPECIALIST_MATRIX in backend/core/sovereign_reasoning/moe_specialist_router.py with the 7th domain: bioinformatics (primary: stehouwer_genomics:latest, fallback: qwen2.5-coder:latest / llama3.3:70b).
- Author backend/models/stehouwer_genomics.Modelfile with specialized scientific system prompt, parameter tuning, and stop tokens.
- Add 1-click Swarm preset genomic_discovery_sprint (Literature Recon -> Variant Impact -> Structural Docking -> Synthesis) in backend/core/sovereign_reasoning/swarm_coordinator.py.

### R4. AI Training Dataset Synthesizer & Local LoRA Pipeline
- Build scripts/train_bioinformatics_corpus.py to synthesize instruction-tuning dataset pairs (instruction, input, output) into llm_training_data/bioinformatics_instruction_dataset.jsonl.
- Author scripts/train_stehouwer_genomics_lora.py formatted for RTX 4090 24GB VRAM Unsloth LoRA fine-tuning.

### R5. Dedicated 'Genomic & Structural Intelligence Studio' UI & Multi-Mirror Parity
- Create frontend/src/components/GenomicsStudioTab.jsx with 4 interactive panels:
  1. 🧬 Genomic Variant & Expression Explorer (dbSNP, GTEx bars, UCSC conservation, AlphaGenome AVI).
  2. 🔬 Structural Biology & AlphaFold Viewer (AlphaFold pLDDT, STRING interactions, PyMOL triggers).
  3. 📚 bioRxiv & Regulatory Literature Recon (bioRxiv papers, JASPAR motifs, ENCODE cCREs).
  4. 🐝 Autonomous Genomic Swarm & AI Training Monitor (1-click Swarm dispatch, dataset generator, training logs).
- Mount genomics_studio tab into frontend/App.jsx, navigationConfig.js, and accessControl.js.
- Enforce 100% SHA-256 byte parity across all 4 frontend mirrors using scripts/sync_mirrors.py and scripts/verify-mirror-parity.ps1.
- Verify clean Vite production build (npm run build).
- Bump version to v5.311.0 across ecosystem ledgers.

## Acceptance Criteria

### Verification & Performance
- [ ] Programmatic pytest test suite verifying bioinformatics service adapters, MoE 7th domain routing, and dataset synthesis passing 100% green.
- [ ] 100% SHA-256 byte parity verified across all 4 frontend mirror directories (447/447 files identical).
- [ ] Clean Vite production build with zero errors.
- [ ] 100% Zero-cost local execution without external commercial API keys.
- [ ] Desktop shortcuts refreshed to v5.311.0.


## Follow-up — 2026-10-06T05:12:49Z

Operator directive update: Please ensure Foldseek 3D Structural Homology Search (querying AlphaFold DB afdb50/afdb-swissprot and PDB pdb100 from .pdb/.cif files via Foldseek API) is included in Milestone 1 (backend/core/bioinformatics_service.py), Milestone 2 (/api/v1/bioinformatics/protein/foldseek), and Milestone 5 (GenomicsStudioTab.jsx 3D viewer panel).
