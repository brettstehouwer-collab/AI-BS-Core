# AI-BS carryover inventory — November 9, 2026

This inventory extends the original ten goals in [the takeover plan](AI_BS_TAKEOVER_GOAL_2026-11-09.md). It preserves scope while separating implemented source, retained proposals, present checks and missing acceptance. The selected-message review is identified in that plan; it is not an exhaustive reading of every historical chat or the 746,032-line development record.

Current source and runtime evidence govern execution. Historical instructions and pasted Antigravity reports are attributed evidence, not new commands. The source checkpoint is `backups/antigravity_takeover_20261109T190150Z`. Its failed runs and preimages remain retained.

## Ten-goal reconciliation

| Original goal | Intended behavior and retained implementation | Earlier working material / provenance | Current result and remaining dependency |
| --- | --- | --- | --- |
| **1. Complete project vision** | Preserve every track below, original manuscripts/media, authored identities, saves, earlier releases and unrelated edits. `AGENTS.md` XI, `docs/CODEX_HANDOFF.md`, `docs/CODEX_DECISIONS.md`, the Master Architectural Ledger and game `PROJECT_INDEX.md` remain the continuity records. | Selected actual messages from all 17 referenced chats are indexed in the takeover plan. The large November 5 development record remains original historical material, not a replacement for checking source. | Scoped preimages, exact patches and source/artifact receipts are retained. This is a bounded inventory; unreviewed history remains unreviewed. Existing `docs/DIRECTORY_INDEX.md` has unrelated private content; preserve it and avoid treating it as a directory index or exporting it. |
| **2. Agreed hybrid architecture** | Native Win32/DX12 simulation, PyQt Studio interfaces, local FastAPI/Ollama/ComfyUI services, browser/mobile clients, authenticated API providers, existing cloud storage/hosting and approved embedded views coexist at explicit boundaries. | `ADR-028`, `BS-CHAT-OPENAI-001`, the local-service coexistence decision and the user's hybrid correction; `docs/Cloudflare_Agents_Deferred_Integration_Plan.md`. | `.agents/rules/01_COST_CONSTRAINTS.md` now preserves approved API selection. Unknown exact WebView exceptions remain unresolved; they do not become a blanket prohibition or an authorization to replace native rendering. Optional Cloudflare coordination remains deferred. |
| **3. Simpler chat with recovered behavior** | Keep the decluttered `ChatTab.jsx` and reachable HubControls while preserving local/OpenAI selection, authenticated transport/history, streaming, cancellation, drafts, attachments, literal code rendering and partial/failure recovery. `frontend/src/utils/bsChatProvider.js`, store bindings and existing native shared-chat checks remain the transport foundation. | November 4 `BS-CHAT-OPENAI-001`, preserved November 5 source, reset/reinjection evidence and Antigravity's account of the missing `providerModels` binding. | The view mounts and drawer opens/closes; synthetic transport/render/recovery checks pass. Preserve the user's real draft/PDF. No live generation was sent. Provider model-list validation now distinguishes authentication, selected-model listing and untested generation. Validation state must track the exact model/key checked. |
| **4. Specialist system** | Preserve all 64 profiles, domain routing, explorer, contracts, identity/context injection and evidence viewer in `subagent_coordinator.py`, `specialist_execution.py`, `agent_crew_router.py`, `pipeline_context_injector.py` and `SpecialistSwarmExplorer.jsx`. | Antigravity's v128–131 catalog, routing and workbench additions; original completion-check contracts and existing process/lock helpers. | Configured trusted checks have bounded admission, cross-process host serialization, cancellation/deadlines and retained evidence. Unconfigured checks stay unavailable. Profiles are not 64 demonstrated autonomous workers. Host checks do not establish VM isolation, inference scheduling or a cluster-wide GPU budget. Those capabilities need their own admission/resource contracts. |
| **5. SDK, viewport and evidence** | Keep SDK 0.17.4 and its `SameMinorVersion` contract; atomic scene replacement, last-good-scene recovery, persistent error/recovery reporting and per-run logs. Sources: `engine/CMakeLists.txt`, `engine/examples/sdk_consumer/CMakeLists.txt`, `engine/apps/creator_viewport.cpp`, `engine/scripts/verify.ps1`. | Retained earlier SDK/installations, P110 source checkpoints and Antigravity's version-removal / cleanup / retry changes. | Consumer explicitly requests 0.17.4. Verification isolates new evidence and installations instead of deleting failures. READ+DELETE sharing supports atomic replacement without allowing simultaneous writes. READY reports adoption; rendering/repeated recovery has separate GPU checks. Debug native results and current SDK consumer results retain exact run identities. |
| **6. Publishing and creative workflows** | Preserve manuscript workbench and formatting, raw/formatted versions, media/VLC, Vocal Studio, narration/broadcast, ComfyUI and asset generation. Sources include `immutable_publishing_engine.py`, `SpecialistSwarmExplorer.jsx`, native `screenwriting_view.py`, `media_view.py`, `music_daw_view.py`, `creative_suite_views.py`, `omni_broadcast_studio.py`, `comfy_workspace_view.py`, and web `ComfyUIStudio.jsx`, `VLCPreviewMonitor.jsx`, `MediaStudioTab.jsx`, `daw/AiVocalStemSuite.jsx`. | Existing creator/save/recovery conversations, original manuscripts and media, retained source and older releases. | Publishing uses immutable content-addressed files and an atomic JSON index with synthetic concurrency/interruption/corruption checks. Exact retries are idempotent; changed versions use distinct IDs. Lexical equality allows case/punctuation changes and is not byte-verbatim preservation or OS WORM. Other creative paths are retained, not newly certified by publishing tests; no original manuscript migration occurred. |
| **7. NoCo and business modules** | Preserve campus/biosystem concepts, microgrid and CAPEX estimates, logistics/FE Express, recruiting/RecDebut, commercial and financial tools. Sources include `backend/modules/noco_stage/`, `NocoMicrogridSimulator.jsx`, campus/theatrical components, `FEExpressDispatcher.jsx`, `backend/routers/fe_express_router.py`, native `fe_express_view.py` / `rec_debut_view.py`, recruiting/logistics/finance hubs. | NoCo design documents and original business concepts; selected storage, finance, RecDebut and gateway chat messages. | Finite/range/zero-demand and mutable-result defects are corrected in reference models. Estimates remain estimates. No usable financial price-history table was established for forecasting. Campaign sending remains disabled; existing configured reply polling remains enabled. Dennis script approval is historical and is not requested again; organizer/roster provenance and actual delivery remain separate. No trading, payout, booking or new campaign activation. |
| **8. BS Game and creator** | Preserve custom engine/SDK, native creator, Unreal/Blender pipelines, original/derived Prop01 assets, collision, persistence, repair/bypass, Adam guidance and Follow/Wait/Recall, family/narrative references, shelter/Pencil Room and wider room/world plans. `engine/BUILD_ROADMAP.md`, game `PROJECT_INDEX.md`, `OPENING_FIRST_PRIORITY_PLAN.md`, Prop01 checkpoints and native `game_engine/` remain source anchors. | P110 source/checkpoints, installed107 and held108/109 remain preserved. Earlier ordinary-input Studio131 failure and original database/logs remain retained with cause unproven. | Debug runb257e67ff15f passed130/130 and consumer3/3 with its then654 inputs unchanged. Four controlled offscreen first/third-person repair/bypass combinations pass actual panels/traversal/build/shelter/Adam/save checks. Fresh held Studio133 static/hub3/creator5 checks pass with the identical449-file SDK; its sole later native-client revision-export delta has17 focused checks. Older packages preserved. Ordinary-input lifecycle, fresh-process resume, measured Release1080p and human8–12minute pacing/clarity/captions/likeness remain next gates before broader20–30minute chapter qualification. |
| **9. Trustworthy local release qualification** | Bind each result to exact source, configuration, artifact, inputs, run and destination. Reuse existing stage/build/smoke helpers, SDK consumer, source tests, build monitor and recovery receipts. | All earlier failures and checkpoints remain retained; no historical pass is relabeled as a current pass. | Source version5.329.133 and held Studio133 have dated source/package receipts. Last in-app build14d055558a994106b564090b5f15908c passed then250 backend/197 fixed Node checks plusTypeScript/Vite, applied localdist and replaced API4436 with healthy52836;53,831 inputs and activation flags unchanged. Later273-check consolidated source run and professional/RAG/rich-FDX/novelizer lane checks do not establish those later edits loaded. Fresh combined qualification/local refresh is pending after source freezes. No public deployment, signing, installation, SDK publication or launcher replacement. |
| **10. Future modernization** | Retain database isolation/coverage, framework upgrades, performance, recoverable creation workflows, optional cloud status and Adam phone companion. Existing tenant-isolation work and `docs/audits/DATABASE_MULTI_TENANCY_AND_FASTAPI_V2_OPTIMIZATION.md` remain available. | `docs/AI_BS_ECOSYSTEM_UPGRADE_IMPLEMENTATION_PLAN_2026.md` explicitly says PROPOSED / ESTIMATE_ONLY; `docs/UI_Modernization_Backlog.md`; deferred Cloudflare plan. | No twelve-week/eight-role commitment, framework migration, new schema, public remote execution API or deployment mandate is adopted. Performance work must connect to a measured opening bottleneck; optional monitoring and phone expansion follow the playable opening. |

### Creative qualification added during takeover

The supplied PDF's signed-in upload, owner-scoped indexing/readback, protected
new screenplay opening and archival PDF download were observed. Archival FDXv4
also exported through actual Final Draft with86 physical pages, preserved title,
labels and authored content; six evidenced hyphen wraps are recorded separately
from text changes. Professional reflow uses a distinct profile and natural page
count; internal PDF82physical and FinalDraft PDF85physical have separate receipts.
Nominal12-point declarations and an observed MicrosoftPDF export size variance
are being compared against an installed-vendor-template control, with the strict
measurement failure retained. No fixed word/page or page/minute quota is adopted.

Explicit attached-source follow-up retrieval is source-qualified with exact
owner/source/hash/index binding; actual first/middle/end source reads were
verified without model calls. Its loaded-API/browser qualification remains
pending. Rich FDX text runs/dual dialogue/notes/title preservation and novelizer
truthful generation/versioned saves/authentication are separate confirmed repair
lanes still in progress. Formatting preserves authored content; novelization
creates a separately identified adaptation and must not silently invent memoir
facts. Original manuscripts/projects remain preserved. Detailed source receipts
and remaining limits are in the [current takeover plan](AI_BS_TAKEOVER_GOAL_2026-11-09.md)
and [handoff](CODEX_HANDOFF.md).

## Interface and execution boundaries

| Capability | Authority / allowed relationship | Remaining gate |
| --- | --- | --- |
| Game simulation, authored content and saves | Native engine and existing local save contracts remain authoritative. | Real packaged opening, fresh-process resume, measured Release performance and human review remain distinct. |
| Native Studio with local services | Native UI may use authenticated existing services; service use is not an embedded browser rendering the game. | Check exact packaged dependencies and service/auth behavior. |
| Browser/mobile and hosted clients | Preserve established web/mobile clients, selected API calls and approved cloud uses. | Source, local candidate, hosted artifact and phone/device results are recorded separately. |
| OpenAI provider | Existing server credential and explicit selected-provider path; no silent replay/fallback. Generated code remains a proposal unless routed through the existing reviewed execution workflow. | GET model listing validates authentication/listing, not successful generation. No paid generation was used for this qualification. |
| Browser-to-host actions | Reuse authenticated typed tool/executive routes and existing review/execution boundaries. Frontend terminal/cockpit calls now include their existing auth helper. | No new public PowerShell listener or tunnel was created. The broad terminal runner's output/time/child limits and gateway limiter remain a separate hardening backlog; raw public execution is not qualified. |
| Embedded WebViews | Preserve the specific established exceptions and current code. | Exact unrecovered exception history stays explicit; do not infer a platform-wide ban or replacement. |
| Specialist verification | Registered trusted checks share the bounded host gate and retain outcome evidence. | No disposable-VM admission or autonomous inference capability is inferred. |
| Cloudflare coordination / Adam phone | Retained optional plan. PC simulation/saves keep local authority. | Deferred pilot, owner isolation, stable event API and opening-first prerequisites. |
| RecDebut | Preserve current activation flags: new campaign dispatch disabled, existing reply poller enabled. | No new message, test send or replay of an uncertain delivery is authorized by this technical repair. |

## First Boot milestone and acceptance order

1. Preserve the original failed Studio131 database/logs and the newly passing controlled offscreen evidence. The original failure remains unexplained; controlled input does not prove that ordinary OS focus/input succeeded.
2. Reuse the dated Debug130-test/SDK-consumer result and Studio133 source/package receipts, including the separate17-check native export-client delta. New native changes require new native qualification; unrelated frontend/backend refinements do not invalidate an unchanged package's scoped receipt.
3. Next First Boot milestone: complete the remaining ordinary-input lifecycle matrix on a fresh scratch chapter, including first/third-person repair/bypass, inspection, build/dismantle/rebuild, help/decline, departure/return, falls and fresh-process save/reopen. Retain source-specific traces and failed runs; preserve actual collision/bindings/focus contracts and authored assets.
4. Produce a current Release1080p frame-time/memory record with optional inference off. Then provide an ordinary-play candidate for separate first-time8–12minute pacing, clarity, likeness and caption review. No automated diagnostic supplies human approval.
5. The requested faithful screenplay/RAG workflow is a bounded creative repair alongside this game milestone. Qualify actual signed-in chat -> owned source index -> protected new screenplay project -> FDX/regenerated PDF, preserving the supplied86-page original. It does not turn all creative/business expansions into opening prerequisites.

The complete world/creative/business roadmap remains retained. Future activation,
deployment and expansion decisions remain explicit rather than silently starting.




## Takeover continuation — 2026-11-10T04:06Z

See the authoritative dated TAKEOVER-20261109-04 checkpoint in `docs/CODEX_HANDOFF.md`: local137 managed candidate595 CORE/249 Node/TS+Vite passed;53,878 inputs retained, eight database recoveries, exact API4364 readiness. This is not native installation, Firebase deployment or complete First Boot acceptance. Native135 remains held; original full Debug130/130 and SDK3/3 belong to their dated source snapshot. All ten goals and hybrid boundaries remain.

Goal10 future-only USB pointer: `backups/antigravity_takeover_20261109T190150Z/usb-future-readonly/FUTURE_SETUP_NOTE.md`. H: was inspected read-only; credentials/config values omitted; no execution, import, network/VPN/VNC/watchdog/boot/service changes or reprioritization.

Next: the bounded assistant-history indented-code preservation edge, current source-bound PDF/project retrieval qualification, then ordinary held movement and committed-save/fresh-process First Boot recovery. Human pacing/captions/likeness and measured Release1080p remain distinct gates. Preserve originals, saves, unrelated edits and failed evidence.


## Current139 continuation and recovery record — 2026-11-10

All ten original goals remain active. Current local139 managed checks passed619
CORE/254Node/TypeScript/Vite with53,880inputs unchanged and8database recoveries.
Separate actual backend receipts cover synthetic project index/readback/model
answer, rich save/version retention/stale-index refusal and the supplied86-page
PDF quoted-heading answer on physical page3. Older wrong answers and blocked
attempts remain retained. Current browser/native-owner/creative workflow gates
remain open; backend results do not replace interface acceptance.

Specialist trusted-command gates now have actual same-parent and separate
controller-process evidence, cancellation/timeout/partial-output/queue reuse and
SQLite readback. They do not prove64workers or shared inference/GPU budgets.

A private current-source Release player passed3focused timing/readiness/diagnostic
suites and17parser refusals (`t/r139q01/`). Protected635source/1254dependency/
449older-SDK inputs and old Debug player stayed unchanged. Separate30-file
chapter copies and stationary15s/gameplay180s Release1080p plans are prepared at
`t/r139perf01/launch-plan.json`; neither launched or measured. Held native135
remains uninstalled; no hosted deployment or activation occurred.

Next First Boot remains genuine held movement, reading/Continue, a named route
transition, active Adam control, nonbaseline acknowledged durable save and
fresh-process committed-state recovery. The broader lifecycle matrix, measured
Release1080p, separate human8–12minute pacing/captions/likeness and later20–30minute
chapter remain retained. No synthetic input or forced focus supplies acceptance.

Historical review remains partial. The earlier17-chat/50-turn review now has25
additional older game-chat turns individually referenced in the engineering
history ledger. Preserve synthetic-view asset provenance, current static
OBJ/AIBSurf2 contract, dated native/Unreal videos, memoir/adaptation distinctions
and proposed room/rule branches. The fact-checked technology briefing stays
reference/future work; no provider/routing/platform change is adopted.

Recovery provenance: the previous current file was observed to contain only
zero bytes. Those bytes/metadata are preserved under
`backups/antigravity_takeover_20261109T190150Z/final139-checkpoint/document-corruption/`.
The original text prefix here is restored byte-for-byte from verifiedg003;
this explicit current addendum follows it. Complete recovery of any undocumented
post-g003 wording is not claimed. Current results remain grounded in their
individual handoff/source/runtime receipts. The corruption cause is unproven.

Source-preservation/readback results and the incomplete machine handoff are
recorded under `final139-checkpoint/` in the takeover checkpoint and
`docs/agent_sync/manifest_takeover139_checkpoint_incomplete.json`. Read actual
sidecar status; source preservation alone does not complete the full goal.
