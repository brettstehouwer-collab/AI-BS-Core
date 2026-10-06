# Dispatch: Survey Explorer 1 (Backend Core & Router Survey)

## Identity
- Archetype: teamwork_preview_explorer
- Working directory: C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1
- Parent Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b

## Objective
Read C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md.
Investigate the existing backend architecture in C:\AI-BS to map the foundational requirements for R1 (Unified Core Bioinformatics & Structural Intelligence Service) and R2 (FastAPI REST Router on Port 8080).

## Scope Boundaries
- Read-only exploration. DO NOT write or modify application code.
- Focus on:
  1. backend/AI_BS_Backend.py: How routers are mounted, middleware, port/startup settings, lifecycle events.
  2. backend/core/: Existing services, patterns for database caching (e.g. SQLite caching in saved_data/), error handling, async vs sync patterns.
  3. backend/routers/: Existing routers structure, dependency injection, Pydantic schemas, response models.
  4. 10 scientific databases & tools specified in R1:
     - bioRxiv
     - AlphaFold (pLDDT curves, domain boundaries)
     - STRING database (protein-protein interactions, enrichments)
     - PyMOL script synthesizer & headless runner
     - dbSNP short genetic variant / rsID lookup
     - GTEx tissue-specific RNA quantitative expression (54 tissues)
     - JASPAR transcription factor binding profiles / PWMs
     - ENCODE Registry of cis-Regulatory Elements (cCREs)
     - AlphaGenome Variant Impact (AVI) scoring & regulatory prediction
     - UCSC Genome Browser evolutionary conservation (phyloP/phastCons) & TFBS
  5. Existing tests in tests/ or pytest setup, mocks, and how backend services are tested.

## Output Requirements
Write your detailed report to C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1\survey_report.py or survey_report.md (prefer markdown: survey_report.md), and write handoff.md in your working directory.
Send a message back to parent when done.


## 2026-10-06T05:13:16Z
**Context**: Milestone 1 & 2 requirements update
**Content**: Operator directive added to ORIGINAL_REQUEST.md: Foldseek 3D Structural Homology Search (querying AlphaFold DB afdb50/afdb-swissprot and PDB pdb100 from .pdb/.cif files via Foldseek API) must be included in Milestone 1 (backend/core/bioinformatics_service.py) and Milestone 2 (/api/v1/bioinformatics/protein/foldseek).
**Action**: Incorporate Foldseek API patterns and requirements into your survey_report.md.
