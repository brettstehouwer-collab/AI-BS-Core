# Implementation Plan: Stehouwer LLM Self-Improvement Directive (v5.255.0)

A structured self-improvement implementation addressing all five domains identified in the Stehouwer LLM self-assessment directive:
1. **Ingestion Daemons:** Refactor `AI_BS_Universal_Data_Ingestor.py` and knowledge ingestion pipelines for multi-path resolution, concurrent scraping, batch transactions, and vector store bridging.
2. **ChromaDB / Crypto-Swarm AEO Tracker:** Replace static mock scores in `AeoTracker.jsx` with real LLM analysis via a dedicated FastAPI AEO router (`/api/advertising/aeo`) resolving the Port 8001 collision.
3. **Vector Memory Access Upgrade:** Remediate the ChromaDB 768d vs 384d dimension mismatch in `AI_BS_Backend.py` with dual-port Ollama `nomic-embed-text` query embedding generation and multi-collection search.
4. **User Interface (Reasoning Inspector):** Upgrade `ReasoningInspector` in `ChatTab.jsx` to render Vector Memory retrieval telemetry and execution traces.
5. **Ecosystem Ledgers & Deployment:** Full ledger updates, version bump to `v5.255.0`, and Firebase Hosting deployment.

---

## User Review Required

> [!IMPORTANT]
> **ChromaDB Dimension Parity Remediated:** The active ChromaDB collection `ai_bs_context_memory` expects 768-dimensional vectors (created via `nomic-embed-text`), but default text queries generated 384d vectors, causing runtime query failure in `AI_BS_Backend.py` (`Collection expecting embedding with dimension of 768, got 384`). The proposed upgrade implements an active embedding generator that produces native 768d vectors across Ollama ports 11434/11435, restoring full conversational context memory.

> [!IMPORTANT]
> **Zero-Mock AEO Tracker:** Per the **Zero-Mock Rule**, `AeoTracker.jsx` will be migrated away from synthetic numbers (`78/100`, static prompt rankings) to authentic brand visibility scores computed live by the Stehouwer LLM and semantic vector indexing in ChromaDB.

---

## Open Questions

- None. All requirements and architectural specifications are clearly defined.

---

## Proposed Changes

### Phase 1: Ingestion Daemons Refactoring & Concurrency Optimization

#### [MODIFY] [`backend/AI_BS_Universal_Data_Ingestor.py`](file:///C:/AI-BS/backend/AI_BS_Universal_Data_Ingestor.py)
- **Path Resolution:** Update directory resolution to dynamically check `E:\AI_BS_Resources\Databases`, `E:\AI_BS_Resources`, and fallback to `C:\AI-BS\database\industry_dbs`, creating target SQLite schemas on-demand if missing.
- **Concurrency & Non-Blocking I/O:** Replace sequential loop with `concurrent.futures.ThreadPoolExecutor(max_workers=8)` to fetch RSS feeds in parallel.
- **Batching:** Instead of sampling a single random entry per cycle (`random.choice`), ingest up to 20 recent unseen entries per feed using `executemany` in a single WAL transaction.
- **Vector Ingestion Bridge:** Ingest title and content excerpts directly into ChromaDB collection `industry_knowledge_vault` via `MemoryService` with multi-tenant client metadata (`stehouwer_publishing`).

#### [MODIFY] [`backend/scan_and_ingest_root.py`](file:///C:/AI-BS/backend/scan_and_ingest_root.py)
- Add dimension verification before inserting documents into ChromaDB to ensure consistent 768d embedding storage.

---

### Phase 2: ChromaDB / Crypto-Swarm AEO Tracker Optimization

#### [NEW] [`backend/routers/aeo_router.py`](file:///C:/AI-BS/backend/routers/aeo_router.py)
- Expose `GET /api/advertising/aeo` and `POST /api/advertising/aeo/evaluate` on Port 8080.
- Implements authentic AI Engine Optimization (AEO) tracking:
  - Queries local Stehouwer LLM / Ollama with target industry prompts to evaluate brand mention share.
  - Queries ChromaDB collections for semantic relevance scores.
  - Computes dynamic AI Share of Voice (0-100) and actionable strategic recommendations based on real corpus gaps.
  - Returns structured telemetry: `overall_score`, `prompts` array with live rankings, and LLM-generated `suggestions`.

#### [MODIFY] [`backend/AI_BS_Backend.py`](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Mount `aeo_router` at `/api/advertising/aeo` with `Depends(get_tenant)` header isolation.

#### [MODIFY] [`frontend/src/components/AeoTracker.jsx`](file:///C:/AI-BS/frontend/src/components/AeoTracker.jsx) (and mirror components)
- Update `API_BASE` to resolve dynamically to `BACKEND_URL` (Port 8080) rather than hardcoded `http://127.0.0.1:8001`.
- Add "Run Live LLM AEO Audit" button and interactive prompt analyzer.

---

### Phase 3: Vector Memory Access Upgrade & Dimension Mismatch Resolution

#### [NEW] [`backend/core/vector_vault.py`](file:///C:/AI-BS/backend/core/vector_vault.py)
- Centralized vector utility providing:
  - `get_embedding(text: str, model: str = "nomic-embed-text") -> List[float]`: Generates 768d embeddings probing Ollama on candidate ports `[11434, 11435]` with automatic failover.
  - `query_collection_safe(collection, query_text: str, n_results: int = 3) -> List[str]`: Inspects collection dimension; generates matching 768d embeddings; handles dimension fallback gracefully without crashing.
  - `query_multi_collections(collections: List[str], query_text: str, top_k: int = 3) -> Dict[str, List[str]]`: Queries context memory, heuristics, and industry knowledge concurrently.

#### [MODIFY] [`backend/AI_BS_Backend.py`](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Replace lines 3118–3129 with call to `vector_vault.query_collection_safe` using 768d embeddings.
- Incorporate retrieved context directly into `retrieved_context` and populate `msg["memory_trace"]` for the UI inspector.

---

### Phase 4: User Interface (Reasoning Inspector) Enhancement

#### [MODIFY] [`frontend/src/components/ChatTab.jsx`](file:///C:/AI-BS/frontend/src/components/ChatTab.jsx) (and mirror components)
- Enhance `ReasoningInspector`:
  - Display Vector Memory status badge (`🧠 Context Retrieved: N chunks` or `⚡ Direct Inference`).
  - Display execution pipeline phase breakdown (Preflight Guardrail -> Vector Retrieval -> Graph Reasoner -> LLM Stream).
  - Render genetic drift / adaptive reasoning variance indicators when multi-turn memory feedback is present.

---

### Phase 5: Verification, Version Parity & Live Production Deployment

#### [NEW] [`backend/test_self_improvement_engine.py`](file:///C:/AI-BS/backend/test_self_improvement_engine.py)
- Test 1: Ingestor multi-path resolver and concurrent batch insert verification.
- Test 2: 768d vector generation via Ollama across ports 11434/11435.
- Test 3: ChromaDB `ai_bs_context_memory` query without dimension mismatch errors.
- Test 4: `GET /api/advertising/aeo` authentic response validation (Zero-Mock verification).
- Test 5: End-to-end encrypted chat with active Vector Memory injection.

#### Ecosystem Ledgers & Production Deployment
- Bump version to `v5.255.0` across manifests and UI badges.
- Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md`, `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md`.
- Synchronize chronologies and historical index.
- Build production bundle (`npm run build`) and deploy to Firebase Hosting (`firebase deploy --only hosting --non-interactive`).

---

## Verification Plan

### Automated Tests
1. `C:\AI-BS\pyppeteer_env\Scripts\python.exe backend/test_self_improvement_engine.py` (Assert 100% pass).
2. `C:\AI-BS\pyppeteer_env\Scripts\python.exe backend/test_aes_e2e_encryption.py` (Assert 0 regressions).
3. `C:\AI-BS\pyppeteer_env\Scripts\python.exe backend/test_full_tool_and_zero_mock_audit.py` (Assert 100% zero-mock compliance).

### Manual Verification
1. Probe `GET http://127.0.0.1:8080/api/advertising/aeo` to verify dynamic LLM AEO scores.
2. Send test chat message to `POST http://127.0.0.1:8080/api/chat` and verify zero ChromaDB dimension warnings in console.
3. Confirm live deployment at `https://ai-bs-dashboard.web.app`.
