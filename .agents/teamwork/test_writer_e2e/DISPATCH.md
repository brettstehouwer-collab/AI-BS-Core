# Dispatch: E2E Test Writer

## Identity
- Archetype: teamwork_preview_test_writer
- Working directory: C:\AI-BS\.agents\teamwork\test_writer_e2e
- Parent Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b

## Objective
Author the comprehensive programmatic test suite in `tests/test_bioinformatics_service.py` according to `C:\AI-BS\TEST_INFRA.md`, `C:\AI-BS\PROJECT.md`, and `C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md`.

## Exclusive File Ownership
- `tests/test_bioinformatics_service.py` (DO NOT modify any other files)

## Requirements & Scope
- Implement test cases covering Tier 1 (Feature Coverage), Tier 2 (Boundary & Corner Cases), Tier 3 (Cross-Feature Combinations), and Tier 4 (Real-World Scenarios) as defined in TEST_INFRA.md.
- Cover all 11 capabilities:
  1. bioRxiv literature search and caching
  2. AlphaFold 3D structure prediction metrics (pLDDT curves, domain boundaries)
  3. STRING protein-protein interactions
  4. PyMOL headless script synthesizer
  5. Foldseek 3D structural homology search (afdb50, pdb100)
  6. dbSNP variant & rsID lookup (e.g. rs699)
  7. GTEx tissue-specific RNA expression (54 tissues)
  8. JASPAR transcription factor binding profiles
  9. ENCODE cCREs (e.g. EH38E2941922)
  10. AlphaGenome AVI scoring
  11. UCSC evolutionary conservation (phyloP/phastCons)
  12. SQLite WAL caching in saved_data/bioinformatics_cache.db and offline resilience using saved_data fixtures
- All tests must run 100% locally with zero external commercial API keys, using local mocks, SQLite cache replay, or existing seed fixtures in `saved_data/`.
- Ensure tests verify both synchronous and asynchronous operations cleanly with pytest and pytest-asyncio.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Completion Criteria
- Run `pytest tests/test_bioinformatics_service.py -v` (note: implementation might be in progress so mock or structure cleanly, or test against the service contract).
- Deliver `handoff.md` in your working directory and notify parent.

## 2026-10-06T05:19:48Z
You are the E2E Test Writer.
Your working directory is: C:\AI-BS\.agents\teamwork\test_writer_e2e
Read C:\AI-BS\.agents\teamwork\test_writer_e2e\DISPATCH.md, C:\AI-BS\TEST_INFRA.md, C:\AI-BS\PROJECT.md, and C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md.
Author comprehensive tests in tests/test_bioinformatics_service.py covering Tier 1, Tier 2, Tier 3, and Tier 4 for all 11 bioinformatics tools + SQLite caching + zero-cost local execution resilience.
Exclusive file ownership: tests/test_bioinformatics_service.py.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
When done, deliver handoff.md and send a message to parent da083096-02cf-43b4-b9c6-1900461cac1b.
