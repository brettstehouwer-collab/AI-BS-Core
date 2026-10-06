## 2026-10-06T05:08:38Z
You are the Project Orchestrator for the AI-BS Sovereign Intelligence Ecosystem.

Your working directory is:
C:\AI-BS\.agents\teamwork\orchestrator_1

The authoritative user request is recorded in:
C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md

Project root directory:
C:\AI-BS

Task Summary:
Integrate a complete life sciences, genomic variant analysis, structural biology, and bioRxiv literature intelligence suite into the AI-BS Sovereign Intelligence Ecosystem with multi-system AI training, 7th MoE specialist domain, autonomous genomic swarm pipeline, and dedicated studio workspace.

Requirements:
- R1: Unified Core Bioinformatics & Structural Intelligence Service (backend/core/bioinformatics_service.py wrapping 10 scientific databases & tools with SQLite caching in saved_data/bioinformatics_cache.db).
- R2: FastAPI REST Router on Port 8080 (backend/routers/bioinformatics_router.py mounted at /api/v1/bioinformatics in backend/AI_BS_Backend.py).
- R3: MoE 7th Domain & Autonomous Genomic Swarm Pipeline (SpecialistDomain.BIOINFORMATICS in moe_specialist_router.py, stehouwer_genomics.Modelfile, genomic_discovery_sprint preset in swarm_coordinator.py).
- R4: AI Training Dataset Synthesizer & Local LoRA Pipeline (scripts/train_bioinformatics_corpus.py, scripts/train_stehouwer_genomics_lora.py).
- R5: Dedicated 'Genomic & Structural Intelligence Studio' UI (GenomicsStudioTab.jsx with 4 interactive panels, mounted in App.jsx, navigationConfig.js, accessControl.js, 100% SHA-256 mirror parity, clean Vite build, bump version to v5.311.0 across ledgers).

Acceptance Criteria:
- Programmatic pytest test suite verifying bioinformatics service adapters, MoE 7th domain routing, and dataset synthesis passing 100% green.
- 100% SHA-256 byte parity verified across all 4 frontend mirrors (447/447 files identical).
- Clean Vite production build with zero errors.
- 100% Zero-cost local execution without external commercial API keys.
- Desktop shortcuts refreshed to v5.311.0.

Please execute the project according to team conventions, decompose tasks to specialists, monitor progress in progress.md and BRIEFING.md, verify all acceptance criteria thoroughly, and report back when finished.

## 2026-10-06T05:13:02Z
Operator directive update received and recorded in ORIGINAL_REQUEST.md:

"Please ensure Foldseek 3D Structural Homology Search (querying AlphaFold DB afdb50/afdb-swissprot and PDB pdb100 from .pdb/.cif files via Foldseek API) is included in Milestone 1 (backend/core/bioinformatics_service.py), Milestone 2 (/api/v1/bioinformatics/protein/foldseek), and Milestone 5 (GenomicsStudioTab.jsx 3D viewer panel)."

Please incorporate this into your project plan, requirements, and milestone execution.
