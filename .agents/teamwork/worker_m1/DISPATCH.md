# Dispatch: Worker M1 (Core Bioinformatics & Structural Intelligence Service)

## Identity
- Archetype: teamwork_preview_worker
- Working directory: C:\AI-BS\.agents\teamwork\worker_m1
- Parent Conversation ID: da083096-02cf-43b4-b9c6-1900461cac1b

## Objective
Implement `backend/core/bioinformatics_service.py` and local SQLite caching in `saved_data/bioinformatics_cache.db` as specified in `C:\AI-BS\PROJECT.md`, `C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md`, and the survey findings in `C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1\survey_report.md`.

## Exclusive File Ownership
- `backend/core/bioinformatics_service.py`
- `saved_data/bioinformatics_cache.db` (auto-created by service)
(DO NOT modify files outside your ownership)

## Implementation Requirements
1. **BioinformaticsService Class**:
   Build a unified service with async methods wrapping:
   - `search_biorxiv(query, limit=10, server="biorxiv")`: Query bioRxiv / medRxiv or fall back to seed/offline cache.
   - `get_alphafold_metrics(uniprot_id)`: Retrieve pLDDT scores, domain boundaries, and CIF/PDB metadata. Leverage local `saved_data/alphafold_p53` fixture for P04637 or offline queries.
   - `get_string_interactions(identifiers, species=9606)`: Protein interaction network nodes and edges.
   - `synthesize_pymol_script(pdb_id_or_path, representation="cartoon", color_by="chain", output_image=None)`: Generate valid headless PyMOL script with OSMesa fallback.
   - `search_foldseek_homology(pdb_content_or_path, database="afdb50")`: Submit Foldseek 3D structural homology search against afdb50 or pdb100 via Foldseek API ticket workflow with local mock/cache fallback.
   - `lookup_dbsnp_variant(rsid)`: Retrieve variant clinical annotations, SPDI, HGVS, and alleles. Leverage `saved_data/rs699.json` for rs699 or offline replay.
   - `get_gtex_expression(gencode_id)`: Median RNA TPM expression across all 54 GTEx human tissues.
   - `get_jaspar_motif(matrix_id)`: Transcription factor binding profile, PWM, consensus sequence.
   - `query_encode_ccres(assembly="GRCh38", accession=None, coordinates=None)`: Candidate cis-regulatory elements. Leverage `saved_data/encode_test.json` for EH38E2941922.
   - `score_alphagenome_variant(variant_spdi_or_hgvs)`: Functional impact AVI score, regulatory impact classification (Promoter, Enhancer, Neutral).
   - `get_ucsc_conservation(chrom, start, end, track="phyloP100way")`: Evolutionary conservation score arrays and mean score.
2. **SQLite Cache & Offline Resilience**:
   - SQLite database path: `C:\AI-BS\saved_data\bioinformatics_cache.db`.
   - Table schema: `bioinformatics_cache(tool TEXT, query_key TEXT, parameters_json TEXT, response_json TEXT, status TEXT, created_at REAL, ttl_seconds INTEGER, PRIMARY KEY (tool, query_key))`.
   - Pragmas: `PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;`, `PRAGMA timeout = 10.0;`.
   - Offline fallback: If any upstream network request fails, times out, or returns non-200, check cache first. If not in cache, fallback to deterministic seed fixtures or offline mock responses so execution NEVER crashes or requires commercial API keys.
3. **Verification**:
   - Verify importing `backend.core.bioinformatics_service.BioinformaticsService`.
   - Verify instantiation and query calls for all 11 tools.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Completion Criteria
- Test service methods directly via python script or pytest.
- Write `handoff.md` with full details in your working directory and message parent.


## 2026-10-06T05:19:48Z
You are Worker M1 (Core Bioinformatics & Structural Intelligence Service).
Your working directory is: C:\AI-BS\.agents\teamwork\worker_m1
Read C:\AI-BS\.agents\teamwork\worker_m1\DISPATCH.md, C:\AI-BS\PROJECT.md, and C:\AI-BS\.agents\teamwork\ORIGINAL_REQUEST.md.
Implement backend/core/bioinformatics_service.py and SQLite caching in saved_data/bioinformatics_cache.db wrapping all 11 scientific capabilities (bioRxiv, AlphaFold, STRING, PyMOL, Foldseek, dbSNP, GTEx, JASPAR, ENCODE, AlphaGenome, UCSC) with offline seed fixture fallbacks.
Exclusive file ownership: backend/core/bioinformatics_service.py, saved_data/bioinformatics_cache.db.
MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Verify your service, write handoff.md, and send a message to parent da083096-02cf-43b4-b9c6-1900461cac1b.
