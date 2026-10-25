# Conversation learning and RAG: policy and source checkpoint

Updated: October 24, 2026. Source checkpoint: v5.329.34. Historical source findings below retain their stated version; current status follows. This is not a claim of verified semantic learning, weight training or platform release.

## User intent

Clearing the visible chat must preserve the conversation as an eligible learning source, including unfinished work, failed attempts, corrections and ordinary conversations across topics. A completed task or successful answer is not a prerequisite for retention. Preserve originals and earlier versions; record source, date, project, authenticated ownership and outcome. Never silently turn an unverified model answer into a fact or copy a failed solution as a recommended one.

The user's original approach offloaded a large corpus using parsing and retrieval similar to the script-conversion workflow. Retain and improve that foundation rather than replace it blindly. An indexed million-token corpus is different from one million tokens in the model's live attention window. Actual storage, ingestion, retrieval, answer quality and weight updates each need separate evidence.

## Learning routes, in sequence

| Route | Purpose | Evidence required before claiming it works |
| --- | --- | --- |
| Full transcript/source retention | Preserve what was actually said and tried, including incomplete work | Durable commit/readback, exact bytes or canonical JSON hash, safe retry and reload recovery |
| Source-aware retrieval | Recall relevant passages without loading the entire archive | Owner/project filtering; source hash and chunk offsets; beginning/middle/end recall; citations and context budget |
| Summaries and structured memory | Retain decisions, preferences, constraints and unresolved tasks | Trace back to full sources; versioned corrections; no replacement/deletion of the transcript |
| Lessons and case library | Reuse successful approaches and avoid known failed ones | Actual error/check evidence; labels for verified, failed, untested and superseded; held-out usefulness checks |
| Curated model training | Potentially update the local Stehouwer model's behavior | Separate versioned dataset, secret review, retained original model, held-out comparisons and rollback before promotion |

These routes can cover any topic within authorized sources; they are not confined to programming. They do not authorize unrelated actions, outbound messages, additional account access, unreviewed private/client exports or automatic code promotion. Archived instructions are reference data, never fresh permission to execute. Save observable decisions and concise explanations, not a fabricated record of private internal reasoning. No training daemon was started at this checkpoint.

## Current implementation and limits at v5.329.34

v31 adds authenticated owner-scoped private revisions in the existing vault; v32 adds the browser's durable pending journal; v33 connects those to desktop/mobile, preserving complete finite JSON message records and text drafts with visible confirmation, retry/conflict/history states. Clear remains archive-first and fails without confirmation. Incomplete and failed discussions remain eligible sources; later corrections should create attributed revisions or lesson records rather than rewrite original evidence. Topic breadth is not limited to coding. Failed ideas are useful as labeled counterexamples, not validated advice. None of these steps automatically updates model weights.

Controlled connected-browser fixtures pass, including restarts and scope changes. At v34 the actual main API is healthy and its private identity/list endpoints reject anonymous and invalid credentials while accepting the configured local administrator. Consistent real-vault/master backups and888 selected document copies are verified before startup, and preservation is checked afterward. Actual user save/clear/reload, Firebase identity, complete browser widget tree, semantic retrieval and training acceptance remain pending. No production private-revision tables or synthetic chat writes have been created at this checkpoint. Old implementation descriptions below are historical, not current missing-feature claims.

Durability limits remain explicit: capture is debounced, browser storage may be denied/evicted, and sudden termination can lose uncommitted text. Unsent component-local binary attachments are not part of this text/message journal. Historical/third-party sources are not all inventoried or imported. Owner/secret review precedes ingestion or cloud copying. Archiving cannot guarantee that every conversation on every platform is accessible or retained forever. The ledger contains observable decisions and brief explanations, not private internal chain-of-thought.

## Historical source findings verified at v5.329.30

- `frontend/src/components/ChatTab.jsx` handled inputs over 16,000 characters by writing one shared `workspace/pasted_1m_buffer.txt`. The old branch announced offload completion after any resolved fetch, without checking HTTP/body success, stored bytes, indexing or retrieval. It opened an editable preview truncated to 50,000 characters. v5.329.30 fixes the source-staging portion described below; other context badges are not validated by this fix.
- `backend/core/project_rag.py` already has `parse_fdx_content`, `sync_project_screenplay` and `query_project_rag_assistant`. It uses structured screenplay scenes and manuscript `chunks.json`, stores source metadata in Chroma and builds retrieved script/book context for Ollama. This supports the user's parsing analogy. Source was inspected; live retrieval and complete screenplay fidelity were not tested here, and no screenplay files were changed.
- That project module embeds prefixes of stored text (including scene/book text limited to 2,000 characters and an embedding helper limit of 4,000). Full stored text is not proof that its entire meaning was embedded. It also contains a zero-vector fallback on embedding failure. Those paths need explicit failure reporting and evaluation before relying on them for complete large-source recall.
- `backend/context_ingestor_daemon.py` is a broad drive scanner, with a 150-KiB file limit, snippets limited to 5,000 characters and scan caps. It is not evidence of lossless million-token ingestion. Its main-app daemon registration has auto-start disabled in the reviewed source; it was not run.
- `backend/core/vector_vault.py` limits embedding input and has a deterministic hash fallback when inference is unavailable. Its existing multicontext retrieval does not by itself prove full large-source coverage, authenticated ownership or a bounded final prompt.
- `backend/routers/rag_bridge.py` has a separate industry RAG store on E: and port-11435 synthesis. Do not merge it with private chat ownership by assumption. `backend/core/sovereign_reasoning/dispatcher.py` requests `num_ctx: 8192`, while chat labels describe 4096. Neither source setting is a live GPU/context measurement.

## Implemented in v5.329.30

`frontend/src/utils/ragSourceStage.js::stageRagSource` sends the exact raw large-paste text to a unique `C:\AI-BS\workspace\rag_inputs\context_<random-id>.txt`. It rejects sources over 16 MiB without truncating, requests exclusive creation, checks HTTP and both response statuses, and verifies returned path, UTF-8 byte count and SHA-256. The backend's existing `backend/executive_runtime_router.py::execute_multi_runtime` file-write branch supports opt-in exclusive creation, flush/fsync and exact readback before confirming success. Existing default backup/write behavior remains.

The desktop large-paste branch uses this helper. Failures preserve/restore the draft when it has not been replaced, stop subsequent analysis dispatch and leave an honest error. Confirmed storage identifies the actual file/hash and explicitly leaves indexing/retrieval unverified. It no longer opens a truncated editable source buffer. Separate pastes no longer overwrite the same staging filename. This is not a restart-persistent staging outbox or a parser/indexer connection.

Active desktop `Clear Screen` and mobile `New Chat` callbacks now use the v5.329.29 confirmed archive handler. Save-and-clear also already used it. A failed or unconfirmed save retains visible chat; newer messages are not cleared by an older save result. Four mirrors of each active component match. This does not prove every unused component, third-party chat, tab close or reload is protected. An unused `MobileGeminiChat.jsx` contains direct clears and was left untouched pending reachability review.

The v5.329.29 archive helper saves full finite message JSON and a searchable transcript in the existing `backend/stehouwer_vault.db`, confirming an idempotent receipt. That is not automatic semantic indexing or model training. Current active generation cannot be cleared through this handler until stopped/finished; an otherwise incomplete conversation can be archived. Unsaved chat and in-memory pending retry state still need durable reload recovery.

## Retained verification

Save point: `backups/rag_staging_5_329_30_20261024T041018797Z`. Version before-images: `backups/release_versioning/20261024T041532363Z_rag_staging_ed9b8d1b`.

- Native file tests: `red.json` failed 4 of 6 methods before implementation; final `green2.json` passes 7 of 7. A synthetic source over four million ASCII characters preserves exact start/middle/end bytes. This is a storage test, not a tokenizer or retrieval benchmark.
- Actual helper/large-paste handler fixtures: `ui_red2.json` passed 1 of 15 before implementation; `ui_green3.json` passes 16 of 16. Includes authorization/network/body failures, altered receipts, draft preservation, separate files and size rejection before a request.
- Actual clear callback fixtures: `clear_red.json` failed all 4 checks before wiring; `clear_green.json` passes 4 of 4 afterward. Existing archive handler bodies remain unchanged from v5.329.29.
- Scoped source/evidence audit: `audit.json` passes 66 checks, including both four-mirror groups, 16 version metadata originals/current hashes and unchanged timestamps for 11 selected real stores. `js_audit.json` passes 9 syntax/helper-bundle checks. This is not a full app build, rendered browser test, live auth/chat test, database-integrity check or VM acceptance.
- An early UI fixture falsely matched the word "complete" in a rejection message. Its failed report, original fixture and `ui_fixture_correction.md` are retained. Only the success-announcement predicate was corrected; application failure behavior was already correct. Do not erase failures or count repeated suites as unique tests.

No production archive/schema write, model call, broad scan, embedding, trainer, VM action, service restart or platform release occurred. Existing legacy buffer/transcripts, screenplay documents and customized model versions remain untouched by this task. Selected store timestamps are evidence for the selected files only, not a claim that every historical source was inventoried.

## Next bounded task and acceptance

Verify ordinary chat using the existing customized Stehouwer registry, then actual main-app owner-scoped save/read/reload/clear and document preservation on the backed-up backend. Do not rebuild the already implemented session/outbox foundations, recreate customized model weights or publish new UI against an old backend. Network/API identity and browser behavior need actual acceptance beyond fixtures.

Then connect rebuildable source-hash/offset-bearing parsing to genuine embeddings and source-cited retrieval under a measured prompt budget. Test recall at beginning/middle/end, relevant negatives, ownership boundaries and unavailable inference; reject invalid embeddings without presenting hash/zero fallbacks as successful semantic recall. Evaluate attributed summaries, decisions/preferences, successful/failed case lessons and any versioned training candidates separately, preserving full sources and original model versions. No automatic code promotion, outbound activation, broad private export or guarantee of learning quality from retention alone.
