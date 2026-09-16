# Task: Stehouwer LLM Self-Improvement Directive: Ingestion Daemons, AEO Tracker, Vector Memory & BS-Chat Ecosystem Management

- [ ] **Phase 1: Ingestion Daemons Refactoring & Concurrency Optimization** <!-- id: 0 -->
  - [ ] Refactor `backend/AI_BS_Universal_Data_Ingestor.py` with multi-path resolution (`E:\AI_BS_Resources\Databases`, `E:\AI_BS_Resources`, and `C:\AI-BS\database\industry_dbs`) <!-- id: 1 -->
  - [ ] Replace sequential single-item polling with concurrent multi-feed fetching (`ThreadPoolExecutor`) and batched SQLite insertions <!-- id: 2 -->
  - [ ] Add ChromaDB vectorization bridge (`industry_knowledge_vault` collection) for ingested feed items <!-- id: 3 -->
  - [ ] Audit and optimize `backend/scan_and_ingest_root.py` and `backend/vault_auto_ingestor.py` <!-- id: 4 -->

- [ ] **Phase 2: ChromaDB / Crypto-Swarm AEO Tracker Optimization & Real LLM Integration** <!-- id: 5 -->
  - [ ] Resolve port collision between Crypto-Swarm API and ChromaDB on port 8001; author canonical FastAPI AEO router (`backend/routers/aeo_router.py`) mounted on Port 8080 under `/api/advertising/aeo` <!-- id: 6 -->
  - [ ] Replace static mock payloads with real Stehouwer LLM / Ollama scoring and ChromaDB semantic similarity analysis (Zero-Mock compliance) <!-- id: 7 -->
  - [ ] Update `frontend/src/components/AeoTracker.jsx` (and mirrors) to consume `/api/advertising/aeo` with live prompt evaluation and interactive analysis <!-- id: 8 -->

- [ ] **Phase 3: Vector Memory Access Upgrade & Dimension Mismatch Resolution** <!-- id: 9 -->
  - [ ] Author centralized vector retrieval helper `backend/core/vector_vault.py` with dual-port Ollama failover (11434/11435) using `nomic-embed-text` (768d) <!-- id: 10 -->
  - [ ] Remediate ChromaDB dimension mismatch error (`768 got 384`) in `backend/AI_BS_Backend.py` (line 3120) by injecting explicit 768d query embeddings <!-- id: 11 -->
  - [ ] Enhance context retrieval across multi-collections (`ai_bs_context_memory`, `heuristics`, `industry_knowledge_vault`) with token budgeting <!-- id: 12 -->

- [ ] **Phase 4: BS-Chat Ecosystem Management & Live Script Execution Engine** <!-- id: 13 -->
  - [ ] Author ecosystem management tools in `backend/tools/tool_registry.py`: `run_ecosystem_script`, `run_ecosystem_command`, `manage_ecosystem_service`, and `get_ecosystem_health` <!-- id: 14 -->
  - [ ] Mount direct execution endpoint `POST /api/chat/execute-script` in `backend/AI_BS_Backend.py` supporting Python (`pyppeteer_env`) and PowerShell with live stdout/stderr return <!-- id: 15 -->
  - [ ] Condition Stehouwer LLM system instructions in `AI_BS_Backend.py` with ecosystem management capabilities <!-- id: 16 -->
  - [ ] Upgrade `frontend/src/components/ChatTab.jsx` (and mirrors) with interactive `[▶ Run in BS-Chat]` buttons on code blocks and slash command dispatch (`/run`, `/ps`, `/health`, `/service`) <!-- id: 17 -->
  - [ ] Upgrade `ReasoningInspector` in `ChatTab.jsx` to render Vector Memory retrieval telemetry, tool execution outputs, and genetic variance metrics <!-- id: 18 -->

- [ ] **Phase 5: Automated Verification, Ecosystem Ledgers & Live Production Deployment** <!-- id: 19 -->
  - [ ] Author automated test suite `backend/test_self_improvement_engine.py` validating ingestion batching, AEO LLM scoring, 768d vector retrieval, and script execution <!-- id: 20 -->
  - [ ] Bump ecosystem version from `v5.254.0` to `v5.255.0` across manifests and UI badges <!-- id: 21 -->
  - [ ] Update `AI_BS_MASTER_ARCHITECTURAL_LEDGER.md` and `docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md` (v5.255.0) <!-- id: 22 -->
  - [ ] Synchronize `MASTER_TASKS_CHRONOLOGY.md`, `MASTER_IMPLEMENTATION_PLANS_CHRONOLOGY.md`, and `MASTER_HISTORICAL_INDEX.md` <!-- id: 23 -->
  - [ ] Execute `npm run build` and deploy live to Firebase Hosting (`ai-bs-dashboard.web.app`) per Strict Deployment Rule <!-- id: 24 -->
