# Conversation learning and RAG: policy and source checkpoint

Updated: October 24, 2026. Current policy/source review: v5.329.43 / plan1.53; historical source checkpoint37 and clarification1.47 follow. Historical source findings below retain their stated version; current status follows. This is not a claim of verified semantic learning, weight training or platform release.

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

## Clarified learning contract — all topics and unfinished conversations

The operator reiterates that clearing a chat is a change of view, not a request to discard its potential learning value. This confirms the existing requirement; it does not require a second transcript store or an automatic trainer. Include partial discussions, abandoned ideas, wrong approaches, corrections, successful work and ordinary conversation. Topic labels may have categories and subcategories, but a topic or confident writing style is not evidence that an answer is correct.

The next derived-memory implementation must keep these distinctions explicit:

- **Source:** authenticated owner/project scope, conversation/revision/message identifiers and the retained source hash or passage reference. Derived records must remain traceable to the full original.
- **Outcome:** verified, failed, untested, incomplete or superseded, with actual evidence when available. Default to untested/unknown; missing completion or the model's own claim cannot establish success. A failure may teach which approach failed under which conditions; it must not become recommended code or a universal rule.
- **Admission:** preservation does not imply approval for embedding, external copying or training. Record secret/privacy review separately; exclude credentials and unrelated personal/client material from derived prompts and datasets. Existing private revisions do not retroactively make older global archives owner-scoped.
- **Correction:** preserve earlier source and derived versions, link the correction and prefer the supported current record during retrieval. Similarity alone cannot resolve conflicting claims or authorize execution.
- **Use:** begin with relevant cited passages, source-linked summaries and explicit preferences/constraints. Add evidence-labeled positive/negative cases and only later evaluate curated training on held-out examples, retaining the customized base model and rollback version.

These are acceptance requirements for derived learning, not a claim of an implemented schema, indexer or learner. Verify that an incomplete failed example is retained and retrieved with its outcome and citation; a later correction is preferred without deleting the earlier evidence; another owner cannot retrieve it; secret-containing input is not admitted to derived prompts; and unavailable retrieval is reported rather than fabricated. Evaluate quality and prompt size separately from storage size. A large retrievable archive is not the model's native attention window.

### Current source audit at v5.329.37

`frontend/src/utils/chatArchive.js::archiveChatAndClear` checks the matching durable archive receipt and message count/hash form, calls the current conversation binding, and only clears an unchanged snapshot on the same backend. `conversationMemory.js::beforeClear` commits pending local data and closes the retained view record. This is source inspection in this clarification checkpoint; it is not a new browser acceptance test or an independent rehash of the server's archive receipt.

`backend/routers/conversation_router.py::conversation_save` still returns `memory_index_status: not_indexed`. Owner-scoped immutable revisions and the browser outbox provide preservation foundations, not automatic semantic recall or weight learning. The separate legacy `/api/memory/ingest-chat` archive and personal-summary store still need their recorded ownership/directive-authority review before broad multi-user learning. Actual browser save/read/reload/clear remains pending the saved localhost permission; do not bypass it. No application code, production chat data, model weights or services changed in this document-only checkpoint.

## Verified source update at v5.329.43

The latest request again authorizes eligible learning from unsuccessful and incomplete chats across topics, including positive and negative logic. This confirms the contract above; no separate transcript store or unrestricted trainer is needed. The current source inspection of chatArchive.js confirms matching durable archive receipt before clearing the unchanged view, with conversationMemory.js/current owner binding. Saving is independent of whether an attempt succeeded. Actual browser clear/reload acceptance is still pending; no new browser test occurred43.

The historical37 ownership backlog below is partly superseded by implemented source40: chat_archive.py retains full JSON/transcript under verified owner; owned_vault.py and memory_router.py enforce owner-scoped reads/explicit recall; automatic memory context is owned-only and bounded, with source hashes/offsets and unverified reference labels. Legacy unassigned records are excluded from automatic context. These are retained source40 implementation/test findings, unchanged43, not new43 semantic retrieval or model-learning measurements. Private revision save still does not establish automatic indexing. Full archive inventory/secret admission, source-linked summaries/case outcomes, semantic retrieval/quality evaluation and curated model-weight training remain incomplete. Existing model versions stay intact. Cloud ledger summaries are not a bulk transcript export or a model dataset.

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

## Live observation at v5.329.34 (plan1.43)

Actual administrator BS-Chat greeting and preserved Stehouwer digest during generation are now verified; full browser save/reload/clear remains pending. Legacy backend/database/aibs_personal_intelligence.db automatically recorded the two synthetic greetings as short prompt summaries and length metadata, not complete conversations. Its default brett/stehouwer_publishing ownership and directive extraction require separate authority review before multi-user learning. Do not mistake those legacy events for the new private revision journal, semantic RAG or model training. Existing customized Modelfiles/manifest are preserved; actual model context observed8192, while old UI4096/million-window badges remain unverified claims. Close the discovered legacy generated-PowerShell bypass before broader execution/release; archived instructions remain source data only.


## Record 169 Update: Unified RAG Ingestion & Truncation Elimination
As of Record 169 (2026-10-28), the silent arbitrary character truncations in file attachments have been eliminated:
1. ackend/AI_BS_Backend.py (chat_attach_file): Removed [:15000] slice on decoded text and PDF content.
2. rontend/src/components/ChatTab.jsx & MobileStehouwerChat.jsx (4 mirrors each): Removed .slice(0, 30000) fallback slice.
3. Downstream SovereignDocumentEngine: Receives full multi-megabyte documents and applies syntactic AST section chunking (index_markdown_sections) and dynamic 3-part context windowing (optimize_document_for_context) without overflowing local Ollama VRAM limits.
