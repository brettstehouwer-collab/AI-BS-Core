# BRIEFING — 2026-10-06T05:21:00Z

## Mission
Implement backend/core/bioinformatics_service.py and SQLite caching in saved_data/bioinformatics_cache.db wrapping all 11 scientific capabilities (bioRxiv, AlphaFold, STRING, PyMOL, Foldseek, dbSNP, GTEx, JASPAR, ENCODE, AlphaGenome, UCSC) with offline seed fixture fallbacks.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: C:\AI-BS\.agents\teamwork\worker_m1
- Original parent: da083096-02cf-43b4-b9c6-1900461cac1b
- Milestone: M1 (Core Bioinformatics & Structural Intelligence Service)

## 🔒 Key Constraints
- Exclusive file ownership: backend/core/bioinformatics_service.py, saved_data/bioinformatics_cache.db.
- DO NOT modify files outside exclusive ownership.
- MANDATORY INTEGRITY MANDATE: Genuine logic, genuine offline seed fixtures, genuine SQLite caching, real state and real behavior. No dummy/facade implementations.
- SQLite WAL mode caching with zero-cost offline resilience.

## Current Parent
- Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b
- Updated: 2026-10-06T05:21:00Z

## Task Summary
- **What to build**: BioinformaticsService class in backend/core/bioinformatics_service.py wrapping 11 scientific capabilities + SQLite cache manager for saved_data/bioinformatics_cache.db.
- **Success criteria**: All 11 capabilities implemented with async methods, real network requests with timeout/fallback, offline seed fixtures for zero-crash execution, SQLite WAL caching, full test verification.
- **Interface contracts**: C:\AI-BS\PROJECT.md § Interface Contracts (Service ↔ Router).
- **Code layout**: C:\AI-BS\PROJECT.md § Code Layout.

## Key Decisions Made
- Follow asyncio + httpx with graceful sync/offline fallbacks.
- Store cache in saved_data/bioinformatics_cache.db using WAL mode and PRAGMA timeout.
- Provide deterministic offline seed fixture handlers for all 11 capabilities referencing existing files in saved_data/ (e.g., alphafold_p53, rs699.json, encode_test.json) and embedded rich scientific seed fixtures.

## Artifact Index
- C:\AI-BS\backend\core\bioinformatics_service.py — Core service implementation
- C:\AI-BS\saved_data\bioinformatics_cache.db — Local SQLite cache
- C:\AI-BS\.agents\teamwork\worker_m1\handoff.md — Final handoff report
- C:\AI-BS\.agents\teamwork\worker_m1\progress.md — Progress log

## Change Tracker
- **Files modified**: None yet.
- **Build status**: Baseline pytest 36 passed.
- **Pending issues**: None.

## Quality Status
- **Build/test result**: Untested (new service).
- **Lint status**: Clean.
- **Tests added/modified**: Pending tests.

## Loaded Skills
- None explicitly loaded via external dump.
