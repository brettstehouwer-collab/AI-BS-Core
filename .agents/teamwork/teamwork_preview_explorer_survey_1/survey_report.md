# Backend Architecture & Bioinformatics Intelligence Survey Report

**Author**: Survey Explorer 1  
**Timestamp**: 2026-10-06T05:15:00Z  
**Ecosystem**: AI-BS Sovereign Intelligence Ecosystem  
**Target Milestone Scope**: R1 (Unified Core Bioinformatics & Structural Intelligence Service), R2 (FastAPI REST Router on Port 8080), and foundational mapping for R3, R4, R5.

---

## 1. Executive Summary

This survey report provides the architectural foundation and implementation specifications for integrating the complete Life Sciences, Genomic Variant Analysis, Structural Biology, and bioRxiv Literature Intelligence suite into the AI-BS Sovereign Intelligence Ecosystem.

The investigation examined:
1. `backend/AI_BS_Backend.py`: Lifespan hooks, middleware stack, router mounting, port 8080 configuration.
2. `backend/core/`: Service instantiation patterns, local SQLite storage managers, WAL mode caching, and offline resilience strategies.
3. `backend/routers/`: Existing router patterns, Pydantic schemas, dependency injection, and uniform JSON response contracts.
4. The **10 bioinformatics capabilities** required in R1 + the **Foldseek 3D structural homology search** added via operator directive.
5. The existing test suite in `tests/` and the `pytest` runner environment (36/36 passing baseline).
6. Cross-cutting touchpoints for R3 (MoE 7th Domain & Swarm Sprint), R4 (LoRA training & dataset synthesis), and R5 (Genomics Studio Tab & 4-mirror byte parity).

---

## 2. Backend Architecture Survey (`backend/AI_BS_Backend.py`)

### 2.1 Server Entry Point & Port Configuration
- **File**: `C:\AI-BS\backend\AI_BS_Backend.py` (7,570 lines, ~316 KB).
- **Execution**: Run via `uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")` in lines 7551–7566.
- **Port**: Default is `8080` (configurable via `--port` argument or `PORT` environment variable).
- **Silent Subprocess Shim**: Lines 9–34 wrap `subprocess.run`, `subprocess.Popen`, and `subprocess.check_output` with `creationflags=subprocess.CREATE_NO_WINDOW` on Windows to suppress console popups.
- **Recursion & DLLs**: Recursion limit set to 5000 (line 43); CUDA/cuDNN DLL paths injected into `os.environ["PATH"]` and `os.add_dll_directory` (lines 45–54).

### 2.2 Lifespan Management (`lifespan`)
- Defined at lines 427–482 using `@asynccontextmanager async def lifespan(app: FastAPI):`.
- **Startup sequence**:
  1. `daemon_supervisor.start_all(target_ports=[8080, 8002, 8003, 8004, 8005])`: pre-flight port reclamation and supervised daemon startup.
  2. Auto-resume interrupted Screenplay adaptations.
  3. `asyncio.create_task(daemon_engine.start())`: background memory, heuristics, wallet, and vault daemons.
  4. `asyncio.create_task(telemetry_broadcast_loop())`: 2-second heartbeat loop over `telemetry_hub` WebSockets.
  5. `sentinel_engine.start()`: Autonomous Sentinel Engine.
- **Shutdown sequence**:
  1. `sentinel_engine.stop()`.
  2. `daemon_engine.stop()`.
  3. `daemon_supervisor.stop_all()`.

### 2.3 Middleware Stack
The middlewares are applied to `app` in order:
1. `SecurityHeadersMiddleware` (line 811): OWASP defensive headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `X-XSS-Protection`).
2. `RateLimiterMiddleware` (line 825): Rate limiting per IP/tenant.
3. `CORSMiddleware` (lines 830–836 & 1528–1534): `allow_origin_regex=r".*"`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.
4. `NetworkTelemetryMiddleware` (line 841): Packet analysis and latency telemetry engine.
5. `TenantMiddleware` (line 1124): Multi-tenant identification and tenant context propagation.
6. `HSTSMiddleware` (line 1549): `Strict-Transport-Security` enforcement.

### 2.4 Router Mounting Pattern
Routers in `AI_BS_Backend.py` are loaded using protected `try-except ImportError` blocks to ensure high system fault tolerance:
```python
try:
    from routers.bioinformatics_router import router as bioinformatics_router
    app.include_router(bioinformatics_router)
except ImportError as e:
    print(f"Warning: Could not load bioinformatics_router: {e}")
```
Existing routers in `AI_BS_Backend.py` include:
- `hybrid_reasoning_engine.router` (line 516)
- `gpu_telemetry_router` (line 522)
- `moe_specialist_router` (line 528)
- `agent_harness_router` (line 534)
- `wan_media_router` (line 540)
- `chef_orders_router` (line 611)
- `media_render_router` (line 659)
- `executive_cockpit_router` (line 665)
- `ecosystem_telemetry_router` (line 713)

---

## 3. Core Services & Data Layer Survey (`backend/core/` & `saved_data/`)

### 3.1 Service Architecture Pattern
Core services in `backend/core/` follow distinct high-performance patterns:
1. **Singleton Instances**: E.g. `hot_cache` in `hot_cache.py`, `moe_router` in `sovereign_reasoning/moe_specialist_router.py`, `swarm_coordinator` in `sovereign_reasoning/swarm_coordinator.py`.
2. **Path Discovery**:
   ```python
   _backend_dir = Path(__file__).resolve().parent.parent
   _root_dir = _backend_dir.parent  # C:\AI-BS
   DATA_DIR = _root_dir / "saved_data"
   ```
3. **Thread-Safe SQLite Management**: E.g. `storage_manager.py` (`UnifiedStorageManager`) uses:
   - `sqlite3.connect(path, check_same_thread=False, timeout=10.0)`
   - `PRAGMA journal_mode = WAL;` (Write-Ahead Logging for non-blocking concurrent reads and writes)
   - `PRAGMA synchronous = NORMAL;`
   - `PRAGMA mmap_size = 268435456;` (256 MB memory-mapped I/O)
   - `PRAGMA cache_size = -64000;` (64 MB page cache)

### 3.2 Database Caching Specification for `saved_data/bioinformatics_cache.db`
Requirement R1 mandates:
> "All queries must support local SQLite caching in saved_data/bioinformatics_cache.db for offline resilience."

#### Schema Design:
```sql
CREATE TABLE IF NOT EXISTS bioinformatics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,                -- e.g. 'biorxiv', 'alphafold', 'string', 'dbsnp', 'gtex', 'jaspar', 'encode', 'alphagenome', 'ucsc', 'foldseek', 'pymol'
    query_key TEXT NOT NULL,           -- normalized query key (e.g. 'rs699', 'P04637', 'TNF', 'MA0488.2', 'chr11:5291251-5291587')
    parameters_json TEXT,              -- full serialized arguments
    response_json TEXT NOT NULL,       -- complete parsed response payload
    status TEXT NOT NULL DEFAULT 'OK', -- 'OK', 'ERROR', 'CACHED'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ttl_seconds INTEGER DEFAULT 604800, -- default 7-day TTL
    UNIQUE(tool, query_key)
);

CREATE INDEX IF NOT EXISTS idx_bioinfo_cache_lookup ON bioinformatics_cache(tool, query_key);
```

#### Cache Read/Write Flow:
1. Normalize query parameters into a deterministic `query_key` (e.g. lowercase, trimmed).
2. Check `bioinformatics_cache` table for matching `tool` and `query_key`.
3. If entry exists and has not expired: return cached JSON with `"cached": True, "source": "cache"`.
4. If not in cache (or offline):
   - In online mode: make HTTP request via `httpx` or `requests` with a 15–30s timeout.
   - If successful: persist to `bioinformatics_cache` and return with `"cached": False, "source": "live"`.
   - If network request fails or times out: fall back to local seed fixtures in `saved_data/` or generated deterministic offline mock payload with `"cached": True, "source": "offline_fallback"`.

### 3.3 Existing Local Seed Fixtures in `saved_data/`
Inspection of `C:\AI-BS\saved_data\` revealed existing pre-seeded scientific data files:
- `saved_data/alphafold_p53/`:
  * `AF-P04637-F1-metadata.json` (2.7 KB, pLDDT scores, global confidence metrics)
  * `AF-P04637-F1-model_v6.cif` (363 KB, full mmCIF coordinates)
  * `AF-P04637-F1-predicted_aligned_error_v6.json` (422 KB, PAE matrix)
- `saved_data/rs699.json`: dbSNP reference variant payload for rs699 (AGT gene, 1378 bytes) with SPDI and HGVS coordinates.
- `saved_data/encode_test.json`: ENCODE candidate cis-regulatory element response for EH38E2941922 (pELS, chr11:5291251-5291587, 887 KB).
- `saved_data/clinvar_test.json` & `clinvar_summary_test.json`: Variant pathogenicity annotations.
- `saved_data/trials_test.json`: Clinical trials records.

These files serve as offline baseline fixtures for the service.

---

## 4. FastAPI Router Design Survey (`backend/routers/` & R2)

### 4.1 Router Specification
- **File**: `backend/routers/bioinformatics_router.py`
- **Prefix**: `/api/v1/bioinformatics`
- **Tags**: `["Bioinformatics & Structural Intelligence"]`
- **Mount Point**: Mount in `backend/AI_BS_Backend.py` via `app.include_router(bioinformatics_router)`.

### 4.2 Uniform Response Envelope
All router endpoints should conform to the AI-BS ecosystem's uniform API envelope:
```json
{
  "status": "success",
  "tool": "alphafold",
  "query": "P04637",
  "cached": true,
  "source": "cache",
  "timestamp": "2026-10-06T05:15:00Z",
  "data": { ... }
}
```
Errors return HTTP 400/404/500 with:
```json
{
  "status": "error",
  "tool": "alphafold",
  "error": "UniProt ID not found or invalid format",
  "fallback_available": false
}
```

### 4.3 Endpoint Mapping Matrix

| Route | Method | Purpose | Input Parameters / Body | Response Fields |
|---|---|---|---|---|
| `/literature/biorxiv` | GET, POST | bioRxiv/medRxiv search & metadata | `query`: str, `doi`: Optional[str], `server`: "biorxiv"\|"medrxiv", `start_date`, `end_date`, `category`, `limit`: int | `papers`: List[PaperSummary], `total_count`: int |
| `/protein/alphafold` | GET, POST | 3D structure predictions, pLDDT & PAE | `uniprot_id`: str (e.g. "P04637"), `include_pae`: bool | `uniprot_id`, `plddt_summary` (mean, min, max, category), `domains`: List[DomainBoundary], `cif_url`, `pae_url` |
| `/protein/string` | GET, POST | PPI networks & functional enrichments | `identifiers`: List[str] (e.g. ["TP53", "MDM2"]), `species`: int (9606), `required_score`: int (400), `add_nodes`: int | `interactions`: List[PPI], `enrichment`: List[Term], `network_image_url`: Optional[str] |
| `/protein/pymol/render` | POST | Headless PyMOL script synthesis & dispatch | `structure_path`: str, `representation`: "cartoon"\|"surface"\|"spheres", `color_by`: "plddt"\|"chain"\|"spectrum", `highlight_residues`: List[str], `output_name`: str | `script_content`: str, `pse_path`: str, `png_path`: str, `atom_count`: int, `render_status`: str |
| `/protein/foldseek` | POST | 3D structural homology search | `file_path`: str (.pdb or .cif), `databases`: List[str] (["pdb100", "afdb50"]), `mode`: str ("3diaa") | `ticket_id`: str, `status`: "COMPLETE", `hits`: List[StructuralHit] (target, prob, q_cov, e_value) |
| `/genomics/dbsnp` | GET, POST | rsID lookup & SPDI/HGVS resolution | `rsid`: Optional[str] (e.g. "rs699"), `chrom`, `pos`, `ref`, `alt` | `rsid`, `gene_associations`, `clinical_significance`, `spdi`, `hgvs`, `alleles` |
| `/genomics/gtex` | GET, POST | Quantitative RNA expression (54 tissues) | `gene`: str (e.g. "TNF" or "ENSG00000232810"), `dataset`: str | `gene_symbol`, `gencode_id`, `tissue_expressions`: List[{tissue, median_tpm}], `top_tissues`: List[str] |
| `/genomics/jaspar` | GET, POST | TF binding profiles & PWM matrices | `tf_name`: Optional[str] (e.g. "JUN"), `matrix_id`: Optional[str] (e.g. "MA0488.2"), `tax_id`: int (9606) | `matrix_id`, `name`, `tf_family`, `pwm`: List[List[float]], `consensus_sequence`: str |
| `/genomics/encode` | GET, POST | Candidate cis-regulatory elements (cCREs) | `chrom`: str (e.g. "chr11"), `start`: int, `end`: int, `accession`: Optional[str] | `ccres`: List[{accession, group, coordinates, z_scores, biosamples}] |
| `/genomics/alphagenome` | GET, POST | AlphaGenome Variant Impact (AVI) scoring | `variant`: str (e.g. "chr9:128225994:G>A"), `include_track_info`: bool | `variant`, `avi_score`, `impact_category`, `feature_attributions`: Dict[str, float] |
| `/genomics/ucsc` | GET, POST | Conservation (phyloP/phastCons) & TFBS | `chrom`: str, `start`: int, `end`: int, `genome`: str ("hg38"), `track`: str | `chrom`, `start`, `end`, `phylop_score`: float, `phastcons_score`: float, `tfbs_peaks`: List[dict] |
| `/training/dataset/generate` | POST | Trigger instruction-tuning dataset synthesis | `output_file`: Optional[str], `sample_limit`: Optional[int] | `status`: "success", `output_file`: str, `records_generated`: int, `bytes_written`: int |
| `/training/status` | GET | Query dataset & LoRA training state | None | `dataset_ready`: bool, `dataset_records`: int, `lora_config_ready`: bool, `target_device`: "RTX 4090", `vram_allocated_gb`: float |

---

## 5. Detailed Survey of the 11 Bioinformatics Capabilities

### 5.1 bioRxiv Literature Search
- **Upstream Source**: bioRxiv / medRxiv API (`https://api.biorxiv.org/details/{server}/{doi}` or `https://api.biorxiv.org/details/{server}/{start_date}/{end_date}/{cursor}`).
- **Key Characteristics**:
  * Free public REST API.
  * Server-side keyword search is not supported by upstream API; keyword matching is performed via local title/abstract token filtering.
  * Returns: DOI, title, authors, date, version, category, abstract, server (`biorxiv` or `medrxiv`).
- **Caching**: Cache by query hash, DOI, or date-interval string.
- **Offline Fallback**: Pre-indexed local bibliography of life sciences papers.

### 5.2 AlphaFold 3D Structural Predictions & Metrics
- **Upstream Source**: AlphaFold Protein Structure Database REST API (`https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}`).
- **Key Metrics**:
  * pLDDT score curve per residue (0–100 scale):
    - Very high confidence: pLDDT > 90
    - High confidence: 70 < pLDDT <= 90
    - Low confidence: 50 < pLDDT <= 70
    - Very low confidence (intrinsically disordered): pLDDT < 50
  * PAE (Predicted Aligned Error) matrix for rigid domain boundary identification.
- **Local Seed Data**: `saved_data/alphafold_p53` already contains full data for UniProt `P04637` (human p53).
- **Caching**: Store parsed pLDDT curves and domain spans keyed by UniProt ID.

### 5.3 STRING Protein-Protein Interaction (PPI) Networks
- **Upstream Source**: STRING DB API v12 (`https://string-db.org/api/json/network` and `https://string-db.org/api/json/enrichment`).
- **Parameters**: `identifiers`, `species` (9606 for Homo sapiens), `required_score` (0–1000 threshold), `network_type` (`functional` or `physical`).
- **Data Extracted**: Interacting nodes, combined score, evidence sub-scores (`escore` experimental, `dscore` database, `tscore` textmining, `ascore` coexpression), and functional GO/KEGG enrichments.
- **Caching**: Keyed by sorted protein tuple and species ID.

### 5.4 PyMOL Headless Script Synthesizer & Dispatcher
- **Execution Mechanism**:
  * Synthesizes Python/PyMOL automation scripts that execute headlessly via OSMesa (`PYOPENGL_PLATFORM=osmesa`) or command line.
  * Uses `cmd.load(structure_path)`, sets cartoon/surface display, applies B-factor/pLDDT color ramps:
    ```python
    cmd.spectrum("b", "blue_white_red", "all", minimum=50, maximum=90)
    ```
  * Exports high-resolution PNG via `cmd.png(output_png, width=1920, height=1080, ray=0)` and `.pse` PyMOL session file.
  * Always issues `cmd.quit()` at script termination to prevent hanging processes.
- **Command Dispatcher**: Executes script via `python` or `uv run`, capturing stdout, stderr, and generated image paths.

### 5.5 Foldseek 3D Structural Homology Search (Operator Directive)
- **Upstream Source**: Foldseek Web API (`https://search.foldseek.com/api/ticket`).
- **Workflow**:
  1. POST multipart payload with `mode="3diaa"`, `database[]=["pdb100", "afdb50"]`, and binary PDB/mmCIF coordinates to `/api/ticket`.
  2. Receives `ticket_id`.
  3. Polls `/api/ticket/{ticket_id}` until `status == "COMPLETE"`.
  4. Downloads result table from `/api/result/download/{ticket_id}`.
- **Result Schema**: Target ID, alignment probability (0.0–1.0), query coverage, E-value, sequence identity, target description.
- **Offline Fallback**: Returns cached structural alignments for standard control proteins (e.g. p53, hemoglobin, kinase domains).

### 5.6 dbSNP Variant & rsID Lookup
- **Upstream Source**: NCBI SNP API (`https://api.ncbi.nlm.nih.gov/variation/v0/beta/refsnp/{rsid}`).
- **Data Extracted**: Canonical rsID, chromosome placement, GRCh38 genomic coordinates, alleles (ref/alt), SPDI representation, HGVS notation, clinical significance (e.g., pathogenic, benign), and minor allele frequency (MAF).
- **Local Seed Data**: `saved_data/rs699.json` provides ground-truth AGT variant structure.

### 5.7 GTEx Quantitative RNA Expression
- **Upstream Source**: GTEx Portal API v2 (`https://gtexportal.org/api/v2/expression/medianGeneExpression?gencodeId={gencode_id}`).
- **Scope**: Baseline median RNA expression (in TPM) across all 54 non-diseased human tissue sites (Adipose, Brain cortex, Heart, Liver, Lung, Muscle, Whole Blood, etc.).
- **ID Resolution**: Converts common gene symbols (e.g. `TNF`, `TP53`, `BRCA1`) to GENCODE IDs (`ENSG...`).
- **Data Schema**: Array of `{tissueSiteDetailId, median, unit: "TPM"}`.

### 5.8 JASPAR Transcription Factor Binding Profiles
- **Upstream Source**: JASPAR REST API (`https://jaspar.elixir.no/api/v1/matrix/` and `/api/v1/matrix/{matrix_id}/`).
- **Parameters**: `name` (e.g. "CTCF", "JUN", "TP53"), `tax_id` (9606).
- **Data Extracted**: JASPAR Matrix ID (e.g. `MA0488.2`), TF class and family, Position Frequency Matrix (PFM), Position Weight Matrix (PWM), and IUPAC consensus sequence.

### 5.9 ENCODE Registry of cis-Regulatory Elements (cCREs)
- **Upstream Source**: SCREEN GraphQL API (`https://api.screen.encodeproject.org/graphql`) and ENCODE Portal REST API.
- **Classes of Elements**:
  * `PLS`: Promoter-like signature (high DNase and H3K4me3)
  * `pELS`: Proximal enhancer-like signature (high DNase and H3K27ac within 2kb of TSS)
  * `dELS`: Distal enhancer-like signature (high DNase and H3K27ac >2kb from TSS)
  * `CTCF-only`: Insulator elements
- **Local Seed Data**: `saved_data/encode_test.json` (887 KB) contains complete cCRE entries and cell-line biosample Z-scores for chr11.

### 5.10 AlphaGenome Variant Impact (AVI) Scoring
- **Upstream Source / Model Interface**: AlphaGenome Atlas API / AVI evaluation module.
- **Input**: 1-based `chr:pos:ref>alt` variant string (e.g. `chr9:128225994:G>A`).
- **Metrics**:
  * Unified AVI score (0.0 to 1.0 impact index).
  * 18 biological feature attribution channels (RNA-seq expression shift, splicing disruption, chromatin accessibility / DNASE, histone modifications H3K27ac/H3K4me3, and TF binding affinity changes).
  * Safety disclaimer: Research use only (strict molecular/functional framing, non-clinical).

### 5.11 UCSC Genome Browser Conservation & TFBS
- **Upstream Source**: UCSC Genome Browser API (`https://api.genome.ucsc.edu/getData/track?genome=hg38;track={track};chrom={chrom};start={start};end={end}`).
- **Metrics**:
  * `phyloP`: Per-base evolutionary constraint score (positive = conservation, negative = acceleration).
  * `phastCons`: Multi-species alignment block posterior probabilities of conservation (0.0 to 1.0).
  * TFBS conserved regulatory tracks from ENCODE/JASPAR/ReMap.

---

## 6. Cross-Cutting System Integrations (R3, R4, R5)

### 6.1 R3. MoE 7th Domain & Autonomous Genomic Swarm Pipeline
- **File**: `backend/core/sovereign_reasoning/moe_specialist_router.py`
  * Add `BIOINFORMATICS = "bioinformatics"` to `SpecialistDomain` enum (line 38).
  * Add `"bioinformatics"` entry to `SPECIALIST_MATRIX`:
    - `primary`: `"stehouwer_genomics:latest"`
    - `fallback`: `"qwen2.5-coder:latest"`
    - `secondary_fallback`: `"llama3.3:70b"`
    - `description`: `"Genomic variant interpretation, AlphaFold structural biology, protein interaction networks, and bioRxiv literature synthesis."`
    - `context_window`: `65536`
    - `keywords`: `["genomics", "variant", "mutation", "protein", "alphafold", "structure", "dbsnp", "gtex", "encode", "jaspar", "biorxiv", "dna", "rna", "amino acid", "plddt", "foldseek"]`
- **Modelfile**: `backend/models/stehouwer_genomics.Modelfile`
  * Base: `FROM qwen2.5-coder:latest` (or `llama3.3:70b`).
  * System prompt: Specialized scientific directive covering molecular biology, genetics, and structural proteomics.
- **Swarm Preset**: In `backend/core/sovereign_reasoning/swarm_coordinator.py`:
  * Add `"genomic_discovery_sprint"` to `SWARM_PRESETS`:
    1. Step 1: `Literature Recon` (Role: "Literature Recon", App: "hermes_agent", Domain: "bioinformatics")
    2. Step 2: `Variant Impact` (Role: "Variant Analyst", App: "codex_cli", Domain: "bioinformatics")
    3. Step 3: `Structural Docking` (Role: "Structural Biologist", App: "opencode", Domain: "bioinformatics")
    4. Step 4: `Synthesis` (Role: "Lead Bioinformatician", App: "claude_code", Domain: "bioinformatics")

### 6.2 R4. AI Training Dataset Synthesizer & LoRA Pipeline
- **Script 1**: `scripts/train_bioinformatics_corpus.py`
  * Synthesizes prompt-completion instruction pairs across all 11 domains into:
    `llm_training_data/bioinformatics_instruction_dataset.jsonl`
  * Format: `{"instruction": "...", "input": "...", "output": "..."}`.
- **Script 2**: `scripts/train_stehouwer_genomics_lora.py`
  * Modeled directly after `scripts/train_stehouwer_lora_unsloth.py`.
  * Targeted for NVIDIA GeForce RTX 4090 24GB VRAM:
    - 4-bit NF4 quantization (`load_in_4bit: True`)
    - LoRA rank $r=32$, alpha $\alpha=64$
    - Target modules: `["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]`
    - Effective batch size: 16 (batch 2, gradient accumulation 8)
    - Target ceiling: ~14 GB VRAM
    - GGUF Q5_K_M export target: `backend/models/stehouwer_genomics.Modelfile`

### 6.3 R5. Dedicated Studio UI & Multi-Mirror Parity
- **Component**: `frontend/src/components/GenomicsStudioTab.jsx`
  * 4 interactive panels:
    1. Genomic Variant & Expression Explorer (dbSNP, GTEx bars, UCSC, AlphaGenome AVI).
    2. Structural Biology & AlphaFold Viewer (pLDDT curves, STRING PPIs, PyMOL render dispatch, Foldseek).
    3. bioRxiv & Regulatory Literature Recon (paper browser, JASPAR PWMs, ENCODE cCREs).
    4. Autonomous Genomic Swarm & AI Training Monitor (1-click Swarm sprint dispatch, dataset generator, LoRA monitor).
- **Navigation & Access**:
  * Register in `frontend/src/components/navigationConfig.js` under `masterHubs`.
  * Register in `frontend/src/components/accessControl.js`.
  * Mount in `frontend/App.jsx`.
- **Mirror Sync**:
  * Run `python scripts/sync_mirrors.py` to copy to:
    1. `frontend/components/`
    2. `frontend/src/components/components/`
    3. `frontend/components/components/`
  * Enforce 100% SHA-256 byte parity (all 447 files identical).
- **Version Bump**: Bump from `v5.310.0` to `v5.311.0` in `version.txt` and system ledgers.

---

## 7. Test Suite Baseline & Verification Strategy

### 7.1 Existing Baseline Status
- Pytest environment: Python 3.12.10, pytest 9.1.1, anyio 4.14.2.
- Verified test run: **36 passed, 2 warnings in 27.84s** on `tests/`.
- Zero test failures currently exist in the repository.

### 7.2 Programmatic Pytest Verification Suite for Milestone 1 & 2
A dedicated test suite should be placed at `tests/test_bioinformatics_service.py` to test:
1. `TestBioinformaticsService`:
   - Instantiation of `BioinformaticsService`.
   - SQLite cache initialization in `saved_data/bioinformatics_cache.db`.
   - Cache hit/miss logic and offline resilience fallback.
   - bioRxiv adapter: search and DOI lookup.
   - AlphaFold adapter: pLDDT calculation and domain boundary parsing.
   - STRING adapter: PPI graph construction and enrichment parser.
   - PyMOL script synthesizer: script generation and headless command builder.
   - Foldseek adapter: ticket submission and result parsing.
   - dbSNP adapter: rsID coordinate resolution and SPDI/HGVS mapping.
   - GTEx adapter: 54-tissue median TPM retrieval.
   - JASPAR adapter: PWM matrix parsing and consensus extraction.
   - ENCODE adapter: cCRE coordinates and biosample Z-scores.
   - AlphaGenome adapter: AVI scoring and feature weights.
   - UCSC adapter: phyloP and phastCons score parsing.
2. `TestBioinformaticsRouter`:
   - FastAPI `TestClient` verification of all `/api/v1/bioinformatics/*` routes on Port 8080.
   - Valid response status, JSON schema validation, error handling.
3. `TestMoEBioinformaticsDomain`:
   - `SpecialistDomain.BIOINFORMATICS` presence.
   - Prompt intent routing to `stehouwer_genomics:latest`.
   - Swarm coordinator `genomic_discovery_sprint` preset integrity.
4. `TestDatasetSynthesizer`:
   - Synthetic JSONL generation and record validity in `llm_training_data/`.

---

## 8. Conclusion & Implementation Readiness

The AI-BS codebase provides an exceptionally well-structured and modular architecture:
1. `backend/AI_BS_Backend.py` is fully prepared to receive `app.include_router(bioinformatics_router)`.
2. `saved_data/` is already utilized across the ecosystem and contains sample seed data for AlphaFold, dbSNP, and ENCODE.
3. `sovereign_reasoning/` cleanly supports the 7th domain expansion and the 1-click Swarm sprint preset.
4. `scripts/` has proven patterns for Unsloth RTX 4090 LoRA training and mirror synchronization.
5. All 11 bioinformatics capabilities have clear public REST/GraphQL APIs and local fallback strategies.

The investigation is complete. Detailed actionable findings are summarized in the accompanying `handoff.md`.
