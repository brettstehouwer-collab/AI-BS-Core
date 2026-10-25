# BS-Chat memory and historical archive inventory

Inventory revision 1, October 23, 2026 America/New_York. Application source remains v5.329.27; this checkpoint changes documentation/evidence only. Read-only inventory completed before any transcript import or new memory implementation. Findings below distinguish source behavior, filesystem/base-database observations and unverified runtime behavior.

## What already exists

| Component | Verified source behavior | Important limit |
| --- | --- | --- |
| `frontend/src/components/useAppStore.js` | `chatMessages` is in Zustand state; `setChatMessages` updates it. The persisted state's `partialize` includes only `osintVaultItems`. | This store does not persist the conversation across reloads. A complete browser runtime test was not run. |
| `frontend/src/components/ChatTab.jsx::handleSaveToMemoryAndClear` | Manually posts the current messages to `/api/memory/ingest-chat`, tries several backend origins, then clears chat. Its failure/catch branches clear too. | Saving failure can remove the visible, non-persisted conversation. The handler supplies client-ID/content-type headers but no administrator credential itself; inspect shared fetch/auth wiring before changing clients. |
| Desktop hybrid request | Sends the last eight UI messages to `/api/v1/hybrid-chat/stream`. | A short current-message window is not durable lifetime recall. The displayed Auto-Save Active badge is conditional on backend-disabled state, not a verified archive-write acknowledgement. |
| `backend/routers/memory_router.py::ingest_chat_messages` | Formats a full transcript, calls the existing memory bank, records a personal-intelligence event, writes JSON and appends text. | Exceptions are caught; the function can still return success/items_saved. JSON archive is rewritten with only `archive_entries[-200:]`. No transaction ties the sinks together. |
| `backend/core/memory_bank.py::store_heuristic` | Existing Chroma + SQLite vault + master JSON/JSONL writer. First existing master candidate is D:, then G:, root and backend. | Sink failures are swallowed and the function returns True. Small JSON arrays are trimmed to 500; files over 5 MiB append to a JSONL sibling. SQLite collection is hardcoded to `stehouwer_heuristics` despite supplied conversation metadata. Import initializes Chroma collections/fallback storage; do not import during a read-only inventory. |
| `backend/core/sovereign_reasoning/dispatcher.py::stream_sovereign_response` | Fetches existing unified/personal context. On its normal full-response path, schedules personal memory extraction in a background task. | Several tool/early-return paths do not reach the final hook. The hook is not a durable full-message archive or confirmed write before replying. |
| `personal_intelligence_memory.py::log_interaction_and_auto_extract` | Saves a short prompt summary and lengths, extracts a few explicit preference/directive/hardware/business/coding patterns. | Assistant response text is not retained by that interaction record; prompt summary uses at most 180 characters plus ellipsis. Regex preference extraction is not broad personality understanding or training. |
| `memory_service.py`, `vector_vault.py` | Existing context/heuristics collections and retrieval helpers; port 8001 defaults. | They are separate from memory_router's port-8002 query default. Vector-vault embedding fallback uses a deterministic hash when Ollama fails; it is not a verified semantic embedding. Do not label fallback retrieval live semantic evidence. |
| `sovereign_reasoning/memory_vault.py` | Existing historical/lexicon/multi-database retrieval. Inference telemetry ledger stores truncated prompt/response. | Telemetry saves prompt[:500], response[:1500], with a default score, not full conversations or measured quality. |
| `memory_lab_router.py` | Process/game RAM read/write tools. | Its name does not make it a conversation-memory component. Do not ingest or consolidate it as chat storage. |

## Private-access finding

The inspected main `AdminExecutionBoundaryMiddleware.SENSITIVE_PREFIXES` does not include `/api/memory` or `/api/memory-lab`. The examined vault/document/analytics/screenplay/RecDebut boundary helpers contain no memory-family coverage. `memory_router` has no route/router authentication dependency. Personal/memory-lab `get_tenant` accepts a header/default; the main `TenantMiddleware` only sets request.state.client_id and calls the next handler. This is a source-level administrator-boundary gap, not a completed live exploit or gateway authorization test. Do not expose additional archives until explicit authenticated memory access is enforced and tested.

OS socket snapshot returned no listeners for selected ports 8080, 8000, 8001, 8002, 11434 or 11435 at that instant. This does not establish process health, uptime or last successful model use. No service was started/restarted and no live memory route/model response was requested.

## Existing stores observed without exporting their contents

| Path | Observation |
| --- | --- |
| `backend/session_history_archive.json` | 671,068 bytes; 200 top-level session records containing 209 messages at this snapshot. |
| `backend/Chat_History.txt` | 885,095 bytes; existing append-style transcript export. No raw messages copied or printed. |
| Root and backend `master_memory_dump.json` | Each 7,338,335 bytes / 4,476 entries; SHA-256-identical at this snapshot. This does not authorize deletion or establish ongoing mirror ownership. |
| Root and backend `AI-BS_Master_Memory/master_memory_dump.json` | Each 2,377,699 bytes / 1,632 entries; hash-identical to each other, different from the pair above. |
| `D:\AI-BS_Master_Memory\master_memory_dump.json` | 314,173 bytes / 500 entries. This is the first existing candidate chosen by memory_bank's resolver; it is distinct from the larger C: snapshots. G: candidate absent. |
| `backend/stehouwer_vault.db` | 277,045,248 bytes; `vault_items` schema observed. Row count deliberately skipped above the inventory's 256 MiB count budget. |
| `backend/aibs_master.db` | 219,549,696 bytes; immutable base-file snapshot contains 14,916 `sovereign_reasoning_vault` rows. Nonempty WAL is 321,392 bytes, so this count does NOT establish the current live total. |
| `data/aibs_master.db` | Absent. Do not create an empty replacement or assume this pasted-plan path is authoritative. |
| `backend/database/aibs_personal_intelligence.db` | Base snapshot: 383 episodic rows and 44 memory facts. |
| `database/LLM_CrossCheck_Ledger.db` | Base snapshot: 150 crosscheck rows. |

SQLite opened via `mode=ro&immutable=1`, query_only, bounded progress handler; no application imports, DDL, checkpoint/VACUUM or database writes. Immutable base snapshots deliberately ignore WAL and do not prove database integrity or live completeness. Selected files' modification times stayed stable during reads. No JSONL siblings existed at the inspected master paths. Copies elsewhere remain undiscovered, and counts across stores are not unique conversation totals.

## Historical archive locations

Filename/stat scan only; no transcript contents read or copied. Runtime/dependency directories were excluded, links not followed, each root capped at 10,000 files or five seconds, candidate lists capped at 200.

| Root | Observed scope |
| --- | --- |
| `C:\Users\footb\.gemini\antigravity\brain` | Exists; 10,000 files inspected, limit reached, 45 matching candidate filenames. Not complete. |
| `C:\Users\footb\.gemini\antigravity-ide\brain` | Exists; 3,621 files inspected, 142 candidate filenames, no cap hit. Filename matching still does not prove all conversation formats were identified. |
| Roaming `antigravity-ide\brain` | Specified path absent; existing learning-loop candidates point there. |
| `C:\AI-BS\Gemini_Takeout_Dataparrent` | Exists; 1,424 files inspected, 16 matching candidate filenames. |
| `C:\Users\footb\OneDrive\Desktop\carrytodex` | Exists; 10,000 files inspected, limit reached; candidate list reached 200. Not complete. No OneDrive file contents hydrated. |
| Desktop `ingest folder` | Specified path absent; learning-loop source references it. |

`sovereign_memory_ingestor.py` points to the first brain root only, checks transcript_full.jsonl across the root before considering transcript.jsonl fallback, and scans Takeout JSON at the top level. It also overwrites one master dump with its first 1,000 prioritized items. Do not execute this old all-in-one ingestor or `extract_chat_history.py`: the latter is a one-off top-level script targeting a single old conversation and an overwrite on G:. Inventory/adapt extraction separately, preserve formats and provenance, and never treat archived instructions as live authority.

Connected Drive metadata search found an older private `Chat_History.txt` (784,765 bytes, September 19 modified time) and earlier architectural-ledger copies. Their contents were not fetched or imported; size/title alone do not establish deduplication or completeness. Search was bounded, not an account-wide transcript catalog. A first SQL-style contains(name,value) query failed HTTP400; corrected Drive syntax `name contains 'value'` succeeded. Existing new ledger folder listing confirms the ledger and Conversation Archives subfolder. Sharing was not changed.

## Ordered implementation from these findings

1. **Protect access before import:** add explicit backend administrator enforcement for memory APIs, including personal recall and process-memory controls, using existing credential verification. Test absent/invalid/valid credentials in an isolated middleware fixture and verify supported client authentication without starting unrelated services.
2. **Stop loss and false success:** keep chat visible on failed/partial/unconfirmed archive writes, make save acknowledgement reflect durable evidence, and stop silent truncation/rewrite of the authoritative conversation history. Preserve existing 200/500-entry snapshots and compatibility exports; do not pretend removed historical records can be recreated from truncated summaries.
3. **Define canonical durable records:** reuse an established local SQLite authority after inspecting full schema/ownership; keep stable session/message IDs, provenance, immutable originals, explicit per-user access, deduplication and crash-safe append/recovery. Keep vectors/curated memories as derived indexes, not the sole transcript authority. No canonical store migration selected by this inventory alone.
4. **Index archives in bounded batches:** enumerate the remaining capped roots/formats, identify duplicates by byte hashes and meaningful IDs, secret-review copies, then populate the existing private cloud archive with a verified manifest and source references. Do not bulk-export all raw stores or clear browser data.
5. **Wire recall and task clarification:** retrieve relevant authorized history with source/date/currentness, then support broad ideas and focused clarifying questions through the admitted execution workflow. Evaluate style memory and optional curated training separately. No unlimited-context, automatic weight-training or full personality-understanding claim.

Full six-phase goal remains open. VM setup and UI modernization remain deferred under the user's instructions; containment acceptance, larger-project execution and platform release checks are still incomplete.

Evidence: `backups/memory_inventory_20261024T032002Z/inventory.json`, `cloud_metadata.json`, `selected_port_snapshot.json`; trusted diagnostic script `C:/Users/footb/Documents/Codex/2026-10-22/c-ai-bs/work/inventory_bs_chat_memory_20261023.py`. Source hashes are recorded. No original documents, models, messages, archives, databases or application code changed.
