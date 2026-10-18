# E2E Test Infra: AI-BS Bioinformatics & Structural Intelligence Suite

## Test Philosophy
- Opaque-box, requirement-driven.
- Zero-cost local execution without external commercial API keys.
- Offline resilience via local SQLite cache and deterministic seed fixtures.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Interactions + Real-World Workloads.

## Feature Inventory & Test Coverage Goals
| # | Feature | Source | Tier 1 (Coverage) | Tier 2 (Boundaries) | Tier 3 (Pairwise) |
|---|---------|--------|:-----------------:|:-------------------:|:-----------------:|
| 1 | bioRxiv literature | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 2 | AlphaFold structure metrics | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 3 | STRING interactions | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 4 | PyMOL script synthesizer | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 5 | Foldseek 3D search | Operator Directive | ≥5 | ≥5 | ✓ |
| 6 | dbSNP variant lookup | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 7 | GTEx RNA expression | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 8 | JASPAR motif profiles | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 9 | ENCODE cCREs | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 10 | AlphaGenome AVI scoring | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 11 | UCSC conservation tracks | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 12 | SQLite cache engine | ORIGINAL_REQUEST §R1 | ≥5 | ≥5 | ✓ |
| 13 | FastAPI REST router | ORIGINAL_REQUEST §R2 | ≥5 | ≥5 | ✓ |
| 14 | MoE 7th domain | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 15 | Genomic Swarm preset | ORIGINAL_REQUEST §R3 | ≥5 | ≥5 | ✓ |
| 16 | Training corpus synthesizer | ORIGINAL_REQUEST §R4 | ≥5 | ≥5 | ✓ |
| 17 | Unsloth LoRA pipeline | ORIGINAL_REQUEST §R4 | ≥5 | ≥5 | ✓ |

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Multi-Omic Oncology Dossier (TP53) | AlphaFold + STRING + PyMOL + Foldseek + bioRxiv | High |
| 2 | Non-Coding Regulatory Variant Analysis (rs699) | dbSNP + GTEx + JASPAR + ENCODE + UCSC + AlphaGenome | High |
| 3 | Autonomous Genomic Sprint Swarm Execution | Swarm Coordinator + MoE 7th domain + 4 stage progression | High |
| 4 | Offline Air-Gapped Query & Cache Replay | SQLite WAL cache + seed fixture recovery + zero-network | Medium |
| 5 | AI Instruction Corpus Generation & LoRA Config Export | Corpus Synthesizer + JSONL validation + LoRA config export | Medium |

## Test Architecture
- Test runner: `pytest tests/test_bioinformatics_service.py tests/test_moe_and_agent_harness.py tests/test_swarm_coordinator.py -v`
- Pass/Fail semantics: 100% green exit code 0.
- Zero external commercial API keys required.
