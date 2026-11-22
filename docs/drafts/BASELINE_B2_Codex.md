# AI-BS baseline B2 | Backend import audit

This is Codex. Read-only source review on November 21, 2026. The checkout is `C:\AI-BS`, branch `codex/audit-v532976-20261031`, HEAD `64fad2871e0a716d9964f506bdef1050612b173d`. Paths and line numbers below are relative to that checkout. For tracked paths, line numbers refer to the pinned Git blob. For absent-at-pin paths, they refer to the local candidate source.

**Verdict.** Source exists on disk for every local import found in the 12 providers’ own closure. The original 12 require four more modules through unconditional imports and two package initializers to preserve the local game-trainer packages. Across the full backend, adding files alone cannot make every static import resolve. Four module names lack a provider at the requested location. Three additional import sites request exports that the resolved files do not provide. The effects and fallback behavior are listed below. Backend startup has not been executed or certified.

## 1. How this was checked

1. Confirmed the branch and full HEAD with Git. Read the 12 rows from the Codex B1 outside-ledger table and the 178 rows from the separate provider ledger in `docs/drafts/PHASE2_Codex.md`. Read B1 assignments from `docs/drafts/BASELINE_B1_Codex.md`.
2. Used the tree from `git ls-tree -rz --name-only <pin>` and read each pinned Python file from its Git blob. Used a local `.py` file only when the path was absent from the pin. Compared missing-at-pin candidates against the Git index and checked disk presence separately.
3. Parsed Python syntax as data. Followed `import`, `from`, relative imports and available package initializers. Kept guarded statements and function bodies for the broad graph. The unconditional column follows only module/class-body edges outside guards. An import in a called function can still execute during startup. The lifespan evidence below identifies examples.
4. Modeled the repository and backend search roots at `backend/AI_BS_Backend.py:91–101`, the ComfyUI core path at `backend/routers/comfyui_workspace_router.py:13–17`, the repository root at `backend/routers/memory_lab_router.py:16–21`, the core path at `backend/core/infinite_learning_loop.py:18–26` and the shared-memory path at `backend/omnidrive_service.py:10–17`. Runtime import order can change bare-name resolution. Checked project-like unresolved names against their effective roots and checked requested exports against Python definitions and re-exports.
5. Ran `git --no-optional-locks -c core.fsmonitor=false -C C:\AI-BS check-ignore -v -n -z --stdin` on the 85 outside-ledger paths. Input was UTF-8 paths terminated by NUL. Parsed four NUL-separated output fields per input. An empty match means no rule. A final `!` pattern includes the file. Results below use current checkout ignore rules.
6. This review used Git metadata and Python source. It did not import the application, open credential stores or runtime databases, run tests/builds, contact services or inspect remote repositories. The only deliverable is this report.

## 2. The 12 B1 providers

All 12 are **SOURCE**, exist on disk, and are absent from both HEAD and the index. Each consists of Python definitions or router declarations consumed by the indicated importer. “None” in the last column means no additional project-local import in that file. Third-party imports are covered below.

| Local provider | Disk / HEAD / index | Current Git ignore result | One incoming edge | Own local imports (provider line) |
| --- | --- | --- | --- | --- |
| `backend/routers/comfyui_workspace_router.py` | Yes / No / No | No matching rule | `backend/AI_BS_Backend.py:2048` | `core/comfy_workflow_builders.py` via bare import L17. `core/video_workflows.py` at L105, L326 and L340 is request-time. |
| `backend/routers/calendar_tasks_router.py` | Yes / No / No | Ignored by `.gitignore:348` `*NDA*` | `backend/AI_BS_Backend.py:2060` | None. SQLite initialization runs at L67. |
| `backend/core/cryptographic_vault.py` | Yes / No / No | Ignored by `.gitignore:329` `*crypto*` | `backend/AI_BS_Backend.py:3299` | None. Imports the external `cryptography` package. |
| `backend/security/analytics_access.py` | Yes / No / No | No matching rule | `backend/commercial_gateway/admin_telemetry_router.py:8` | `security/firebase_auth.py` L4. |
| `backend/security/vault_access.py` | Yes / No / No | No matching rule | `backend/modules/vault_router.py:9` | `security/firebase_auth.py` L6. |
| `backend/security/screenwriting_access.py` | Yes / No / No | No matching rule | `backend/routers/agent_routing.py:19` | `security/firebase_auth.py` L4 and pinned `security/document_access.py` L5. Reverse import of the screenwriting router at L23 is inside a request function. |
| `backend/routers/conversation_router.py` | Yes / No / No | No matching rule | `backend/routers/agent_routing.py:18` | `core/conversation_sessions.py` L10 and `security/firebase_auth.py` L14. |
| `backend/core/adaptation_store.py` | Yes / No / No | No matching rule | `backend/core/ai_adapter.py:13` | Pinned `routers/screenwriting_router.py` L58 and `core/matrix_docs.py` L152, both function-local. |
| `backend/core/chat_archive.py` | Yes / No / No | No matching rule | `backend/routers/memory_router.py:21` | `core/owned_vault.py` L10. Its `personal_memory_scope` import at L222 occurs inside a function. |
| `game_trainer/core/memory.py` | Yes / No / No | No matching rule | `backend/routers/memory_lab_router.py:20` | None. Platform-specific Windows APIs are used by constructors. `psutil` is a runtime dependency for process queries. |
| `game_trainer/profiles/btd6_profile.py` | Yes / No / No | No matching rule | `backend/routers/memory_lab_router.py:21` | `game_trainer/core/memory.py` L14, `hotkeys.py` L15 and `trainer.py` L20. |
| `backend/core/code_quality_gate.py` | Yes / No / No | No matching rule | `backend/core/coding_workflow.py:19` | None. Uses the standard library. |

Of these 12, 10 have no ignore match. Two are ignored. The `*NDA*` rule matches the letters “nda” in “calendar”, and `*crypto*` matches the vault module name. File classification and Git ignore status are independent.

## 3. Where the 12 chains end

Following all literal local imports from the 12 providers, including function-local imports and the initializers used when importing the game-trainer packages, reaches **54 distinct Python files**. Ten are at the pin, 22 belong to the 178-path ledger, and 22 are outside it. The last 22 consist of the 12 input paths and the following 10. All 10 exist on disk, are absent from the pin and index, and classify as SOURCE.

| Additional path | Why this path is reached | Importer and line | Source evidence |
| --- | --- | --- | --- |
| `backend/core/comfy_workflow_builders.py` | Unconditional import | `backend/routers/comfyui_workspace_router.py:17` | `get_resolution_specs` at L36 |
| `backend/core/conversation_sessions.py` | Unconditional import | `backend/routers/conversation_router.py:10` | `ConversationConflict` at L16 |
| `backend/core/document_text.py` | Reachable via deferred code | `backend/core/ai_adapter.py:88` | `iter_docx_paragraphs` at L6 |
| `backend/core/screenplay_workflows.py` | Reachable via deferred code | `backend/routers/screenwriting_router.py:280` | `WorkflowError` at L25 |
| `backend/security/native_creative_handoff.py` | Reachable via deferred code | `backend/routers/screenwriting_router.py:837` | `HandoffDenied` at L16 |
| `backend/security/native_creative_source.py` | Reachable via deferred code | `backend/routers/screenwriting_router.py:839` | `require_native_creative_source` at L13 |
| `game_trainer/core/__init__.py` | Local package initialization | `backend/routers/memory_lab_router.py:20` | Re-exports memory, hotkeys and trainer at L5, L12 and L20. |
| `game_trainer/core/hotkeys.py` | Unconditional import | `game_trainer/profiles/btd6_profile.py:15` | `HotkeyManager` at L101 |
| `game_trainer/core/trainer.py` | Unconditional import | `game_trainer/profiles/btd6_profile.py:20` | `TrainerVariable` at L14 |
| `game_trainer/profiles/__init__.py` | Local package initialization | `backend/routers/memory_lab_router.py:21` | Re-exports the BTD6 profile at L5. |

The builder and session modules import only the standard library. The game trainer imports its sibling memory and hotkey helpers at `game_trainer/core/trainer.py:10–11`. The two package initializers re-export these same components. The top-level `game_trainer` directory works as a namespace package. Restoring both child initializers preserves the existing package exports.

The only eagerly reached B1 files downstream of the 12 explicit modules are `backend/security/firebase_auth.py` and `backend/core/owned_vault.py`. The pinned `backend/security/document_access.py:13` also imports the Firebase helper. Firebase credential validation and the optional third-party Google provider have separate execution conditions.

**Pinned endpoints of this 54-file closure**
- `backend/core/ai_adapter.py`
- `backend/core/audio_transcriber.py`
- `backend/core/character_extractor.py`
- `backend/core/matrix_docs.py`
- `backend/core/project_rag.py`
- `backend/core/state_tax_incentives.py`
- `backend/routers/screenwriting_router.py`
- `backend/routers/shared_drive_router.py`
- `backend/routers/video_router.py`
- `backend/security/document_access.py`

**Existing ledger endpoints of this 54-file closure**
- `backend/core/chat_pdf_sources.py` (B02)
- `backend/core/fdx_source_documents.py` (B03)
- `backend/core/local_chat_inference.py` (B03)
- `backend/core/local_ollama_http.py` (B02)
- `backend/core/owned_rag_sources.py` (B02)
- `backend/core/owned_vault.py` (B02)
- `backend/core/pdf_text_source.py` (B02)
- `backend/core/personal_memory_scope.py` (B02)
- `backend/core/pipeline_context_injector.py` (B03)
- `backend/core/screenplay_pdf.py` (B02)
- `backend/core/screenplay_professional.py` (B02)
- `backend/core/video_workflows.py` (F08)
- `backend/gpu/__init__.py` (B02)
- `backend/gpu/compute_scheduler.py` (B02)
- `backend/gpu/gpu_telemetry.py` (B02)
- `backend/gpu/model_residency.py` (B02)
- `backend/gpu/stability_supervisor.py` (B02)
- `backend/gpu/vram_manager.py` (B02)
- `backend/orchestrator/__init__.py` (B02)
- `backend/orchestrator/gpu_task_dispatcher.py` (B02)
- `backend/security/document_retention.py` (B02)
- `backend/security/firebase_auth.py` (B02)

## 4. Broader backend graph and revised B02

The following are counts of unique local Python paths reached from pinned `backend/AI_BS_Backend.py`. A provider shared by several importers is counted once. The broad graph includes guarded integrations, imports made on individual requests, namespace/package initialization and fallbacks. It describes a stricter acceptance test than importing the module.

| Walk | Pinned paths | In the 178 | Outside the 178 | Total |
| --- | --- | --- | --- | --- |
| Unconditional import edges, including package initializers | 117 | 34 | 18 | 169 |
| All modeled literal local import edges | 262 | 70 | 85 | 417 |

**B02 for unconditional imports.** Retain the original 37 B02 sources. They include the 34 eager ledger files above and three retained for the B1 package/deferred behavior. Add the 12 initial providers, four unconditional transitive modules and two game-trainer initializers. That produces **55 proposed B02 files**. B01 remains the 17-file frontend group. All resolved local modules on the unconditional walk have on-disk candidates. None of the 18 additions is tracked in the pin or index. The 55-file proposal requires source and sensitivity review before adoption.

**B02 for the owner’s every-static-import criterion.** The available source envelope consists of **70 existing ledger paths plus 85 outside-ledger paths = 155 files beyond HEAD**. Relative to the 55-file proposal, that is 33 additional existing-ledger paths and 67 further outside-ledger paths. The 70 break down as B02 37, B03 8, B04 3, F08 1 and F11 21. Moving feature or trading providers forward would change the approved scope of future features. Even including all 155 files would leave the missing module names and export mismatches below. Consequently there is **no source-only B02 from the present candidates that satisfies every static import**. No promotion of these paths is approved by this report.

### Unavailable modules and incompatible imports

There was no missing local file at its expected path inside the 12-root closure. The broader graph exposes four unresolved module names. Absence refers to the effective project import locations in the checkout. Archived or backup copies are outside the import profile. Third-party installations were not inspected.

| Requested import | Pinned caller | Availability and effect |
| --- | --- | --- |
| `routers.bioinformatics_router` | `backend/AI_BS_Backend.py:1209` | No provider at `backend/routers/bioinformatics_router.py` or equivalent importable package. The entry point catches ImportError and skips registering the router at L1213–1217. |
| `imagegen_agent` | `backend/bullshit_orchestrator.py:69` | No module/package in the checked project import roots. L70–72 disable its integration when import fails. |
| `local_imagegen` | `backend/bullshit_orchestrator.py:75` and L944 | No module/package in the checked project import roots. L76–78 disable the optional module and the request-time code at L944 also asks for it. |
| `.media_chromadb_vault` | `backend/core/sovereign_reasoning/vlm_guidance_engine.py:97` | The relative name requires `backend/core/sovereign_reasoning/media_chromadb_vault.py` or its package. The existing `backend/core/media_chromadb_vault.py` sits one level higher. The stream handler reaches the unresolved import when called. |

Three more static import sites have incompatible exports. The third site below requests two missing symbols.

| Pinned caller | Requested export | Available source and effect |
| --- | --- | --- |
| `backend/AI_BS_Backend.py:432` | `get_self_healing_sentinel` | `backend/core/self_healing_sentinel.py:6,67` defines a code-quality class and validation function. The recovery callback catches the failure at L438, so the recovery attempt can be silently skipped. |
| `backend/modules/syndication_router.py:696` | `run_validation_suite` | `backend/scripts/validate_syndication_matrix.py:383` defines `run_validation`. The matrix audit catches the failure at L699 and returns an error. |
| `backend/bullshit_orchestrator.py:63` | `HeuristicsDaemon` and `get_heuristics_daemon` | The fallback module `backend/bullshit_heuristics_daemon.py:13,79` defines other functions. The first import at L60 can find the intended symbols at `backend/core/heuristic_filter.py:50,421` when `backend/core` is on the search path. Otherwise L65–66 disable the integration. |

**Bare-name and dynamic imports.** `backend/core/friction_manager.py:9`, `backend/bullshit_orchestrator.py:1317,1461` and `backend/core/memory_bank.py:20` use the bare names `tool_result`, `memory_service` and `coding_locks`. Their corresponding files exist under `backend/core`. The outcome depends on search-path order or fallback handling. `memory_bank.py:18` first tries its relative import. `backend/core/infinite_learning_loop.py:18–26` sets a core search path for `memory_bank`. `backend/omnidrive_service.py:10–18` appends `sandbox_scratch/ipc_benchmark`, which supplies `shm_bridge.py`, and has a fallback. No stale backup or file with the wrong qualified name was substituted for a missing provider.

`backend/core/plugin_loader.py:161` computes an import name at runtime. `backend/gpu/gpu_telemetry.py:68` dynamically imports the external `pynvml` library. No complete claim about plugin manifests, installed dependencies, service configuration, or import-time execution follows from the path counts.

### Existing-ledger membership needed for the broad profile

This table specifies all 70 existing-ledger files. The original B02 grouping is included so the revised membership can be reconstructed independently. The separate outside-ledger ledger below specifies the other 85.

**B02**

- `backend/core/chat_pdf_sources.py`
- `backend/core/coding_journal.py`
- `backend/core/coding_locks.py`
- `backend/core/coding_mode_execution.py`
- `backend/core/coding_mode_local.py`
- `backend/core/coding_preparation.py`
- `backend/core/coding_preparation_planning.py`
- `backend/core/coding_preparation_proposals.py`
- `backend/core/coding_process.py`
- `backend/core/coding_recovery.py`
- `backend/core/coding_repository_snapshot.py`
- `backend/core/coding_syntax.py`
- `backend/core/coding_vm_inputs.py`
- `backend/core/coding_vm_staging.py`
- `backend/core/local_ollama_http.py`
- `backend/core/owned_rag_sources.py`
- `backend/core/owned_vault.py`
- `backend/core/payment_receipts.py`
- `backend/core/pdf_text_source.py`
- `backend/core/personal_memory_scope.py`
- `backend/core/screenplay_pdf.py`
- `backend/core/screenplay_professional.py`
- `backend/gpu/__init__.py`
- `backend/gpu/compute_scheduler.py`
- `backend/gpu/gpu_telemetry.py`
- `backend/gpu/model_residency.py`
- `backend/gpu/stability_supervisor.py`
- `backend/gpu/vram_manager.py`
- `backend/modules/accounting_router.py`
- `backend/orchestrator/__init__.py`
- `backend/orchestrator/gpu_task_dispatcher.py`
- `backend/routers/coding_mode_router.py`
- `backend/routers/coding_preparation_router.py`
- `backend/routers/coding_review_router.py`
- `backend/security/document_retention.py`
- `backend/security/financial_auth.py`
- `backend/security/firebase_auth.py`

**B03**

- `backend/core/attached_source_context.py`
- `backend/core/chat_context_budget.py`
- `backend/core/fdx_source_documents.py`
- `backend/core/local_chat_inference.py`
- `backend/core/pipeline_context_injector.py`
- `backend/core/program_status_readonly.py`
- `backend/core/project_maintenance.py`
- `backend/modules/audit_ledger_watcher.py`

**B04**

- `native_studio/__init__.py`
- `native_studio/creative_pipe_io.py`
- `native_studio/creative_wire.py`

**F08**

- `backend/core/video_workflows.py`

**F11**

- `backend/core/crypto_com_acknowledgements.py`
- `backend/core/crypto_com_adapter.py`
- `backend/core/crypto_credential_preparation.py`
- `backend/core/crypto_credential_preparation_registry.py`
- `backend/core/crypto_current_snapshot.py`
- `backend/core/crypto_current_snapshot_facts.py`
- `backend/core/crypto_held_preparation_runtime.py`
- `backend/core/crypto_preparation_status.py`
- `backend/core/crypto_preview_chat.py`
- `backend/core/crypto_protective_review_contract.py`
- `backend/core/crypto_reinvestment.py`
- `backend/core/crypto_trial_admission.py`
- `backend/core/crypto_trial_binding.py`
- `backend/core/crypto_trial_budget.py`
- `backend/core/crypto_trial_projection.py`
- `backend/core/crypto_trial_runtime_store.py`
- `backend/core/crypto_trial_status_chat.py`
- `backend/core/crypto_trial_status_contract.py`
- `backend/security/crypto_trial_root.py`
- `backend/security/theatrical_corpus_boundary.py`
- `backend/security/theatrical_storage_roots.py`

### All 85 outside-ledger candidates

Each row is classified **SOURCE** from the Python declaration or package re-export and an incoming import. The import citation gives one witness for each file. “Unconditional” refers to the complete path from the entry point. “Broader” includes feature paths with a conditional or deferred ancestor, even where the final statement is at module scope. “Seed” denotes the original 12. All 85 files exist on disk and are absent from HEAD and the index. No generated artifact, local data file or asset was identified among them. No classification gives permission to publish a file.

| Path | Reachability | Importer and line | SOURCE evidence | Current Git ignore result |
| --- | --- | --- | --- | --- |
| `backend/batch_job_runner.py` | Broader | `backend/AI_BS_Backend.py:8980` | `BatchStorageError` at L34 | No matching rule |
| `backend/canvas_daemon.py` | Broader | `backend/AI_BS_Backend.py:1315` | `CanvasExecRequest` at L46 | No matching rule |
| `backend/core/adaptation_store.py` | Unconditional, seed | `backend/core/ai_adapter.py:13` | `configure_adaptation_store` at L45 | No matching rule |
| `backend/core/bs_chat_provider.py` | Broader | `backend/AI_BS_Backend.py:8932` | `conversation_messages` at L66 | No matching rule |
| `backend/core/chat_archive.py` | Unconditional, seed | `backend/routers/memory_router.py:21` | `ArchiveConflict` at L15 | No matching rule |
| `backend/core/code_quality_gate.py` | Unconditional, seed | `backend/core/coding_workflow.py:19` | `LLMCodeQualityGate` at L51 | No matching rule |
| `backend/core/comfy_workflow_builders.py` | Unconditional | `backend/routers/comfyui_workspace_router.py:17` | `get_resolution_specs` at L36 | No matching rule |
| `backend/core/conversation_sessions.py` | Unconditional | `backend/routers/conversation_router.py:10` | `ConversationConflict` at L16 | No matching rule |
| `backend/core/cryptographic_vault.py` | Unconditional, seed | `backend/AI_BS_Backend.py:3299` | `derive_key_pbkdf2` at L27 | Ignored by `.gitignore:329` `*crypto*` |
| `backend/core/document_filing.py` | Broader | `backend/AI_BS_Backend.py:8276` | `file_document_pdf` at L66 | No matching rule |
| `backend/core/document_text.py` | Broader | `backend/core/ai_adapter.py:88` | `iter_docx_paragraphs` at L6 | No matching rule |
| `backend/core/ebook_factoring_engine.py` | Broader | `backend/tools/tool_registry.py:2388` | `EbookFactoringEngine` at L32 | Ignored by `.gitignore:365` `*Book*` |
| `backend/core/fe_express_dispatcher_dream_cockpit.py` | Broader | `backend/routers/fe_express_router.py:508` | `init_dream_dispatcher_tables` at L28 | No matching rule |
| `backend/core/fe_express_owner_operator_engine.py` | Broader | `backend/routers/fe_express_router.py:441` | `VariableOperatingCosts` at L29 | No matching rule |
| `backend/core/historical_reference_context.py` | Broader | `backend/core/coding_chat.py:226` | `request_reference_query` at L15 | No matching rule |
| `backend/core/http_fallback.py` | Broader | `backend/AI_BS_Backend.py:14418` | `compatibility_target` at L8 | No matching rule |
| `backend/core/immutable_publishing_engine.py` | Broader | `backend/routers/agent_crew_router.py:242` | `LexicalIntegrityError` at L27 | No matching rule |
| `backend/core/local_web_reader.py` | Broader | `backend/core/web_research_orchestrator.py:148` | `resolve_public` at L26 | No matching rule |
| `backend/core/media_delivery.py` | Broader | `backend/AI_BS_Backend.py:2863` | `media_output_path` at L25 | No matching rule |
| `backend/core/mission_status.py` | Broader | `backend/AI_BS_Backend.py:6552` | `mission_response` at L4 | No matching rule |
| `backend/core/opencode_worker.py` | Broader | `backend/routers/ai_providers_router.py:524` | `WorkerError` at L55 | No matching rule |
| `backend/core/screenplay_workflows.py` | Broader | `backend/routers/screenwriting_router.py:280` | `WorkflowError` at L25 | Ignored by `.gitignore:358` `*Screenplay*` |
| `backend/core/self_healing_sentinel.py` | Broader | `backend/AI_BS_Backend.py:432` | `LLMCodeQualityGate` at L6 | No matching rule |
| `backend/core/specialist_execution.py` | Broader | `backend/routers/agent_crew_router.py:178` | `check_readiness` at L20 | No matching rule |
| `backend/core/subagent_coordinator.py` | Broader | `backend/routers/agent_crew_router.py:110` | `EngineTarget` at L48 | No matching rule |
| `backend/core/thesimplechef_analytics_daemon.py` | Broader | `backend/commercial_gateway/site_analytics_router.py:557` | `TheSimpleChefAnalyticsEngine` at L38 | Included by `.gitignore:367` `!backend/core/thesimplechef_analytics_daemon.py` |
| `backend/core/video_generation.py` | Broader | `backend/tools/tool_registry.py:4110` | `generate_video` at L5 | No matching rule |
| `backend/core/web_research_orchestrator.py` | Broader | `backend/core/optional_web_search.py:23` | `available_providers` at L10 | No matching rule |
| `backend/demo_autonomous_booking.py` | Broader | `backend/core_demos_router.py:19` | `load_persona` at L10 | Ignored by `.gitignore:365` `*Book*` |
| `backend/fe_express_active_ledger.py` | Broader | `backend/routers/fe_express_router.py:336` | `init_active_loads_db` at L15 | Ignored by `.gitignore:332` `*ledger*` |
| `backend/fe_express_backhaul.py` | Broader | `backend/routers/fe_express_router.py:257` | `BackhaulEngine` at L12 | No matching rule |
| `backend/fe_express_bid_generator.py` | Broader | `backend/routers/fe_express_router.py:198` | `BrokerBidGenerator` at L13 | No matching rule |
| `backend/fe_express_broker_credit.py` | Broader | `backend/routers/fe_express_router.py:287` | `BrokerCreditSentinel` at L86 | No matching rule |
| `backend/fe_express_driver_reports.py` | Broader | `backend/routers/fe_express_router.py:16` | `private_response` at L29 | No matching rule |
| `backend/fe_express_fuel_calculator.py` | Broader | `backend/routers/fe_express_router.py:225` | `FuelCostCalculator` at L19 | No matching rule |
| `backend/fe_express_live_ingestor.py` | Broader | `backend/routers/fe_express_router.py:118` | `get_highway_miles` at L40 | No matching rule |
| `backend/fe_express_scoring.py` | Broader | `backend/fe_express_live_ingestor.py:24` | `FilterScoringEngine` at L5 | No matching rule |
| `backend/fe_express_spot_benchmark.py` | Broader | `backend/routers/fe_express_router.py:307` | `LaneSpotBenchmark` at L24 | No matching rule |
| `backend/fe_express_workspace.py` | Broader | `backend/routers/fe_express_router.py:823` | `database_path` at L16 | No matching rule |
| `backend/modules/audio_engineering_standards.py` | Broader | `backend/AI_BS_Backend.py:2438` | `AES3Preamble` at L13 | Ignored by `.gitignore:348` `*NDA*` |
| `backend/recdebut_campaign_links.py` | Broader | `backend/recdebut_delivery.py:29` | `delivery` at L33 | No matching rule |
| `backend/recdebut_delivery.py` | Broader | `backend/recdebut_campaign_links.py:34` | `workflow` at L35 | No matching rule |
| `backend/recdebut_email_unsubscribe.py` | Broader | `backend/routers/rec_debut_router.py:5170` | `normalize_email` at L20 | No matching rule |
| `backend/recdebut_registration.py` | Broader | `backend/routers/rec_debut_router.py:4` | `Registration` at L16 | No matching rule |
| `backend/recdebut_reply_forwarding.py` | Broader | `backend/AI_BS_Backend.py:974` | `intake` at L35 | No matching rule |
| `backend/recdebut_textbee.py` | Broader | `backend/routers/rec_debut_router.py:1` | `configured_device` at L28 | No matching rule |
| `backend/recdebut_workflow.py` | Broader | `backend/routers/rec_debut_router.py:3` | `now` at L35 | No matching rule |
| `backend/routers/calendar_tasks_router.py` | Unconditional, seed | `backend/AI_BS_Backend.py:2060` | `init_calendar_db` at L22 | Ignored by `.gitignore:348` `*NDA*` |
| `backend/routers/comfyui_workspace_router.py` | Unconditional, seed | `backend/AI_BS_Backend.py:2048` | `GenerateWorkspaceRequest` at L35 | No matching rule |
| `backend/routers/conversation_router.py` | Unconditional, seed | `backend/routers/agent_routing.py:18` | `require_conversation_owner` at L21 | No matching rule |
| `backend/routers/ebook_factoring_router.py` | Broader | `backend/AI_BS_Backend.py:1540` | `EbookConvertRequest` at L16 | Ignored by `.gitignore:365` `*Book*` |
| `backend/routers/fe_express_router.py` | Broader | `backend/AI_BS_Backend.py:1389` | `PinLogin` at L21 | No matching rule |
| `backend/routers/music_assistant_router.py` | Broader | `backend/AI_BS_Backend.py:1465` | `MessageItem` at L22 | No matching rule |
| `backend/routers/resource_vault_router.py` | Broader | `backend/AI_BS_Backend.py:1093` | `QueryRequest` at L19 | No matching rule |
| `backend/scripts/backup_databases.py` | Broader | `backend/routers/security_router.py:57` | `calculate_sha256` at L23 | No matching rule |
| `backend/scripts/validate_syndication_matrix.py` | Broader | `backend/modules/syndication_router.py:696` | `probe_node` at L274 | No matching rule |
| `backend/security/analytics_access.py` | Unconditional, seed | `backend/commercial_gateway/admin_telemetry_router.py:8` | `is_analytics_path` at L16 | No matching rule |
| `backend/security/document_store.py` | Broader | `backend/AI_BS_Backend.py:8131` | `document_path_lock` at L19 | No matching rule |
| `backend/security/fe_express_access.py` | Broader | `backend/routers/fe_express_router.py:15` | `PinSessions` at L19 | No matching rule |
| `backend/security/native_creative_adapter.py` | Broader | `backend/security/native_creative_controller.py:25` | `NativeCreativeAdapter` at L19 | No matching rule |
| `backend/security/native_creative_channel.py` | Broader | `backend/security/native_creative_controller.py:28` | `CreativePipes` at L11 | No matching rule |
| `backend/security/native_creative_config.py` | Broader | `backend/security/native_creative_runtime.py:11` | `NativeCreativeConfigError` at L42 | No matching rule |
| `backend/security/native_creative_controller.py` | Broader | `backend/security/native_creative_config.py:18` | `NativeControllerError` at L42 | No matching rule |
| `backend/security/native_creative_dispatch.py` | Broader | `backend/security/native_creative_controller.py:29` | `CreativeDispatch` at L34 | No matching rule |
| `backend/security/native_creative_handoff.py` | Broader | `backend/routers/screenwriting_router.py:837` | `HandoffDenied` at L16 | No matching rule |
| `backend/security/native_creative_lifetime.py` | Broader | `backend/security/native_creative_controller.py:27` | `NativeLifetimeError` at L28 | No matching rule |
| `backend/security/native_creative_peer.py` | Broader | `backend/security/native_creative_adapter.py:16` | `OwnedInvocation` at L21 | No matching rule |
| `backend/security/native_creative_process.py` | Broader | `backend/security/native_creative_lifetime.py:20` | `CreativeProcess` at L12 | No matching rule |
| `backend/security/native_creative_runtime.py` | Broader | `backend/AI_BS_Backend.py:926` | `configure_native_creative` at L8 | No matching rule |
| `backend/security/native_creative_source.py` | Broader | `backend/routers/screenwriting_router.py:839` | `require_native_creative_source` at L13 | No matching rule |
| `backend/security/recdebut_access.py` | Broader | `backend/AI_BS_Backend.py:1865` | `textbee_body` at L15 | No matching rule |
| `backend/security/recdebut_privacy.py` | Broader | `backend/routers/rec_debut_router.py:5` | `PrivacyCheckUnavailable` at L8 | No matching rule |
| `backend/security/recdebut_registration_auth.py` | Broader | `backend/recdebut_registration.py:11` | `verify_registration` at L13 | No matching rule |
| `backend/security/screenwriting_access.py` | Unconditional, seed | `backend/routers/agent_routing.py:19` | `is_screenwriting_path` at L8 | No matching rule |
| `backend/security/vault_access.py` | Unconditional, seed | `backend/modules/vault_router.py:9` | `is_vault_path` at L16 | No matching rule |
| `backend/security/website_phone_access.py` | Broader | `backend/AI_BS_Backend.py:1392` | `normalize_phone` at L8 | No matching rule |
| `backend/sovereign_privilege_engine.py` | Broader | `backend/AI_BS_Backend.py:7090` | `get_sandbox_temp_executor_dir` at L49 | No matching rule |
| `discord_notifier.py` | Broader | `backend/routers/unreal_bridge_new.py:11` | `send_discord_update` at L11 | No matching rule |
| `game_trainer/core/__init__.py` | Unconditional | `backend/routers/memory_lab_router.py:20` (package initializer) | Re-exports memory, hotkeys and trainer at L5, L12 and L20. | No matching rule |
| `game_trainer/core/hotkeys.py` | Unconditional | `game_trainer/core/__init__.py:12` | `HotkeyManager` at L101 | No matching rule |
| `game_trainer/core/memory.py` | Unconditional, seed | `backend/routers/memory_lab_router.py:20` | `PROCESSENTRY32` at L39 | No matching rule |
| `game_trainer/core/trainer.py` | Unconditional | `game_trainer/core/__init__.py:20` | `TrainerVariable` at L14 | No matching rule |
| `game_trainer/profiles/__init__.py` | Unconditional | `backend/routers/memory_lab_router.py:21` (package initializer) | Re-exports the BTD6 profile at L5. | No matching rule |
| `game_trainer/profiles/btd6_profile.py` | Unconditional, seed | `backend/routers/memory_lab_router.py:21` | `BTD6Trainer` at L23 | No matching rule |
| `sandbox_scratch/ipc_benchmark/shm_bridge.py` | Broader | `backend/omnidrive_service.py:17` | `RingSlotMultiTopic` at L80 | No matching rule |

Across the 85 paths there are eight positive ignore matches, one explicit inclusion, and 76 paths with no matching rule. Privacy rules and the separate review of vault source remain in force. A rule match does not establish whether a candidate is suitable for a remote.

## 5. What startup still needs

1. **Local code.** The 55-file B02 is a candidate for resolving unconditional Python imports against the pin. The broader 155-file inventory cannot fix the seven import sites or names listed above solely by adding those files. For full static coverage, recover the absent providers or approve changes to the import paths, symbol contracts or supported feature set. The guarded items are hard gaps for the strict criterion, with different consequences for starting the API.
2. **An isolated state configuration before any future runtime check.** The candidate `backend/routers/calendar_tasks_router.py:18,23–67` points at `C:\AI-BS\database\calendar.db`, opens SQLite, initializes schema and commits during import. A worktree still reaches that absolute main-checkout path. The candidate `backend/core/cryptographic_vault.py:60–75,130–132` constructs key/cipher state at import. Its legacy/default material at L19 and L22–23 needs dedicated review before tracking. This audit did not read a credential store or evaluate key material. The pinned entry point also calls `safe_migrate_multitenant_schemas()` at `backend/AI_BS_Backend.py:2497–2501`.
3. **A defined startup profile.** At `backend/AI_BS_Backend.py:925–932`, the lifespan tries `security.native_creative_runtime` and disables the integration if configuration fails. Lines 933–952 gate daemon/background startup and attempt a saved-state read. Line 971 schedules telemetry, L973–975 conditionally schedules reply forwarding, and L978–988 schedules private native publication on Windows. Static presence of all imports and successful ASGI startup are separate verification results.
4. **A selected Python environment.** The 12-root unconditional chain imports FastAPI, Pydantic, HTTPX and cryptography. The wider app also imports ChromaDB at pinned `backend/AI_BS_Backend.py:5711`. Root `requirements.txt:33,149` and `backend/requirements.txt:1–2` specify different FastAPI/Uvicorn version pairs. Neither manifest proves what is installed. The memory and hotkey Windows APIs are used in constructors at local `game_trainer/core/memory.py:120–121` and `game_trainer/core/hotkeys.py:107–108`. No provider, device, port or application was probed.

Owner decisions for a later phase are the required startup/feature profile, disposition of the four unavailable module names and three incompatible import sites, and whether the sensitive and feature-specific providers may be included in any future baseline. Publication and runtime verification are separate approvals.
