# AI-BS Forward Implementation Plan

**Prepared:** 2026-10-23  
**Purpose:** Turn the read-only system review into an ordered, reviewable path for securing, unifying, and then trimming AI-BS.  
**Status:** Source and candidate builds are at v5.329.4. Writer preservation repairs and selected runtime fixes are activated in source and isolated checks pass. Backend 8080 remains offline; Ollama recovery is in progress after the user-confirmed update. Firebase publication and installed native replacement remain held for live verification and artifact review. Historical live results below do not establish current service health.

## Implementation progress — 2026-10-23

### Latest checkpoint — v5.329.4, 2026-10-23 (08:40 Eastern Daylight Time)

- **Writer preservation is now integrated in source:** create-only adaptation jobs use the same store mutex as editor revisions, retain source/chunk/state/predecessor histories, fence stale workers, and preserve verified live process owners across another API worker startup. Real FDX regeneration, word/page metadata, and scoped Git checkpoints are restored. All 46 active-source adaptation fixtures pass. The native writer client/view passes 58 isolated checks; 18 additional checks pair the actual authenticated router, native client, parser, PDF/FDX, Git, and ownership worker using synthetic projects and mocked inference. This supersedes the v5.329.3 staged/feature-omission note below.
- **Preservation evidence:** paired activation save point `backups/writer_contract_activation_20261023T121944Z`; `AI-BS_Writer_Contract_Activation_2026-10-23.json` verifies all 866 prior screenplay files and 20 downloaded Drive originals unchanged. The UTF-8 import path also preserves exact bytes through `write_bytes`. No real manuscript adaptation was run.
- **Other source repairs:** five frontend components across four mirrors are integrated with 30 isolated checks: Definitions modal scope, NOCO selected channel, FE Express response handling, Crypto Accounting URLs, and disabled unverified public checkout. Backend fleet lifecycle now requires explicit opt-in; six actual-lifespan fixtures start/stop no real processes. These are source checks, not live user-flow certification.
- **Version/save points:** `version.txt` and active release metadata align at 5.329.4. Version save point: `backups/release_versioning/20261023T122505681Z_integrated_writer_preservation_and_runtime_fixes_e9f7ac3c`. This review checkpoint copies only named source/configuration files and metadata: `C:\AI-BS\backups\review_checkpoint_5_329_4_20261023T124033Z`; no environment files, secret stores, manuscripts, or model weights are included.
- **Candidate builds, no release:** web production build passed with 7,308 transformed modules into `backups/firebase_release_5_329_4_20261023/artifact`; Hosting manifest records zero inspected credential-pattern findings, no public source maps, and internal-document exclusions. A bounded scan is not exhaustive privacy proof. Native PyInstaller candidate built at `backups/native_candidate_5_329_4_20261023/dist/AI_BS_Studio/AI_BS_Studio.exe`; writer packaging pins pypdf 6.14.2 and supplies Windows version metadata. Native artifact audit and signed-in/live workflows remain pending. Neither Firebase nor installed native binaries were released.
- **Open release gates:** TypeScript configuration now tracks the active production graph plus separate workers/worklet, with strictness retained; checks still fail with 9,979 production, 3 worker, and 4 worklet diagnostics. Backend 8080 remains offline after the prior start request was blocked by automatic approval review (`blocked by policy`); no bypass was attempted. Gateway 8000 and local Vite 5173 were previously healthy, not refreshed by this documentation task. The user-confirmed Ollama update reset runtime visibility; recovery is in progress and model inference/BS-Chat must be reverified before release.
- **Next:** finish model/store visibility recovery, restore only the intended backend through the allowed service path, verify authorization/retention and BS-Chat live, audit the native candidate, then assess Firebase/native release against the user's instruction to release only when safe. Publishing permission is already recorded; incomplete safety evidence remains the reason to hold publication.

### Earlier checkpoints — historical evidence

The entries below retain their original chronology. Their current/staged/runtime statements describe those earlier checkpoints and are superseded by the v5.329.4 status above.

- **Review pause requested; source v5.329.3:** completed active BS-Chat memory-command and fallback response repairs, admin security URL fixes, dormant storyboard backend scoping, and removal of automatic adaptation resumption at backend startup. Nineteen isolated actual-handler/response checks pass. PayPal create/capture routes now return 503 until real provider verification exists; six isolated route checks confirm no order/pass issuance or existing-record changes. This is containment, not a completed payment integration. Both repairs are source-only where backend restart is required.
- **Safe pause checkpoint:** `C:\AI-BS\backups\review_pause_20261023T120153Z` contains exact current source copies and SHA-256 hashes; no environment credentials or manuscript contents were copied into this release checkpoint. Version metadata aligns at 5.329.3. Vite build passed into `backups/firebase_release_5_329_3_20261023/verified_artifact`; its manifest has no inspected credential-pattern findings and excludes maps/internal documents. The sibling `artifact` folder is an earlier pre-version build and must not be deployed.
- **Staged for review, not activated:** native screenplay client/view (44 isolated checks), create-only adaptation store/worker/router (28 isolated checks), and separate frontend runtime followups (30 isolated checks across20stagedmirrorfiles). Native staging requires coordinated backend capability, packaged pypdf, and live/native verification. Adaptation staging preserves manuscripts but still omits automatic Git/FDX/page-metadata finalization from the previous implementation; restore that functionality before activation. Real manuscripts and installed native executable remain untouched by these candidates.
- **Publication held:** backend 8080 remains offline after the previously rejected start request, and signed-in workflows remain unverified; other confirmed frontend runtime defects are recorded in the TypeScript triage report. No Firebase deployment, native replacement, DNS change, payment, or outgoing message was performed. Resume from this checkpoint with staged review/integration and remaining release gates, not a new inventory scan.

- **v5.329.2 native release safety:** opening/closing the source native client no longer starts all ecosystem daemons or runs process cleanup by default; each requires an explicit runtime option. Frozen builds resolve their bundled version and avoid live-source sys.path overrides. Ten isolated policy/version checks passed, with zero daemon starts, process terminations, or GUI launches. Exact backups and hashes: `backups/native_release_safety_20261023`; metadata save point: `backups/release_versioning/20261023T114905651Z_native_release_safety_d92d175d`. Localhost 5173 serves the updated 5.329.2 version module and repaired document/screenwriting modules. This proves HTTP module delivery only.
- **Release instruction:** publish only when safe. No Firebase release or installed native binary replacement has occurred. The prior prepared web artifact remains 5.329.1; current source is 5.329.2. Firebase live channel/version was captured read-only for rollback metadata. Native packaging target is PyQt6 `native_studio/AI_BS_Studio.spec`, separate from Electron. Native direct screenplay Save, duplicate New Project, and placeholder adaptation output bypass the backend revision protocol; repair these before rebuilding/replacing the installed native app. Backend 8080 is still offline; live backend/auth and signed-in workflow checks remain pending. Global TypeScript diagnostics also remain unresolved.

- **Current checkpoint (v5.329.1, 2026-10-23):** backend port 8080 is offline after its supervisor exhausted the accumulated restart budget. Automatic approval review rejected the subsequent backend-start request before execution; no reason beyond `blocked by policy` was provided. Earlier successful live results below are historical evidence, not a current backend-health claim. A manual start of only `ai_bs_backend` is needed before the prepared live vault and document-retention checks can run.
- Source version authority is now `version.txt`; three package manifests and root lock records, seven generated version modules, dashboard public metadata, Sidebar mirrors, and Broadcast Studio badge align at 5.329.1. `scripts/release-version.cjs` supplies read-only checks and checkpointed sync/bump commands. Existing binaries and installer feeds keep their actual versions. Exact source and metadata backups are under `backups/release_versioning_20261023` and `backups/release_versioning`.
- Drive intake discovery downloaded 20 files from 14 Drive sources, including DOCX and PDF copies of six native Docs, into `shared_cloud_drive/Documents/Drive_Intake/2026-10-23/Originals`. The inventory covers 897 candidate records, not 897 confirmed screenplays. All 20 downloaded originals retain their verified hashes. No manuscript adaptation or automatic conversion was performed.
- Document-retention backend and paired Documents/Shared Drive UI are installed in source. Originals and Previous_Versions reject mutations through these APIs; permanent Drive deletion is disabled; DOCX is cataloged as binary; PDF text extraction and explicitly requested editable copies use unique Working_Copies paths. Eighteen active-source isolated backend checks and ten staged/byte-matched UI behavior checks passed. Save point: `backups/drive_retention_activation_20261023T114045Z`. Live verification remains pending backend availability; this policy does not cover arbitrary terminal/file tools.
- Removed 45 obsolete frontend Authorization headers that suppressed the authenticated fetch wrapper; replaced four credential-shaped examples. All 44 component files retain four-mirror parity; 124 mocked checks passed. Save point: `backups/frontend_legacy_auth_20261023113849`. No real execution or messages were sent by those fixtures.
- Release privacy settings exclude five internal-looking reference documents from Firebase Hosting and disable public source maps. Original files remain on disk. Save point: `backups/release_privacy_20261023`. Two existing syntax defects (a JSX tag typo and malformed hybrid-chat URL expression) were repaired across nine source copies with exact backups in `backups/static_syntax_20261023`.
- Dashboard production build passed (7,308 transformed modules) into `backups/firebase_release_5_329_1_20261023/final_artifact`, preserving the existing dist. The Hosting manifest records hashes, sizes, exclusions, and a bounded credential scan with no findings. Global TypeScript validation remains failing with extensive type/import diagnostics; its log is `AI-BS_TypeScript_Preflight_2026-10-23.log`. A production build is not evidence that every advertised action works. Firebase publication is authorized but has NOT occurred; live backend/auth checks and authenticated user workflow verification remain release gates.

- Both Ollama IPv4 endpoints now expose 30 models. Direct Stehouwer inference and the FastAPI BS-Chat streaming route returned generated responses. See `AI-BS_Recovery_Progress_2026-10-23.md`.
- Writing projects backed up to `C:\AI-BS\backups\screenwriting_recovery_20261023_035551\projects.zip`, with a SHA-256 manifest. All 866 files, including hidden project histories, verified against the archive. Original project files remained unchanged after the code repairs.
- Backend source now requires explicit project names for saves, validates project paths, rejects duplicate creation, uses atomic file replacement, and keeps explicit reads independent of the process-global current project.
- Frontend source guards autosave while switching/loading projects, ignores superseded load results, and loads newly created projects by their returned name. Three mirrors that matched the original were synchronized.
- Isolated route checks passed using temporary sample projects; Python and JSX syntax checks passed. The live backend process is not running with a reload flag, so these backend repairs require a service restart before they become active. Live manuscript requests were not used for verification.
- Backend restarted and the repaired save schema is active. Live verification passed for explicit project saves, duplicate-name rejection, read-back, and invalid/missing project rejection. Two synthetic projects were archived under `C:\AI-BS\backups\save_verification_8d199df727`; original selection restored and all 866 pre-existing project files verified unchanged. Evidence: `AI-BS_Live_Save_Verification_2026-10-23.json`.
- Recoverable project archival is active: both the archive route and legacy delete URL move the complete folder to `C:\AI-BS\screenplay_archive\<archive_id>\project`; restore rejects name conflicts. The editor includes an Archived projects panel and Restore controls. Active adaptations and Default Project are protected. Existing route authorization policy is unchanged and remains scheduled for the permissions workstream.
- Live archive/restore checks passed using synthetic files; all 866 pre-existing project files remained unchanged and original selection was restored. Test artifacts were preserved under `C:\AI-BS\backups\archive_verification_75df212a77`. Evidence: `AI-BS_Live_Archive_Verification_2026-10-23.json`. Frontend JSX checks and four-mirror byte parity passed; browser interaction was not exercised.
- General Documents text persistence is active and live-verified: `/api/tree`, `/api/read`, and `/api/save` now use a real recursive document catalog, accept both path spellings, enforce directory boundaries, reject binary text overwrites, and save atomically. New documents and Save As use `C:\AI-BS\shared_cloud_drive\Documents`; existing legacy E: Documents paths remain accessible only if that folder exists. Originals were not moved.
- The Documents frontend uses unique new filenames, create-only Save As, saved-content tracking to prevent save loops, and stale-response guards. Word imports save an editable Markdown copy rather than replacing a DOCX with plain text. Backend fixture checks, extracted frontend save-handler checks, JSX syntax, and live API checks passed. All 2,105 pre-existing shared-drive files remained unchanged. Evidence: `AI-BS_Documents_Verification_2026-10-23.json`. No browser click-through was performed.
- PDF import now uploads originals into unique shared-drive folders and reopens them through the real binary preview route. Conversion uses the declared PyPDF2 dependency, extracts text into unique create-only files, and rejects invalid, encrypted, missing, outside-root, and textless PDFs without fabricated content. The backend was restarted; live upload, backend/gateway preview, conversion, catalog, and error checks passed. All 2,105 pre-existing shared-drive files remained unchanged. Evidence: `AI-BS_PDF_Verification_2026-10-23.json`. Frontend handler checks and four-mirror parity passed; no browser click-through. Disposable samples are preserved in `C:\AI-BS\backups\pdf_verification_fca5c92a3cbc`.
- Documents Sign & File now saves a real PDF to `shared_cloud_drive/Documents/Filed`, includes an optional drawn signature mark, and downloads the stored PDF instead of JSON mislabeled as PDF. Unique atomic publication preserves prior documents; errors distinguish filing failure from download failure. The signature canvas now handles mouse/touch/pen through pointer events. Certificate signing and signer identity verification are explicitly not implemented. Isolated module/frontend checks and live backend/gateway checks passed; rendered first and signature pages reviewed. All 2,105 pre-existing shared-drive files unchanged. Evidence: `AI-BS_Filing_Verification_2026-10-23.json`; synthetic artifacts: `C:\AI-BS\backups\filing_verification_be1d46c98125`.
- Document authorization is now active for the tree/read/save/convert aliases, `/api/documents/*`, and the shared-drive router. Existing administrator credentials are required even on loopback. Authenticated administrators can obtain a one-hour read link bound to one canonical path and preview/download action; links are invalidated by backend restart. Documents preview and Admin Shared Drive preview/audio/download clients use these links. A sibling-directory prefix escape in shared-drive path resolution was also fixed. Live anonymous and invalid-key probes were denied on 13 routes via 8080 and 8000; admin save/read/upload/convert/file/media workflows passed. All 2,105 existing files unchanged. Evidence: `AI-BS_Document_Authorization_Verification_2026-10-23.json`. Firebase browser sign-in was not exercised live; the existing fetch interceptor was tested with a simulated admin identity. Public hosted frontend release is pending approval; local Vite module transforms passed.
- Screenplay PDF/FDX export no longer depends on process-global project selection. Requests require an explicit project, read existing source and metadata without initializing Git or creating files, and reject missing/invalid targets. Editor server-export controls save the captured draft to its explicit project and download through authenticated fetch rather than window.open. Isolated handler/API checks and live PDF/FDX checks on two synthetic projects via both 8080 and 8000 passed; all 866 original project files unchanged. Evidence: `AI-BS_Screenplay_Export_Verification_2026-10-23.json`. Synthetic projects/exports are in `C:\AI-BS\backups\export_verification_43d716034e`.
- Visual review found duplicated scenes caused by repeated FountainParser.parse calls appending to existing elements. Parsing now replaces its prior result. Repeated-parse checks and live PDF/FDX exports confirm each marker occurs exactly once; all 866 original files remain unchanged. The corrected rendered screenplay page was reviewed.
- Screenplay/adaptation authorization is active in the backend middleware and router dependency. Anonymous and invalid credentials were rejected across 12 route cases through both 8080 and 8000; admin and bearer access passed. Project audio now uses file-scoped expiring media tickets, with byte-range playback verified and wrong-project/tampered/mutation requests rejected. All 866 existing screenplay files are unchanged. Evidence: `AI-BS_Screenwriting_Authorization_Verification_2026-10-23.json`.
- Local UI progress streams now use authenticated fetch; standalone writer waits for the existing Firebase administrator session and selects the local or hosted API appropriately. Four component mirrors are synchronized. Fixed three location-dependent FDX utility imports discovered by Vite verification. Syntax, simulated Firebase token attachment, SSE parsing, export UI regression and local module transforms pass. Interactive Firebase sign-in/browser playback and hosted frontend release remain unverified/pending.
- Live progress verification found an existing Go gateway defect: its CORS response wrapper hides ResponseController flushing. Direct FastAPI streams work; production port 8000 buffers them. Added Unwrap in `go-core/pkg/telemetry/security.go`; focused regression went from failing to passing. Built replacement at `C:\AI-BS\backups\screenwriting_auth_20261023_053335\aibs_engine_stream_fix.exe`, and verified actual proxy streaming on temporary loopback port 18000, then stopped that verifier. At that checkpoint the production executable was left unchanged because its StartAll startup launches managed daemons and reported stale process states; the later verified handoff below resolves that rollout blocker. No additional supervisor services were launched by verification.
- Gateway streaming rollout completed after a verified process handoff. `C:\AI-BS\go-core\aibs_engine.exe` now runs the flush repair and handoff-aware supervisor. Eight existing daemons were adopted with unchanged PIDs; all 21 processes in their trees retained their creation times; three stopped entries stayed stopped. Other service listeners were unchanged. Actual SSE, authorization, audio range requests, and manuscript preservation now pass on production ports 8080 and 8000. Evidence: `AI-BS_Gateway_Handoff_Verification_2026-10-23.json` and refreshed `AI-BS_Screenwriting_Authorization_Verification_2026-10-23.json`.
- Supervisor status now reflects running, starting, stopping, backoff, stopped, or failed state; terminal processes are no longer reported running because a stale cancellation handle exists. Handoff validates executable, process creation time, and the registered command before starting any monitor, and missing/invalid manifests fail closed. Gateway port reservation precedes ordinary daemon startup, preventing a second active engine from spawning duplicate daemons. Normal launch/stop, adopted-process exit, immediate stop, bad identity, no-op validation, and failed-launch regression checks passed; affected Go packages pass vet. Previous source and binary are preserved in `C:\AI-BS\backups\gateway_handoff_20261023`.
- Handoff is a point-in-time operation, not a persistent reboot configuration. Regenerate and validate the manifest for later gateway-only replacements; do not reuse stale PIDs or blindly restore the older executable, whose default startup launches all configured automatic daemons. `Prepare-GatewayHandoff.ps1` in the work folder records the checked selection procedure.
- BS-Chat generation also passed through the repaired production gateway using the explicitly requested `stehouwer_llm:latest`: 19 response chunks, completed in 18.641 seconds, with a generated greeting. This is a live API check, not a browser/mobile UI click-through. Evidence: `AI-BS_Gateway_Chat_Verification_2026-10-23.json`.
- RecDebut privacy repair is active: the missing Desktop contact export reference was replaced with the existing `C:\AI-BS\saved_data\MyPhoneContacts.csv`. Exclusions cover 264 normalized phone identities and 16 emails. Forwarding now requires one exact roster match, independently rechecks exclusions at the final forwarding helper, and blocks if the contact export cannot be read. Ambiguous matches and unmatched phone senders cannot fall back to email or an old desktop roster. Webhook/poll message IDs share deduplication, and unsuccessful primary inserts cannot trigger forwarding.
- RecDebut administration is now protected by router dependencies and middleware covering legacy aliases. Public intake/tracking exceptions remain explicit; inbound TextBee webhooks require HMAC verification using the existing subscription secret. The provider subscription was not modified. Fixture checks cover 93 declared route aliases, all excluded identities, missing-contact failures, and forwarding bypass attempts with mocked transports. Live checks passed on ports 8080/8000 and the existing public webhook: unsigned/tampered payloads rejected, correctly signed empty payloads safely ignored. No verification messages were sent to Dennis. Evidence: `AI-BS_RecDebut_Privacy_Fixture_Verification_2026-10-23.json` and `AI-BS_RecDebut_Live_Privacy_Verification_2026-10-23.json`.
- Both checked RecDebut databases still contain 7,350 athletes, zero stored athlete replies, and zero recorded `sms_reply` forwarding attempts. This is not a complete historical provider-delivery audit. Sender-based exclusion cannot determine whether a permitted athlete's message is personal. Original source, environment, and SQLite snapshots are preserved under `C:\AI-BS\backups\recdebut_privacy_20261023`. Backend restarted under the existing supervisor; dashboard, gateway, backend, and both Stehouwer model APIs respond successfully.
- RecDebut frontend compatibility repaired locally: the standalone portal now waits behind the existing Firebase session gate. Its shared live-data loader rejects HTTP/authentication and malformed-response failures, displays a retryable error, and preserves genuine empty lists and zero counts. Removed hard-coded summary counts, fabricated excluded-coach rows, bundled fallback athletes, fallback coach contacts, and reads/writes of unscoped roster/statistics caches from the active desktop/mobile client implementations. Existing browser cache records were not deleted. Older refresh responses cannot replace a newer load. Both active portal entry components and their matching mirrors were synchronized; originals are backed up under `C:\AI-BS\backups\recdebut_frontend_20261023`.
- Frontend fixture checks passed for session gating, Firebase header attachment, external-origin exclusion, failed HTTP/network responses, malformed payloads, empty rosters, real zero counts, JSX parsing, and mirror parity. Read-only live loading through 8080 and 8000 returned 7,350 athletes and 18 campaigns; Vite successfully served all five affected entry/modules. No outgoing messages or signed-in browser click-through were performed. Public frontend publication remains pending approval. Evidence: `AI-BS_RecDebut_Frontend_Verification_2026-10-23.json`.
- Analytics access controls are active. Visitor/security reports, gateway aliases, the DuckDB query route, Chef analytics reads, and `/api/admin` now require verified Firebase/admin credentials. Explicit public POST intake routes remain available. Public traffic beacons only record telemetry; they no longer initiate email/SMS/Discord/TTS notifications. `/notify-login` remains available to authenticated administrators. The old caller-supplied email whitelist in admin telemetry was replaced, closing the same bypass on IP-ban and tester-passkey creation. The testing scope manifest is now private.
- Live verification passed 44 analytics/service checks plus 24 admin telemetry cases, including rejection of forged email headers. Authorized mutation probes used empty payloads and returned validation errors before side effects. Isolated actual-handler tests used disposable SQLite and mocked notification transports; public beacon recording still works. No real notifications, bans, or tester passkeys were created by verification. Backend restarted under its existing supervisor; all other managed daemon states remained unchanged. Backups: `C:\AI-BS\backups\analytics_auth_20261023`. Evidence: `AI-BS_Analytics_Authorization_Verification_2026-10-23.json`, `AI-BS_Admin_Telemetry_Authorization_2026-10-23.json`.
- Analytics frontend now sends login notifications through authenticated fetch without uncertain-POST retries. Traffic/security results clear on failed authentication/network reads, errors are visible, and stale site/session responses cannot restore private data. Four component mirrors match. Isolated frontend checks and Vite transforms passed; the actual shared loader successfully read reports through both 8080 and 8000. No signed-in browser click-through or public publication occurred. Evidence: `AI-BS_Analytics_Frontend_Verification_2026-10-23.json`, `AI-BS_Analytics_Live_Frontend_Verification_2026-10-23.json`. Public frontend release remains pending approval.
- Read-only screenplay review identified the next data-integrity priorities: beat reorder, character-vault edits/deletes, and async scene-video mapping still use process-global project selection; project switch/import bypass the existing path validator. Repair these with explicit project identity and metadata locking, then verify with two synthetic projects while preserving manuscripts. Also retain follow-up for JohnBarr's stale analytics error handling and older BroadcastStudioApp caller compatibility.
- Screenplay project scoping is active for character reads/saves/deletes, beat reorder, and scene-video mapping. Each requires explicit `project_name`; metadata updates are locked and atomically replaced. Character inference no longer writes during GET. Switching validates an existing project and cannot create a folder. Import validates the name, rejects collisions with 409, prepares a complete project outside the store, and publishes by directory rename only after a successful save. Original manuscripts and source were backed up under `C:\AI-BS\backups\screenwriting_project_scope_20261023`.
- Beat reorder now uses the captured unsaved draft and explicit project. It preserves all scene text, the title/preamble, FDX refresh, metadata counts, and Git revision behavior. Files are restored on an ordinary write failure; this is not a crash-proof transaction across multiple files. Git failures are reported separately after successful saves, and unrelated staged files are excluded from the revision. Frontend actions capture project/load identity, ignore stale results, and coordinate reorder with autosave. Character modal instances are keyed by project; import selects the returned project and preserves editor contents on collision. Four mirrors match.
- Verification passed 22 backend fixtures and 21 frontend fixtures, including two-project isolation, concurrent metadata updates, real Git/FDX behavior, malformed metadata preservation, write/publish failures, stale responses, and import collisions. Live gateway checks used three synthetic projects, archived them afterward, restored the original selection, and confirmed all 866 original files unchanged. Vite transforms, authorization checks, backend/gateway health, and both Stehouwer model registries passed. Evidence: `AI-BS_Screenwriting_Project_Scope_Verification_2026-10-23.json`, `AI-BS_Screenwriting_Project_Scope_UI_Verification_2026-10-23.json`, `AI-BS_Screenwriting_Project_Scope_Live_2026-10-23.json`. No signed-in browser click-through or public frontend publication occurred.
- Draft-preservation and revision-conflict protection is now active locally. Screenplay reads return exact-byte revisions; write/reorder require the loaded revision and reject missing tokens (428) or conflicts (409) before mutation. A Windows mutex serializes participating API workers; busy or unreadable adaptation state blocks interactive saves. Read-only adaptation fallbacks use their own content hash. Exact UTF-8/CRLF bytes are preserved. The editor serializes saves, flushes dirty drafts before project transitions, retains text on failed/conflicting saves, and provides browser recovery copies, downloads, and confirmed reload. Incoming shared-workspace text cannot silently overwrite the selected project. Four active mirrors match.
- Revision verification passed 34 backend concurrency fixtures, 22 project-scope regressions, and 38 isolated frontend behavior fixtures, plus coordinator/wiring/JSX checks. Production gateway checks passed 27 content/integrity assertions and 34 HTTP status cases using four synthetic projects. They were archived, original selection restored, and all 866 original screenplay files remained unchanged. Backend restarted under its supervisor; 5173/8000/8080 health, five Vite modules, both 30-model Ollama registries, and unchanged other managed daemons were verified. Evidence: `AI-BS_Screenwriting_Revision_Backend_Verification_2026-10-23.json`, `AI-BS_Screenwriting_Revision_Scope_Regression_2026-10-23.json`, `AI-BS_Screenwriting_Revision_UI_Fixtures_2026-10-23.json`, `AI-BS_Screenwriting_Revision_Live_2026-10-23.json`, and `AI-BS_Screenwriting_Revision_Runtime_After_2026-10-23.json`.
- This checkpoint covers participating interactive API writers. Internal adaptation/direct filesystem writers still do not share the mutex and can race after the busy-state check; coordination of their lifecycle and writes remains required. Plain saves retain Fountain-only behavior; reorder refreshes FDX/metadata/Git. Signed-in browser interaction and public frontend publication remain pending. Legacy clients without a loaded revision now fail closed and need contract alignment before release.
- Metadata-only credential inventory is complete in `AI-BS_Secret_Storage_Map_2026-10-23.md`. A Git-tracked vault master key is used by existing encryption/decryption code and must remain recoverable. Root OAuth files lack ignore rules; API-key vault records are stored as plaintext SQLite TEXT; dotenv precedence differs by component. No secret migration, decryption, provider validation, rotation, or Codex credential storage was performed by the inventory. Subsequent status-only checks confirmed unauthenticated vault reads; their authorization repair is in progress.
- Next manuscript priorities: coordinate adaptation writers and validate upload/text paths, complete older-client compatibility, and organize the newly requested Google Drive manuscript copies. Continue other file/execution permissions and reconcile duplicate Ollama/Chroma listeners and stores. Certificate-based document signing remains a separate unfinished capability.

## Recommended direction

Keep AI-BS as a modular local control plane. BS-Chat and the dashboard should call a shared, versioned Go/FastAPI service layer. The Windows Studio, October7 DAW, publishing site, RecDebut, and other business tools should remain distinct clients or services with clear permissions and data boundaries.

For now, preserve the existing React dashboard and the separate native Studio. The current plan’s Electron shell conflicts with the earlier browser-free desktop goal. Do not merge these into one desktop runtime until that direction is chosen.

## First 30-day optimization cycle

The day ranges are planning checkpoints, not mandatory waiting periods or a promised completion date. Complete and verify repairs as soon as practical; retain longer observation where service stability requires it. Publishing, deleting user data, DNS changes, and purchases remain approval gates. Overall completion depends on verified scope and remaining findings.

This is a time-boxed sequence over the existing review and implementation phases below. The first month should focus on making the current system more reliable, secure, understandable, and easier to maintain. Keep new features to a small number of additions that resolve a verified gap; do not rewrite working subsystems or remove files just to reduce their count.

### Days 1–5 — Restore BS-Chat and confirm the baseline

- Treat the current BS-Chat model failure as the first priority. The reported requests to both `127.0.0.1:11434` and `127.0.0.1:11435` return HTTP 404 with `Model 'stehouwer_llm' not found`. That response indicates the endpoint answered but did not resolve the requested tag; it does not by itself prove the Ollama engine is unreachable.
- Reuse the review baseline below and capture only what has changed since it: Git state, active processes and ports, current builds, model tags/runtime paths, public routes, and database file metadata.
- Create the source-of-truth registry from Phase 2, starting with the services and programs that are live or actively used.
- Rank issues by security exposure, user impact, and likelihood of breaking a working flow. Select at most three workstreams for this cycle; proposed starting priorities are BS-Chat/model recovery, protecting the writing project store, and confirmed access gaps. Carry RecDebut database reconciliation into the next slot unless the initial comparison shows an urgent data risk.
- Record a short before-state for each selected workstream so improvement can be checked later.

**Checkpoint:** Identify the Ollama daemon BS-Chat is configured to use, its actual model store, and the tags it serves; agree on the remaining workstreams and success criteria before source changes begin.

### Days 6–12 — Stabilize access control and model runtime visibility

- Trace the selected admin and public routes through the Go gateway and FastAPI backend, then prepare the smallest authorization changes that close confirmed gaps while preserving intended public flows.
- Map each Ollama process to its effective model directory, manifest/tag, configured client, and health endpoint. Check each daemon’s `/api/tags` and `/api/show` response, the exact configured model name, and BS-Chat’s endpoint/model settings. Keep manifests, Modelfiles, and weights intact while resolving the empty model lists and 404 error.
- Restore BS-Chat against the canonical daemon/tag once the existing model-store lineage is confirmed. If the tag must be recreated, first confirm its exact Modelfile and base dependency; do not rebuild or retrain while runtime and base-weight dependencies are unclear.
- Review the Stehouwer LLM route-specific prompts and model selection against the lineage map in Phase 3A.

**Checkpoint:** BS-Chat can identify the canonical Stehouwer model and complete a local inference request; review the proposed auth diff and model/runtime map before applying changes that could affect public behavior or model availability.

### Days 13–19 — Reconcile data paths and active code paths

- Compare the two RecDebut databases at the schema and table-count level, and produce a reversible reconciliation proposal. Preserve row-level contact data from broad review outputs.
- Trace the telemetry database references and the active frontend/backend build paths. Confirm which copies are imported, packaged, or served before consolidating anything.
- Document the Nginx, Tunnel, API, dashboard, and domain routes in the source-of-truth registry, including the exact singular/plural production hostname discrepancy.

**Checkpoint:** No database merge, file retirement, tunnel stop, or hostname/DNS change proceeds until its diff or migration plan and rollback are reviewable.

### Days 20–26 — Apply a few measured improvements

- Implement the approved, highest-impact fixes from the first three workstreams, in small reversible changes.
- Choose no more than one or two small additions, and only where existing architecture already has a stable integration point. Candidate examples are a real linked-folder catalog for the DAW Sound Vault or clearer model/runtime status in the existing dashboard.
- Keep the sample library on E: and use existing links; avoid copying large media trees or rebuilding the native Studio as part of this optimization cycle.

**Checkpoint:** Compare the changed behavior with the before-state and keep a rollback path for each change.

### Days 27–30 — Verify outcomes and set the next backlog

- Check the affected local services, routes, UI flows, data counts, and model visibility using the verification steps approved for the changes. Compare the local dashboard with the hosted version only where the change affects both.
- Produce a compact before/after report: what changed, what remains unresolved, operational risks, and whether the improvement is present in local, installed, or hosted builds.
- Rank the next month’s work from observed impact, and defer broad cleanup or new product areas until the canonical source and runtime map is dependable.

**30-day success criteria:** The selected workstreams have a documented owner and canonical path; the confirmed high-risk route gaps have a reviewed resolution; model tags can be tied to a known runtime/store; database divergence has a reversible disposition; and each implemented change has an observed verification result and rollback path.

This schedule is a planning overlay for Phases 0–6, not approval to modify production services. Existing approval gates below still apply.

## Protected subsystem — Universal Screenwriting Studio and document workspace

**Current retention instruction (2026-10-23): Never delete created documents, duplicate documents, or older versions.** Organize them in separate clearly labeled folders. Preserve existing paths until their consumers are mapped. Project archival remains recoverable; duplicate detection labels or links copies without deletion. New Google Drive intake must retain source originals, separate working copies, previous versions, and a provenance index. Native Google Docs are explicitly authorized for both DOCX and PDF copy export. Drive originals remain unchanged. Downloaded originals must be protected from the current editor autosave paths before exposure as editable workspace documents.

Treat the screenplay projects and documents as high-value user work. Do not change save paths, project names, format conversions, app mirrors, or backend routes until there is a read-only inventory and a recoverable backup of the relevant files.

The browser security gate denied access to observe `http://localhost:5173`, so this pass is based on source code and filesystem metadata. The live UI, current autosave indicator, and HTTP behavior were not verified.

**Source review and current storage map (2026-10-23)**

- The local dashboard route `?tab=unified_creation` maps to the Universal Creation Suite, which opens the Writing Studio by default. Its `PlaywrightTab` also contains a separate Studio Workspace for general documents and Fire Writing.
- The repository’s mirror-sync script treats `frontend/src/components` as the source and copies it to `frontend/components` and nested mirror folders before a production build. The inspected writing-suite component copies currently match by SHA-256. Any later code fix must be made in the canonical source and synchronized; editing a mirror alone could be overwritten on the next build.
- The active screenplay editor uses Fountain text and a Fountain/AST editor pipeline. It writes the main draft to `C:\AI-BS\screenplay_projects\<project>\screenplay.fountain`; project metadata and source/adaptation files also live in those project folders. FDX export is generated in the browser for download. The backend also has a `ScreenplayProject` helper that can create an FDX sidecar and Git commit, but the active autosave route writes the Fountain file directly and does not call that helper.
- The editor keeps an origin-specific browser `localStorage` snapshot and debounces a backend save by 1.5 seconds. That snapshot is a recovery aid, not a substitute for the disk copy or a portable backup. A ChatGPT individual-plan change is separate from these AI-BS files and browser-origin data.
- The read-only filesystem inventory found 13 project directories under `C:\AI-BS\screenplay_projects`; each had a non-empty `screenplay.fountain` and `project.json`, and six had an FDX sidecar. `C:\AI-BS\frontend\screenplay_projects\Default Project` is a separate placeholder without a `screenplay.fountain`; do not treat it as canonical. No screenplay content was opened during this inventory.

**Data-integrity risks to resolve before relying on autosave alone**

1. The frontend sends `project_name` on save, but the backend write payload accepts only `content` and selects the target using one process-global `_current_project`. Project switching and writes from multiple tabs/sessions can therefore race and save into the wrong project.
2. Creating a project whose name already exists writes the starter template directly over its `screenplay.fountain`. The UI/backend do not show a duplicate-name protection step in the reviewed code.
3. The delete endpoint recursively removes the project directory. The confirmation is in the UI; the backend route itself does not require a second confirmation or provide a recovery/trash path.
4. The guide describes a SQLite screenplay vault and encrypted scripts, but the active save route reviewed here writes plaintext files. Do not rely on a SQLite or encryption copy until one is verified in code and on disk.
5. The general Documents pane has a separate, inconsistent API contract: the frontend posts `filepath`, while `/api/save` requires `path`; its `/api/tree` and `/api/read` aliases import helper names not present in the reviewed shared-drive router (which exposes different names/routes). Static review therefore does not establish that general-document save/load works. Verify this pane before using it as the only copy of new writing.
6. The screenwriting router has no per-route authorization dependency, and `/api/screenwriting` is absent from the reviewed admin-execution middleware prefix list. If these routes are exposed through a public proxy, verify the actual ingress protection before treating the UI lock as access control. The suite’s embedded client-side unlock and local-development bypass are not backend security controls.

**Safe order of work**

- Record paths, file sizes, timestamps, and hashes for screenplay and source files without printing manuscript contents; make a recoverable backup before implementation.
- Make screenwriting saves explicitly project-scoped in each request, validate project names as a single safe directory component, and prevent duplicate project creation from overwriting existing drafts.
- Replace permanent project deletion with a recoverable archive flow, then reconcile save-status indicators and documentation with the real persistence path.
- Repair and verify the general Documents API contracts and allowed-root behavior separately from screenplay persistence.
- Review route authorization at both local and tunneled ingress. After each approved change, verify the saved file, expected project, and recoverability before continuing.

**Historical guides and recordings (2026-10-23)**

- The five supplied screenwriting guides are separate revisions, cataloged by SHA-256 in the [Screenwriting Studio evidence index](AI-BS_Screenwriting_Studio_Evidence_Index_2026-10-23.md). Treat them as records of intended workflow and feature claims, not proof that each feature currently works.
- The guides claim screenplay autosave into an encrypted SQLite vault. That conflicts with the reviewed active route, which writes plaintext Fountain files. The guides also disagree on 54-line versus 55-line page limits. Resolve both against the actual implementation and exported output before claiming vault protection or pagination compliance.
- The manuals advertise AI alt-takes, novelization, synthesized table reads with MMCSS priority, Wan2.1/RTX 4090 dispatch, ComfyUI, Unreal exports, CMS publishing, and tax-credit calculations. Add each to a feature-verification matrix: UI control → frontend handler → API/runtime → persisted/exported result. Do not infer availability, security, accuracy, or hardware execution from the manual alone.
- The Videos tree contains 76 MP4 files totaling 8,507,320,818 bytes (about 7.93 GiB): 52 timestamped clips in Screen Recordings and 24 named clips at the Videos root. Discord Clips, NVIDIA, and Captures are empty; no image files were found in this Videos tree. The clips have been indexed by name, modification time, size, duration, and frame dimensions, but have not been watched or transcribed.
- SHA-256 confirms that AI-BS walktyhrough.mp4 and Recording 2026-10-05 144740.mp4 are exact duplicates. Keep both originals until the owner reviews the evidence index and chooses which copy to retain; use hashes for any later deduplication.
- Use the October 5–19 named recordings first, then the July–September Screen Recordings, to build a timeline of observed behavior, versions, fixes, and regressions. Record clip timestamp plus the source/build/data path that corroborates each conclusion. Filename and filesystem timestamp alone are not proof of what the clip demonstrates.

## Review baseline

- The C:\AI-BS Git branch is 18 commits ahead, with 145 modified and 792 untracked items. Preserve that state; do not reset or clean it.
- Current version labels differ: version.txt is v5.329.0, the main frontend is 5.328.0, and BroadcastStudioApp is 5.327.0. The found Studio installer is 5.296.0.
- Go on 127.0.0.1:8000, FastAPI on 127.0.0.1:8080, and Nginx on loopback are active. Cloudflare Tunnel supplies public ingress.
- Unauthenticated checks returned 401 for Go daemon status and terminal routes, but 200 for the analytics traffic summary and RecDebut stats.
- The RecDebut router points to saved_data\rec_debut.db; a second backend\rec_debut.db has divergent row counts. Two telemetry checkpoint databases have identical hashes.
- 118 E: sample-pack junctions resolve to unique existing targets. The Sound Vault UI currently filters a hard-coded list instead of browsing those folders.
- The exact stehouwerproduction.com hostname is unresolved; local config uses the plural stehouwerproductions.com.
- The writing tool is a high-value existing subsystem. Its canonical screenplay store is `C:\AI-BS\screenplay_projects`; the save-flow and general-document pane findings are recorded in the protected-subsystem section above. Preserve these files before any repair.

## Phase 0 — Protect the current working state

**Actions**

1. Capture Git status, diffs, branch ancestry, and a path inventory before editing. Do not run git clean, reset, or broad mirror-copy commands.
2. Identify which untracked files are source, generated build output, databases, user data, or third-party tools. Preserve required untracked sources before any cleanup.
3. Record current service processes, listening ports, tunnel owners, domain routes, executable hashes, and SQLite file metadata. Do not collect lead or visitor row contents.
4. Create SQLite backups with SQLite’s online backup mechanism before any data migration.
5. Treat `C:\Users\footb\OneDrive\Desktop\carrytodex` as a historical/staging archive until its contents are mapped to canonical repositories. Its source bundle `.md` and `.txt` exports are byte-identical; the folder also contains contact/roster exports and other sensitive data. Do not bulk-ingest it into model/RAG context or deduplicate/delete files before a hash-and-reference inventory.
6. Treat the supplied DevTools favicon/MNU errors and audit checklist as unverified observations/proposals. Confirm the hostname and route in live logs/source before changing auth or request methods.

**Complete when:** There is a recoverable baseline and a manifest linking each active program to its source, executable, port, data store, and public hostname.

## Phase 1 — Close confirmed access and credential gaps

**Actions**

1. Rotate the RecDebut provider credential found in source, after confirming which provider account it belongs to. Remove all hard-coded fallbacks and load the replacement through a protected runtime secret source.
2. Define a public-route allowlist for RecDebut: intended landing, registration, short-link, tracking, and signed webhook endpoints only.
3. Require admin authorization on roster access, athlete email/contact data, campaigns, dispatch, messaging, provider configuration, and other control routes. Apply the same policy to both modern and legacy route prefixes.
4. Remove the duplicate include_router(rec_debut_router) registration once the route inventory confirms which registration is canonical.
5. Require admin authorization for detailed analytics summaries. Keep event ingestion public only with payload size/schema limits, abuse controls, and no raw form values.
6. Replace the Go rate-limit stub with an actual limit. When behind Cloudflare Tunnel, derive client IP only from a trusted proxy header and only when the request came through that proxy.
7. Review Cloudflare Access and WAF policies for AI-BS control surfaces. Keep public publishing/recruiting pages public while protecting admin interfaces and APIs.

**Complete when:** Anonymous access to admin/data routes is denied; intended public flows still work; no provider credential remains in source; analytics summaries do not expose visitor-level data.

## Phase 2 — Establish one source-of-truth registry

Create a maintained registry for each AI-BS entity with:

- Canonical source directory and current build/version
- Executable, launcher, owner, and lifecycle method
- Local port and health endpoint
- Permission scope and identity mechanism
- Database(s) and canonical data path
- Public domain/path and Tunnel/Proxy mapping
- External asset roots and whether they are links or copied data

Include the Go gateway, FastAPI backend, dashboard, native Studio, BroadcastStudioApp, Nginx, Cloudflare Tunnel processes, October7 DAW, RecDebut, and connected business programs.

Also resolve the hostname spelling for stehouwerproduction.com versus stehouwerproductions.com. Update DNS, Nginx, Tunnel, CORS, and certificates only after the intended name is confirmed.

**Complete when:** Every live process and public hostname has one named owner and one current source path; stale ledger and symbol-graph files are labeled historical or regenerated.

## Phase 3 — Reconcile data stores and service ports

**Actions**

1. Treat saved_data\rec_debut.db as the current code-selected RecDebut database, but do not discard the other database. Produce a table-level comparison and a dry-run reconciliation for athletes, campaigns, dispatches, and tracking history.
2. Review the two identical telemetry_checkpoint.sqlite copies and their code references. Select one canonical location, update references, then archive the other only after a backup and post-change checks.
3. Inventory all SQLite stores and document their purpose, retention, backup method, and owning service. Confirm whether ai_bs_db.sqlite is truly absent or whether another named database is its replacement.
4. Choose one ChromaDB port and data path. Current source and UI references disagree between ports 8001 and 8002, and neither appeared in the captured listener snapshot.
5. Record which inference models and ports are actually active; distinguish configured fallback paths from services running now.

**Complete when:** There is one documented path per live logical database and one ChromaDB endpoint. Any merge is reversible and its before/after counts reconcile.

## Phase 3A — Establish the Stehouwer LLM source and runtime lineage

**Review findings**

- `backend/models/stehouwer_llm.Modelfile` is a customized source definition with a Qwen ChatML/FIM template, tool-call formatting, a 16,384-token context setting, and hybrid GPU layer setting. It is referenced as the configured fallback model, so preserve it as a first-class source artifact.
- The July study guide describes an older Llama 3.1 / 8k configuration. The Sept. hybrid-context plan is also historical. Keep both as provenance; neither should silently replace the current Modelfile.
- The current model source depends on `stehouwer_qwen:latest`; the Qwen Modelfile also names `stehouwer_qwen:latest` as its base. The bulk build scripts attempt `stehouwer_llm` before `stehouwer_qwen`, so the build graph requires a separately available base model.
- Correction from the follow-up cross-check: `C:\AI-BS\models\ollama\manifests` contains manifests for underscore and hyphen variants including `stehouwer_llm`, `stehouwer_qwen`, and several related tags. Their referenced blobs exist in the local store. The Qwen and Dolphin GGUF symlink targets on E: also exist. However, both configured Ollama API endpoints (11434 and 11435) returned empty model lists, and `stehouwer_llm` was not found through the primary CLI endpoint. The verified state is a model-store/runtime visibility mismatch, not “no model installed.” Identify each daemon’s effective `OLLAMA_MODELS` path and canonical tag before rebuilding, moving, or deleting anything.
- Current BS-Chat incident reported after that cross-check: its “Hybrid Stream” status says the local engine is unreachable, but its detailed errors show HTTP 404 from both `127.0.0.1:11434/api/generate` and `127.0.0.1:11435/api/generate`, each stating that model `stehouwer_llm` is not found. Interpret this as a failed model lookup at responding endpoints until process/health checks establish otherwise. Determine whether the selected model tag differs from the manifests, the daemon points at another model store, or BS-Chat is using a stale endpoint/tag configuration. Do not assume the UI’s “unreachable” label diagnoses the underlying fault.
- The repo has a separate `backend/scripts/train_aibs_sovereign_coder.py` that implements a real Transformers/PEFT/TRL QLoRA training path for a DeepSeek Coder base and a FIM dataset. This establishes a training implementation, not a successful completed run or a trained Stehouwer persona artifact. Verify the dataset, adapter outputs, dependency versions, and model lineage separately.
- The persona v2/v3 scripts validate or assemble datasets and export configuration; they do not perform LoRA training. The v3 script writes its unified JSONL dataset as part of its main path even when `--dry-run` is supplied, so do not invoke it until its write behavior and corpus provenance are addressed. Separately, `backend/bullshit_trainer.py` currently simulates training with `sleep` calls and logs a “complete” message without invoking an actual trainer; treat its `/finetune/start` endpoint as a misleading stub and review its exposure before use.
- `dispatcher.py` and `chat_router.py` can pass request-level system prompts to separate Ollama API routes. That affects effective behavior by route; it does not prove that all model calls replace the Modelfile prompt. Trace each client path before making global claims about prompt precedence.

**Actions**

1. Preserve and inventory the current Modelfiles, tracked `.bak` versions, `clean_modelfile`, `optimized_modelfile`, training datasets/configs, and any model weights on C: or E:. Mark which are canonical source, generated output, and historical reference.
2. Resolve the true upstream base weights and model tags, then define a dependency-ordered, reproducible build graph. Do not run the existing rebuild scripts while the base model and model storage paths are unresolved.
3. Separate persona/style tuning from factual project knowledge. Verify training-data source, consent, provenance, and factual claims before using that corpus for LoRA training; keep changing facts in retrieval-backed data.
4. Treat prompts and Modelfiles as behavior guidance only. Enforce filesystem, database, network, and execution permissions in the backend tool registry and authorization layer.
5. Review the repository operating instructions for embedded credentials and unsafe assumptions about universal authority. Rotate any live credential exposed in source or instructions.
6. Inventory model-store manifests, blob references, GGUF links, service process environment, CLI endpoint, and per-route prompt construction into one lineage map. Preserve duplicate tag variants until consumers are identified. Use the map to restore BS-Chat’s configured endpoint and model tag, then verify tag discovery and a successful local generation request against the canonical runtime.
7. Separate the genuine QLoRA trainer, persona dataset/config generators, and simulated `/finetune/start` endpoint in the registry and UI; label training status from artifacts/logs rather than endpoint messages.

**Complete when:** The active backend model tag maps to a reproducibly built model with identified source weights and Modelfile; runtime health confirms the tag exists; training status and corpus provenance are explicit; and execution authority is enforced outside the model prompt.

## Phase 4 — Consolidate code and executable paths safely

**Actions**

1. Keep frontend/src/components as the candidate canonical React source. Map imports and generated mirrors before changing the build. Do not delete mirrors until the build no longer imports them and parity is verified.
2. Keep the newest RecDebut router as active source; move older copies/backups to a dated archive only after confirming they are not imported by launchers or packaging.
3. Compare the multiple aibs_updater.exe copies and installer contents by hash and reference. Name one build output as canonical; retain rollback copies until the replacement is proven.
4. Identify the one intended Cloudflare Tunnel manager. The Windows service and the separate named-tunnel process may serve different routes, so do not stop or remove either until tunnel IDs and route ownership are mapped.
5. Compare source, built website assets, installed binaries, and Firebase assets by version/hash. Regenerate historical architecture artifacts only after the canonical map is settled.

**Complete when:** Each executable and source mirror has a documented purpose; unused duplicates are archived with a recovery path rather than deleted during discovery.

## Phase 5 — Connect the DAW to the real E: library

**Actions**

1. Keep the sample packs on E: and retain the working junction approach to conserve C: space.
2. Replace the Sound Vault’s hard-coded demo labels with a catalog generated from the actual linked pack folders. Use an explicit allowlist/manifest so unrelated folders are not swept in by broad keyword matching.
3. Make missing-drive and missing-junction states visible without copying assets back to C:.
4. Keep the AI-BS DAW launcher pointed at the selected October7 Native executable. Compare its build against the source project before replacing the installed binary.
5. Do not run the existing broad junction-creation script as part of cleanup; it performs filesystem changes at import/run time.

**Complete when:** The UI lists actual E: packs, opens a selected folder/file correctly, and does not create duplicate audio copies on C:.

## Phase 6 — Align, validate, and release

**Actions**

1. Choose one version authority and align app/package/build metadata.
2. Build the intended local dashboard, native Studio, and DAW artifacts from their named source projects. Do not treat file modification time alone as proof of feature parity.
3. Perform authorized, read-only service checks for health, public pages, and anonymous-versus-admin route behavior. Do not add a new test suite unless requested.
4. Compare the local dashboard build with Firebase and the Nginx-served publishing build. Prepare a rollback artifact before any public deployment.
5. Deploy only the approved artifacts to the confirmed hostnames, then verify their health and route behavior.

**Complete when:** Version labels agree, the local and public artifacts are identified, protected endpoints reject anonymous requests, intended public endpoints remain available, and rollback is ready.

## Decisions for plan review

The recommended defaults are:

1. Keep the web dashboard and native Studio as separate clients sharing the same service API.
2. Treat RecDebut admin/data endpoints as private; expose only explicitly approved recruiting, tracking, registration, and signed webhook routes.
3. Resolve the production domain to one spelling before changing routing.
4. Reconcile databases before retiring any copy.
5. Keep E: media in place and make AI-BS browse it through the existing junctions.

## Approval and execution gates

Your approval of this plan can start the non-destructive inventory and implementation work. Database retirement, stopping a Tunnel process, DNS changes, and public deployment remain explicit checkpoints: first produce the exact diff, migration comparison, or route change for review, then perform the corresponding operation after approval.

No destructive cleanup, credential rotation, DNS change, or deployment is part of this plan document itself.

## ChatGPT subscription decision

The user prefers an individual subscription rather than a Business workspace. An individual account can be used by its owner on multiple devices, including the user’s mother’s computer; the mother should use her own account if she wants to use ChatGPT herself. OpenAI’s [account-sharing policy](https://help.openai.com/en/articles/10471989-openai-account-sharing-policy) allows multi-device use by one account owner and says accounts are for individual use. This plan records a preference only; it does not verify a purchase or change an account.

If the intended individual plan is **Pro $100**, that is a one-person subscription, separate from Business Premium pricing. Her occasional document reviews can start under her own account, subject to that account’s available features and limits. Subscription selection is outside the AI-BS recovery work and does not establish that Gmail/Drive connectors are enabled; confirm those app settings separately.
