# Codex • B1 baseline classification and import readiness

**2026-11-21. Review only.** Checkout `C:\AI-BS`, branch `codex/audit-v532976-20261031`, HEAD `64fad2871e0a716d9964f506bdef1050612b173d`.

**Result.** All 178 Phase 2 provider paths exist locally and are absent from both the pinned tree and index. **52** are ignored. The 178 consist of **154 SOURCE, 18 GENERATED, 6 ASSET, 0 LOCAL-DATA and 0 UNSURE**. They include inherited baseline dependencies, feature-only inputs, and potential replacements whose current behavior is newer than the base. Being source is not a decision to track, enable, or deploy it.

**Milestones.** B01 is the first source-complete candidate for the pinned default Studio/writer frontend build. Its 17 paths do not establish that npm, the release check or Vite will run successfully on a new machine. **No subset of the 178, nor all of them together, restores all mandatory local Python startup imports.** B02 is the first *proposed* backend startup group and is **blocked**. A bounded import walk already proves at least 12 additional paths are needed; the 12 are a frontier, not an exhaustive recovery list.

## Method and scope

1. Read the “Separate provider ledger” section of PHASE2_Codex.md. Parsed 178 distinct relative paths and the 52 positive ignore flags. Checked the branch, pinned commit, index/pinned-tree membership and path existence. This is an independent Codex review; the other tool’s B1 report was not an input.
2. Ran `git --no-optional-locks -C C:\AI-BS check-ignore -v -- <path>` separately for each flagged path. Cross-checked the entire input twice using a byte stream of 178 **NUL-terminated** paths and `git check-ignore -z --stdin` with and without `-v`. Input contained no CR or LF. Nonverbose mode returned exactly the 52 flagged paths; symmetric difference was empty. Verbose mode returned 53 rule records: 52 positive exclusions and one negative re-inclusion at .gitignore:364, `!scripts/**` for `scripts/check_coding_candidate.py`. The last file is trackable. This reproduces the count without depending on another tool’s parser.
3. Read source declarations, literal import/specifier edges, consumer call sites and build plugin asset reads. Parsed Python with the standard-library AST without importing project modules. Used pinned blobs for existing callers and clearly distinguished a local provider or later working-copy caller. Compared local raw bytes for the four-way mirror sets and inspected the sync loop. One category per path: tool-produced satellite copies are GENERATED; authored CSS is ASSET; authored executable modules, build config, entry HTML and service-worker templates are SOURCE.
4. For the frontend, traced the *pinned default* Studio and writer entry/import graph; treated later chat/driver/personal release profiles separately. For backend startup, traversed unguarded module-level local imports from the pinned FastAPI entry point, using pinned files when present and only the reviewed ledger source for missing modules. Stopped at out-of-ledger paths. Also checked deferred local edges among candidates, package initializers, and examples where a provider needs a newer symbol, function signature or struct field.
5. Proposed baseline membership from those specific consumers and checked that the named ledger-to-ledger edges of B01–B04 have no forward references to later groups or deferred feature files. B02 and B04 still have inherited *outside-ledger* gaps. A path-level topological check does not prove side-effect-free module initialization, installed SDKs or API compatibility.
6. No build, test, sync, application import, listener probe, remote connection, credential-store read, or change to ignore rules was performed. The “52” result is an ignore check, not a secret-scan result. Phase 2 reported no hits for its specified patterns; that does not clear new exceptions or authorize publication.

## Ignore results by effective rule • 52 paths

All exclusions below come from **`C:\AI-BS\.gitignore`**. The line number and literal pattern in each heading apply to every path beneath it. The checkout’s Git configuration reports `core.ignorecase=true`. A slashless pattern can match a directory component and thus also exclude descendants. Verbose output reports the winning rule; other patterns can also match the same path.

### .gitignore:328 • `*accounting*` • 1 exclusions

Overbroad for this repository: it excludes a Python API router. Retain the existing `saved_data/` exclusion; use a known accounting export root such as `/saved_data/accounting/` if that is the approved location. Retain `*.csv` and `*.xlsx` for exported financial tables. For private accounting JSON outside those roots, add exact owner-confirmed paths before narrowing this blanket rule.

- `backend/modules/accounting_router.py`

### .gitignore:329 • `*crypto*` • 23 exclusions

Overbroad: it excludes handwritten backend modules and the `Crypto-Swarm` directory by name, including a Go helper with no “crypto” in its basename. Preserve scoped data rules such as `/saved_data/crypto*/` and `/trade/market_news/`. The preparation registry writes under saved_data, whereas its Python implementation is source. Preserve existing exclusions for specific key files, .env files and databases. No single filename suffix covers private exchange records; inventory any other private roots first.

- `backend/core/crypto_com_acknowledgements.py`
- `backend/core/crypto_com_adapter.py`
- `backend/core/crypto_com_native_stop.py`
- `backend/core/crypto_credential_preparation_registry.py`
- `backend/core/crypto_credential_preparation.py`
- `backend/core/crypto_current_snapshot_facts.py`
- `backend/core/crypto_current_snapshot.py`
- `backend/core/crypto_held_preparation_runtime.py`
- `backend/core/crypto_preparation_status.py`
- `backend/core/crypto_preview_chat.py`
- `backend/core/crypto_protective_lifecycle.py`
- `backend/core/crypto_reinvestment.py`
- `backend/core/crypto_spot_preview.py`
- `backend/core/crypto_spot_protection.py`
- `backend/core/crypto_trial_admission.py`
- `backend/core/crypto_trial_binding.py`
- `backend/core/crypto_trial_budget.py`
- `backend/core/crypto_trial_projection.py`
- `backend/core/crypto_trial_registry.py`
- `backend/core/crypto_trial_runtime_store.py`
- `backend/core/crypto_trial_status_chat.py`
- `backend/security/crypto_trial_root.py`
- `Crypto-Swarm/internal/daemons/public_market_data.go`

### .gitignore:332 • `*ledger*` • 2 exclusions

Overbroad: excludes the watcher and export implementation. Prefer `drip_ledger.json`, `*ledger*.jsonl` and `*ledger*.db` for named runtime artifacts, plus confirmed private ledger-export roots. Existing SQLite/JSONL guards cover much of this. A public source filename containing “ledger” does not identify private record contents.

- `backend/modules/audit_ledger_watcher.py`
- `backend/modules/personal_ledger_export.py`

### .gitignore:348 • `*NDA*` • 5 exclusions

Overbroad: substring “nda” matches “calendar” and “boundary” here. Keep `contracts_vault/` and document guards such as `*NDA*.pdf` and `*NDA*.docx` (already subsumed by broader document-extension rules). Protect additional private formats by exact storage root rather than a word inside every basename.

- `frontend/components/components/WorkspaceCalendarTab.css`
- `frontend/components/WorkspaceCalendarTab.css`
- `frontend/src/components/components/WorkspaceCalendarTab.css`
- `frontend/src/components/WorkspaceCalendarTab.css`
- `backend/security/theatrical_corpus_boundary.py`

### .gitignore:350 • `*Contract*` • 2 exclusions

Overbroad: the two matches are Python validators of response contracts. Keep `contracts_vault/` and document patterns such as `*contract*.docx` and `*contract*.pdf`, plus owner-confirmed contract archive roots. Both modules also contain “crypto”; changing only line 350 can expose the earlier line 329 as the next matching exclusion.

- `backend/core/crypto_protective_review_contract.py`
- `backend/core/crypto_trial_status_contract.py`

### .gitignore:358 • `*Screenplay*` • 11 exclusions

Overbroad: catches PDF generation code, UI handoff utilities, a native document model, and CSS. Keep `screenplay_projects/` and, for other confirmed private roots, path-specific patterns such as `/<private-screenplay-root>/**/*.fdx` and `/<private-screenplay-root>/**/*.fountain`. The angle-bracket root is a placeholder to resolve with the owner. Avoid excluding reviewed test fixtures by extension throughout the repo.

- `backend/core/screenplay_pdf.py`
- `backend/core/screenplay_professional.py`
- `frontend/components/components/ScreenplayTableReadModal.css`
- `frontend/components/ScreenplayTableReadModal.css`
- `frontend/src/components/components/ScreenplayTableReadModal.css`
- `frontend/src/components/ScreenplayTableReadModal.css`
- `frontend/src/utils/nativeScreenplayHandoff.js`
- `frontend/src/utils/screenplayAdaptation.js`
- `frontend/src/utils/screenplayHandoff.js`
- `native_studio/rich_screenplay_draft.py`
- `native_studio/screenplay_client.py`

### .gitignore:359 • `*Film*` • 4 exclusions

Overbroad: the four entries implement a film command, store API, runner and router. Keep the generated project state under `/saved_data/chat_films/` and add only confirmed private render/output and media roots. Preserve existing media/private-data guards. The FilmStore class is source even though it manages private files when invoked.

- `backend/core/chat_film_runner.py`
- `backend/core/chat_film_store.py`
- `backend/core/chat_film.py`
- `backend/routers/chat_films.py`

### .gitignore:365 • `*Book*` • 4 exclusions

This rule catches three generated stylesheet copies and one primary stylesheet; it has zero SOURCE-class hits in this ledger but does hide an authored ASSET. Preserve confirmed private manuscript roots, for example `/<private-book-root>/**`, and appropriate document formats such as `*book*.epub` or `*book*.docx`. Treat this as a proposed narrowing only after the private locations are known.

- `frontend/components/components/ScriptToBookNovelizerModal.css`
- `frontend/components/ScriptToBookNovelizerModal.css`
- `frontend/src/components/components/ScriptToBookNovelizerModal.css`
- `frontend/src/components/ScriptToBookNovelizerModal.css`

### Privacy and remotes

Root .gitignore:327 labels financial, crypto and accounting ledgers; lines 343–356 explicitly identify confidential publishing/contracts and creative manuscripts. Lines 302–305 exclude PDF, DOCX, XLSX and CSV, and other rules protect runtime/private directories. This supports a privacy purpose. Only the owner can confirm every location and the intended disclosure policy. The owner has confirmed that these protections are intentional and should be kept. The alternatives above illustrate bounded *positive excludes* for the requested analysis, not a ready-to-apply changeset proving equivalent coverage for all untracked files.

If the private-data inventory is incomplete, preserve the broad rules and consider *exact reviewed path exceptions* after the last matching rule. Do not adopt blanket `!*.py`, `!*.js`, etc. Source extensions can contain private literals, customer data or credentials. A negation cannot reopen a file under an excluded parent directory. In particular, for Crypto-Swarm a precise exception design would have to allow traversal of excluded ancestors while continuing to ignore unreviewed siblings; a single file exception is insufficient. Any approved rule change needs a before/after ignore check on positive *and negative* example paths and a separate review for newly exposed paths.

Local metadata names two configured remotes, `origin` and `stehouwer`, and eight remote-tracking refs. I did not read or publish their URLs. That establishes configuration and retained refs; push history, audience, destination visibility and current remote state are unresolved. No fetch, push or network contact.

## Ordered baseline proposal • before feature work

| Group | Ledger paths | Contents and disposition | Gate |
|---|---:|---|---|
| B01 | 17 | Pinned default frontend build inputs. Include as one reviewed tree: sync helper, four JS utilities, three primary CSS assets and nine generated CSS mirrors. | First frontend source milestone. Confirm toolchain and worktree safety before any future build. |
| B02 | 37 | Backend startup restoration unit, reviewed in three slices: 17 shared GPU/inference/identity/PDF helpers; 16 coding primitives/routers; four accounting/receipt/auth providers. Same-group import cycles and package initializers stay together. | **Blocked:** requires owner-approved recovery and recursive review of at least 12 additional local paths outside the 178 before it could be called startup-complete. Do not accept these 37 as a standalone startup fix. |
| B03 | 8 | Pinned, guarded or function-local behavior: audit watcher, attached source context, context budgeting, local chat inference, pipeline context injection, program status, project maintenance and FDX source documents. Uses B02. | Select a legacy-compatible watcher or split its newer injected-store branch. Keep non-default runtime behavior distinct from startup imports. |
| B04 | 22 | Ledger subset reached by pinned native desktop paths and their provider chains, including the native package initializer, shell views, creative entry, session and pipe transport. | Conditional on desktop scope and additional native prerequisites. It cannot certify a complete Windows package. |
| Retain for feature-specific review | 94 | Remaining source/assets/mirrors have no demonstrated need for the selected pinned milestones in this walk, or explicitly rely on future producer changes. Fxx in the ledger refers to the prior plan’s feature number. | Do not transfer current feature implementation into the baseline solely because the path is absent at HEAD. Re-evaluate after the recovered baseline exists. |

This is an ordering proposal, not authorization. B01 is independent; B02 is deliberately a conditional atomic group instead of several purportedly runnable commits with hidden forward dependencies. A group consumes pinned code, earlier groups and its own files. The first *provable* complete backend startup group under a strict 178-only limit is **none**. If every intermediate commit must boot the entire backend even before B02, the pinned starting repository already fails that source requirement. In that case recover B02 first in the eventual execution order; B01 can follow independently.

**Frontend evidence.** Pinned frontend/package.json:11,13–15 performs the release version check first, then calls the missing sync helper and Vite. Pinned index.html selects /main.jsx; writer.html selects /src/writer_main.jsx. A static walk from pinned Studio/writer inputs and Vite configuration reached 403 files and identified seven missing imported paths: three frontend/components CSS modules and four JS helpers. The 17-file B01 group also supplies the primary and other satellite CSS counterparts and the missing script. At the pinned tree the 494 existing canonical files selected by the sync traversal already have matching Git blobs in each satellite. The new three CSS families also match by raw on-disk SHA-256. This predicts source availability, not a live sync outcome.

Important prebuild caveat: the pinned source version is 5.329.145; working-tree version markers belong to a later feature plan. All 16 pinned version inputs match the LF form expected by scripts/release-version.cjs. The validator compares raw bytes; this machine has core.autocrlf=true and the pinned tree contains no .gitattributes. A checkout that materializes those files as CRLF can fail before sync. Node/Python/Vite and a matching locked install remain untested. The working sync script also has a hardcoded main-checkout fallback. Select an isolation and line-ending policy before any later build authorization.

**Backend evidence.** Starting at pinned backend/AI_BS_Backend.py, the restricted module-level walk visited 145 Python files, 32 supplied by the provider ledger. Following additional in-ledger guarded imports and package initialization for those candidates brings the modeled B02 subset to 37. The following edges encounter *local paths outside both the pinned tree and the 178*. Git/source path checks only; no credential or data store was opened. The line cites the importing file at the pin.

| Outside-ledger dependency | First recorded importer |
|---|---|
| `backend/routers/comfyui_workspace_router.py` | `backend/AI_BS_Backend.py:2048` |
| `backend/routers/calendar_tasks_router.py` | `backend/AI_BS_Backend.py:2060` |
| `backend/core/cryptographic_vault.py` | `backend/AI_BS_Backend.py:3299` |
| `backend/security/analytics_access.py` | `backend/commercial_gateway/gateway_router.py:9` |
| `backend/security/vault_access.py` | `backend/modules/vault_router.py:9` |
| `backend/security/screenwriting_access.py` | `backend/routers/screenwriting_router.py:20` |
| `backend/routers/conversation_router.py` | `backend/routers/screenwriting_router.py:21` |
| `backend/core/adaptation_store.py` | `backend/routers/screenwriting_router.py:159` |
| `backend/core/chat_archive.py` | `backend/routers/memory_router.py:21` |
| `game_trainer/core/memory.py` | `backend/routers/memory_lab_router.py:20` |
| `game_trainer/profiles/btd6_profile.py` | `backend/routers/memory_lab_router.py:21` |
| `backend/core/code_quality_gate.py` | `backend/core/coding_workflow.py:19` |

Three are unconditional direct imports in AI_BS_Backend.py itself (2048, 2060 and 3299). The others appear through routers and modules, including code-quality, conversation and game-trainer dependencies. Classification of these 12 is deliberately outside the 178-row ledger. Their own imports, package initializers and import-time behavior have not been signed off. Guarded imports such as the optional FE/music/canvas paths are a separate runtime profile, not additional proof that startup works. The native baseline similarly references unlisted runtime_policy, navigation_registry, window_geometry and other view modules.

**Two counterexamples to “include all providers first.”** The new Go helper uses `c.publicHTTPClient` at public_market_data.go:21; the pinned CryptoComClient lacks that field. Its two new public-data parsing helpers are needed by the later trading change. Keep the Go source with F11, or approve an explicitly reviewed prerequisite field change. The local audit watcher passes store= and raise_on_read_error= at audit_ledger_watcher.py:144 on an injected-store path; pinned cdz_audit_db.py’s ingest_ledger_file accepts file_path and client_id. Ordinary import presence cannot fix a runtime signature mismatch. The current coding-review router also includes a new coding-mode subrouter; choose a faithful historic version or explicitly approve the changed feature surface before treating the current file as “baseline.”

## Classification ledger • exactly one row per input path

**How to read the evidence:** SOURCE includes executable/configuration inputs and authored HTML/service-worker templates. GENERATED takes precedence for mechanically maintained satellite copies even when Git tracks mirrors by policy. ASSET covers canonical CSS read by the UI build. Database/store names in Python/JS filenames describe implementations, not database or runtime-state files. The prefix “pinned” means the reference was inspected in a pinned caller; “provider” means it occurs in a new local provider; “working” means it occurs in a later working-copy caller. A referenced provider inside a function or guard is a deferred call path. Counts are about this ledger only.

| Path | Class | Group | Evidence: file type, consumer and role |
|---|---|---|---|
| `backend/modules/audit_ledger_watcher.py` | SOURCE | B03 | Python module defining `CDZAuditLedgerWatcher`; `backend/routers/audit_ledger_router.py:12` imports it (top-level pinned). |
| `backend/core/attached_source_context.py` | SOURCE | B03 | Python module defining `AttachedSourceError`; `backend/core/sovereign_reasoning/dispatcher.py:427` imports it (deferred/guarded pinned). |
| `backend/core/chat_context_budget.py` | SOURCE | B03 | Python module defining `ChatContextBudgetError`; `scripts/tests/test_chat_context_budget.py:16` imports it (top-level pinned). |
| `backend/core/chat_pdf_sources.py` | SOURCE | B02 | Python module defining `PDFSourceError`; `backend/routers/screenwriting_router.py:177` imports it (deferred/guarded pinned). |
| `backend/core/local_chat_inference.py` | SOURCE | B03 | Python module defining `LocalInferenceError`; `backend/core/sovereign_reasoning/dispatcher.py:149` imports it (deferred/guarded pinned). |
| `backend/core/local_ollama_http.py` | SOURCE | B02 | Python module defining `canonicalize_tool_definitions`; `backend/routers/agent_routing.py:15` imports it (top-level pinned). |
| `backend/core/owned_rag_sources.py` | SOURCE | B02 | Python module defining `_word_spans`; `backend/core/sovereign_reasoning/dispatcher.py:433` imports it (deferred/guarded pinned). |
| `backend/core/owned_vault.py` | SOURCE | B02 | Python module defining `VaultEvidenceError`; `backend/AI_BS_Backend.py:12109` imports it (deferred/guarded pinned). |
| `backend/core/pdf_text_source.py` | SOURCE | B02 | Python module defining `PDFTextSourceError`; `backend/core/chat_pdf_sources.py:111` imports it (deferred/guarded provider). |
| `backend/core/personal_memory_scope.py` | SOURCE | B02 | Python module defining `bind_memory_principal`; `backend/routers/screenwriting_router.py:59` imports it (deferred/guarded pinned). |
| `backend/core/pipeline_context_injector.py` | SOURCE | B03 | Python module defining `get_current_build_version`; `backend/core/sovereign_reasoning/dispatcher.py:498` imports it (deferred/guarded pinned). |
| `backend/core/program_status_readonly.py` | SOURCE | B03 | Python module defining `is_program_update_question`; `backend/core/sovereign_reasoning/dispatcher.py:492` imports it (deferred/guarded pinned). |
| `backend/core/screenplay_pdf.py` | SOURCE | B02 | Python module defining `ScreenplayPdfError`; `backend/core/screenplay_professional.py:20` imports it (top-level provider). |
| `backend/core/screenplay_professional.py` | SOURCE | B02 | Python module defining `ProfessionalScreenplayError`; `backend/core/fdx_professional_pdf.py:15` imports it (top-level provider). |
| `backend/core/sovereign_reasoning/dag_topological_reasoner.py` | SOURCE | F05 | Python module defining `SecretRetentionVault`; `backend/core/sovereign_reasoning/dispatcher.py:573` imports it (deferred/guarded working). |
| `backend/gpu/__init__.py` | SOURCE | B02 | Python package initializer; imports .compute_scheduler and re-exports the scheduler API when Python initializes the gpu package. |
| `backend/gpu/compute_scheduler.py` | SOURCE | B02 | Python module defining `GPUAdmissionError`; `scripts/tests/test_local_ollama_http.py:14` imports it (top-level pinned). |
| `backend/gpu/gpu_telemetry.py` | SOURCE | B02 | Python module defining `finite_number`; `backend/gpu/vram_manager.py:4` imports it (top-level provider). |
| `backend/gpu/model_residency.py` | SOURCE | B02 | Python module defining `ModelResidencyManager`; `backend/gpu/compute_scheduler.py:16` imports it (top-level provider). |
| `backend/gpu/stability_supervisor.py` | SOURCE | B02 | Python module defining `StabilitySupervisor`; `backend/gpu/compute_scheduler.py:17` imports it (top-level provider). |
| `backend/gpu/vram_manager.py` | SOURCE | B02 | Python module defining `available_budget_mib`; `backend/gpu/compute_scheduler.py:18` imports it (top-level provider). |
| `backend/orchestrator/__init__.py` | SOURCE | B02 | Python package initializer for imports such as orchestrator.gpu_task_dispatcher; the file contains package documentation. |
| `backend/orchestrator/gpu_task_dispatcher.py` | SOURCE | B02 | Python module defining `admitted_options`; `backend/routers/agent_routing.py:17` imports it (top-level pinned). |
| `backend/core/coding_journal.py` | SOURCE | B02 | Python module defining `write_json_record`; `backend/core/crypto_com_acknowledgements.py:11` imports it (top-level provider). |
| `backend/core/coding_locks.py` | SOURCE | B02 | Python module defining `record_lock`; `backend/tools/tool_registry.py:43` imports it (deferred/guarded pinned). |
| `backend/core/coding_process.py` | SOURCE | B02 | Python module defining `run_bounded_check`; `backend/core/coding_mode_local.py:21` imports it (top-level provider). |
| `backend/core/project_maintenance.py` | SOURCE | B03 | Python module defining `utc`; `backend/tools/tool_registry.py:4551` imports it (deferred/guarded pinned). |
| `backend/core/fdx_professional_pdf.py` | SOURCE | F07 | Python module defining `TypedFdxPdfError`; `backend/routers/screenwriting_router.py:1531` imports it (deferred/guarded working). |
| `backend/core/fdx_source_documents.py` | SOURCE | B03 | Python module defining `FDXSourceError`; `backend/routers/screenwriting_router.py:184` imports it (deferred/guarded pinned). |
| `frontend/components/components/ScreenplayTableReadModal.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/ScreenplayTableReadModal.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (029f28635eac…). |
| `frontend/components/components/ScriptToBookNovelizerModal.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/ScriptToBookNovelizerModal.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (52348d70bfaf…). |
| `frontend/components/components/WorkspaceCalendarTab.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/WorkspaceCalendarTab.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (5156b3a709aa…). |
| `frontend/components/ScreenplayTableReadModal.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/ScreenplayTableReadModal.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (029f28635eac…). |
| `frontend/components/ScriptToBookNovelizerModal.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/ScriptToBookNovelizerModal.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (52348d70bfaf…). |
| `frontend/components/WorkspaceCalendarTab.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/WorkspaceCalendarTab.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (5156b3a709aa…). |
| `frontend/scripts/sync_mirrors.py` | SOURCE | B01 | Python build tool invoked by pinned frontend/package.json:11,15. Its primary-to-satellite copy loop is at 48–81; it is a generator, not its output. |
| `frontend/src/components/components/ScreenplayTableReadModal.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/ScreenplayTableReadModal.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (029f28635eac…). |
| `frontend/src/components/components/ScriptToBookNovelizerModal.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/ScriptToBookNovelizerModal.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (52348d70bfaf…). |
| `frontend/src/components/components/WorkspaceCalendarTab.css` | GENERATED | B01 | CSS satellite of `frontend/src/components/WorkspaceCalendarTab.css`; sync writes this destination if bytes differ. Same SHA-256 as primary (5156b3a709aa…). |
| `frontend/src/components/ScreenplayTableReadModal.css` | ASSET | B01 | Authored primary CSS; pinned ScreenplayTableReadModal.jsx:2 imports the stylesheet. The sync tool reads this input to produce three satellite copies. |
| `frontend/src/components/ScriptToBookNovelizerModal.css` | ASSET | B01 | Authored primary CSS; pinned ScriptToBookNovelizerModal.jsx:2 imports the stylesheet. The sync tool reads this input to produce three satellite copies. |
| `frontend/src/components/WorkspaceCalendarTab.css` | ASSET | B01 | Authored primary CSS; pinned WorkspaceCalendarTab.jsx:9 imports the stylesheet. The sync tool reads this input to produce three satellite copies. |
| `frontend/src/utils/nativeScreenplayHandoff.js` | SOURCE | B01 | JavaScript module; `frontend/components/ScreenwritingTab.jsx:22` references it via a literal import or entry (literal pinned). |
| `frontend/src/utils/screenplayAdaptation.js` | SOURCE | B01 | JavaScript module; `frontend/components/ScreenwritingTab.jsx:5` references it via a literal import or entry (literal pinned). |
| `frontend/src/utils/screenplayHandoff.js` | SOURCE | B01 | JavaScript module; `scripts/tests/test_mobile_attached_sources.mjs:8` references it via a literal import or entry (literal pinned). |
| `frontend/utils/fdxDocumentFormat.js` | SOURCE | B01 | JavaScript helper imported by pinned frontend/src/components/RichFDXEditor.jsx:2 and frontend/src/utils/richFdxDraft.js:1 for FDX document formatting. |
| `backend/core/chat_film_runner.py` | SOURCE | F08 | Python module defining `start`; `backend/core/chat_film.py:30` imports it (deferred/guarded provider). |
| `backend/core/chat_film_store.py` | SOURCE | F08 | Python module defining `owner_key`; `backend/core/chat_film.py:4` imports it (top-level provider). |
| `backend/core/chat_film.py` | SOURCE | F08 | Python module defining `describe`; `backend/core/media_intent_policy.py:175` imports it (deferred/guarded working). |
| `backend/core/video_workflows.py` | SOURCE | F08 | Python module defining `video_capabilities`; `backend/core/chat_film_runner.py:12` imports it (top-level provider). |
| `backend/routers/chat_films.py` | SOURCE | F08 | Python module defining `download`; `backend/AI_BS_Backend.py:2148` imports it (top-level working). |
| `backend/core/coding_mode_execution.py` | SOURCE | B02 | Python module defining `ExecutionPayload`; `backend/routers/coding_mode_router.py:3` imports it (top-level provider). |
| `backend/core/coding_mode_local.py` | SOURCE | B02 | Python module defining `available`; `backend/core/coding_mode_execution.py:25` imports it (top-level provider). |
| `backend/core/coding_preparation_planning.py` | SOURCE | B02 | Python module defining `PlanPayload`; `backend/routers/coding_preparation_router.py:8` imports it (top-level provider). |
| `backend/core/coding_preparation_proposals.py` | SOURCE | B02 | Python module defining `ProposalPayload`; `backend/routers/coding_preparation_router.py:9` imports it (top-level provider). |
| `backend/core/coding_preparation.py` | SOURCE | B02 | Python module defining `PreparationConflict`; `backend/routers/coding_preparation_router.py:4` imports it (top-level provider). |
| `backend/core/coding_recovery.py` | SOURCE | B02 | Python module defining `worker_identity`; `backend/routers/coding_review_router.py:8` imports it (top-level provider). |
| `backend/core/coding_repository_snapshot.py` | SOURCE | B02 | Python module defining `_root`; `backend/core/coding_preparation.py:20` imports it (top-level provider). |
| `backend/core/coding_syntax.py` | SOURCE | B02 | Python module defining `available`; `backend/core/coding_mode_execution.py:24` imports it (top-level provider). |
| `backend/core/coding_vm_inputs.py` | SOURCE | B02 | Python module defining `_require`; `backend/core/coding_repository_snapshot.py:17` imports it (top-level provider). |
| `backend/core/coding_vm_staging.py` | SOURCE | B02 | Python module defining `_FileInformation`; `backend/core/coding_repository_snapshot.py:18` imports it (top-level provider). |
| `backend/routers/coding_mode_router.py` | SOURCE | B02 | Python module defining `ApplyPayload`; `backend/routers/coding_review_router.py:12` imports it (top-level provider). |
| `backend/routers/coding_preparation_router.py` | SOURCE | B02 | Python module defining `require_preparation_owner`; `backend/routers/coding_mode_router.py:4` imports it (top-level provider). |
| `backend/routers/coding_review_router.py` | SOURCE | B02 | Python module defining `require_coding_admin`; `backend/AI_BS_Backend.py:2127` imports it (top-level pinned). |
| `backend/security/firebase_auth.py` | SOURCE | B02 | Python module defining `firebase_admin_principal`; `backend/routers/screenwriting_router.py:58` imports it (deferred/guarded pinned). |
| `frontend/components/CodingModePanel.jsx` | GENERATED | F09 | JSX satellite of `frontend/src/components/CodingModePanel.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (2c42ab9432ca…). |
| `frontend/components/components/CodingModePanel.jsx` | GENERATED | F09 | JSX satellite of `frontend/src/components/CodingModePanel.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (2c42ab9432ca…). |
| `frontend/src/components/CodingModePanel.jsx` | SOURCE | F09 | React JSX module; `frontend/src/components/ChatTab.jsx:10` references it via a literal import or entry (literal working). |
| `frontend/src/components/components/CodingModePanel.jsx` | GENERATED | F09 | JSX satellite of `frontend/src/components/CodingModePanel.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (2c42ab9432ca…). |
| `frontend/src/utils/chatStream.js` | SOURCE | F09 | JavaScript module; `scripts/tests/test_mobile_attached_sources.mjs:10` references it via a literal import or entry (literal working). |
| `frontend/src/utils/codingMode.js` | SOURCE | F09 | JavaScript module; `frontend/src/utils/codingModeClient.js:2` references it via a literal import or entry (literal provider). |
| `frontend/src/utils/codingModeClient.js` | SOURCE | F09 | JavaScript module; `frontend/components/CodingModePanel.jsx:7` references it via a literal import or entry (literal provider). |
| `backend/core/crypto_com_acknowledgements.py` | SOURCE | F11 | Python module defining `_hash`; `backend/core/crypto_protective_lifecycle.py:11` imports it (top-level provider). |
| `backend/core/crypto_com_adapter.py` | SOURCE | F11 | Python module defining `_client_id`; `backend/core/crypto_protective_lifecycle.py:12` imports it (top-level provider). |
| `backend/core/crypto_com_native_stop.py` | SOURCE | F11 | Python module defining `build_native_stop_draft`; `backend/core/crypto_protective_lifecycle.py:13` imports it (top-level provider). |
| `backend/core/crypto_credential_preparation_registry.py` | SOURCE | F11 | Python module defining `_principal`; `backend/core/crypto_held_preparation_runtime.py:17` imports it (top-level provider). |
| `backend/core/crypto_credential_preparation.py` | SOURCE | F11 | Python module defining `CredentialPreparation`; `backend/core/crypto_held_preparation_runtime.py:16` imports it (top-level provider). |
| `backend/core/crypto_current_snapshot_facts.py` | SOURCE | F11 | Python module defining `_decimal`; `backend/core/crypto_current_snapshot.py:19` imports it (top-level provider). |
| `backend/core/crypto_current_snapshot.py` | SOURCE | F11 | Python module defining `CurrentSnapshot`; `backend/core/crypto_held_preparation_runtime.py:18` imports it (top-level provider). |
| `backend/core/crypto_held_preparation_runtime.py` | SOURCE | F11 | Python module defining `_document`; `backend/core/crypto_preparation_status.py:52` imports it (deferred/guarded provider). |
| `backend/core/crypto_preparation_status.py` | SOURCE | F11 | Python module defining `validate_preparation_status`; `backend/core/crypto_trial_status_chat.py:27` imports it (deferred/guarded provider). |
| `backend/core/crypto_preview_chat.py` | SOURCE | F11 | Python module defining `crypto_preview_declarations`; `backend/routers/trading_router.py:65` imports it (deferred/guarded working). |
| `backend/core/crypto_protective_lifecycle.py` | SOURCE | F11 | Python module defining `OfflineProtectiveLifecycle`; `backend/core/crypto_trial_registry.py:147` imports it (deferred/guarded provider). |
| `backend/core/crypto_protective_review_contract.py` | SOURCE | F11 | Python module defining `validate_protective_review`; `backend/core/crypto_trial_status_chat.py:44` imports it (deferred/guarded provider). |
| `backend/core/crypto_reinvestment.py` | SOURCE | F11 | Python module defining `OfflineReinvestment`; `backend/core/crypto_protective_lifecycle.py:15` imports it (top-level provider). |
| `backend/core/crypto_spot_preview.py` | SOURCE | F11 | Python module defining `preview_cro_spot`; `backend/tools/bs_chat_tool_bridge.py:151` imports it (deferred/guarded provider). |
| `backend/core/crypto_spot_protection.py` | SOURCE | F11 | Python module defining `review_cro_protection`; `backend/tools/bs_chat_tool_bridge.py:188` imports it (deferred/guarded provider). |
| `backend/core/crypto_trial_admission.py` | SOURCE | F11 | Python module defining `TrialEntryHeld`; `backend/core/crypto_trial_runtime_store.py:23` imports it (top-level provider). |
| `backend/core/crypto_trial_binding.py` | SOURCE | F11 | Python module defining `CurrentAccountObservation`; `backend/core/crypto_credential_preparation.py:15` imports it (top-level provider). |
| `backend/core/crypto_trial_budget.py` | SOURCE | F11 | Python module defining `create_baseline`; `backend/core/crypto_reinvestment.py:15` imports it (top-level provider). |
| `backend/core/crypto_trial_projection.py` | SOURCE | F11 | Python module defining `project_trial_budget`; `backend/core/crypto_protective_lifecycle.py:16` imports it (top-level provider). |
| `backend/core/crypto_trial_registry.py` | SOURCE | F11 | Python module defining `_answer`; `backend/tools/bs_chat_tool_bridge.py:99` imports it (deferred/guarded provider). |
| `backend/core/crypto_trial_runtime_store.py` | SOURCE | F11 | Python module defining `_key`; `backend/core/crypto_trial_registry.py:16` imports it (top-level provider). |
| `backend/core/crypto_trial_status_chat.py` | SOURCE | F11 | Python module defining `crypto_trial_status_declarations`; `backend/tools/tool_registry.py:146` imports it (deferred/guarded working). |
| `backend/core/crypto_trial_status_contract.py` | SOURCE | F11 | Python module defining `validate_trial_status`; `backend/core/crypto_trial_registry.py:27` imports it (deferred/guarded provider). |
| `backend/security/crypto_trial_root.py` | SOURCE | F11 | Python module defining `TrialRootError`; `backend/core/crypto_credential_preparation_registry.py:10` imports it (top-level provider). |
| `backend/security/theatrical_corpus_boundary.py` | SOURCE | F11 | Python module defining `CorpusBoundaryError`; `backend/security/crypto_trial_root.py:20` imports it (top-level provider). |
| `backend/security/theatrical_storage_roots.py` | SOURCE | F11 | Python module defining `_fail`; `backend/security/crypto_trial_root.py:19` imports it (top-level provider). |
| `backend/tools/bs_chat_tool_bridge.py` | SOURCE | F11 | Python module defining `BSChatToolBridge`; `backend/routers/trading_router.py:71` imports it (deferred/guarded working). |
| `Crypto-Swarm/internal/daemons/public_market_data.go` | SOURCE | F11 | Go package implementation; later trade_engine.go calls publicMarketData, marketPrecision and marketPrice. Its receiver reads a field missing from the pinned type. |
| `scripts/check_coding_candidate.py` | SOURCE | F11 | Python diagnostic helper dynamically loaded by the local backend/tools/bs_chat_tool_bridge.py:201–203. No script was executed. |
| `frontend/components/BrandCampaignManager.jsx` | GENERATED | F12 | JSX satellite of `frontend/src/components/BrandCampaignManager.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (12f3e742d3b8…). |
| `frontend/components/components/BrandCampaignManager.jsx` | GENERATED | F12 | JSX satellite of `frontend/src/components/BrandCampaignManager.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (12f3e742d3b8…). |
| `frontend/components/components/OutreachReceipts.jsx` | GENERATED | F12 | JSX satellite of `frontend/src/components/OutreachReceipts.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (64f2aea5b237…). |
| `frontend/components/OutreachReceipts.jsx` | GENERATED | F12 | JSX satellite of `frontend/src/components/OutreachReceipts.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (64f2aea5b237…). |
| `frontend/src/components/BrandCampaignManager.jsx` | SOURCE | F12 | React JSX module; `frontend/src/components/BetaAnalyticsTab.jsx:6` references it via a literal import or entry (literal working). |
| `frontend/src/components/components/BrandCampaignManager.jsx` | GENERATED | F12 | JSX satellite of `frontend/src/components/BrandCampaignManager.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (12f3e742d3b8…). |
| `frontend/src/components/components/OutreachReceipts.jsx` | GENERATED | F12 | JSX satellite of `frontend/src/components/OutreachReceipts.jsx`; sync writes this destination if bytes differ. Same SHA-256 as primary (64f2aea5b237…). |
| `frontend/src/components/OutreachReceipts.jsx` | SOURCE | F12 | React JSX module; `frontend/src/components/BrandCampaignManager.jsx:4` references it via a literal import or entry (literal provider). |
| `frontend/src/utils/productionsCloudAnalytics.js` | SOURCE | F12 | JavaScript module; `frontend/src/utils/analyticsData.js:1` references it via a literal import or entry (literal working). |
| `backend/core/payment_receipts.py` | SOURCE | B02 | Python module defining `PaymentConflict`; `backend/modules/personal_ledger_export.py:9` imports it (top-level provider). |
| `backend/fe_express_owned_records.py` | SOURCE | F13 | Python module defining `database_path`; `backend/routers/fe_driver_registration.py:9` imports it (deferred/guarded provider). |
| `backend/fe_truck_profiles.py` | SOURCE | F13 | Python module defining `profile_connection`; `backend/routers/fe_driver_registration.py:10` imports it (deferred/guarded provider). |
| `backend/modules/accounting_router.py` | SOURCE | B02 | Python module defining `get_db`; `backend/AI_BS_Backend.py:220` imports it (top-level pinned). |
| `backend/modules/personal_export_parts.py` | SOURCE | F13 | Python module defining `snapshot`; `backend/modules/personal_ledger_export.py:66` imports it (deferred/guarded provider). |
| `backend/modules/personal_filing_archive.py` | SOURCE | F13 | Python module defining `complete_archive`; `backend/modules/personal_ledger_export.py:64` imports it (deferred/guarded provider). |
| `backend/modules/personal_financial_filings.py` | SOURCE | F13 | Python module defining `FinancialFiling`; `backend/modules/personal_filing_archive.py:9` imports it (top-level provider). |
| `backend/modules/personal_ledger_export.py` | SOURCE | F13 | Python module defining `ledger_reader`; `backend/modules/personal_export_parts.py:42` imports it (deferred/guarded provider). |
| `backend/modules/personal_payment_documents.py` | SOURCE | F13 | Python module defining `failure`; `backend/modules/personal_filing_archive.py:7` imports it (top-level provider). |
| `backend/modules/personal_payments.py` | SOURCE | F13 | Python module defining `ManualPayment`; `backend/modules/personal_financial_filings.py:7` imports it (top-level provider). |
| `backend/modules/personal_year_archive.py` | SOURCE | F13 | Python module defining `encoded`; `backend/modules/personal_filing_archive.py:8` imports it (top-level provider). |
| `backend/routers/fe_driver_registration.py` | SOURCE | F13 | Python module defining `register_driver_portal`; `backend/AI_BS_Backend.py:1400` imports it (top-level working). |
| `backend/security/document_retention.py` | SOURCE | B02 | Python module defining `_relative_parts`; `backend/AI_BS_Backend.py:8093` imports it (deferred/guarded pinned). |
| `backend/security/financial_auth.py` | SOURCE | B02 | Python module defining `require_financial_owner`; `backend/modules/personal_financial_filings.py:9` imports it (top-level provider). |
| `native_studio/__init__.py` | SOURCE | B04 | Python package initializer; pinned app.py:150 and bs_chat_ide_full.py:962 consume its __version__ export. The fallback reads a hardcoded main-checkout version path. |
| `native_studio/ai_bs_ide_terminal.py` | SOURCE | B04 | Python module defining `shell_argv`; `native_studio/process_batch_view.py:265` imports it (deferred/guarded provider). |
| `native_studio/audio_kernel.py` | SOURCE | B04 | Python module defining `SpscRing`; `native_studio/screenwriting_modals.py:59` imports it (deferred/guarded provider). |
| `native_studio/coding_mode_service.py` | SOURCE | F14 | Python module defining `coding_mode_enabled`; `native_studio/coding_mode_view.py:9` imports it (top-level provider). |
| `native_studio/coding_mode_view.py` | SOURCE | F14 | Python module defining `CodingModeView`; `native_studio/bs_chat_ide_full.py:501` imports it (deferred/guarded working). |
| `native_studio/creation_suite_subtools.py` | SOURCE | B04 | Python module defining `VideoStudioPage`; `native_studio/screenwriting_view.py:387` imports it (deferred/guarded provider). |
| `native_studio/creative_handoff.py` | SOURCE | B04 | Python module defining `active_script_snapshot`; `native_studio/creation_suite_subtools.py:63` imports it (top-level provider). |
| `native_studio/creative_pipe_bootstrap.py` | SOURCE | B04 | Python module defining `PipeBootstrapError`; `native_studio/creative_session.py:158` imports it (deferred/guarded provider). |
| `native_studio/creative_pipe_io.py` | SOURCE | B04 | Python module defining `PipeIOError`; `native_studio/creative_pipe_transport.py:10` imports it (top-level provider). |
| `native_studio/creative_pipe_transport.py` | SOURCE | B04 | Python module defining `CreativePipeTransport`; `native_studio/creative_session.py:145` imports it (deferred/guarded provider). |
| `native_studio/creative_session.py` | SOURCE | B04 | Python module defining `silence_native_bootstrap_output`; `native_studio/native_creative_entry.py:9` imports it (top-level provider). |
| `native_studio/creative_wire.py` | SOURCE | B04 | Python module defining `WireError`; `native_studio/creative_pipe_transport.py:11` imports it (top-level provider). |
| `native_studio/local_refactor_view.py` | SOURCE | B04 | Python module defining `prepare_local_proposal`; `native_studio/process_batch_view.py:272` imports it (deferred/guarded provider). |
| `native_studio/native_creative_entry.py` | SOURCE | B04 | Python module defining `create_native_creative_window`; `native_studio/app.py:95` imports it (deferred/guarded pinned). |
| `native_studio/owned_process.py` | SOURCE | B04 | Python module defining `OwnedProcessError`; `native_studio/local_refactor_view.py:13` imports it (top-level provider). |
| `native_studio/packaged_writer_acceptance.py` | SOURCE | F14 | Python module defining `need`; `native_studio/app.py:106` imports it (deferred/guarded working). |
| `native_studio/process_batch_view.py` | SOURCE | B04 | Python module defining `shared_batch_controller`; `native_studio/bs_chat_ide_full.py:457` imports it (deferred/guarded pinned). |
| `native_studio/process_batch.py` | SOURCE | B04 | Python module defining `BatchLimits`; `native_studio/syntax_check.py:8` imports it (top-level provider). |
| `native_studio/responsive_layout.py` | SOURCE | B04 | Python module defining `FlowLayout`; `native_studio/process_batch_view.py:288` imports it (deferred/guarded provider). |
| `native_studio/rich_screenplay_draft.py` | SOURCE | B04 | Python module defining `RichDraftError`; `native_studio/screenplay_client.py:17` imports it (top-level provider). |
| `native_studio/screenplay_client.py` | SOURCE | B04 | Python module defining `ScreenplayError`; `native_studio/syntax_check.py:10` imports it (top-level provider). |
| `native_studio/screenwriting_modals.py` | SOURCE | B04 | Python module defining `format_eighths`; `native_studio/screenwriting_view.py:1748` imports it (deferred/guarded provider). |
| `native_studio/screenwriting_view.py` | SOURCE | B04 | Python module defining `BeatCardWidget`; `native_studio/app.py:179` imports it (top-level pinned). |
| `native_studio/syntax_check.py` | SOURCE | F14 | Python module defining `SyntaxCheck`; `native_studio/bs_chat_ide_full.py:2308` imports it (deferred/guarded working). |
| `native_studio/syntax_worker.py` | SOURCE | F14 | Python module defining `inspect_snapshot`; `native_studio/syntax_check.py:11` imports it (top-level provider). |
| `native_studio/theme.py` | SOURCE | B04 | Python module defining `severity_color`; `native_studio/app.py:154` imports it (top-level pinned). |
| `native_studio/windows_profile.py` | SOURCE | B04 | Python module defining `WindowsProfileError`; `native_studio/screenplay_client.py:426` imports it (deferred/guarded provider). |
| `frontend/bs-chat.html` | SOURCE | F15 | Authored HTML entry; `frontend/vite.bs-chat.config.mjs:6` selects it as a build input (literal provider). |
| `frontend/bs-chat.jsx` | SOURCE | F15 | React JSX module; `frontend/bs-chat.html:15` references it via a literal import or entry (literal provider). |
| `frontend/driver/index.html` | SOURCE | F15 | Authored HTML entry; `frontend/vite.driver.config.mjs:47` selects it as a build input (literal provider). |
| `frontend/driver/main.jsx` | SOURCE | F15 | React JSX module; `frontend/driver/index.html:2` references it via a literal import or entry (literal provider). |
| `frontend/personal/index.html` | SOURCE | F15 | Authored HTML entry; `frontend/vite.release.config.mjs:7` selects it as a build input (literal provider). |
| `frontend/personal/main.jsx` | SOURCE | F15 | React JSX module; `frontend/personal/index.html:2` references it via a literal import or entry (literal provider). |
| `frontend/public/driver/manifest.webmanifest` | SOURCE | F15 | Web app manifest configuration; linked by driver/index.html and read by the driver Vite plugin while building the asset manifest. The emitted asset manifest is a different file. |
| `frontend/public/driver/sw.js` | SOURCE | F15 | Service-worker source template. The driver Vite plugin reads it and substitutes a build identifier to emit dist/driver/sw.js. |
| `frontend/public/personal/sw.js` | SOURCE | F15 | Service-worker source template. The personal Vite plugin reads it and substitutes a build identifier to emit dist/personal/sw.js. |
| `frontend/src/fe-express/driver.css` | ASSET | F15 | Stylesheet; `frontend/driver/main.jsx:4` loads it for UI styling (literal provider). |
| `frontend/src/fe-express/driverClient.js` | SOURCE | F15 | JavaScript module; `frontend/src/fe-express/DriverPortal.jsx:6` references it via a literal import or entry (literal provider). |
| `frontend/src/fe-express/DriverPortal.jsx` | SOURCE | F15 | React JSX module; `frontend/driver/main.jsx:3` references it via a literal import or entry (literal provider). |
| `frontend/src/fe-express/truckProfile.css` | ASSET | F15 | Stylesheet; `frontend/src/fe-express/TruckProfile.jsx:3` loads it for UI styling (literal provider). |
| `frontend/src/fe-express/TruckProfile.jsx` | SOURCE | F15 | React JSX module; `frontend/src/fe-express/DriverPortal.jsx:7` references it via a literal import or entry (literal provider). |
| `frontend/src/fe-express/truckProfileStore.js` | SOURCE | F15 | JavaScript module; `frontend/src/fe-express/TruckProfile.jsx:2` references it via a literal import or entry (literal provider). |
| `frontend/src/personal-finance/FinancialFilings.jsx` | SOURCE | F15 | React JSX module; `frontend/src/personal-finance/PersonalFinancePortal.jsx:7` references it via a literal import or entry (literal provider). |
| `frontend/src/personal-finance/MultipartExport.jsx` | SOURCE | F15 | React JSX module; `frontend/src/personal-finance/PersonalFinancePortal.jsx:9` references it via a literal import or entry (literal provider). |
| `frontend/src/personal-finance/OfflineShell.jsx` | SOURCE | F15 | React JSX module; `frontend/src/personal-finance/PersonalFinancePortal.jsx:8` references it via a literal import or entry (literal provider). |
| `frontend/src/personal-finance/personal.css` | ASSET | F15 | Stylesheet; `frontend/personal/main.jsx:4` loads it for UI styling (literal provider). |
| `frontend/src/personal-finance/personalClient.js` | SOURCE | F15 | JavaScript module; `frontend/src/personal-finance/PersonalFinancePortal.jsx:6` references it via a literal import or entry (literal provider). |
| `frontend/src/personal-finance/PersonalFinancePortal.jsx` | SOURCE | F15 | React JSX module; `frontend/personal/main.jsx:3` references it via a literal import or entry (literal provider). |
| `frontend/src/personal-finance/PersonalSignIn.jsx` | SOURCE | F15 | React JSX module; `frontend/src/personal-finance/PersonalFinancePortal.jsx:4` references it via a literal import or entry (literal provider). |
| `frontend/src/utils/feExpressOfflineStore.js` | SOURCE | F15 | JavaScript module; `frontend/src/fe-express/driverClient.js:1` references it via a literal import or entry (literal provider). |
| `frontend/vite.bs-chat.config.mjs` | SOURCE | F15 | Vite configuration; `frontend/vite.driver.config.mjs:4` references it via a literal import or entry (literal provider). |
| `frontend/vite.driver.config.mjs` | SOURCE | F15 | Vite configuration; `frontend/vite.release.config.mjs:2` references it via a literal import or entry (literal provider). |
| `frontend/vite.personal.config.mjs` | SOURCE | F15 | Vite configuration; `frontend/vite.release.config.mjs:3` references it via a literal import or entry (literal provider). |
| `frontend/vite.release.config.mjs` | SOURCE | F15 | Authored Vite configuration; later frontend/package.json requests this profile for build:release; merges driver/personal inputs. |

## Required owner decisions and publication hold

1. **Preserve the policy.** The owner has confirmed the financial and publishing rules are intentional. Keep them. Prefer individual, reviewed path exceptions over unrestricted source-extension allowlists. A filename with a source extension can still disclose proprietary strategy, private text or a credential. For a generated mirror, decide explicitly whether project parity policy requires the generated bytes in Git as well as the primary. Do not interpret classification as a clearance decision.
2. **Remote audience and trading ownership.** Two remotes are configured; their audience, actual push history and intended publication rights were not determined locally. Obtain the owner’s answer separately for each destination and for proprietary trading logic. Line 329 has 23 winning matches; two additional crypto-named validators fall under line 350. If the owner wants these excluded from shared history, keep them held pending an approved separate repository or enforceable publication policy. “Local branch” is not a confidentiality control after a ref is pushed or merged.
3. **Carry the reported security findings forward.** Claude reports a possible API key at `docs/agent_sync/current_long_term_goal.json:12` and 73 hostname findings. These are reported findings from outside this provider classification. I did not inspect the suspected key, print values, examine credential stores or independently verify past publication. The Phase 2 limited pattern scan cannot overrule a specific report. Treat the key as a release blocker; arrange authorized remediation and exposure/history assessment, including revocation/rotation if warranted. If it already exists in Git history, fixing a current file does not remove historical exposure. The owner must decide hostname redaction and audience. Hold crypto, ledger, accounting and contract candidates and any other sensitive file until reviewed. No commit—even for a nominally non-sensitive family—is authorized by B1.
4. **Backend recovery scope.** Decide whether to authorize static review of the 12 outside-ledger startup dependencies and then their transitive frontier, or provide a verified known-complete historic snapshot. Keep data/private vault contents outside that recovery. If financial providers must remain private, B02 must use an owner-approved architecture or private dependency mechanism; it cannot be called a complete standalone public tree by leaving those files out. Decide whether historical coding-review/provider behavior is available rather than pre-landing new features.
5. **Definition of “complete.”** Specify startup-only versus default web build, optional audit/inference/export flows, native packaged Studio and new multi-entry hosting. B01 is for the pinned default build. The candidate chat/driver/personal release profiles are feature inputs, not a prerequisite for that original default entry. B03 and B04 have separate behavior and compatibility gates. Select worktree isolation and release-marker line-ending policy before future dynamic checks. No build or service was run in B1.
6. **Rebase the plan on the resulting reviewed baseline.** Only when its commits actually exist can later feature hunks/providers be checked against real parents. Repeat path membership, secret/proprietary review, import/symbol checks, release-input checks and mirror parity at those SHAs with separate authorization. The 15 original feature numbers are references, not approvals.

## Output reconciliation

178 unique classification rows. 52 positive ignore matches from 8 effective exclusion rules; 126 paths are not ignored. The one negated verbose match is among those 126. B01–B04 assign 84 named candidates across conditional baseline/profile groups; 94 retain feature-specific review labels. The extra backend startup frontier is outside the 178 denominator. No previous report, tracked file, ignore rule, branch or commit was changed.
