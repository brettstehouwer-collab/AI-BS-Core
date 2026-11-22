# Codex tracked-change dependency triage

2026-11-21 · C:\AI-BS · codex/audit-v532976-20261031 · HEAD 64fad2871e0a716d9964f506bdef1050612b173d

The tracked-only porcelain query returned 137 unstaged modifications, no staged changes. Git diff --stat reported 10,934 insertions and 2,014 deletions. This is static analysis of the working changes versus HEAD. No tests, builds, imports of application code, service requests, credential reads, or untracked-tree inventory. Coverage below means test source or test intent, never a passing result. A file can participate in several contracts.

## Consequences of taking an individual file in isolation

| Changed caller or area | Producer, consumer and failure mode |
|---|---|
| backend/AI_BS_Backend.py | Module-level registration of the driver portal, chat films, ledger export and personal payments requires four providers listed below. With only this diff on HEAD the imports cannot resolve from the repository; application initialization is at risk before requests are served. The same file independently changes allowed headers and translates unavailable tool results to HTTP 503. |
| backend/routers/trading_router.py, backend/core/hybrid_reasoning_engine.py, backend/tools/tool_registry.py | Routes, chat intent, declaration functions and the BS-chat bridge must agree on preview, trial, preparation and protective-review names, shapes and held states. Preview/trial/review code imports providers outside the tracked delta. Some imports are inside handlers, so failures can appear only when invoked. UI CryptoLiveStreamTab expects public-book and public-preview and formats missing/nonfinite data. A UI-only change against the earlier API can yield missing routes or unavailable data. |
| Crypto-Swarm/internal/daemons/trade_engine.go | Changes public Crypto.com instrument and ticker reads to publicMarketData, marketPrecision and marketPrice defined in public_market_data.go. It changes response fields, rejects malformed/duplicate items and replaces the market map after validation. Without the companion definitions the Go package cannot compile. Prices and precisions feed downstream order sizing; the observed edits are in public market reads, not a verified change to private order submission. No exchange behavior was exercised. |
| backend/core/program_builder_engine.py, real_system_tools.py, routers/artifacts_sync_router.py, AI_BS_Backend.py and native_studio/bs_chat_ide_full.py | Program builder gates execution, can dispatch maintenance, and returns unavailable. Real-system-tools requests source-only scaffolds and handles unavailable. Artifact build/run and generic tool execution expose 503; native rendering handles result/error presentation. An old caller can misreport a failed or unavailable operation; a caller passing a new keyword to an older signature can raise TypeError. This is separate from live startup validation. |
| backend/database/cdz_audit_db.py and backend/routers/audit_ledger_router.py | Router injects a store, passes store= into database functions and selects a watcher for that store. The older database signatures do not accept that keyword. Router alone would fail on those requests. Database module retains a default path for legacy callers; injected mode needs a compatible app-state store/watcher. |
| backend/core/matrix_docs.py, routers/screenwriting_router.py, ScreenwritingTab.jsx | Fountain classification now preserves authored headings and dialogue blocks. Typed-professional PDF requests use the new renderer, and the frontend restricts FDX vs PDF modes and reads page-count/hash receipts. UI alone offers a layout the old backend does not implement. Preserved FDX and legacy reflow are separate paths. |
| backend/f5_tts_daemon.py, ComfyUIStudio.jsx and NeuralAudioStudioTab.jsx | UI consumes proxied audio paths for workflow listing, screenplay list/load, creative narration and VoiceStudio launch. New daemon handlers supply these; stale daemon/proxy can produce missing routes. The launch path involves a subprocess. |
| backend/core/sovereign_reasoning/dispatcher.py, math_autograd.py, routers/agent_routing.py | Dispatcher consumes local_chat_inference history/message/budget helpers and an operation-specific reasoner. Changes couple inference prompt handling with the context-budget and local Ollama HTTP tests. math_autograd makes torch import optional; that alone does not prove torch-dependent calls can execute. Agent routing adds an optional Ollama origin override. |
| backend/core/media_intent_policy.py | Eligible film prompts now import core.chat_film before ordinary media classification. Missing provider can fail even before the ComfyUI branch. Separate from the new chat-films router registration. |
| ChatTab.jsx, MobileStehouwerChat.jsx, CodingPreparationPanel.jsx, attachedSources.js, conversationOutbox.js | Desktop/mobile share frame parsing and metadata stripping. Desktop also imports CodingModePanel and codingMode; preparation panel adds allowCodeProposal. Attached-source checks handle empty history; outbox changes revision advancement under streaming. Updated mobile test imports the same parser. Missing JS modules can block bundling; splitting data producer and consumer can lose metadata or change conflict handling. |
| frontend/App.jsx, LoginModal.jsx, TopNavbar.jsx, accessControl.js, utils/antiTamperGuard.js | App restores local desktop identity and supplies sign-out; modal creates the expected identity shape, accessControl distinguishes local and verified Firebase admin, navbar calls the sign-out callback with fallback. Anti-tamper allowlist also changes. Partial changes can disagree on visible/admin state and session cleanup. Browser role decisions are distinct from backend authorization. |
| BetaAnalyticsTab.jsx, frontend/src/utils/analyticsData.js, frontend/App.jsx | Campaign manager is imported by the tab and selected in the app. Analytics loader imports the productions cloud loader. Missing modules break resolution when the relevant entry is bundled. |
| API config copies, useBackendHealth.js, TopNavbar.jsx, CryptoAccountingTab.jsx, CryptoSwarmMobileController.jsx, MiningDashboardTab.jsx, PearlMiningHubTab.jsx, go-core/pkg/gateway/gateway.go and go-core/pkg/telemetry/security.go | Browser default changes toward port 8000; health selection also considers 8080. Gateway now derives a loopback Python target from its configured worker port, wraps the mux with the defense shield, and proxies media/API calls. CORS headers must allow the headers sent by clients. Deploying only a default URL or proxy change can route to the wrong worker or reject a preflight. No listener checks were made. |
| native_studio/app.py and bs_chat_ide_full.py | Entry adds syntax-worker and packaged writer acceptance modes. IDE imports CodingModeView and SyntaxCheck and adds worker/UI callbacks. Missing native modules can block UI import or fail on a selected launch mode. Packaging and subprocess paths are unverified. |
| frontend/firebase.json and frontend/index.html | Hosting rewrites introduce /chat, /driver and /personal destinations. Published HTML/assets and hosting cache rules must agree with the built artifact. A rewrite alone does not supply its destination. The HTML shell change needs deployment-level validation. |
| Version markers and manifests | release.json, version.txt, root/frontend/BroadcastStudioApp package manifests and locks, public/version.json, version.js copies and HTML references are release consumers. Partial updates can leave package/lock metadata, visible version and release checks inconsistent. No version tool or packaging command was run. |
| Planning, architecture, handoff, runtime JSON, tracked bytecode | AGENTS/GEMINI, plans, project/test docs and agent_sync/architecture/game docs reference shared decisions and checkpoints. They do not supply imported modules. matrix_health_report.json and viewport.json are observations, not evidence of current health. Four .pyc changes are interpreter artifacts, not coverage or proof of success. Two have no changed same-name .py test in this delta. |

## Trading, exchange and credential-handling flags

- Direct exchange-client logic changes in trade_engine.go; market-data schema/precision decisions affect consumers even if private dispatch is held. The tracked desktop variant is a separate tree. Do not infer parity of the two engines from the similar names.
- trading_router adds guarded and public data paths, host-admin access checks, scoped principal binding/reset, bridge calls, and public HTTP book reads. Hybrid reasoning and registry expose crypto operations to chat. Public preview arithmetic, private account observations, and live submission are distinct boundaries. This review establishes no live-order authorization.
- CryptoLiveStreamTab changes optional auth headers and preview/book consumption. Accounting, swarm, mining and Pearl panels change routing. Personal payments/ledger registration is financial exposure even though this tracked entry file does not implement the providers.
- Local desktop login, Firebase verified identity, frontend role allowlists, session restore/sign-out, Go defense/CORS and FastAPI allowed-header changes affect identity or credential transport. Allowing a header is not validation of its value. The vault migration plan is documentation; fixture names and past claims are not evidence of active credentials. No credential values were inspected.

## Import and helper availability

Checked against the Git index (there are no staged changes) and, only for the named import target, ordinary path existence. “Outside HEAD” means a clean checkout containing only the tracked delta cannot obtain this provider from HEAD at that path. This is not a request to include untracked contents.

| Provider | In HEAD | File present locally |
|---|---|---|
| `backend/routers/fe_driver_registration.py` | outside HEAD | yes |
| `backend/routers/chat_films.py` | outside HEAD | yes |
| `backend/modules/personal_ledger_export.py` | outside HEAD | yes |
| `backend/modules/personal_payments.py` | outside HEAD | yes |
| `backend/core/crypto_preview_chat.py` | outside HEAD | yes |
| `backend/core/crypto_trial_status_chat.py` | outside HEAD | yes |
| `backend/core/chat_film.py` | outside HEAD | yes |
| `backend/core/project_maintenance.py` | outside HEAD | yes |
| `backend/core/local_chat_inference.py` | outside HEAD | yes |
| `backend/core/sovereign_reasoning/dag_topological_reasoner.py` | outside HEAD | yes |
| `backend/core/fdx_source_documents.py` | outside HEAD | yes |
| `backend/core/fdx_professional_pdf.py` | outside HEAD | yes |
| `backend/core/crypto_spot_preview.py` | outside HEAD | yes |
| `backend/core/crypto_execution_controls.py` | yes | yes |
| `backend/core/crypto_trial_status_contract.py` | outside HEAD | yes |
| `backend/core/crypto_protective_review_contract.py` | outside HEAD | yes |
| `backend/core/crypto_com_acknowledgements.py` | outside HEAD | yes |
| `backend/core/personal_memory_scope.py` | outside HEAD | yes |
| `backend/security/host_control_access.py` | yes | yes |
| `backend/tools/bs_chat_tool_bridge.py` | outside HEAD | yes |
| `Crypto-Swarm/internal/daemons/public_market_data.go` | outside HEAD | yes |
| `frontend/src/components/CodingModePanel.jsx` | outside HEAD | yes |
| `frontend/src/components/BrandCampaignManager.jsx` | outside HEAD | yes |
| `frontend/src/utils/chatStream.js` | outside HEAD | yes |
| `frontend/src/utils/codingMode.js` | outside HEAD | yes |
| `frontend/src/utils/productionsCloudAnalytics.js` | outside HEAD | yes |
| `native_studio/syntax_worker.py` | outside HEAD | yes |
| `native_studio/syntax_check.py` | outside HEAD | yes |
| `native_studio/coding_mode_view.py` | outside HEAD | yes |
| `native_studio/packaged_writer_acceptance.py` | outside HEAD | yes |

## Test source evidence by area

Paths below are existing tracked test files. “Related” means neighboring behavior only. Exact checks of new contracts require inspection beyond a matching suite name. No suite was executed.

- **Exchange and financial controls**. `Crypto-Swarm/internal/daemons/trade_engine_safety_test.go`, `scripts/tests/test_crypto_execution_controls.py`, `scripts/tests/test_native_crypto_truth.py`. Safety, execution controls and native reporting; public-v1 parser and new endpoint schemas need separate coverage.
- **Gateway, identity, login and security headers**. `go-core/pkg/telemetry/security_id_keys_test.go`, `go-core/pkg/telemetry/security_identity_test.go`, `scripts/tests/test_host_action_browser_auth.cjs`, `scripts/tests/test_login_redirect_recovery.cjs`. Identity and login behaviors; new CORS allowlist, local-admin trust and proxy routing need dedicated assertions.
- **Provider routing, history and specialist reasoning**. `scripts/tests/test_chat_context_budget.py`, `scripts/tests/test_gpu_dispatcher_integration.py`, `scripts/tests/test_local_ollama_http.py`. Changed tests exercise budget/history and prompt stability; helpers/fixtures are dependencies in their own right.
- **Desktop/mobile chat, sources and durable state**. `scripts/tests/test_attached_sources.mjs`, `scripts/tests/test_mobile_attached_sources.mjs`, `scripts/tests/test_conversation_memory_context.mjs`. Mobile test directly imports the stream parser; adjacent conversation/source coverage does not establish complete outbox concurrency or JSX rendering coverage.
- **Scaffold generation and maintenance**. `backend/test_program_builder.py`, `scripts/tests/test_program_builder_takeover.py`, `scripts/tests/test_project_maintenance.py`, `scripts/tests/test_project_maintenance.mjs`. Related builder and maintenance suites. Verify unavailable/503 across each public adapter separately.
- **Screenwriting, media and audio**. `scripts/tests/test_fountain_export_title_page.py`, `scripts/tests/test_fdx_source_workflow.py`, `scripts/tests/test_fdx_rich_workflow.mjs`, `scripts/tests/test_fdx_source_documents.py`, `scripts/tests/test_screenwriting_audio_owner_handoff.py`, `scripts/tests/test_audio_router_trace.py`, `scripts/tests/test_comfy_status_routing.py`. Source-document, UI, routing and handoff coverage; no claim all new PDF, narration, workflow or film-intent branches are asserted.
- **Native desktop**. `scripts/tests/test_native_creative_handoff.py`, `scripts/tests/test_native_creative_entry.py`, `scripts/tests/test_native_telemetry_shutdown.py`. Related entry, handoff and lifecycle. A tracked bytecode change is not evidence that a new packaged worker was tested.
- **Health and process telemetry**. `backend/test_ecosystem_telemetry_and_port_tools.py`, `scripts/tests/test_network_telemetry_security.py`. Related test sources; recorded JSON is point-in-time data.
- **Release and packaging**. `scripts/tests/test_asset_release_smoke.py`, `scripts/tests/test_native_game_release.py`. Related release areas, not proof of npm lock/hosting or multi-package version consistency.

No direct tracked assertion established here for the new campaign/cloud analytics integration, personal payments and ledger registration, driver portal registration, CDZ injected-store/watcher pairing, Firebase rewrite destinations, or the historical documents.

## Full tracked-path inventory

Each entry below was in the tracked-only status at capture. Repeated frontend paths are deliberate: they are distinct committed consumers/mirrors. Presence in this inventory does not establish byte equality.

- `AGENTS.md`
- `BroadcastStudioApp/package-lock.json`
- `BroadcastStudioApp/package.json`
- `BroadcastStudioApp/src/version.js`
- `Crypto-Swarm/internal/daemons/trade_engine.go`
- `GEMINI.md`
- `PLAN.md`
- `PROJECT.md`
- `TEST_INFRA.md`
- `backend/AI_BS_Backend.py`
- `backend/core/hybrid_reasoning_engine.py`
- `backend/core/matrix_docs.py`
- `backend/core/media_intent_policy.py`
- `backend/core/program_builder_engine.py`
- `backend/core/real_system_tools.py`
- `backend/core/sovereign_reasoning/dispatcher.py`
- `backend/core/sovereign_reasoning/math_autograd.py`
- `backend/database/cdz_audit_db.py`
- `backend/f5_tts_daemon.py`
- `backend/matrix_health_report.json`
- `backend/routers/agent_routing.py`
- `backend/routers/artifacts_sync_router.py`
- `backend/routers/audit_ledger_router.py`
- `backend/routers/screenwriting_router.py`
- `backend/routers/trading_router.py`
- `backend/tools/tool_registry.py`
- `docs/CODEX_HANDOFF.md`
- `docs/agent_sync/GOAL_ADDITIONS_2026-11-11.json`
- `docs/agent_sync/current_long_term_goal.json`
- `docs/architecture/AI_BS_MASTER_ECOSYSTEM_ARCHITECTURE_2026-11-11.md`
- `docs/architecture/LEGACY_BUILD_EXECUTION_REVIEW_2026-11-11.md`
- `docs/architecture/SITES_SERVERS_REGISTER_2026-11-11.json`
- `docs/architecture/VAULT_KEY_MIGRATION_PLAN_2026-11-11.md`
- `docs/game_engine/PROJECT_INDEX.md`
- `docs/game_engine/UPDATED_GAME_TOOLS_2026-11-11.md`
- `docs/viewport_telemetry/probe_run/viewport.json`
- `frontend/App.jsx`
- `frontend/components/BetaAnalyticsTab.jsx`
- `frontend/components/ChatTab.jsx`
- `frontend/components/CodingPreparationPanel.jsx`
- `frontend/components/ComfyUIStudio.jsx`
- `frontend/components/CryptoAccountingTab.jsx`
- `frontend/components/CryptoLiveStreamTab.jsx`
- `frontend/components/CryptoSwarmMobileController.jsx`
- `frontend/components/LoginModal.jsx`
- `frontend/components/MiningDashboardTab.jsx`
- `frontend/components/MobileStehouwerChat.jsx`
- `frontend/components/NeuralAudioStudioTab.jsx`
- `frontend/components/PearlMiningHubTab.jsx`
- `frontend/components/ScreenwritingTab.jsx`
- `frontend/components/TopNavbar.jsx`
- `frontend/components/accessControl.js`
- `frontend/components/components/BetaAnalyticsTab.jsx`
- `frontend/components/components/ChatTab.jsx`
- `frontend/components/components/CodingPreparationPanel.jsx`
- `frontend/components/components/ComfyUIStudio.jsx`
- `frontend/components/components/CryptoAccountingTab.jsx`
- `frontend/components/components/CryptoLiveStreamTab.jsx`
- `frontend/components/components/CryptoSwarmMobileController.jsx`
- `frontend/components/components/LoginModal.jsx`
- `frontend/components/components/MiningDashboardTab.jsx`
- `frontend/components/components/MobileStehouwerChat.jsx`
- `frontend/components/components/NeuralAudioStudioTab.jsx`
- `frontend/components/components/PearlMiningHubTab.jsx`
- `frontend/components/components/ScreenwritingTab.jsx`
- `frontend/components/components/TopNavbar.jsx`
- `frontend/components/components/accessControl.js`
- `frontend/components/components/config/api.js`
- `frontend/components/components/useBackendHealth.js`
- `frontend/components/components/version.js`
- `frontend/components/config/api.js`
- `frontend/components/useBackendHealth.js`
- `frontend/components/version.js`
- `frontend/config/api.js`
- `frontend/firebase.json`
- `frontend/index.html`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/public/version.json`
- `frontend/src/components/BetaAnalyticsTab.jsx`
- `frontend/src/components/ChatTab.jsx`
- `frontend/src/components/CodingPreparationPanel.jsx`
- `frontend/src/components/ComfyUIStudio.jsx`
- `frontend/src/components/CryptoAccountingTab.jsx`
- `frontend/src/components/CryptoLiveStreamTab.jsx`
- `frontend/src/components/CryptoSwarmMobileController.jsx`
- `frontend/src/components/LoginModal.jsx`
- `frontend/src/components/MiningDashboardTab.jsx`
- `frontend/src/components/MobileStehouwerChat.jsx`
- `frontend/src/components/NeuralAudioStudioTab.jsx`
- `frontend/src/components/PearlMiningHubTab.jsx`
- `frontend/src/components/ScreenwritingTab.jsx`
- `frontend/src/components/TopNavbar.jsx`
- `frontend/src/components/accessControl.js`
- `frontend/src/components/components/BetaAnalyticsTab.jsx`
- `frontend/src/components/components/ChatTab.jsx`
- `frontend/src/components/components/CodingPreparationPanel.jsx`
- `frontend/src/components/components/ComfyUIStudio.jsx`
- `frontend/src/components/components/CryptoAccountingTab.jsx`
- `frontend/src/components/components/CryptoLiveStreamTab.jsx`
- `frontend/src/components/components/CryptoSwarmMobileController.jsx`
- `frontend/src/components/components/LoginModal.jsx`
- `frontend/src/components/components/MiningDashboardTab.jsx`
- `frontend/src/components/components/MobileStehouwerChat.jsx`
- `frontend/src/components/components/NeuralAudioStudioTab.jsx`
- `frontend/src/components/components/PearlMiningHubTab.jsx`
- `frontend/src/components/components/ScreenwritingTab.jsx`
- `frontend/src/components/components/TopNavbar.jsx`
- `frontend/src/components/components/accessControl.js`
- `frontend/src/components/components/config/api.js`
- `frontend/src/components/components/useBackendHealth.js`
- `frontend/src/components/components/version.js`
- `frontend/src/components/config/api.js`
- `frontend/src/components/useBackendHealth.js`
- `frontend/src/components/version.js`
- `frontend/src/config/api.js`
- `frontend/src/utils/analyticsData.js`
- `frontend/src/utils/attachedSources.js`
- `frontend/src/utils/conversationOutbox.js`
- `frontend/src/version.js`
- `frontend/utils/antiTamperGuard.js`
- `frontend/version.js`
- `go-core/pkg/gateway/gateway.go`
- `go-core/pkg/telemetry/security.go`
- `native_studio/app.py`
- `native_studio/bs_chat_ide_full.py`
- `package-lock.json`
- `package.json`
- `release.json`
- `scripts/tests/__pycache__/test_chat_context_budget.cpython-312.pyc`
- `scripts/tests/__pycache__/test_local_ollama_http.cpython-312.pyc`
- `scripts/tests/__pycache__/test_native_creative_handoff.cpython-312.pyc`
- `scripts/tests/__pycache__/test_native_telemetry_shutdown.cpython-312.pyc`
- `scripts/tests/test_chat_context_budget.py`
- `scripts/tests/test_local_ollama_http.py`
- `scripts/tests/test_mobile_attached_sources.mjs`
- `version.txt`
