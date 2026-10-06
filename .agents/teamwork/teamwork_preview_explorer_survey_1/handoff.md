# Handoff Report: Backend Architecture & Bioinformatics Survey

**Agent**: Survey Explorer 1 (`teamwork_preview_explorer_survey_1`)  
**Parent Agent**: `da083096-02cf-43b4-b9c6-1900461cac1b`  
**Working Directory**: `C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1`  
**Milestone Focus**: R1 (Unified Core Bioinformatics & Structural Intelligence Service) and R2 (FastAPI REST Router on Port 8080)  
**Deliverable Document**: `C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1\survey_report.md`

---

## 1. Observation

1. **Backend Server & Lifespan Entry Point**:
   - `backend/AI_BS_Backend.py` (7,570 lines, 316,622 bytes) initializes FastAPI at line 485:
     ```python
     app = FastAPI(title="AI-BS Central Cognitive Engine API", lifespan=lifespan)
     ```
   - Execution occurs at lines 7551–7566:
     ```python
     if __name__ == "__main__":
         ...
         port = int(os.getenv("PORT", "8080"))
         print(f"Starting AI-BS Master Core Engine on Port {port}...")
         uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
     ```
   - The lifespan context manager `@asynccontextmanager async def lifespan(app: FastAPI):` (lines 427–482) handles port pre-flight reclamation (`target_ports=[8080, 8002, 8003, 8004, 8005]`), daemon supervisor startup (`daemon_supervisor.start_all`), background daemons (`daemon_engine.start()`), and periodic telemetry WebSocket broadcasting (`telemetry_broadcast_loop()`).

2. **Middleware Stack**:
   - `SecurityHeadersMiddleware` is registered at line 821.
   - `RateLimiterMiddleware` is registered at line 825.
   - `CORSMiddleware` with `allow_origin_regex=r".*"` and `allow_credentials=True` is registered at line 830.
   - `NetworkTelemetryMiddleware` is registered at line 841.
   - `TenantMiddleware` is registered at line 1124.
   - `HSTSMiddleware` is registered at line 1549.

3. **Router Mounting Pattern**:
   - Routers are loaded using modular try-except import blocks, for example lines 526–531:
     ```python
     try:
         from routers.moe_specialist_router_api import router as moe_specialist_router
         app.include_router(moe_specialist_router)
     except ImportError as e:
         print(f"Warning: Could not load moe_specialist_router: {e}")
     ```
   - The same pattern applies directly to `backend/routers/bioinformatics_router.py`.

4. **Data Layer & SQLite Caching Patterns**:
   - `backend/core/storage_manager.py` defines `UnifiedStorageManager` using thread-safe connection caching:
     ```python
     conn = sqlite3.connect(path, check_same_thread=False)
     conn.execute("PRAGMA journal_mode = WAL;")
     conn.execute("PRAGMA synchronous = NORMAL;")
     conn.execute("PRAGMA mmap_size = 268435456;") # 256MB mmap
     conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
     ```
   - Local storage directory is `C:\AI-BS\saved_data\`. Existing files in `saved_data/` include:
     * `saved_data/alphafold_p53/`: `AF-P04637-F1-metadata.json`, `AF-P04637-F1-model_v6.cif`, `AF-P04637-F1-predicted_aligned_error_v6.json`.
     * `saved_data/rs699.json`: dbSNP reference variant with SPDI and HGVS coordinates.
     * `saved_data/encode_test.json`: ENCODE candidate cis-regulatory element response for EH38E2941922.

5. **10 Required Scientific Databases/Tools + Operator Foldseek Directive**:
   - bioRxiv / medRxiv: REST API `https://api.biorxiv.org/details/{server}/{doi}`.
   - AlphaFold DB: REST API `https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}`.
   - STRING DB: REST API `https://string-db.org/api/json/network`.
   - Headless PyMOL: Script generator utilizing `cmd.load`, `cmd.spectrum`, and `cmd.png(..., ray=0)` with OSMesa software rendering (`PYOPENGL_PLATFORM=osmesa`).
   - dbSNP: NCBI Variation API `https://api.ncbi.nlm.nih.gov/variation/v0/beta/refsnp/{rsid}`.
   - GTEx: GTEx Portal API v2 `https://gtexportal.org/api/v2/expression/medianGeneExpression?gencodeId={gencode_id}`.
   - JASPAR: REST API `https://jaspar.elixir.no/api/v1/matrix/` and `/matrix/{matrix_id}/`.
   - ENCODE: SCREEN GraphQL API `https://api.screen.encodeproject.org/graphql`.
   - AlphaGenome: AVI impact scoring on 1-based `chr:pos:ref>alt` variant notation.
   - UCSC Genome Browser: REST API `https://api.genome.ucsc.edu/getData/track`.
   - Foldseek (Operator Directive): Web API ticket dispatch to `https://search.foldseek.com/api/ticket` against `afdb50` and `pdb100`.

6. **Cross-Cutting Systems (R3, R4, R5)**:
   - `backend/core/sovereign_reasoning/moe_specialist_router.py` defines `SpecialistDomain` (currently 6 domains: `code`, `creative`, `function_calling`, `vision`, `reasoning`, `embedding`) and `SPECIALIST_MATRIX`.
   - `backend/core/sovereign_reasoning/swarm_coordinator.py` defines `SWARM_PRESETS` and uses `agent_harness_sessions.db`.
   - `scripts/train_stehouwer_lora_unsloth.py` provides the exact architecture for RTX 4090 24GB Unsloth LoRA fine-tuning.
   - `scripts/sync_mirrors.py` enforces 100% SHA-256 byte parity across 4 frontend mirrors.
   - `version.txt` currently reads `v5.310.0`.

7. **Test Baseline Execution**:
   - Command: `pytest tests/ -v`
   - Result: `36 passed, 2 warnings in 27.84s`. 100% pass rate on existing codebase.

---

## 2. Logic Chain

1. **Mounting Point (R2 -> Backend)**:
   - Observation 1 and 3 establish that routers are mounted in `backend/AI_BS_Backend.py` via `app.include_router(router)`.
   - Observation 3 shows the convention of importing the router under `try-except ImportError`.
   - Therefore, `backend/routers/bioinformatics_router.py` must define `router = APIRouter(prefix="/api/v1/bioinformatics", tags=["Bioinformatics & Structural Intelligence"])` and be mounted in `AI_BS_Backend.py` at line ~545 (or adjacent router import section).

2. **Core Service & Offline Resilience (R1 -> Core)**:
   - Requirement R1 mandates `backend/core/bioinformatics_service.py` wrapping all tools with local SQLite caching in `saved_data/bioinformatics_cache.db`.
   - Observation 4 demonstrates that SQLite WAL mode (`PRAGMA journal_mode = WAL`) and `timeout=10.0` is the standard across `backend/core/storage_manager.py` and other services to prevent write locks during concurrent FastAPI requests.
   - Observation 4 also shows that seed fixtures already exist in `saved_data/` for AlphaFold (`alphafold_p53`), dbSNP (`rs699.json`), and ENCODE (`encode_test.json`).
   - Therefore, `bioinformatics_service.py` should implement a query cache table `bioinformatics_cache(tool, query_key, parameters_json, response_json, status, created_at, ttl_seconds)` and fallback to seed/mock data when network requests fail or offline mode is engaged.

3. **API Contract Compatibility (R2 -> Frontend R5)**:
   - Observation 5 maps the input and output requirements for all 10 tools + Foldseek.
   - Observation 6 outlines that Frontend R5 (`GenomicsStudioTab.jsx`) requires 4 distinct panels corresponding to:
     1. Genomic Variant & Expression Explorer (`/genomics/*`)
     2. Structural Biology & AlphaFold Viewer (`/protein/*`)
     3. bioRxiv & Regulatory Literature Recon (`/literature/*`, `/genomics/jaspar`, `/genomics/encode`)
     4. Autonomous Swarm & AI Training Monitor (`/training/*`, Swarm presets)
   - Therefore, grouping endpoints under `/literature/`, `/protein/`, `/genomics/`, and `/training/` satisfies both R2 and R5 seamlessly.

4. **Testability & Non-Regression**:
   - Observation 7 proves the test suite is 100% green.
   - Therefore, new tests for R1 and R2 can be safely isolated in `tests/test_bioinformatics_service.py` and run alongside existing tests without regressions.

---

## 3. Caveats

1. **External API Network Availability**: Public life sciences APIs (EBI AlphaFold, NCBI, STRING, Foldseek, UCSC, GTEx) are subject to intermittent network latency or rate-limiting. The local SQLite caching mechanism in `saved_data/bioinformatics_cache.db` and seed fixtures are essential for zero-cost local execution and automated CI/CD testing without network calls.
2. **PyMOL Host Binary**: Headless PyMOL rendering can run via `pymol-open-source-whl` using OSMesa software rendering on systems with or without a dedicated X-server/display. If PyMOL is not installed on a specific test node, the script synthesizer must still produce valid Python scripts and return deterministic mock rendering status.
3. **MoE Model Presence**: In local development environments where Ollama does not have `stehouwer_genomics:latest` pre-pulled, fallback routing to `qwen2.5-coder:latest` or `llama3.3:70b` ensures uninterrupted functionality.

---

## 4. Conclusion

1. **Foundational Architecture Mapped**: The backend architecture in `AI_BS_Backend.py`, `backend/core/`, and `backend/routers/` is completely analyzed and ready for Milestone 1 (Core Service) and Milestone 2 (Router).
2. **Schema & Caching Ready**: A high-performance SQLite caching schema with WAL mode is designed for `saved_data/bioinformatics_cache.db`, utilizing existing local seed fixtures for offline reliability.
3. **11 Capabilities Specified**: Exact endpoint structures, parameters, data models, and upstream APIs are documented for bioRxiv, AlphaFold, STRING, PyMOL, Foldseek, dbSNP, GTEx, JASPAR, ENCODE, AlphaGenome, and UCSC.
4. **Test Suite Baseline Clear**: Existing test suite passes 36/36 tests in 27.84s. The testing strategy for `tests/test_bioinformatics_service.py` is established.

The full survey report is available at:  
`C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1\survey_report.md`

---

## 5. Verification Method

To verify the findings of this survey:
1. **Inspect Survey Report**:
   ```powershell
   Get-Content C:\AI-BS\.agents\teamwork\teamwork_preview_explorer_survey_1\survey_report.md
   ```
2. **Verify Baseline Pytest Suite**:
   ```powershell
   pytest tests/ -v
   ```
   *Expected result*: 36 passed in ~28s.
3. **Verify Existing Seed Fixtures**:
   ```powershell
   Test-Path C:\AI-BS\saved_data\alphafold_p53\AF-P04637-F1-metadata.json
   Test-Path C:\AI-BS\saved_data\rs699.json
   Test-Path C:\AI-BS\saved_data\encode_test.json
   ```
   *Expected result*: True for all three paths.
4. **Invalidation Conditions**:
   - If `AI_BS_Backend.py` port or lifespan structure changes.
   - If `saved_data/` directory is moved or permissions are modified.
