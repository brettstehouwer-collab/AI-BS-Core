# Project: AI-BS Sovereign Intelligence Ecosystem — Life Sciences & Bioinformatics Suite

## Architecture
- **Layer 1: Data & Intelligence Core (`backend/core/`)**:
  - `bioinformatics_service.py`: Unified adapter wrapping 10 public life-sciences databases + Foldseek 3D structural homology search.
  - `bioinformatics_cache.db` in `saved_data/`: SQLite WAL-mode local storage caching API responses for zero-cost offline resilience.
- **Layer 2: API Gateway (`backend/routers/` & `backend/AI_BS_Backend.py`)**:
  - `bioinformatics_router.py`: FastAPI router mounted at `/api/v1/bioinformatics` on Port 8080.
  - Endpoints grouped into `/literature/`, `/protein/`, `/genomics/`, and `/training/`.
- **Layer 3: Sovereign Reasoning & Swarm Swarm (`backend/core/sovereign_reasoning/` & `backend/models/`)**:
  - `SpecialistDomain.BIOINFORMATICS`: 7th MoE specialist domain in `moe_specialist_router.py`.
  - `stehouwer_genomics.Modelfile`: Ollama model definition with 32k context, temperature 0.2, and scientific system prompt.
  - `genomic_discovery_sprint`: 4-stage autonomous Swarm sprint in `swarm_coordinator.py`.
- **Layer 4: AI Dataset Synthesis & LoRA Training (`scripts/` & `llm_training_data/`)**:
  - `train_bioinformatics_corpus.py`: Generates instruction-tuning dataset pairs into `bioinformatics_instruction_dataset.jsonl`.
  - `train_stehouwer_genomics_lora.py`: Formatted for NVIDIA RTX 4090 24GB Unsloth LoRA fine-tuning and GGUF export.
- **Layer 5: Presentation & Multi-Mirror Studio UI (`frontend/src/`)**:
  - `GenomicsStudioTab.jsx`: 4-panel interactive workspace mounted in `App.jsx`, `navigationConfig.js`, and `accessControl.js`.
  - 4-Mirror Parity: Enforced across 447 component files with 100% SHA-256 byte parity.
  - Ecosystem Version: Bumped to `v5.311.0` across all 9 ledgers.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | biorxiv_literature | bioRxiv literature search and summary extraction | M1 | ORIGINAL_REQUEST R1 |
| 2 | alphafold_structures | AlphaFold 3D structure prediction metrics (pLDDT curves, domain boundaries) | M1 | ORIGINAL_REQUEST R1 |
| 3 | string_interactions | STRING database protein-protein interaction networks and enrichments | M1 | ORIGINAL_REQUEST R1 |
| 4 | pymol_synthesizer | Headless PyMOL script synthesizer and command dispatcher | M1 | ORIGINAL_REQUEST R1 |
| 5 | foldseek_search | Foldseek 3D structural homology search against afdb50 and pdb100 | M1 | Operator Directive |
| 6 | dbsnp_variants | dbSNP short genetic variant & rsID lookup with clinical annotations | M1 | ORIGINAL_REQUEST R1 |
| 7 | gtex_expression | GTEx tissue-specific RNA quantitative expression across 54 human tissues | M1 | ORIGINAL_REQUEST R1 |
| 8 | jaspar_motifs | JASPAR transcription factor binding profiles and PWMs | M1 | ORIGINAL_REQUEST R1 |
| 9 | encode_ccres | ENCODE Registry of cis-Regulatory Elements (cCREs) | M1 | ORIGINAL_REQUEST R1 |
| 10 | alphagenome_avi | AlphaGenome Variant Impact (AVI) scoring and regulatory prediction | M1 | ORIGINAL_REQUEST R1 |
| 11 | ucsc_conservation | UCSC Genome Browser evolutionary conservation (phyloP/phastCons) and TFBS | M1 | ORIGINAL_REQUEST R1 |
| 12 | sqlite_caching | SQLite caching in saved_data/bioinformatics_cache.db for zero-cost offline resilience | M1 | ORIGINAL_REQUEST R1 |
| 13 | fastapi_router | FastAPI REST router mounted at /api/v1/bioinformatics in AI_BS_Backend.py | M2 | ORIGINAL_REQUEST R2 |
| 14 | moe_7th_domain | SpecialistDomain.BIOINFORMATICS and SPECIALIST_MATRIX expansion | M3 | ORIGINAL_REQUEST R3 |
| 15 | modelfile_genomics | backend/models/stehouwer_genomics.Modelfile with scientific prompt & tuning | M3 | ORIGINAL_REQUEST R3 |
| 16 | genomic_swarm_sprint | 1-click Swarm preset genomic_discovery_sprint in swarm_coordinator.py | M3 | ORIGINAL_REQUEST R3 |
| 17 | dataset_synthesizer | scripts/train_bioinformatics_corpus.py generating JSONL dataset | M4 | ORIGINAL_REQUEST R4 |
| 18 | unsloth_lora_pipeline | scripts/train_stehouwer_genomics_lora.py for RTX 4090 24GB Unsloth LoRA fine-tuning | M4 | ORIGINAL_REQUEST R4 |
| 19 | genomics_studio_ui | frontend/src/components/GenomicsStudioTab.jsx with 4 interactive panels | M5 | ORIGINAL_REQUEST R5 |
| 20 | app_navigation_mount | Mount genomics_studio in App.jsx, navigationConfig.js, accessControl.js | M5 | ORIGINAL_REQUEST R5 |
| 21 | mirror_parity_sync | 100% SHA-256 byte parity verified across all 4 frontend mirrors (447/447 files) | M5 | ORIGINAL_REQUEST R5 |
| 22 | version_ledgers_bump | Version bump to v5.311.0 across ecosystem ledgers & desktop shortcuts | M5 | ORIGINAL_REQUEST R5 |
| 23 | e2e_acceptance_suite | Pytest test suite verifying adapters, MoE, and dataset generation (100% green) | M6 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Core Bioinformatics Service | `backend/core/bioinformatics_service.py`, SQLite caching in `saved_data/bioinformatics_cache.db` | none | PLANNED |
| 2 | M2: FastAPI REST Router | `backend/routers/bioinformatics_router.py`, mounting in `backend/AI_BS_Backend.py` | M1 | PLANNED |
| 3 | M3: MoE 7th Domain & Swarm Pipeline | `moe_specialist_router.py`, `stehouwer_genomics.Modelfile`, `swarm_coordinator.py` | none | PLANNED |
| 4 | M4: Training Synthesizer & LoRA Pipeline | `scripts/train_bioinformatics_corpus.py`, `scripts/train_stehouwer_genomics_lora.py` | M1 | PLANNED |
| 5 | M5: Dedicated Studio UI & Mirror Parity | `GenomicsStudioTab.jsx`, `App.jsx`, `navigationConfig.js`, `accessControl.js`, parity sync, version bump | M2, M3, M4 | PLANNED |
| 6 | M6: Acceptance Testing & Release Audit | Programmatic test suite verification, clean Vite build, mirror audit, desktop shortcuts | M1, M2, M3, M4, M5 | PLANNED |

## Interface Contracts

### Service ↔ Router (`bioinformatics_service.py` ↔ `bioinformatics_router.py`)
- `BioinformaticsService.search_biorxiv(query: str, limit: int = 10) -> Dict[str, Any]`
- `BioinformaticsService.get_alphafold_metrics(uniprot_id: str) -> Dict[str, Any]`
- `BioinformaticsService.get_string_interactions(identifiers: List[str], species: int = 9606) -> Dict[str, Any]`
- `BioinformaticsService.synthesize_pymol_script(pdb_id: str, representation: str = "cartoon", color_by: str = "chain") -> Dict[str, Any]`
- `BioinformaticsService.search_foldseek_homology(pdb_content: str, database: str = "afdb50") -> Dict[str, Any]`
- `BioinformaticsService.lookup_dbsnp_variant(rsid: str) -> Dict[str, Any]`
- `BioinformaticsService.get_gtex_expression(gencode_id: str) -> Dict[str, Any]`
- `BioinformaticsService.get_jaspar_motif(matrix_id: str) -> Dict[str, Any]`
- `BioinformaticsService.query_encode_ccres(assembly: str = "GRCh38", accession: str = None, coordinates: str = None) -> Dict[str, Any]`
- `BioinformaticsService.score_alphagenome_variant(variant_spdi_or_hgvs: str) -> Dict[str, Any]`
- `BioinformaticsService.get_ucsc_conservation(chrom: str, start: int, end: int, track: str = "phyloP100way") -> Dict[str, Any]`

### MoE Router ↔ Swarm Coordinator (`moe_specialist_router.py` ↔ `swarm_coordinator.py`)
- `SpecialistDomain.BIOINFORMATICS = "bioinformatics"`
- Primary model: `"stehouwer_genomics:latest"`
- Fallback models: `["qwen2.5-coder:latest", "llama3.3:70b"]`
- `moe_router.dispatch(domain_hint="bioinformatics", ...)`

### Frontend ↔ Backend API Gateway
- Endpoints:
  - `GET /api/v1/bioinformatics/literature/biorxiv`
  - `GET /api/v1/bioinformatics/protein/alphafold`
  - `GET /api/v1/bioinformatics/protein/string`
  - `POST /api/v1/bioinformatics/protein/pymol/render`
  - `POST /api/v1/bioinformatics/protein/foldseek`
  - `GET /api/v1/bioinformatics/genomics/dbsnp`
  - `GET /api/v1/bioinformatics/genomics/gtex`
  - `GET /api/v1/bioinformatics/genomics/jaspar`
  - `GET /api/v1/bioinformatics/genomics/encode`
  - `GET /api/v1/bioinformatics/genomics/alphagenome`
  - `GET /api/v1/bioinformatics/genomics/ucsc`
  - `POST /api/v1/bioinformatics/training/dataset/generate`
  - `GET /api/v1/bioinformatics/training/status`

## Code Layout
- Backend Core: `backend/core/bioinformatics_service.py`
- Database Cache: `saved_data/bioinformatics_cache.db`
- Router: `backend/routers/bioinformatics_router.py`
- Backend Server: `backend/AI_BS_Backend.py`
- MoE & Swarms: `backend/core/sovereign_reasoning/moe_specialist_router.py`, `backend/core/sovereign_reasoning/swarm_coordinator.py`, `backend/models/stehouwer_genomics.Modelfile`
- Training Scripts: `scripts/train_bioinformatics_corpus.py`, `scripts/train_stehouwer_genomics_lora.py`
- Frontend Components: `frontend/src/components/GenomicsStudioTab.jsx`
- Frontend Mirror Sync: `scripts/sync_mirrors.py`, `scripts/verify-mirror-parity.ps1`
- Test Suites: `tests/test_bioinformatics_service.py`
