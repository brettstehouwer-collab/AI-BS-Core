# Phase 2 • Codex • Main-checkout integration triage

**Decision: the 15-step sequence below is a dependency model, not an approved or independently buildable commit series.** The ledger balances. Feature-specific source requirements can be named. Clean application startup, clean Vite packaging and complete native launch remain blocked by evidence about the pinned base itself. Nothing in this report authorizes adding ignored files, promoting a release, or activating financial, diagnostic or service workflows.

Snapshot: 2026-11-21, `C:\AI-BS`, branch `codex/audit-v532976-20261031`, base `64fad2871e0a716d9964f506bdef1050612b173d`. Inputs were both TRIAGE reports in docs/drafts, the owner's 15-part draft and the current tracked-only status. The separate ui/status-checked-at worktree and its commits are outside this plan.

## How the review was performed

1. Read the two triage reports, then independently read tracked-only porcelain status with optional locks and fsmonitor disabled. Each of the 137 records had an unstaged modification and a clean index column. The six held paths were classified from their names only. No live, fixture or migration commands were run.
2. Used the pinned Git *tree* as the provider baseline. Compared added hunks with the pinned *blobs*, then read callers, definitions, route registration, frontend entry points, dispatch, selected data contracts and file-based asset references. A working-directory import target was never treated as present in HEAD simply because it was readable.
3. For named Python entry providers, parsed local import statements without importing the application; followed relative imports, package members, guarded/function-local imports and selected dynamic loads. For the JS/UI/hosting providers, resolved static imports/re-exports, literal dynamic imports, relative UI imports, Vite profiles, HTML entries and explicit plugin asset reads. Deduplicated shared providers at their earliest modeled demand. Checked the Go method/helper definitions in their package. No databases, key stores, env files, endpoint credentials or customer data were accessed.
4. Compared four-way SHA-256 within each changed mirror family on disk. Reviewed package version/lock metadata and the release validator source. Checked named tests for local existence and membership in the pinned tree; local-only tests do not spontaneously appear in a clean checkout.
5. Applied the owner’s six exclusions. Assigned one primary owner to each tracked path and separate hunk ownership where a whole-file assignment would violate dependency order. Separately checked the named provider paths against the index, pinned tree and Git ignore rules. Did not scan unrelated untracked entries.
6. Checked 131 candidate tracked paths (changed lines), both sensitive documents in full, and 176 specifically named new source/asset candidates (full text); the two additional Python package initializers were directly inspected for selected recognizable secret patterns. Suppressed matched text. Rules covered private-key headers, common cloud/provider token shapes, JWT-shaped literals, literal secret assignments and credentials in URLs. Zero hits under those rules. **This is a bounded static scan, not a security clearance.** Indirect secrets, custom formats, data sensitivity, historical receipts, production endpoints, identifiers and whether publishing these documents is appropriate still require owner review. The six held files and linked private artifacts were not opened for scanning.
7. Reconciled file counts and checked the no-forward-reference rule within the named provider graph. Dependencies outside that graph, including existing broken entry points and runtime assets, are explicitly called out below.

### What “against the parent” means here

Only the pinned base is an actual Git parent available for this new series. Commit 1 can be compared with that object. For commit N > 1 the modeled parent is the pinned tree plus the explicit paths and hunk subsets from steps 1 through N−1. The reviewed postimage adds N's own hunks and providers. “Same step” is allowed; a provider in a later step is not. No future commit objects or trees were created. No claim of actual-parent checkout, executable import, clean build or passing tests is made. After actual commits exist, compare their real parent trees with this ledger and rerun validation in a separately authorized environment.

- **V — verified static** means a path, literal edge, contract implementation or registration was inspected in source. For new providers this is conditional on including that exact content; a clean parent alone lacks it.
- **R — runtime-only** covers configuration, permission, subprocess, file discovery, optional imports, service or data requirements. A code reference can be verified while its availability is R.
- **U — unresolved** covers a missing prerequisite, ambiguous ownership, package/deployment uncertainty or an acceptance condition static inspection cannot establish. An inherited failure is still a blocker for an independently runnable commit.

## Revised sequence, parent checks and tests

Numbers remain stable so the owner can compare this with the draft. The order changes **inside** the series through earlier provider ownership, explicit cross-file hunk moves and baseline gates. Test paths in this section are expanded with their provenance in the test index. No tests were run.

**1 — Historical project and engineering records. Parent: pinned HEAD.** V: 12 documentation/ledger paths and no new executable import. Current additions cite local checkpoints absent from the pinned tree, e.g. `backups/bs_chat_coding_mode_20261114_v02/checkpoint.json` and `docs/agent_sync/LEGACY_BUILD_ADMISSION153_2026-11-14.md`. U: decide which references are external historical evidence and which must resolve from the clean repository. A record of a prior run is not validation of this series. Do not import all referenced backup directories. Tests: no direct executable coverage identified; link/claim review applies.

**2 — Restricted operational documentation. Parent: 1.** V: the vault migration plan and sites/server register are documents. New links include the absent `docs/agent_sync/VAULT_ACTUAL_PREFLIGHT_2026-11-14.md`. R/U: referenced stores, hosts and receipts were neither opened nor contacted. Keep the sensitivity/provenance decision separate from the pattern scan. No direct test for document publishability.

**3 — Release metadata only. Parent: 2.** V: pinned `scripts/release-version.cjs` names the root, frontend and broadcast package/lock pairs, version JS modules, public version receipt and version.txt. Current version authority is v5.329.192; the three package/lock version pairs and release.json agree on 5.329.192. Keep the four new frontend build scripts for 15. R/U: updating a source marker does not prove a viable release artifact. Owner must decide whether the historical version should mark these interim commits or be presented only after the completed series. No focused tracked package-version test established; validator source exists and was not run.

**4 — Audit persistence and API contract. Parent: 3.** V: `backend/routers/audit_ledger_router.py:27–48,53–96` chooses app-state store/watcher, passes `store=` and uses thread dispatch. `cdz_audit_db.py:34–69` defines the supported store name, submit/future and reader conventions and the legacy no-store path. Include the existing but outside-HEAD watcher imported at router line 13. The app’s audit router registration already exists at the base. R: a populated runtime must supply the correct store instance and compatible watcher; no activation or SQLite file was inspected. U: cannot certify whole-app boot; see baseline gate. Tests: test_cdz_router_composition.py and test_cdz_host_composition.py are local only.

**5 — Inference, reasoning and context boundaries. Parent: 4.** V: dispatcher, agent routing and tests consume local_chat_inference, local_ollama_http, GPU scheduler/telemetry, DAG operations and request context. The test file itself imports chat_context_budget, and source-aware paths also use attached_source_context, owned_rag_sources and program_status_readonly. Walking those dependencies puts personal_memory_scope, screenplay_pdf and screenplay_professional here. An analysis limited to newly added import statements would miss these earlier obligations. Preserve the package namespace/provider identity; a file on disk is not proof of import search-path configuration. R: protected storage adapters, optional torch, GPU/inference hosts and installed packages. U: fallback operation in all modes is untested. Tests: test_chat_context_budget.py, test_local_ollama_http.py and test_gpu_dispatcher_integration.py.

**6 — Program builder and unavailable/503 contracts. Parent: 5.** V: source-only scaffold/maintenance handling flows from real_system_tools to program_builder_engine, artifacts_sync_router and the general tool endpoint. Include the unavailable branch from AI_BS_Backend.py here, plus the corresponding native error/reporting hunks. `backend/core/project_maintenance.py:490` can dispatch pinned `scripts/run_takeover_checks.py`; its locks, journal and process modules must be included together. R: subprocess/runtime tools, artifact locations and worker isolation. U: the general FastAPI module already has unresolved startup imports. Do not imply a verified system-level 503 response. Tests: test_program_builder.py, test_program_builder_takeover.py, test_project_maintenance.py and .mjs.

**7 — Fountain, source FDX and typed PDF. Parent: 6.** V: the parser preserves authored text and dialogue structure, the router accepts the typed-professional layout, and ScreenwritingTab’s four copies select compatible formats and read PDF page-count/hash receipts. `fdx_professional_pdf.py` and `fdx_source_documents.py` are new; the shared PDF and principal helpers are supplied by 5. This is the first changed UI feature needing the general Studio build in this order; see the inherited shell and sync prerequisites in the provider ledger. R: fitz, reportlab, fonts and source documents. U: source dependency closure alone cannot validate rendering, prior exports or a Vite build. Tests: test_fdx_source_workflow.py, test_fdx_rich_workflow.mjs, test_screenplay_pdf.py.

**8 — Audio and film. Parent: 7.** V: dispatch via media_intent_policy → chat_film → store/runner/workflows; include the matching backend entry router mount at working lines 2148–2149 now. Audio daemon endpoints supply screenplay list/load, narration, workflow compatibility and executable-launch paths that the four copies of each audio/Comfy UI consume. Earlier steps supply coding_locks and principal scope. R: `chat_film_runner.py:14–17` names a Comfy endpoint, output tree and ffmpeg binary; the audio handler selects local voice assets/VoiceStudio. U: installed assets, route proxy configuration and actual rendering are unverified. Tests: test_audio_router_trace.py, test_comfy_status_routing.py, and local-only test_chat_film_smoke.py.

**9 — Streaming, coding-mode UI and execution boundary. Parent: 8.** V: canonical ChatTab and MobileStehouwerChat import chatStream; CodingModePanel imports codingModeClient, existing CodingTaskHistory, projectPreparation, chatAuth and the preparation panel contract. Include stream metadata/header hunks in hybrid_reasoning_engine here. Static frontend entry is index.html → main.jsx → App → SplitPaneIDEWorkspace → components/ChatTab. The pre-existing backend entry imports coding_review_router (HEAD line 2127) and mounts it (2144); its outside-HEAD source includes coding_preparation_router and coding_mode_router. `codingModeClient.js:59` expects the mode API. Include candidate service/router closure or explicitly defer the callable UI path. R: execution queues, isolated workers and their state; no execution granted. U: clean startup still has independent blockers, and reconciling an outbox revision with Math.max does not prove concurrency safety. Tests: test_mobile_attached_sources.mjs, test_conversation_memory_context.mjs and local-only test_coding_mode_execution.py.

**10 — Port selection, Go gateway and CORS. Parent: 9.** V: six API config copies, four health hooks and port-only panel changes target the 8000 gateway, with 8080 still considered by selected clients. The gateway uses existing IPCBridge.PythonPort and telemetry.ActiveDefenseShield. Align browser decisions, gateway preflight headers and Python allow_headers in this step. Python document/idempotency headers are also consumed later by personal payments. `CryptoAccountingTab.jsx:12`, `CryptoSwarmMobileController.jsx:49,74,111`, `MiningDashboardTab.jsx:10` and `PearlMiningHubTab.jsx:10` are routing changes across their mirror sets. R/U: reverse proxy, TLS host, Python worker config and actual reachability are runtime facts, never inferred from default constants. Tests: security_identity_test.go, and local-only backend_routing_test.go and fe_capture_cors_test.go.

**11 — Exchange market data, trading contracts and shared chat bridge. Parent: 10.** V: the Go engine calls publicMarketData, marketPrecision and marketPrice in a non-base .go file in the same package. Python public preview/book, scoped trial/protective/preparation status, bridge declarations, chat intent and frontend data shapes must travel together. Trading router calls require_host_admin and binds/resets the principal. crypto_execution_controls and host_control_access are in HEAD; personal_memory_scope is already supplied by 5. The bridge also handles gated coding diagnostics and dynamically loads scripts/check_coding_candidate.py; this is a shared capability, not purely trading. See the per-provider edge list for the larger transitive closure. R: public HTTP, account gates, external stores and operator state. U: no order, exchange call or credential path was exercised. The bridge default root is C:/AI-BS; an isolated checkout alone does not prove isolated runtime effects. Do not infer order readiness from public data parsing. Tests: trade_engine_safety_test.go, test_crypto_execution_controls.py, and local-only public_market_data_test.go and test_crypto_trial_status_http_smoke.py.

**12 — Identity, campaigns and cloud analytics. Parent: 11.** V: App/TopNavbar sign-out callback, local identity restoration, LoginModal, accessControl and antiTamperGuard form one frontend identity contract. App and BetaAnalyticsTab load BrandCampaignManager → OutreachReceipts; the loader imports productionsCloudAnalytics. Include the HTML CSP connect-origin change with that consumer. The campaign request helper uses /api/brand-campaigns; the cloud summary adapter validates its expected origin. R: Firebase identity, browser-local state, external service contracts. U: independent campaign service source exists outside the pinned base at backend/brand_campaigns/service.py; neither its deployment nor provider configuration is part of the frontend closure. Do not pull a service or its secrets into a UI commit by implication. No dedicated campaign end-to-end coverage established. Tests: test_login_redirect_recovery.cjs and test_host_action_browser_auth.cjs cover related behavior.

**13 — Driver registration, ledger export and personal payments. Parent: 12.** V: main module mounts driver portal registration and ledger/payments modules. The opt-in driver registration imports owned records and truck profiles only when enabled. New financial providers depend on payment receipts, statement/year/filing export modules, document retention and authenticated identity. financial_auth and firebase_auth are separate contracts. Earlier CORS must support Idempotency-Key and document headers. R: driver gate, signed-in principal, account/storage access, document streams and idempotency behavior. U: no payments, authentication, private data or deployment tested. Several providers refer to one another within functions; availability does not establish safe initialization. Tests local only: test_fe_driver_registration.py, test_personal_payments.py and test_personal_ledger_export.py.

**14 — Native Studio authoring, coding pane and packaged worker. Parent: 13.** V: app.py:93–109 dispatches the syntax worker and packaged writer acceptance; the IDE imports CodingModeView and SyntaxCheck, uses callbacks, and receives builder error handling from 6. Outside-HEAD __init__.py supplies the version export. The new native modules have a substantial import closure through screenwriting UI, creative session, process groups and pipe transport. R: GUI frameworks, Windows processes/pipes, installed apps, assets, packaged entry points and paths. U: many inherited native imports absent at HEAD; do not assert desktop boot or clean package independence. Tests: test_native_creative_handoff.py; local-only test_packaged_writer_acceptance.py and test_coding_mode_view.py.

**15 — Hosting rewrites, multi-entry build and offline shell assets. Parent: 14.** V: move frontend/package.json’s four new build commands here. Vite release profile imports driver and personal profiles; driver imports chat profile, which extends pinned Studio config. HTML→JSX entry chains, portal clients/UI/CSS, driver manifest, service workers and favicon references must exist before dist can serve /chat, /driver and /personal. The driver plugin reads public/driver/manifest.webmanifest and public/driver/sw.js; the personal plugin reads public/personal/sw.js. Firebase hosting serves dist. Runtime/generated asset manifests are build outputs, not source inputs to copy from a working deployment. R: deployment configuration, offline caching and installed Vite dependencies. U: no build proves the emitted files exist; verifying rewrite strings alone is insufficient. No direct tracked test established for these three deployed paths together.

## Mixed-file routing and evidence anchors

Ranges refer to working-copy line numbers at capture. Apply the named diff hunks only; blank context may move between Git and a text diff algorithm. Each file still has a single primary ledger row.

| Ledger owner | File or family | Allocation of changes |
|---|---|---|
| 13 | backend/AI_BS_Backend.py | 1400–1403 driver registration → 13; 1948 allowed request headers → 10, including future payment/document needs; 2148–2149 chat films registration → 8; 3165–3168 accounting/payments registrations → 13; 6218–6221 (the unavailable test and 503 return) → 6. |
| 11 | backend/core/hybrid_reasoning_engine.py | 32, 1360–1365, 1371 request correlation/SSE headers → 9; 680–689 crypto preview/trial reply selection → 11. |
| 11 | backend/tools/tool_registry.py | 16–45 diagnostic names/declaration gate, 145–147 combined declarations, 2303–2305 dispatch → 11 as one shared bridge. Splitting only the crypto entries out of the combined dispatch would leave a diagnostic caller/provider mismatch. |
| 6 | backend/core/real_system_tools.py | 201–271 scaffold source-only behavior → 6; 462,466–468 forensic diagnostic intent recognition → 11 with the shared diagnostic bridge. These hunk ranges describe intent ownership, not a requirement to invoke diagnostics. |
| 14 | native_studio/bs_chat_ide_full.py | 49–64, 1131–1136, 1462,1467–1468,1499,1504–1505,1511,1515–1516 result/error handling → 6. Added coding/syntax UI at 415–422,494–505,2244–2245,2307–2330 → 14. |
| 3 | frontend/package.json | Version line 3 → 3. build:bs-chat, build:driver, build:personal and build:release at 16–19 → 15. |
| 12 | frontend/App.jsx | 117 and 266 campaign entry/tab → 12; 545 notify-login API host → 10; other changed hunks (1, 280–310,333–361,498–509,568–593,663,844–855,885–887,914–917) local auth/session/sign-out → 12. |
| 12 | TopNavbar.jsx ×4 | 59–60 and 88 (telemetry URL and dependency) → 10; 15–16 and 955–960 (prop/sign-out) → 12. |
| 11 | CryptoLiveStreamTab.jsx ×4 | 12 (loopback gateway constant) → 10. The prop-based base selection near 26–30 moves with the reshaped component in 11; keep its auth, telemetry, preview and rendering hunks together in 11. |
| 12 | frontend/index.html | Line 7 CSP permits the cloud analytics origin → 12. No separate release/version hunk in this file. |
| 10 | go-core/pkg/telemetry/security.go | Line 67 preflight allowlist → 10 in full; file-operation/idempotency/document headers support later finance calls. No claim that CORS itself authorizes them. |

## Inherited baseline gate

These examples explain why “providers first” still cannot certify all 15 steps runnable. They are not authorization to bulk-copy other working-tree content.

- The pinned backend already imports modules missing from its tree at AI_BS_Backend.py:160 (security/firebase_auth), 220 (modules/accounting_router), 2048 (routers/comfyui_workspace_router), 2060 (routers/calendar_tasks_router), 2127 (routers/coding_review_router) and 3299 (core/cryptographic_vault). These are module-level imports in the pinned source. Some paths appear in the feature manifest at later steps; that does not retroactively make the early app bootable. **Decision before claiming independent startup:** supply a separately scoped, reviewed baseline or choose a known-complete base and rederive this plan. Do not open a vault or acquire authentication material to settle a source-membership question.
- The pinned Studio build invokes frontend/scripts/sync_mirrors.py, which is absent at the base. It can fall back to C:/AI-BS/frontend. This inventory lists the script as a build prerequisite to resolve before the first UI group; blindly running the working copy could modify the main checkout. The inherited shell also references absent screenplay helper files and component CSS. Provider rows marked as inherited build inputs expose this issue. No bundler, sync or browser was invoked.
- The existing native launcher has local imports for absent files before considering its new hunks. Examples include native_studio/runtime_policy.py, window_geometry.py, navigation_registry.py, multiple desktop view modules, and the IDE’s chat_recovery.py and editor_file_store.py. Different startup modes reach different paths. A fully packaged native program would require a distinct baseline/package inventory. The step 14 providers are assigned for the identified feature edges; the plan does not certify unrelated desktop modes.
- Dynamic service URLs, environment-based imports, package availability, code invoked by subprocess, Windows package layout, private assets and generated outputs cannot be resolved by filename existence. Feature tests that exist only on the working machine cannot count as evidence in an earlier commit. Test ownership below is evidence/planning only, outside the 137-path production ledger unless a tracked test is explicitly in that ledger.

## Path ledger • 137 tracked paths, exactly once

**131 candidates + 6 held = 137.** One primary number is used for reconciliation; use the split table above when a later owner shares a file. An expanded pathname is a single tracked record. The proposed inclusion of previously untracked code never changes this denominator.

| Step | Tracked primary owners | Additional outside-index source/assets |
|---|---:|---:|
| 01 | 12 | 0 |
| 02 | 2 | 0 |
| 03 | 16 | 0 |
| 04 | 2 | 1 |
| 05 | 5 | 22 |
| 06 | 3 | 4 |
| 07 | 6 | 19 |
| 08 | 10 | 5 |
| 09 | 15 | 21 |
| 10 | 28 | 0 |
| 11 | 8 | 29 |
| 12 | 20 | 9 |
| 13 | 1 | 14 |
| 14 | 2 | 27 |
| 15 | 1 | 27 |
| HELD | 6 | 0 |

| Owner | Tracked path |
|---|---|
| 01 | `AGENTS.md` |
| 01 | `docs/agent_sync/current_long_term_goal.json` |
| 01 | `docs/agent_sync/GOAL_ADDITIONS_2026-11-11.json` |
| 01 | `docs/architecture/AI_BS_MASTER_ECOSYSTEM_ARCHITECTURE_2026-11-11.md` |
| 01 | `docs/architecture/LEGACY_BUILD_EXECUTION_REVIEW_2026-11-11.md` |
| 01 | `docs/CODEX_HANDOFF.md` |
| 01 | `docs/game_engine/PROJECT_INDEX.md` |
| 01 | `docs/game_engine/UPDATED_GAME_TOOLS_2026-11-11.md` |
| 01 | `GEMINI.md` |
| 01 | `PLAN.md` |
| 01 | `PROJECT.md` |
| 01 | `TEST_INFRA.md` |
| 02 | `docs/architecture/SITES_SERVERS_REGISTER_2026-11-11.json` |
| 02 | `docs/architecture/VAULT_KEY_MIGRATION_PLAN_2026-11-11.md` |
| 03 | `BroadcastStudioApp/package-lock.json` |
| 03 | `BroadcastStudioApp/package.json` |
| 03 | `BroadcastStudioApp/src/version.js` |
| 03 | `frontend/components/components/version.js` |
| 03 | `frontend/components/version.js` |
| 03 | `frontend/package-lock.json` |
| 03 | `frontend/package.json` |
| 03 | `frontend/public/version.json` |
| 03 | `frontend/src/components/components/version.js` |
| 03 | `frontend/src/components/version.js` |
| 03 | `frontend/src/version.js` |
| 03 | `frontend/version.js` |
| 03 | `package-lock.json` |
| 03 | `package.json` |
| 03 | `release.json` |
| 03 | `version.txt` |
| 04 | `backend/database/cdz_audit_db.py` |
| 04 | `backend/routers/audit_ledger_router.py` |
| 05 | `backend/core/sovereign_reasoning/dispatcher.py` |
| 05 | `backend/core/sovereign_reasoning/math_autograd.py` |
| 05 | `backend/routers/agent_routing.py` |
| 05 | `scripts/tests/test_chat_context_budget.py` |
| 05 | `scripts/tests/test_local_ollama_http.py` |
| 06 | `backend/core/program_builder_engine.py` |
| 06 | `backend/core/real_system_tools.py` |
| 06 | `backend/routers/artifacts_sync_router.py` |
| 07 | `backend/core/matrix_docs.py` |
| 07 | `backend/routers/screenwriting_router.py` |
| 07 | `frontend/components/components/ScreenwritingTab.jsx` |
| 07 | `frontend/components/ScreenwritingTab.jsx` |
| 07 | `frontend/src/components/components/ScreenwritingTab.jsx` |
| 07 | `frontend/src/components/ScreenwritingTab.jsx` |
| 08 | `backend/core/media_intent_policy.py` |
| 08 | `backend/f5_tts_daemon.py` |
| 08 | `frontend/components/ComfyUIStudio.jsx` |
| 08 | `frontend/components/components/ComfyUIStudio.jsx` |
| 08 | `frontend/components/components/NeuralAudioStudioTab.jsx` |
| 08 | `frontend/components/NeuralAudioStudioTab.jsx` |
| 08 | `frontend/src/components/ComfyUIStudio.jsx` |
| 08 | `frontend/src/components/components/ComfyUIStudio.jsx` |
| 08 | `frontend/src/components/components/NeuralAudioStudioTab.jsx` |
| 08 | `frontend/src/components/NeuralAudioStudioTab.jsx` |
| 09 | `frontend/components/ChatTab.jsx` |
| 09 | `frontend/components/CodingPreparationPanel.jsx` |
| 09 | `frontend/components/components/ChatTab.jsx` |
| 09 | `frontend/components/components/CodingPreparationPanel.jsx` |
| 09 | `frontend/components/components/MobileStehouwerChat.jsx` |
| 09 | `frontend/components/MobileStehouwerChat.jsx` |
| 09 | `frontend/src/components/ChatTab.jsx` |
| 09 | `frontend/src/components/CodingPreparationPanel.jsx` |
| 09 | `frontend/src/components/components/ChatTab.jsx` |
| 09 | `frontend/src/components/components/CodingPreparationPanel.jsx` |
| 09 | `frontend/src/components/components/MobileStehouwerChat.jsx` |
| 09 | `frontend/src/components/MobileStehouwerChat.jsx` |
| 09 | `frontend/src/utils/attachedSources.js` |
| 09 | `frontend/src/utils/conversationOutbox.js` |
| 09 | `scripts/tests/test_mobile_attached_sources.mjs` |
| 10 | `frontend/components/components/config/api.js` |
| 10 | `frontend/components/components/CryptoAccountingTab.jsx` |
| 10 | `frontend/components/components/CryptoSwarmMobileController.jsx` |
| 10 | `frontend/components/components/MiningDashboardTab.jsx` |
| 10 | `frontend/components/components/PearlMiningHubTab.jsx` |
| 10 | `frontend/components/components/useBackendHealth.js` |
| 10 | `frontend/components/config/api.js` |
| 10 | `frontend/components/CryptoAccountingTab.jsx` |
| 10 | `frontend/components/CryptoSwarmMobileController.jsx` |
| 10 | `frontend/components/MiningDashboardTab.jsx` |
| 10 | `frontend/components/PearlMiningHubTab.jsx` |
| 10 | `frontend/components/useBackendHealth.js` |
| 10 | `frontend/config/api.js` |
| 10 | `frontend/src/components/components/config/api.js` |
| 10 | `frontend/src/components/components/CryptoAccountingTab.jsx` |
| 10 | `frontend/src/components/components/CryptoSwarmMobileController.jsx` |
| 10 | `frontend/src/components/components/MiningDashboardTab.jsx` |
| 10 | `frontend/src/components/components/PearlMiningHubTab.jsx` |
| 10 | `frontend/src/components/components/useBackendHealth.js` |
| 10 | `frontend/src/components/config/api.js` |
| 10 | `frontend/src/components/CryptoAccountingTab.jsx` |
| 10 | `frontend/src/components/CryptoSwarmMobileController.jsx` |
| 10 | `frontend/src/components/MiningDashboardTab.jsx` |
| 10 | `frontend/src/components/PearlMiningHubTab.jsx` |
| 10 | `frontend/src/components/useBackendHealth.js` |
| 10 | `frontend/src/config/api.js` |
| 10 | `go-core/pkg/gateway/gateway.go` |
| 10 | `go-core/pkg/telemetry/security.go` |
| 11 | `backend/core/hybrid_reasoning_engine.py` |
| 11 | `backend/routers/trading_router.py` |
| 11 | `backend/tools/tool_registry.py` |
| 11 | `Crypto-Swarm/internal/daemons/trade_engine.go` |
| 11 | `frontend/components/components/CryptoLiveStreamTab.jsx` |
| 11 | `frontend/components/CryptoLiveStreamTab.jsx` |
| 11 | `frontend/src/components/components/CryptoLiveStreamTab.jsx` |
| 11 | `frontend/src/components/CryptoLiveStreamTab.jsx` |
| 12 | `frontend/App.jsx` |
| 12 | `frontend/components/accessControl.js` |
| 12 | `frontend/components/BetaAnalyticsTab.jsx` |
| 12 | `frontend/components/components/accessControl.js` |
| 12 | `frontend/components/components/BetaAnalyticsTab.jsx` |
| 12 | `frontend/components/components/LoginModal.jsx` |
| 12 | `frontend/components/components/TopNavbar.jsx` |
| 12 | `frontend/components/LoginModal.jsx` |
| 12 | `frontend/components/TopNavbar.jsx` |
| 12 | `frontend/index.html` |
| 12 | `frontend/src/components/accessControl.js` |
| 12 | `frontend/src/components/BetaAnalyticsTab.jsx` |
| 12 | `frontend/src/components/components/accessControl.js` |
| 12 | `frontend/src/components/components/BetaAnalyticsTab.jsx` |
| 12 | `frontend/src/components/components/LoginModal.jsx` |
| 12 | `frontend/src/components/components/TopNavbar.jsx` |
| 12 | `frontend/src/components/LoginModal.jsx` |
| 12 | `frontend/src/components/TopNavbar.jsx` |
| 12 | `frontend/src/utils/analyticsData.js` |
| 12 | `frontend/utils/antiTamperGuard.js` |
| 13 | `backend/AI_BS_Backend.py` |
| 14 | `native_studio/app.py` |
| 14 | `native_studio/bs_chat_ide_full.py` |
| 15 | `frontend/firebase.json` |
| HELD | `backend/matrix_health_report.json` |
| HELD | `docs/viewport_telemetry/probe_run/viewport.json` |
| HELD | `scripts/tests/__pycache__/test_chat_context_budget.cpython-312.pyc` |
| HELD | `scripts/tests/__pycache__/test_local_ollama_http.cpython-312.pyc` |
| HELD | `scripts/tests/__pycache__/test_native_creative_handoff.cpython-312.pyc` |
| HELD | `scripts/tests/__pycache__/test_native_telemetry_shutdown.cpython-312.pyc` |

## Separate provider ledger • 178 named outside-HEAD source and asset paths

These files were located locally and are absent from the pinned tree and index. They are feature requirements or explicitly named **inherited prerequisites** for the stated validation target. Inventory is not permission to add them. The two Python package initializers in step 5 preserve the local package shape; gpu/__init__.py re-exports controller symbols, while orchestrator/__init__.py contains a package docstring. Native Studio’s initializer in 14 provides __version__. In 7 the pre-existing sync script, screenplay helpers and missing CSS are inherited clean-build prerequisites. Step 15 includes literal asset reads by build plugins, not generated dist assets. Runtime-only services and unresolved baseline obligations are listed separately.

**52 of these paths match Git ignore rules.** The Ignore column is the result of read-only `git check-ignore --stdin` (or named-path equivalent). A normal discovery or add operation can skip these files. Review why each is ignored before deciding whether it should be integrated. No ignore rule was changed and no file was force-added.

| First step | Provider path | Ignored | Evidence or consumer |
|---|---|---|---|
| 04 | `backend/modules/audit_ledger_watcher.py` | yes | audit_ledger_router.py:13 (pre-existing import) |
| 05 | `backend/core/attached_source_context.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/chat_context_budget.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/chat_pdf_sources.py` | no | backend/core/attached_source_context.py:50 |
| 05 | `backend/core/local_chat_inference.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/local_ollama_http.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/owned_rag_sources.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/owned_vault.py` | no | backend/core/attached_source_context.py:53 |
| 05 | `backend/core/pdf_text_source.py` | no | backend/core/chat_pdf_sources.py:111 |
| 05 | `backend/core/personal_memory_scope.py` | no | backend/core/attached_source_context.py:11 |
| 05 | `backend/core/pipeline_context_injector.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/program_status_readonly.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/core/screenplay_pdf.py` | yes | backend/core/chat_pdf_sources.py:118 |
| 05 | `backend/core/screenplay_professional.py` | yes | backend/core/chat_pdf_sources.py:408 |
| 05 | `backend/core/sovereign_reasoning/dag_topological_reasoner.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/gpu/__init__.py` | no | package loader / exported API |
| 05 | `backend/gpu/compute_scheduler.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 05 | `backend/gpu/gpu_telemetry.py` | no | backend/gpu/compute_scheduler.py:15 |
| 05 | `backend/gpu/model_residency.py` | no | backend/gpu/compute_scheduler.py:16 |
| 05 | `backend/gpu/stability_supervisor.py` | no | backend/gpu/compute_scheduler.py:17 |
| 05 | `backend/gpu/vram_manager.py` | no | backend/gpu/compute_scheduler.py:18 |
| 05 | `backend/orchestrator/__init__.py` | no | package loader / exported API |
| 05 | `backend/orchestrator/gpu_task_dispatcher.py` | no | dispatcher.py, context-budget / local-Ollama test or scheduler chain |
| 06 | `backend/core/coding_journal.py` | no | backend/core/project_maintenance.py:26 |
| 06 | `backend/core/coding_locks.py` | no | backend/core/project_maintenance.py:27 |
| 06 | `backend/core/coding_process.py` | no | backend/core/project_maintenance.py:28 |
| 06 | `backend/core/project_maintenance.py` | no | program_builder_engine.py:641–648 |
| 07 | `backend/core/fdx_professional_pdf.py` | no | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `backend/core/fdx_source_documents.py` | no | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/components/components/ScreenplayTableReadModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/components/components/ScriptToBookNovelizerModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/components/components/WorkspaceCalendarTab.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/components/ScreenplayTableReadModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/components/ScriptToBookNovelizerModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/components/WorkspaceCalendarTab.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/scripts/sync_mirrors.py` | no | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/components/components/ScreenplayTableReadModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/components/components/ScriptToBookNovelizerModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/components/components/WorkspaceCalendarTab.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/components/ScreenplayTableReadModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/components/ScriptToBookNovelizerModal.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/components/WorkspaceCalendarTab.css` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/utils/nativeScreenplayHandoff.js` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/utils/screenplayAdaptation.js` | yes | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 07 | `frontend/src/utils/screenplayHandoff.js` | yes | frontend/src/utils/nativeScreenplayHandoff.js |
| 07 | `frontend/utils/fdxDocumentFormat.js` | no | screenwriting_router, ScreenwritingTab, or existing Studio build/import chain |
| 08 | `backend/core/chat_film_runner.py` | yes | backend/core/chat_film.py:30 |
| 08 | `backend/core/chat_film_store.py` | yes | backend/core/chat_film.py:4 |
| 08 | `backend/core/chat_film.py` | yes | media_intent_policy, chat-films mount or film runner |
| 08 | `backend/core/video_workflows.py` | no | backend/core/chat_film_runner.py:12 |
| 08 | `backend/routers/chat_films.py` | yes | media_intent_policy, chat-films mount or film runner |
| 09 | `backend/core/coding_mode_execution.py` | no | backend/routers/coding_mode_router.py:3 |
| 09 | `backend/core/coding_mode_local.py` | no | backend/core/coding_mode_execution.py:25 |
| 09 | `backend/core/coding_preparation_planning.py` | no | backend/routers/coding_preparation_router.py:8 |
| 09 | `backend/core/coding_preparation_proposals.py` | no | backend/routers/coding_preparation_router.py:9 |
| 09 | `backend/core/coding_preparation.py` | no | backend/routers/coding_preparation_router.py:4 |
| 09 | `backend/core/coding_recovery.py` | no | backend/routers/coding_review_router.py:8 |
| 09 | `backend/core/coding_repository_snapshot.py` | no | backend/core/coding_preparation.py:20 |
| 09 | `backend/core/coding_syntax.py` | no | backend/core/coding_mode_execution.py:24 |
| 09 | `backend/core/coding_vm_inputs.py` | no | backend/core/coding_mode_execution.py:22 |
| 09 | `backend/core/coding_vm_staging.py` | no | backend/core/coding_mode_execution.py:23 |
| 09 | `backend/routers/coding_mode_router.py` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `backend/routers/coding_preparation_router.py` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `backend/routers/coding_review_router.py` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `backend/security/firebase_auth.py` | no | backend/routers/coding_review_router.py:10 |
| 09 | `frontend/components/CodingModePanel.jsx` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `frontend/components/components/CodingModePanel.jsx` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `frontend/src/components/CodingModePanel.jsx` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `frontend/src/components/components/CodingModePanel.jsx` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `frontend/src/utils/chatStream.js` | no | desktop/mobile chat, coding-mode panel/client or existing /api/chat/coding-tasks mount |
| 09 | `frontend/src/utils/codingMode.js` | no | frontend/src/utils/codingModeClient.js |
| 09 | `frontend/src/utils/codingModeClient.js` | no | frontend/src/components/CodingModePanel.jsx |
| 11 | `backend/core/crypto_com_acknowledgements.py` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `backend/core/crypto_com_adapter.py` | yes | backend/core/crypto_com_acknowledgements.py:13 |
| 11 | `backend/core/crypto_com_native_stop.py` | yes | backend/core/crypto_protective_lifecycle.py:13 |
| 11 | `backend/core/crypto_credential_preparation_registry.py` | yes | backend/core/crypto_preparation_status.py:51 |
| 11 | `backend/core/crypto_credential_preparation.py` | yes | backend/core/crypto_credential_preparation_registry.py:41 |
| 11 | `backend/core/crypto_current_snapshot_facts.py` | yes | backend/core/crypto_current_snapshot.py:19 |
| 11 | `backend/core/crypto_current_snapshot.py` | yes | backend/core/crypto_held_preparation_runtime.py:18 |
| 11 | `backend/core/crypto_held_preparation_runtime.py` | yes | backend/core/crypto_preparation_status.py:52 |
| 11 | `backend/core/crypto_preparation_status.py` | yes | backend/core/crypto_trial_status_chat.py:27 |
| 11 | `backend/core/crypto_preview_chat.py` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `backend/core/crypto_protective_lifecycle.py` | yes | backend/core/crypto_trial_registry.py:147 |
| 11 | `backend/core/crypto_protective_review_contract.py` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `backend/core/crypto_reinvestment.py` | yes | backend/core/crypto_held_preparation_runtime.py:20 |
| 11 | `backend/core/crypto_spot_preview.py` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `backend/core/crypto_spot_protection.py` | yes | backend/tools/bs_chat_tool_bridge.py:188 |
| 11 | `backend/core/crypto_trial_admission.py` | yes | backend/core/crypto_trial_runtime_store.py:23 |
| 11 | `backend/core/crypto_trial_binding.py` | yes | backend/core/crypto_trial_runtime_store.py:24 |
| 11 | `backend/core/crypto_trial_budget.py` | yes | backend/core/crypto_held_preparation_runtime.py:21 |
| 11 | `backend/core/crypto_trial_projection.py` | yes | backend/core/crypto_trial_runtime_store.py:26 |
| 11 | `backend/core/crypto_trial_registry.py` | yes | backend/tools/bs_chat_tool_bridge.py:99 |
| 11 | `backend/core/crypto_trial_runtime_store.py` | yes | backend/core/crypto_trial_registry.py:16 |
| 11 | `backend/core/crypto_trial_status_chat.py` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `backend/core/crypto_trial_status_contract.py` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `backend/security/crypto_trial_root.py` | yes | backend/core/crypto_preparation_status.py:53 |
| 11 | `backend/security/theatrical_corpus_boundary.py` | yes | backend/security/crypto_trial_root.py:20 |
| 11 | `backend/security/theatrical_storage_roots.py` | no | backend/security/crypto_trial_root.py:19 |
| 11 | `backend/tools/bs_chat_tool_bridge.py` | no | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `Crypto-Swarm/internal/daemons/public_market_data.go` | yes | trade_engine.go:102–164, trading_router, hybrid crypto intent or tool_registry |
| 11 | `scripts/check_coding_candidate.py` | no | bs_chat_tool_bridge.py:201–203, dynamic load |
| 12 | `frontend/components/BrandCampaignManager.jsx` | no | App/BetaAnalyticsTab/campaign manager or analyticsData.js |
| 12 | `frontend/components/components/BrandCampaignManager.jsx` | no | App/BetaAnalyticsTab/campaign manager or analyticsData.js |
| 12 | `frontend/components/components/OutreachReceipts.jsx` | no | frontend/components/components/BrandCampaignManager.jsx |
| 12 | `frontend/components/OutreachReceipts.jsx` | no | frontend/components/BrandCampaignManager.jsx |
| 12 | `frontend/src/components/BrandCampaignManager.jsx` | no | App/BetaAnalyticsTab/campaign manager or analyticsData.js |
| 12 | `frontend/src/components/components/BrandCampaignManager.jsx` | no | App/BetaAnalyticsTab/campaign manager or analyticsData.js |
| 12 | `frontend/src/components/components/OutreachReceipts.jsx` | no | frontend/src/components/components/BrandCampaignManager.jsx |
| 12 | `frontend/src/components/OutreachReceipts.jsx` | no | frontend/src/components/BrandCampaignManager.jsx |
| 12 | `frontend/src/utils/productionsCloudAnalytics.js` | no | App/BetaAnalyticsTab/campaign manager or analyticsData.js |
| 13 | `backend/core/payment_receipts.py` | no | backend/modules/personal_ledger_export.py:9 |
| 13 | `backend/fe_express_owned_records.py` | no | backend/routers/fe_driver_registration.py:9 |
| 13 | `backend/fe_truck_profiles.py` | no | backend/routers/fe_driver_registration.py:10 |
| 13 | `backend/modules/accounting_router.py` | yes | backend/modules/personal_ledger_export.py:17 |
| 13 | `backend/modules/personal_export_parts.py` | no | backend/modules/personal_ledger_export.py:66 |
| 13 | `backend/modules/personal_filing_archive.py` | no | backend/modules/personal_ledger_export.py:64 |
| 13 | `backend/modules/personal_financial_filings.py` | no | backend/modules/personal_payments.py:114 |
| 13 | `backend/modules/personal_ledger_export.py` | yes | AI_BS_Backend.py:1400–1403,3165–3168 |
| 13 | `backend/modules/personal_payment_documents.py` | no | backend/modules/personal_payments.py:112 |
| 13 | `backend/modules/personal_payments.py` | no | AI_BS_Backend.py:1400–1403,3165–3168 |
| 13 | `backend/modules/personal_year_archive.py` | no | backend/modules/personal_ledger_export.py:62 |
| 13 | `backend/routers/fe_driver_registration.py` | no | AI_BS_Backend.py:1400–1403,3165–3168 |
| 13 | `backend/security/document_retention.py` | no | backend/modules/personal_payment_documents.py:16 |
| 13 | `backend/security/financial_auth.py` | no | backend/modules/personal_ledger_export.py:10 |
| 14 | `native_studio/__init__.py` | no | package loader / exported API |
| 14 | `native_studio/ai_bs_ide_terminal.py` | no | native_studio/process_batch_view.py:265 |
| 14 | `native_studio/audio_kernel.py` | no | native_studio/screenwriting_modals.py:59 |
| 14 | `native_studio/coding_mode_service.py` | no | native_studio/coding_mode_view.py:9 |
| 14 | `native_studio/coding_mode_view.py` | no | native app/IDE entry and packaged authoring flow |
| 14 | `native_studio/creation_suite_subtools.py` | no | native_studio/screenwriting_view.py:2515 |
| 14 | `native_studio/creative_handoff.py` | no | native_studio/creation_suite_subtools.py:63 |
| 14 | `native_studio/creative_pipe_bootstrap.py` | no | native_studio/creative_session.py:158 |
| 14 | `native_studio/creative_pipe_io.py` | no | native_studio/creative_pipe_bootstrap.py:17 |
| 14 | `native_studio/creative_pipe_transport.py` | no | native_studio/creative_session.py:235 |
| 14 | `native_studio/creative_session.py` | no | native_studio/native_creative_entry.py:9 |
| 14 | `native_studio/creative_wire.py` | no | native_studio/creative_pipe_transport.py:11 |
| 14 | `native_studio/local_refactor_view.py` | no | native_studio/process_batch_view.py:272 |
| 14 | `native_studio/native_creative_entry.py` | no | native_studio/packaged_writer_acceptance.py:272 |
| 14 | `native_studio/owned_process.py` | no | native_studio/process_batch.py:222 |
| 14 | `native_studio/packaged_writer_acceptance.py` | no | native app/IDE entry and packaged authoring flow |
| 14 | `native_studio/process_batch_view.py` | no | native_studio/syntax_check.py:9 |
| 14 | `native_studio/process_batch.py` | no | native_studio/syntax_check.py:8 |
| 14 | `native_studio/responsive_layout.py` | no | native_studio/process_batch_view.py:288 |
| 14 | `native_studio/rich_screenplay_draft.py` | yes | native_studio/screenplay_client.py:17 |
| 14 | `native_studio/screenplay_client.py` | yes | native_studio/packaged_writer_acceptance.py:105 |
| 14 | `native_studio/screenwriting_modals.py` | no | native_studio/screenwriting_view.py:1748 |
| 14 | `native_studio/screenwriting_view.py` | no | native_studio/packaged_writer_acceptance.py:106 |
| 14 | `native_studio/syntax_check.py` | no | native app/IDE entry and packaged authoring flow |
| 14 | `native_studio/syntax_worker.py` | no | native app/IDE entry and packaged authoring flow |
| 14 | `native_studio/theme.py` | no | native_studio/native_creative_entry.py:83 |
| 14 | `native_studio/windows_profile.py` | no | native_studio/screenplay_client.py:426 |
| 15 | `frontend/bs-chat.html` | no | Vite multi-entry profile, entry page, service worker or emitted shell |
| 15 | `frontend/bs-chat.jsx` | no | frontend/bs-chat.html |
| 15 | `frontend/driver/index.html` | no | Vite multi-entry profile, entry page, service worker or emitted shell |
| 15 | `frontend/driver/main.jsx` | no | frontend/driver/index.html |
| 15 | `frontend/personal/index.html` | no | Vite multi-entry profile, entry page, service worker or emitted shell |
| 15 | `frontend/personal/main.jsx` | no | frontend/personal/index.html |
| 15 | `frontend/public/driver/manifest.webmanifest` | no | frontend/driver/index.html |
| 15 | `frontend/public/driver/sw.js` | no | Vite multi-entry profile, entry page, service worker or emitted shell |
| 15 | `frontend/public/personal/sw.js` | no | Vite multi-entry profile, entry page, service worker or emitted shell |
| 15 | `frontend/src/fe-express/driver.css` | no | frontend/driver/main.jsx |
| 15 | `frontend/src/fe-express/driverClient.js` | no | frontend/src/fe-express/DriverPortal.jsx |
| 15 | `frontend/src/fe-express/DriverPortal.jsx` | no | frontend/driver/main.jsx |
| 15 | `frontend/src/fe-express/truckProfile.css` | no | frontend/src/fe-express/TruckProfile.jsx |
| 15 | `frontend/src/fe-express/TruckProfile.jsx` | no | frontend/src/fe-express/DriverPortal.jsx |
| 15 | `frontend/src/fe-express/truckProfileStore.js` | no | frontend/src/fe-express/TruckProfile.jsx |
| 15 | `frontend/src/personal-finance/FinancialFilings.jsx` | no | frontend/src/personal-finance/PersonalFinancePortal.jsx |
| 15 | `frontend/src/personal-finance/MultipartExport.jsx` | no | frontend/src/personal-finance/PersonalFinancePortal.jsx |
| 15 | `frontend/src/personal-finance/OfflineShell.jsx` | no | frontend/src/personal-finance/PersonalFinancePortal.jsx |
| 15 | `frontend/src/personal-finance/personal.css` | no | frontend/personal/main.jsx |
| 15 | `frontend/src/personal-finance/personalClient.js` | no | frontend/src/personal-finance/PersonalFinancePortal.jsx |
| 15 | `frontend/src/personal-finance/PersonalFinancePortal.jsx` | no | frontend/personal/main.jsx |
| 15 | `frontend/src/personal-finance/PersonalSignIn.jsx` | no | frontend/src/personal-finance/PersonalFinancePortal.jsx |
| 15 | `frontend/src/utils/feExpressOfflineStore.js` | no | frontend/src/fe-express/driverClient.js |
| 15 | `frontend/vite.bs-chat.config.mjs` | no | frontend/vite.driver.config.mjs |
| 15 | `frontend/vite.driver.config.mjs` | no | frontend/vite.release.config.mjs |
| 15 | `frontend/vite.personal.config.mjs` | no | frontend/vite.release.config.mjs |
| 15 | `frontend/vite.release.config.mjs` | no | Vite multi-entry profile, entry page, service worker or emitted shell |

## Transitive edge evidence

The following adjacency list records resolved local imports from the examined providers. For Python the number after the dependency is the first representative import line. “late/guarded” marks an edge seen only within a function, try or conditional; execution is runtime-only even when the path is verified. “base” is a dependency already represented in the pinned Git tree; if it also has a tracked edit later, availability of its old API is all that is implied. For UI edges, the paths are resolved literal import/asset targets. Dynamic service state and global application closure remain subject to the gates above.

- `backend/modules/audit_ledger_watcher.py` → `backend/database/cdz_audit_db.py` (base; L15).
- `backend/core/attached_source_context.py` → `backend/core/chat_pdf_sources.py` (05; L50, late/guarded), `backend/core/owned_rag_sources.py` (05; L51, late/guarded), `backend/core/owned_vault.py` (05; L53, late/guarded), `backend/core/personal_memory_scope.py` (05; L11).
- `backend/core/chat_pdf_sources.py` → `backend/core/owned_rag_sources.py` (05; L16), `backend/core/owned_vault.py` (05; L15), `backend/core/pdf_text_source.py` (05; L111, late/guarded), `backend/core/personal_memory_scope.py` (05; L17), `backend/core/screenplay_pdf.py` (05; L118, late/guarded), `backend/core/screenplay_professional.py` (05; L408, late/guarded).
- `backend/core/local_chat_inference.py` → `backend/core/local_ollama_http.py` (05; L14), `backend/core/pipeline_context_injector.py` (05; L205, late/guarded), `backend/gpu/compute_scheduler.py` (05; L16), `backend/orchestrator/gpu_task_dispatcher.py` (05; L15).
- `backend/core/local_ollama_http.py` → `backend/gpu/compute_scheduler.py` (05; L11).
- `backend/core/owned_rag_sources.py` → `backend/core/owned_vault.py` (05; L14), `backend/core/personal_memory_scope.py` (05; L16).
- `backend/core/owned_vault.py` → `backend/core/personal_memory_scope.py` (05; L222, late/guarded).
- `backend/core/program_status_readonly.py` → `backend/core/media_intent_policy.py` (base; L125, late/guarded), `backend/core/personal_memory_scope.py` (05; L95, late/guarded).
- `backend/core/screenplay_professional.py` → `backend/core/screenplay_pdf.py` (05; L20).
- `backend/core/sovereign_reasoning/dag_topological_reasoner.py` → `backend/core/personal_intelligence_memory.py` (base; L42, late/guarded).
- `backend/gpu/__init__.py` → `backend/gpu/compute_scheduler.py` (05; L2).
- `backend/gpu/compute_scheduler.py` → `backend/gpu/gpu_telemetry.py` (05; L15), `backend/gpu/model_residency.py` (05; L16), `backend/gpu/stability_supervisor.py` (05; L17), `backend/gpu/vram_manager.py` (05; L18).
- `backend/gpu/stability_supervisor.py` → `backend/gpu/gpu_telemetry.py` (05; L5).
- `backend/gpu/vram_manager.py` → `backend/gpu/gpu_telemetry.py` (05; L4).
- `backend/orchestrator/gpu_task_dispatcher.py` → `backend/core/local_ollama_http.py` (05; L14), `backend/gpu/compute_scheduler.py` (05; L15).
- `backend/core/project_maintenance.py` → `backend/core/coding_journal.py` (06; L26), `backend/core/coding_locks.py` (06; L27), `backend/core/coding_process.py` (06; L28).
- `backend/core/fdx_professional_pdf.py` → `backend/core/fdx_source_documents.py` (07; L14), `backend/core/screenplay_professional.py` (05; L15).
- `backend/core/fdx_source_documents.py` → `backend/core/personal_memory_scope.py` (05; L15).
- `frontend/src/utils/nativeScreenplayHandoff.js` → `frontend/src/utils/screenplayHandoff.js` (07).
- `backend/core/chat_film_runner.py` → `backend/core/chat_film_store.py` (08; L10), `backend/core/coding_locks.py` (06; L11), `backend/core/video_workflows.py` (08; L12).
- `backend/core/chat_film.py` → `backend/core/chat_film_runner.py` (08; L30, late/guarded), `backend/core/chat_film_store.py` (08; L4), `backend/core/personal_memory_scope.py` (05; L5).
- `backend/routers/chat_films.py` → `backend/core/chat_film_store.py` (08; L4), `backend/core/personal_memory_scope.py` (05; L5).
- `backend/core/coding_mode_execution.py` → `backend/core/coding_chat.py` (base; L20), `backend/core/coding_locks.py` (06; L21), `backend/core/coding_mode_local.py` (09; L25), `backend/core/coding_preparation.py` (09; L18), `backend/core/coding_preparation_proposals.py` (09; L19), `backend/core/coding_syntax.py` (09; L24), `backend/core/coding_vm_inputs.py` (09; L22), `backend/core/coding_vm_staging.py` (09; L23).
- `backend/core/coding_mode_local.py` → `backend/core/coding_journal.py` (06; L19), `backend/core/coding_locks.py` (06; L20), `backend/core/coding_preparation.py` (09; L18), `backend/core/coding_process.py` (06; L21), `backend/core/coding_vm_staging.py` (09; L22), `backend/core/coding_workflow.py` (base; L23).
- `backend/core/coding_preparation_planning.py` → `backend/core/coding_chat.py` (base; L17), `backend/core/coding_locks.py` (06; L18), `backend/core/coding_preparation.py` (09; L16), `backend/core/personal_memory_scope.py` (05; L19).
- `backend/core/coding_preparation_proposals.py` → `backend/core/coding_chat.py` (base; L19), `backend/core/coding_locks.py` (06; L20), `backend/core/coding_preparation.py` (09; L17), `backend/core/coding_preparation_planning.py` (09; L18), `backend/core/personal_memory_scope.py` (05; L21).
- `backend/core/coding_preparation.py` → `backend/core/coding_journal.py` (06; L18), `backend/core/coding_locks.py` (06; L19), `backend/core/coding_recovery.py` (09; L17), `backend/core/coding_repository_snapshot.py` (09; L20), `backend/core/coding_vm_inputs.py` (09; L21), `backend/core/coding_vm_staging.py` (09; L22), `backend/core/personal_memory_scope.py` (05; L23).
- `backend/core/coding_recovery.py` → `backend/core/coding_journal.py` (06; L18), `backend/core/coding_locks.py` (06; L17), `backend/core/coding_workflow.py` (base; L16).
- `backend/core/coding_repository_snapshot.py` → `backend/core/coding_vm_inputs.py` (09; L17), `backend/core/coding_vm_staging.py` (09; L18), `backend/core/personal_memory_scope.py` (05; L19).
- `backend/core/coding_vm_staging.py` → `backend/core/coding_vm_inputs.py` (09; L20).
- `backend/routers/coding_mode_router.py` → `backend/core/coding_mode_execution.py` (09; L3), `backend/routers/coding_preparation_router.py` (09; L4).
- `backend/routers/coding_preparation_router.py` → `backend/core/coding_preparation.py` (09; L4), `backend/core/coding_preparation_planning.py` (09; L8), `backend/core/coding_preparation_proposals.py` (09; L9), `backend/security/firebase_auth.py` (09; L7).
- `backend/routers/coding_review_router.py` → `backend/core/coding_recovery.py` (09; L8), `backend/core/coding_review.py` (base; L7), `backend/core/coding_workflow.py` (base; L9), `backend/routers/coding_mode_router.py` (09; L12), `backend/routers/coding_preparation_router.py` (09; L11), `backend/security/firebase_auth.py` (09; L10).
- `frontend/components/CodingModePanel.jsx` → `frontend/components/CodingPreparationPanel.jsx` (base), `frontend/components/CodingTaskHistory.jsx` (base), `frontend/components/useAppStore.js` (base), `frontend/src/hooks/useConversationMemory.jsx` (base), `frontend/src/utils/chatAuth.js` (base), `frontend/src/utils/codingModeClient.js` (09), `frontend/src/utils/projectPreparation.js` (base).
- `frontend/components/components/CodingModePanel.jsx` → `frontend/components/components/CodingPreparationPanel.jsx` (base), `frontend/components/components/CodingTaskHistory.jsx` (base), `frontend/components/components/useAppStore.js` (base), `frontend/src/hooks/useConversationMemory.jsx` (base), `frontend/src/utils/chatAuth.js` (base), `frontend/src/utils/codingModeClient.js` (09), `frontend/src/utils/projectPreparation.js` (base).
- `frontend/src/components/CodingModePanel.jsx` → `frontend/src/components/CodingPreparationPanel.jsx` (base), `frontend/src/components/CodingTaskHistory.jsx` (base), `frontend/src/components/useAppStore.js` (base), `frontend/src/hooks/useConversationMemory.jsx` (base), `frontend/src/utils/chatAuth.js` (base), `frontend/src/utils/codingModeClient.js` (09), `frontend/src/utils/projectPreparation.js` (base).
- `frontend/src/components/components/CodingModePanel.jsx` → `frontend/src/components/components/CodingPreparationPanel.jsx` (base), `frontend/src/components/components/CodingTaskHistory.jsx` (base), `frontend/src/components/components/useAppStore.js` (base), `frontend/src/hooks/useConversationMemory.jsx` (base), `frontend/src/utils/chatAuth.js` (base), `frontend/src/utils/codingModeClient.js` (09), `frontend/src/utils/projectPreparation.js` (base).
- `frontend/src/utils/codingModeClient.js` → `frontend/src/utils/chatHttpResponse.js` (base), `frontend/src/utils/codingMode.js` (09).
- `backend/core/crypto_com_acknowledgements.py` → `backend/core/coding_journal.py` (06; L11), `backend/core/coding_locks.py` (06; L12), `backend/core/crypto_com_adapter.py` (11; L13), `backend/core/crypto_execution_controls.py` (base; L14).
- `backend/core/crypto_com_adapter.py` → `backend/core/crypto_execution_controls.py` (base; L13).
- `backend/core/crypto_com_native_stop.py` → `backend/core/crypto_execution_controls.py` (base; L12).
- `backend/core/crypto_credential_preparation_registry.py` → `backend/core/coding_journal.py` (06; L12), `backend/core/coding_locks.py` (06; L11), `backend/core/crypto_com_acknowledgements.py` (11; L13), `backend/core/crypto_credential_preparation.py` (11; L41, late/guarded), `backend/core/crypto_execution_controls.py` (base; L14), `backend/core/personal_memory_scope.py` (05; L15), `backend/security/crypto_trial_root.py` (11; L10).
- `backend/core/crypto_credential_preparation.py` → `backend/core/crypto_execution_controls.py` (base; L14), `backend/core/crypto_trial_binding.py` (11; L15), `backend/core/personal_memory_scope.py` (05; L16).
- `backend/core/crypto_current_snapshot.py` → `backend/core/crypto_com_acknowledgements.py` (11; L16), `backend/core/crypto_credential_preparation.py` (11; L17), `backend/core/crypto_current_snapshot_facts.py` (11; L19), `backend/core/crypto_execution_controls.py` (base; L20), `backend/core/personal_memory_scope.py` (05; L21).
- `backend/core/crypto_held_preparation_runtime.py` → `backend/core/coding_journal.py` (06; L14), `backend/core/crypto_com_acknowledgements.py` (11; L15), `backend/core/crypto_credential_preparation.py` (11; L16), `backend/core/crypto_credential_preparation_registry.py` (11; L17), `backend/core/crypto_current_snapshot.py` (11; L18), `backend/core/crypto_execution_controls.py` (base; L19), `backend/core/crypto_reinvestment.py` (11; L20), `backend/core/crypto_trial_budget.py` (11; L21), `backend/core/crypto_trial_runtime_store.py` (11; L22), `backend/core/personal_memory_scope.py` (05; L24), `backend/security/crypto_trial_root.py` (11; L13).
- `backend/core/crypto_preparation_status.py` → `backend/core/crypto_credential_preparation_registry.py` (11; L51, late/guarded), `backend/core/crypto_held_preparation_runtime.py` (11; L52, late/guarded), `backend/core/personal_memory_scope.py` (05; L5), `backend/security/crypto_trial_root.py` (11; L53, late/guarded).
- `backend/core/crypto_preview_chat.py` → `backend/core/crypto_com_acknowledgements.py` (11; L27, late/guarded), `backend/tools/tool_registry.py` (base; L84, late/guarded).
- `backend/core/crypto_protective_lifecycle.py` → `backend/core/crypto_com_acknowledgements.py` (11; L11), `backend/core/crypto_com_adapter.py` (11; L12), `backend/core/crypto_com_native_stop.py` (11; L13), `backend/core/crypto_execution_controls.py` (base; L14), `backend/core/crypto_protective_review_contract.py` (11; L165, late/guarded), `backend/core/crypto_reinvestment.py` (11; L15), `backend/core/crypto_trial_projection.py` (11; L16), `backend/core/crypto_trial_runtime_store.py` (11; L17).
- `backend/core/crypto_reinvestment.py` → `backend/core/crypto_execution_controls.py` (base; L11), `backend/core/crypto_trial_budget.py` (11; L15), `backend/core/crypto_trial_projection.py` (11; L16).
- `backend/core/crypto_spot_preview.py` → `backend/core/crypto_execution_controls.py` (base; L4).
- `backend/core/crypto_spot_protection.py` → `backend/core/crypto_execution_controls.py` (base; L3).
- `backend/core/crypto_trial_admission.py` → `backend/core/crypto_execution_controls.py` (base; L11), `backend/core/crypto_reinvestment.py` (11; L15), `backend/core/crypto_trial_budget.py` (11; L16), `backend/core/crypto_trial_projection.py` (11; L17).
- `backend/core/crypto_trial_binding.py` → `backend/core/crypto_execution_controls.py` (base; L17).
- `backend/core/crypto_trial_budget.py` → `backend/core/crypto_execution_controls.py` (base; L13).
- `backend/core/crypto_trial_projection.py` → `backend/core/crypto_execution_controls.py` (base; L11), `backend/core/crypto_trial_budget.py` (11; L15).
- `backend/core/crypto_trial_registry.py` → `backend/core/coding_journal.py` (06; L13), `backend/core/crypto_com_acknowledgements.py` (11; L14), `backend/core/crypto_execution_controls.py` (base; L15), `backend/core/crypto_protective_lifecycle.py` (11; L147, late/guarded), `backend/core/crypto_protective_review_contract.py` (11; L137, late/guarded), `backend/core/crypto_trial_runtime_store.py` (11; L16), `backend/core/crypto_trial_status_contract.py` (11; L27, late/guarded), `backend/core/personal_memory_scope.py` (05; L17), `backend/security/crypto_trial_root.py` (11; L12).
- `backend/core/crypto_trial_runtime_store.py` → `backend/core/coding_journal.py` (06; L18), `backend/core/coding_locks.py` (06; L20), `backend/core/crypto_com_acknowledgements.py` (11; L19), `backend/core/crypto_execution_controls.py` (base; L21), `backend/core/crypto_reinvestment.py` (11; L22), `backend/core/crypto_trial_admission.py` (11; L23), `backend/core/crypto_trial_binding.py` (11; L24), `backend/core/crypto_trial_budget.py` (11; L25), `backend/core/crypto_trial_projection.py` (11; L26), `backend/security/crypto_trial_root.py` (11; L17).
- `backend/core/crypto_trial_status_chat.py` → `backend/core/crypto_preparation_status.py` (11; L27, late/guarded), `backend/core/crypto_protective_review_contract.py` (11; L44, late/guarded), `backend/core/crypto_trial_status_contract.py` (11; L67, late/guarded), `backend/tools/tool_registry.py` (base; L119, late/guarded).
- `backend/security/crypto_trial_root.py` → `backend/security/theatrical_corpus_boundary.py` (11; L20), `backend/security/theatrical_storage_roots.py` (11; L19).
- `backend/security/theatrical_storage_roots.py` → `backend/security/theatrical_corpus_boundary.py` (11; L22).
- `backend/tools/bs_chat_tool_bridge.py` → `backend/core/coding_process.py` (06; L237, late/guarded), `backend/core/crypto_com_acknowledgements.py` (11; L118, late/guarded), `backend/core/crypto_execution_controls.py` (base; L150, late/guarded), `backend/core/crypto_preparation_status.py` (11; L88, late/guarded), `backend/core/crypto_protective_review_contract.py` (11; L106, late/guarded), `backend/core/crypto_spot_preview.py` (11; L151, late/guarded), `backend/core/crypto_spot_protection.py` (11; L188, late/guarded), `backend/core/crypto_trial_registry.py` (11; L99, late/guarded), `backend/core/crypto_trial_status_contract.py` (11; L96, late/guarded), `backend/core/personal_memory_scope.py` (05; L10), `scripts/check_coding_candidate.py` (11; dynamic; explicit script path).
- `scripts/check_coding_candidate.py` → `native_studio/local_connection.py` (base; L41, late/guarded).
- `frontend/components/BrandCampaignManager.jsx` → `frontend/components/OutreachReceipts.jsx` (12), `frontend/firebase.js` (base), `frontend/src/utils/chatAuth.js` (base).
- `frontend/components/components/BrandCampaignManager.jsx` → `frontend/components/components/OutreachReceipts.jsx` (12), `frontend/components/firebase.js` (base), `frontend/src/utils/chatAuth.js` (base).
- `frontend/src/components/BrandCampaignManager.jsx` → `frontend/src/components/OutreachReceipts.jsx` (12), `frontend/src/firebase.js` (base), `frontend/src/utils/chatAuth.js` (base).
- `frontend/src/components/components/BrandCampaignManager.jsx` → `frontend/src/components/components/OutreachReceipts.jsx` (12), `frontend/src/components/firebase.js` (base), `frontend/src/utils/chatAuth.js` (base).
- `frontend/src/utils/productionsCloudAnalytics.js` → `frontend/src/firebase.js` (base), `frontend/src/utils/chatAuth.js` (base).
- `backend/fe_express_owned_records.py` → `backend/security/firebase_auth.py` (09; L12).
- `backend/fe_truck_profiles.py` → `backend/fe_express_owned_records.py` (13; L13).
- `backend/modules/accounting_router.py` → `backend/core/payment_receipts.py` (13; L20), `backend/security/financial_auth.py` (13; L21).
- `backend/modules/personal_export_parts.py` → `backend/modules/accounting_router.py` (13; L25, late/guarded), `backend/modules/personal_financial_filings.py` (13; L41, late/guarded), `backend/modules/personal_ledger_export.py` (13; L42, late/guarded), `backend/modules/personal_payment_documents.py` (13; L11), `backend/modules/personal_payments.py` (13; L40, late/guarded), `backend/modules/personal_year_archive.py` (13; L12), `backend/security/financial_auth.py` (13; L13).
- `backend/modules/personal_filing_archive.py` → `backend/modules/accounting_router.py` (13; L16, late/guarded), `backend/modules/personal_financial_filings.py` (13; L9), `backend/modules/personal_payment_documents.py` (13; L7), `backend/modules/personal_year_archive.py` (13; L8), `backend/security/financial_auth.py` (13; L10).
- `backend/modules/personal_financial_filings.py` → `backend/modules/accounting_router.py` (13; L46, late/guarded), `backend/modules/personal_payment_documents.py` (13; L8), `backend/modules/personal_payments.py` (13; L7), `backend/security/financial_auth.py` (13; L9).
- `backend/modules/personal_ledger_export.py` → `backend/core/payment_receipts.py` (13; L9), `backend/modules/accounting_router.py` (13; L17, late/guarded), `backend/modules/personal_export_parts.py` (13; L66, late/guarded), `backend/modules/personal_filing_archive.py` (13; L64, late/guarded), `backend/modules/personal_year_archive.py` (13; L62, late/guarded), `backend/security/financial_auth.py` (13; L10).
- `backend/modules/personal_payment_documents.py` → `backend/modules/accounting_router.py` (13; L47, late/guarded), `backend/security/document_retention.py` (13; L16), `backend/security/financial_auth.py` (13; L17).
- `backend/modules/personal_payments.py` → `backend/core/payment_receipts.py` (13; L9), `backend/modules/accounting_router.py` (13; L74, late/guarded), `backend/modules/personal_financial_filings.py` (13; L114, late/guarded), `backend/modules/personal_payment_documents.py` (13; L112, late/guarded), `backend/security/financial_auth.py` (13; L10).
- `backend/modules/personal_year_archive.py` → `backend/modules/accounting_router.py` (13; L24, late/guarded), `backend/modules/personal_ledger_export.py` (13; L49, late/guarded), `backend/modules/personal_payment_documents.py` (13; L10), `backend/modules/personal_payments.py` (13; L25, late/guarded), `backend/security/financial_auth.py` (13; L11).
- `backend/routers/fe_driver_registration.py` → `backend/fe_express_owned_records.py` (13; L9, late/guarded), `backend/fe_truck_profiles.py` (13; L10, late/guarded).
- `backend/security/financial_auth.py` → `backend/security/firebase_auth.py` (09; L4).
- `native_studio/coding_mode_service.py` → `native_studio/local_connection.py` (base; L4).
- `native_studio/coding_mode_view.py` → `native_studio/coding_mode_service.py` (14; L9).
- `native_studio/creation_suite_subtools.py` → `native_studio/creative_handoff.py` (14; L63), `native_studio/engine.py` (base; L62), `native_studio/service_orchestrator.py` (base; L64).
- `native_studio/creative_pipe_bootstrap.py` → `native_studio/creative_pipe_io.py` (14; L17), `native_studio/creative_session.py` (14; L13).
- `native_studio/creative_pipe_io.py` → `native_studio/creative_wire.py` (14; L17).
- `native_studio/creative_pipe_transport.py` → `native_studio/creative_pipe_io.py` (14; L10), `native_studio/creative_session.py` (14; L37, late/guarded), `native_studio/creative_wire.py` (14; L11).
- `native_studio/creative_session.py` → `native_studio/creative_pipe_bootstrap.py` (14; L158, late/guarded), `native_studio/creative_pipe_transport.py` (14; L235, late/guarded), `native_studio/local_connection.py` (base; L14).
- `native_studio/local_refactor_view.py` → `native_studio/owned_process.py` (14; L13).
- `native_studio/native_creative_entry.py` → `native_studio/creative_session.py` (14; L9), `native_studio/engine.py` (base; L16, late/guarded), `native_studio/screenwriting_view.py` (14; L17, late/guarded), `native_studio/theme.py` (14; L83, late/guarded).
- `native_studio/packaged_writer_acceptance.py` → `native_studio/native_creative_entry.py` (14; L272, late/guarded), `native_studio/screenplay_client.py` (14; L105, late/guarded), `native_studio/screenwriting_view.py` (14; L106, late/guarded).
- `native_studio/process_batch_view.py` → `native_studio/ai_bs_ide_terminal.py` (14; L265, late/guarded), `native_studio/local_refactor_view.py` (14; L272, late/guarded), `native_studio/process_batch.py` (14; L10), `native_studio/responsive_layout.py` (14; L288, late/guarded).
- `native_studio/process_batch.py` → `native_studio/owned_process.py` (14; L222, late/guarded).
- `native_studio/screenplay_client.py` → `native_studio/creative_session.py` (14; L44, late/guarded), `native_studio/local_connection.py` (base; L16), `native_studio/rich_screenplay_draft.py` (14; L17), `native_studio/windows_profile.py` (14; L426, late/guarded).
- `native_studio/screenwriting_modals.py` → `native_studio/audio_kernel.py` (14; L59, late/guarded), `native_studio/engine.py` (base; L4123, late/guarded), `native_studio/screenplay_client.py` (14; L4120, late/guarded).
- `native_studio/screenwriting_view.py` → `native_studio/creation_suite_subtools.py` (14; L2515, late/guarded), `native_studio/creative_session.py` (14; L289, late/guarded), `native_studio/engine.py` (base; L57), `native_studio/screenplay_client.py` (14; L23), `native_studio/screenwriting_modals.py` (14; L1748, late/guarded), `native_studio/theme.py` (14; L58).
- `native_studio/syntax_check.py` → `native_studio/process_batch.py` (14; L8), `native_studio/process_batch_view.py` (14; L9), `native_studio/screenplay_client.py` (14; L10), `native_studio/syntax_worker.py` (14; L11).
- `frontend/bs-chat.html` → `frontend/bs-chat.jsx` (15), `frontend/public/favicon.svg` (base).
- `frontend/bs-chat.jsx` → `frontend/components/LoginModal.jsx` (base), `frontend/components/MobileStehouwerChat.jsx` (base), `frontend/components/accessControl.js` (base), `frontend/components/useAppStore.js` (base), `frontend/config/api.js` (base), `frontend/firebase.js` (base), `frontend/responsive-fixes.css` (base), `frontend/src/index.css` (base), `frontend/src/utils/bsChatProvider.js` (base), `frontend/src/utils/chatAuth.js` (base), `frontend/style.css` (base).
- `frontend/driver/index.html` → `frontend/driver/main.jsx` (15), `frontend/public/driver/manifest.webmanifest` (15).
- `frontend/driver/main.jsx` → `frontend/src/fe-express/DriverPortal.jsx` (15), `frontend/src/fe-express/driver.css` (15).
- `frontend/personal/index.html` → `frontend/personal/main.jsx` (15).
- `frontend/personal/main.jsx` → `frontend/src/personal-finance/PersonalFinancePortal.jsx` (15), `frontend/src/personal-finance/personal.css` (15).
- `frontend/src/fe-express/driverClient.js` → `frontend/src/utils/feExpressOfflineStore.js` (15).
- `frontend/src/fe-express/DriverPortal.jsx` → `frontend/src/components/LoginModal.jsx` (base), `frontend/src/components/accessControl.js` (base), `frontend/src/fe-express/TruckProfile.jsx` (15), `frontend/src/fe-express/driverClient.js` (15), `frontend/src/firebase.js` (base).
- `frontend/src/fe-express/TruckProfile.jsx` → `frontend/src/fe-express/truckProfile.css` (15), `frontend/src/fe-express/truckProfileStore.js` (15).
- `frontend/src/personal-finance/PersonalFinancePortal.jsx` → `frontend/src/components/accessControl.js` (base), `frontend/src/firebase.js` (base), `frontend/src/personal-finance/FinancialFilings.jsx` (15), `frontend/src/personal-finance/MultipartExport.jsx` (15), `frontend/src/personal-finance/OfflineShell.jsx` (15), `frontend/src/personal-finance/PersonalSignIn.jsx` (15), `frontend/src/personal-finance/personalClient.js` (15).
- `frontend/src/personal-finance/PersonalSignIn.jsx` → `frontend/src/firebase.js` (base).
- `frontend/vite.bs-chat.config.mjs` → `frontend/vite.config.js` (base).
- `frontend/vite.driver.config.mjs` → `frontend/vite.bs-chat.config.mjs` (15).
- `frontend/vite.personal.config.mjs` → `frontend/vite.config.js` (base).
- `frontend/vite.release.config.mjs` → `frontend/vite.driver.config.mjs` (15), `frontend/vite.personal.config.mjs` (15).

Local import path resolution stopped at pinned modules unless their changed interface or a relevant inherited gap was examined separately. Local module paths were checked; Python distribution availability, all exported attributes, dynamic dispatch, packaging, full-stack startup, and all environment-specific branches were not executed or certified. Some packages are cyclic through function-local imports. Include the named peers in the same modeled step; a filename match is insufficient evidence of runtime import order.

## Test index and provenance

Local-only tests are validation evidence to consider, **not** assigned production providers or automatic additions. Base tests may reference infrastructure absent from HEAD. A file’s membership in HEAD does not mean its current uncommitted assertions are in HEAD. No test was run.

| Test file | Source availability |
|---|---|
| `scripts/tests/test_cdz_router_composition.py` | local only; absent from pinned tree |
| `scripts/tests/test_cdz_host_composition.py` | local only; absent from pinned tree |
| `scripts/tests/test_chat_context_budget.py` | in pinned tree |
| `scripts/tests/test_gpu_dispatcher_integration.py` | in pinned tree |
| `scripts/tests/test_local_ollama_http.py` | in pinned tree |
| `backend/test_program_builder.py` | in pinned tree |
| `scripts/tests/test_program_builder_takeover.py` | in pinned tree |
| `scripts/tests/test_project_maintenance.py` | in pinned tree |
| `scripts/tests/test_project_maintenance.mjs` | in pinned tree |
| `scripts/tests/test_fdx_source_workflow.py` | in pinned tree |
| `scripts/tests/test_fdx_rich_workflow.mjs` | in pinned tree |
| `scripts/tests/test_screenplay_pdf.py` | in pinned tree |
| `scripts/tests/test_audio_router_trace.py` | in pinned tree |
| `scripts/tests/test_comfy_status_routing.py` | in pinned tree |
| `backend/tests/test_chat_film_smoke.py` | local only; absent from pinned tree |
| `scripts/tests/test_mobile_attached_sources.mjs` | in pinned tree |
| `scripts/tests/test_conversation_memory_context.mjs` | in pinned tree |
| `backend/tests/test_coding_mode_execution.py` | local only; absent from pinned tree |
| `go-core/pkg/gateway/backend_routing_test.go` | local only; absent from pinned tree |
| `go-core/pkg/telemetry/security_identity_test.go` | in pinned tree |
| `go-core/pkg/telemetry/fe_capture_cors_test.go` | local only; absent from pinned tree |
| `Crypto-Swarm/internal/daemons/trade_engine_safety_test.go` | in pinned tree |
| `Crypto-Swarm/internal/daemons/public_market_data_test.go` | local only; absent from pinned tree |
| `scripts/tests/test_crypto_execution_controls.py` | in pinned tree |
| `backend/tests/test_crypto_trial_status_http_smoke.py` | local only; absent from pinned tree |
| `scripts/tests/test_login_redirect_recovery.cjs` | in pinned tree |
| `scripts/tests/test_host_action_browser_auth.cjs` | in pinned tree |
| `backend/tests/test_fe_driver_registration.py` | local only; absent from pinned tree |
| `backend/tests/test_personal_payments.py` | local only; absent from pinned tree |
| `backend/tests/test_personal_ledger_export.py` | local only; absent from pinned tree |
| `scripts/tests/test_native_creative_handoff.py` | in pinned tree |
| `native_studio/test_packaged_writer_acceptance.py` | local only; absent from pinned tree |
| `native_studio/test_coding_mode_view.py` | local only; absent from pinned tree |

## Disposition

The ledger and named static edges are suitable for owner review. The proposed sequence does not meet a claim that every intermediate checkout can boot or bundle independently. Decide on the inherited baseline first, review the ignored paths and sensitive documents, then re-evaluate exact staged hunks and test availability against each real parent in a separately authorized worktree. Keep the six held paths out of the series. No change to the main branch, index, UI task branch or running services is part of this report.
