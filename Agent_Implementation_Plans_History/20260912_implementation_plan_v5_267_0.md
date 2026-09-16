# Implementation Plan: BS-Chat Universal Cross-Space Retrieval & On-Demand Ingestion Engine

Enable BS-Chat to seamlessly retrieve information from all 11 verified SQLite database spaces (and vector stores), as well as ingest and store structured information into target databases on-demand when instructed by the user.

## User Review Required

> [!IMPORTANT]
> - All 11 primary SQLite databases audited in the system will be indexed and queryable directly from BS-Chat:
>   1. `aibs_master.db` (Master entity & multi-tenant store, 27 tables)
>   2. `lexicon_vault.db` (193k word dictionary & FTS5 index)
>   3. `stehouwer_vault.db` (25k knowledge records in `vault_items`, `vault_data`, `vault_keys`)
>   4. `unreal_assets.db` (5.2k 3D meshes, textures, blueprints, materials)
>   5. `state.db` (Growth leads, client profiles, campaign queues)
>   6. `west_michigan.db` (418 commercial property & real estate records)
>   7. `clients.db` (CRM quotes, competitors, fleet data)
>   8. `drip_ledger.db` (Trades, scalp ledger state)
>   9. `stehouwer_accounting.db` (Accounting entries, tax deductions, Schedule C)
>   10. `audio_catalog.db` (101k audio assets, DSP tags, FTS5 corpus)
>   11. `LLM_CrossCheck_Ledger.db` (Cross-model inference logs)
> - On-demand ingestion will intelligently parse user input and store records in the corresponding specialized table (e.g. leads into `growth_leads`, expenses into `accounting_entries`, trades into `trades`), defaulting general knowledge, notes, or ideas into `stehouwer_vault.db (vault_items)` or `aibs_master.db (vault_data)`.
> - All database writes strictly use parameterized SQLite statements with `PRAGMA journal_mode = WAL;` to prevent corruption or locking conflicts.

## Proposed Changes

### Backend Storage & Space Architecture

#### [NEW] [omni_space_manager.py](file:///C:/AI-BS/backend/core/omni_space_manager.py)
- Create `OmniSpaceManager` singleton that maintains thread-safe connection pools with 256MB mmap and WAL mode across all 11 databases.
- `search_all_spaces(query, spaces=None, limit_per_space=5)`:
  - Rapid parallel or sequential keyword/token search across text and metadata columns in all active tables.
  - Returns structured matches with database filename, table name, row count, record data, and match relevance.
  - Includes `format_retrieval_card(results)`: Formats findings into Markdown tables with column headers and record summaries.
- `ingest_on_demand(content, target_space=None, target_table=None, metadata=None)`:
  - Detects intent or accepts explicit target space.
  - Automatically extracts structured fields (e.g. title, tags, amounts, contact information, niche, notes).
  - Inserts the record using parameterized SQL into the designated database.
  - Executes immediate verification (`PRAGMA quick_check` and record verification).
  - Formats an executive confirmation card for BS-Chat display.
- `get_spaces_overview()`:
  - Returns real-time health, table counts, row counts, and disk sizes across all 11 databases.

#### [MODIFY] [real_system_tools.py](file:///C:/AI-BS/backend/core/real_system_tools.py)
- Update `check_and_execute_system_tools`:
  - Add intent detection for universal space retrieval:
    - Keywords: `"retrieve from space"`, `"search all spaces"`, `"query database for"`, `"find in all spaces"`, `"what is in unreal_assets"`, `"search audio catalog"`, `"look up in lexicon"`, `"show me properties in"`, etc.
  - Add intent detection for on-demand ingestion:
    - Keywords: `"store this in the database"`, `"store in db"`, `"save to database"`, `"save this to the vault"`, `"ingest this into db"`, `"add lead to database"`, `"record this transaction"`, `"store note in db"`, etc.
  - Returns formatted markdown cards with live execution telemetry.

#### [MODIFY] [hybrid_reasoning_engine.py](file:///C:/AI-BS/backend/core/hybrid_reasoning_engine.py)
- In `detect_tool_intent`:
  - Add tool intent detection for `retrieve_from_all_spaces` and `ingest_on_demand_to_db`.
- In `stream_stehouwer_hybrid_response`:
  - Wire tool execution for streaming responses when tools are triggered.

#### [MODIFY] [memory_vault.py](file:///C:/AI-BS/backend/core/sovereign_reasoning/memory_vault.py)
- Integrate `OmniSpaceManager.search_all_spaces` into `SovereignMemoryVault.get_unified_context` so that conversational inquiries are automatically enriched with relevant snippets from the 11 databases before generating answers.

#### [MODIFY] [tool_registry.py](file:///C:/AI-BS/backend/tools/tool_registry.py)
- Register `retrieve_from_all_spaces` and `ingest_on_demand_to_db` in `get_tool_declarations` and `execute_tool`.

#### [MODIFY] [AI_BS_Backend.py](file:///C:/AI-BS/backend/AI_BS_Backend.py)
- Add dedicated REST endpoints:
  - `POST /api/spaces/retrieve`
  - `POST /api/spaces/ingest`
  - `GET /api/spaces/overview`

---

### Frontend BS-Chat & Multi-Mirror Synchronization (Rule 1)

#### [MODIFY] All 4 mirror paths of `ChatTab.jsx`:
1. `frontend/src/components/ChatTab.jsx`
2. `frontend/components/ChatTab.jsx`
3. `frontend/src/components/components/ChatTab.jsx`
4. `frontend/components/components/ChatTab.jsx`
- Add slash command `/retrieve <query>`: Triggers multi-space search and renders structured table cards.
- Add slash command `/ingest <data>`: Triggers on-demand ingestion into the active database space.
- Add slash command `/spaces`: Displays the real-time overview card of all 11 databases.
- Add interactive quick-action chips in the chat header/control bar:
  - `[🔍 Search All Spaces]`
  - `[💾 Ingest to DB]`
  - `[📦 11 Spaces (WAL)]`

---

## Verification Plan

### Automated Tests
- Create `backend/test_omni_space_manager.py`:
  - Test retrieval across all 11 databases (checking `aibs_master.db`, `lexicon_vault.db`, `unreal_assets.db`, `audio_catalog.db`, `west_michigan.db`, `stehouwer_vault.db`, `drip_ledger.db`, `stehouwer_accounting.db`, `clients.db`, `state.db`, `LLM_CrossCheck_Ledger.db`).
  - Test on-demand ingestion into `vault_items` (`stehouwer_vault.db`) and verify the record is persisted.
  - Test on-demand ingestion of a growth lead into `aibs_master.db` and verify the record is persisted.
  - Test on-demand ingestion of an accounting entry into `stehouwer_accounting.db`.
  - Test intent detection in `real_system_tools.py` for both retrieval and ingestion prompts.
  - Test `/api/spaces/retrieve`, `/api/spaces/ingest`, and `/api/spaces/overview` via FastAPI `TestClient`.
- Run: `powershell -ExecutionPolicy Bypass -Command "C:\AI-BS\pyppeteer_env\Scripts\python.exe backend/test_omni_space_manager.py"`

### Multi-Mirror Parity Verification
- Run SHA256 checksum audit across all 4 mirror trees of `ChatTab.jsx` to verify 100% hash parity.

### Frontend Compilation & Build
- Run `npm run build` in `C:\AI-BS\frontend` to confirm Vite production bundle builds with 0 errors.
- Run `firebase deploy --only hosting --non-interactive` as mandated by Rule 3.
