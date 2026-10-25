# AI-BS Autonomy and Differentiation Plan

Plan revision: 1.58 | Updated: October 24, 2026 | Local application source: v5.329.46

## Purpose and current checkpoint

Develop BS-Chat into a reliable central workspace for code changes, creative production, business operations, and local automation. Prove useful workflows between these systems while preserving original work and proprietary methods.

**Latest operator decision: defer Windows VM setup.** Stop VM installation/recovery retries, login requests and monitoring until the user explicitly returns to that task. Preserve the existing VM, ISO, snapshots and evidence. This supersedes the earlier requirement to finish VM provisioning before doing any other work. Phase4 containment acceptance remains incomplete: VM-dependent execution, expanded host execution, unattended maintenance and releases claiming isolation remain disabled. Continue one bounded task at a time on work independent of the VM; do not substitute host execution for the missing worker.

**Remaining plan approved.** The user has approved proceeding with the remaining work. Continue routine implementation/verification and compatible releases after their required checks without repeatedly requesting the same approval. This does not reverse the explicit VM deferral, authorize document deletion, supply credentials/license acceptance/signing material or waive containment/release acceptance.

Current phase count: **3 of 6 completed for the existing limited trusted-local coding workflow**. Phase 1 review/apply, Phase 2 one-attempt repair and Phase 3 interruption recovery have retained passing checkpoint evidence. Phase 4 is partially implemented with VM setup deferred and actual containment acceptance incomplete. Phase 5 larger-project support and Phase 6 complete-workflow/platform release acceptance are incomplete. Later frontend and memory hardening improve those foundations; focused tests do not complete another whole phase. Current source checkpoint v5.329.46 is not a Firebase/Windows release.

Completed foundation: the existing Stehouwer model has generated a small Python change in a separate Git working copy, run a real test, and retained the result and diff without altering the original files. Administrator access and review-mode behavior have been checked. Phase 1 review/apply has since completed a real fixture application with a retained original backup and authenticated HTTP checks.

Current gate: preserve data and verify authenticated memory/coding behavior while VM setup is deferred. Historical Phase 4 feasibility evidence follows. Phase 2 includes one actual Stehouwer repair of a seeded failing proposal using a real unittest error; both attempts remain retained. Phase 3 includes real fixture-worker termination during generation, unittest execution, and file application. v5.329.15 fixed concurrent repository application, verified retained originals/test evidence, and stopped stale inputs after inference. v5.329.16 adds an admitted inference worker with retained inputs/output, bounded lifetime and output, a 300-second admitted-request budget, and authenticated cancellation during initial generation, repair, and linked checks. A live HTTP chat request was cancelled while its real inference client was connected to Ollama, with no subsequent code execution. These trusted-host process controls do not isolate host files or networking, and server compute-release timing after client disconnection was not measured. The PC reports Windows 11 Home; VirtualBox and verified evaluation media are installed/downloaded, and a standard-worker VM exists. Windows installation, terms/activation and controller integration remain incomplete. Browser interaction and full VM/network/document isolation gates remain open. Attachment upload remains a separate issue.

Completed at v5.329.17: admitted tasks now retain raw input, hashes and a terminal failure record before source/path validation. Rejected proposals and actual errors are inspectable with Apply disabled. Cancellation during validation stops before worktree creation. The 42 focused tests, 12 live rejection/review checks, and 16 controlled service/document checks pass. Browser interaction and Windows VM isolation acceptance remain open. The user has now requested resuming one task at a time. The first resumed task restored the handoff opening from its hash-verified snapshot, retaining the overwritten copy; application files remain v5.329.17. Next is a concrete Windows VM setup proposal for review, without installation or broader execution.

Local application source is v5.329.46. The previously published Firebase UI was v5.329.9 at last verification; the native Windows release remains deferred. This plan revision does not publish either artifact. Detailed source, tests, live evidence, limitations, and save points are in `docs/CODEX_HANDOFF.md`.

**Journal regression repaired at v5.329.26:** actual Windows reader locks reproduced the access-denied replacement failure. A shared flushed/exclusive writer now retries only the same promotion for a bounded period and preserves old/staged records on terminal failure. The88-case regression suite,16 affected flow tests and14 actual worker-interruption observations pass. This resolves the observed writer blocker for tested conditions; full live/platform release checks and VM containment acceptance remain separate and incomplete.

## Order and working rules

| Phase | Deliverable | Relative effort |
| --- | --- | --- |
| 1 | Review and apply | Smallest |
| 2 | Handle failures | Moderate |
| 3 | Recover interrupted tasks | Moderate-high |
| 4 | Protect execution | High |
| 5 | Support larger projects | Very high |
| 6 | Verify, demonstrate, and release | Largest combined effort |

The ranking is an estimate, not a deadline. Work proceeds one task at a time, with no parallel agents. Each phase ends with evidence, a save point, and a reviewable result. Application changes receive a version update; document-only changes receive a plan revision. Model calls remain bounded, with one automatic repair maximum.

Never delete created documents, source originals, proposals, or backups. Keep retained material in clearly labeled folders. Preserve the customized Stehouwer model. Routine local edits, checks, and AI-BS service restarts remain preapproved. Ask before deleting data, changing DNS, making purchases, or expanding permissions beyond the authorized scope. Releases follow the existing authorization and must pass their checks. Outbound messages require explicit activation.

## Phase 1 - Review and apply

Goal: accept a tested change directly from BS-Chat while retaining the original.

- Show a coding-task card with changed files, readable diff, actual test output, current state, and an Apply Verified Change button.
- Add authenticated review and apply operations. Failed and older tasks without sufficient verification evidence remain inspectable, with Apply disabled.
- Bind approval to the exact reviewed proposal. Before applying, check that original files, proposed files, and relevant verification inputs still match their recorded hashes. A change invalidates approval and requires verification again.
- Save timestamped backups and an application record before writing. Apply only the reviewed file list; record each completed write and prevent duplicate application.
- Prevent competing applications from overlapping. Preserve partial application evidence if interrupted.

Acceptance: one verified example applies correctly; stale originals, altered proposals, altered verification files, failed tests, duplicate requests, and unauthorized callers behave correctly. Original backups remain readable.

Checkpoint: a working review-to-application flow and the first documented coding case.

## Phase 2 - Handle failures

Goal: use actual errors to attempt one bounded repair.

- Give Stehouwer the failed test output and the relevant proposed source, with confidential values removed from model context and display logs where applicable.
- Allow one automatic repair after the initial attempt. Keep the original editable-file list and operator-approved verification commands fixed.
- Preserve both attempts and rerun the original checks in the separate working copy. The model cannot weaken tests or choose easier commands.
- Stop after the repair attempt. A persistent failure remains visible and cannot be applied.
- Record attempts, model use, elapsed time, and result in the case library.

Acceptance: a repairable example passes on its second attempt; an unrepairable example stops after one repair. Originals stay unchanged and failed results are never reported as successful.

Checkpoint: a passing repair example and an honestly reported failure example.

## Phase 3 - Recover interrupted tasks

Goal: survive restarts without silently repeating consequential actions.

- Persist task inputs, attempt history, verification evidence, progress, and application records from task admission onward.
- Add an authenticated Recover Task action and show interrupted work in BS-Chat.
- Redisplay completed results without repeating generation, tests, or application.
- Resume only from a confirmed safe checkpoint. Uncertain execution requires an explicit rerun; never assume an interrupted command did nothing.
- Reconcile partial application against original, proposed, and backup hashes. Finish or restore only when the saved record determines a safe action; otherwise retain the files and require review.

Acceptance: interrupt generation, testing, and application separately. Recovery preserves evidence, avoids duplicate application, and accurately reports unfinished or ambiguous work.

Checkpoint: a documented recovery demonstration and a persisted task history.

## Phase 4 - Protect execution

Goal: contain generated code and reliably stop its entire execution.

- Use a disposable Windows virtual machine for the expanded execution workflow. Verify the required Windows features, guest image, licenses, and runtimes before enabling it. Any purchase or disruptive host change requires approval.
- Exchange only approved task inputs and outputs. Disable guest networking by default and exclude credentials, personal documents, model originals, and unrelated host folders.
- Enforce backend permissions for repository access, editable files, verification commands, cancellation, recovery, and application. Folder names such as sandbox do not establish a security boundary.
- Add overall time and output limits, cancellation, and termination of task child processes. If the isolated worker is unavailable, reject expanded execution without silently falling back to host execution.
- Show understandable review gates at application and other consequential boundaries. Routine permitted work continues without repeated confirmation.
- Keep the existing limited host workflow explicitly identified as trusted local execution until it is migrated. Do not describe it as VM-protected.

Acceptance: host-document access, unauthorized network access, escaped writes, excess runtime/output, and surviving child processes are blocked. Ordinary checks still pass. A missing worker produces a clear blocked state.

Checkpoint: a verified isolation demonstration. Broader execution and unattended maintenance stay disabled until this passes.

## Phase 5 - Support larger projects

Goal: make coordinated changes across the languages and applications already used by AI-BS.

- Add JavaScript/JSX first, then TypeScript/TSX, using existing project validation tools. Continue Python support.
- Snapshot explicitly selected dependencies and relevant uncommitted files so the tested working copy represents the intended project state. Keep file permissions and editable scope fixed.
- Preserve tests and lockfiles. Dependency installations or upgrades require a separate, scoped task and explicit network authorization when needed.
- Report results by language and distinguish existing project failures from regressions introduced by the proposal.
- Apply the reviewed set through the Phase 1 backup and Phase 3 recovery mechanisms.
- Extend the case library to cross-system workflows, beginning with writing-to-production-planning and lead-record-to-business-workflow demonstrations. Use test data and draft actions for outreach cases.

Acceptance: complete a Python case, a React case, and a coordinated frontend/backend case. Existing failures are visible, new regressions block application, and original material remains recoverable. Record what cross-system workflows actually pass.

Checkpoint: verified examples of several project types and at least one working connection between AI-BS subsystems.

## Phase 6 - Verify, demonstrate, and release

Goal: deliver a consistent workflow and publish evidence of the capabilities that work.

- Exercise request, generation, failed-test repair, verification, review, application, cancellation, and recovery together.
- Verify administrator access, secret exclusion, document preservation, backend health, mirror consistency where applicable, and rollback procedures.
- Measure local execution and offline behavior using the proof protocol below. Claims must identify whether they were demonstrated, merely configured, or remain planned.
- Create versioned release candidates. Validate localhost/backend first, Firebase second, and the Windows package last. Confirm artifact versions and compatibility independently; a shared version label is not proof of equivalent functionality.
- Verify the Windows package and available signing credentials before distribution. Missing prerequisites block Windows distribution while preserving independently verified local work.
- Write a comprehensive shareable AI-BS overview, with a capability map, demonstrated cross-system workflows, remaining limitations, and a sourced comparison with relevant platforms. Explain user benefits without exposing proprietary methods or private configuration.

Acceptance: every released surface completes its supported workflow, reports the correct version, and has a verified rollback path. Unreleased or blocked surfaces remain clearly identified.

## Differentiation track A - Prove local performance and offline resilience

Begin collecting evidence during Phase 1; validate isolation-dependent cases after Phase 4; include results in Phase 6.

- Record hardware, model/version, task, input size, model availability, cold/warm state, and relevant concurrent load. Distinguish inference from tool execution and application time.
- For repeatable benchmark cases, collect at least ten comparable runs per reported condition. Report median, 95th-percentile elapsed time, failures, and first-response time when streaming.
- Test offline behavior inside a network-disabled test environment rather than disrupting the host connection. Record exactly which workflows succeed using already installed models, tools, dependencies, and files.
- Cloud-dependent connectors must report unavailable operation clearly. Do not claim the whole platform is offline-capable because local chat works.
- Compare alternatives only on equivalent tasks and conditions; otherwise report the limitation. Avoid invented latency promises, zero-delay claims, or superiority percentages.

Deliverable: a repeatable benchmark sheet and offline capability matrix backed by saved results.

## Differentiation track B - Build a case library and bounded background maintenance

Start the library in Phase 1. Enable unattended work only after Phases 3 and 4 pass and the operator explicitly activates it.

- Each case records the objective, approved scope, input/version references, baseline, proposal, test commands, actual outputs, resource use, result, and review/application outcome. Preserve unsuccessful cases too.
- Keep a private evidence archive and a sanitized set of demonstrations suitable for sharing. Use copies for manuscripts and business records; never turn personal communications into training material by default.
- Audit existing trainer and watcher modules before reuse. A file named trainer.py may be a game trainer or model-training component; its name does not establish a safe code-maintenance service.
- The initial maintenance schedule is one eligible job per day, after at least fifteen minutes of observed idle time, with no overlapping user task. Use the same configurable overall execution limit and cancellation controls as the interactive workflow.
- Read-only scans may identify a bounded improvement. Once activated, the service can prepare and test one isolated proposal without a new prompt, with one repair maximum. Unknown idle state, worker unavailability, conflicting work, or an exhausted budget defers the job.
- Every proposal passes the same review/apply gate. Initial unattended maintenance cannot apply changes, publish, retrain model weights, or send external messages.
- Measure successful fixes, regressions, accepted proposals, review effort, and recovery outcomes. Compare against a manual or remote-team baseline only if equivalent evidence is available.

Deliverable: a growing library of reproducible cases and, after isolation is proven, a controlled maintenance pilot. Superior maintenance performance remains a hypothesis until measured.

## Differentiation track C - Enforce the local perimeter

- Apply permissions and path restrictions in the backend and worker, including direct API calls. Interface buttons alone cannot enforce them.
- Test containment, secret exclusion, network restrictions, cancellation, unauthorized calls, stale approvals, and recovery as part of release acceptance.
- Keep review gates proportionate to the action and consistent with standing authorization. Preserve explicit activation for outbound communication and unattended maintenance.
- Describe protection in terms of enforced and tested boundaries. No system should be marketed as impenetrable.
- Keep source code, custom prompts, model modifications, detailed security rules, credentials, private datasets, internal network information, and proprietary algorithms out of public demonstrations and the shareable overview.

## Evidence and market claims

Local operation, custom models, connected agents, and self-hosting are not exclusive to AI-BS. For example, [MindStudio](https://www.mindstudio.ai/) documents custom models and self-hosting, while [n8n](https://n8n.io/) documents self-hosted agents and connected workflows. The public comparison also found broad overlap with Genspark, Manus, Abacus.AI, Microsoft, Zoho, Odoo, ChatGPT Work/Codex, Claude, and Google Antigravity.

Assess AI-BS on its demonstrated combination, workflow quality, control, reliability, and usefulness. Do not claim commercial competitors are structurally unable to provide local features, that AI-BS is a category of one, or that only seven comparable platforms exist without additional defensible evidence.

## Next implementation task

VM-independent work continues one bounded task at a time. Source43/plan1.53 connects collapsed desktop/mobile preparation controls and scoped paged history to authenticated preview/prepare/read/recover, with truthful PREPARED/Not run status. Backend36, client22, offline React8, source22 and actual API43 checks pass; live browser acceptance remains pending. Source44/plan1.54 adds authenticated model planning against retained selected Python/React sources, with immutable evidence, deadline/cancel/recovery and no replay.26focused,36prior regressions and11actual-model/ASGI observations pass; the actual model gave correct file changes plus generic questions, retained as Needs clarification. Source45/plan1.55 wires model planning/inspect/cancel/recover/history into the preparation panel and loads actual routes:33backend,41client,16offline React,13source and63actual API/model/cancel observations pass. One explicit Python/JS fixture produced0generic questions; broad quality is unproved. Browser connector still denies localhost after reported permission updates. Next is bounded reviewed-plan to retained proposal/diff, preserving complete-source evidence/checks and no execution admission; browser acceptance remains pending. Existing trusted Python behavior remains bounded; expanded execution requires the deferred accepted VM. Browser acceptance still requires saved localhost permission/genuine sign-in, no alternate-interface workaround. Full containment, larger-project runs, platform/rollback/signing/overview and memory/learning backlog remain incomplete; UI redesign later.

**v5.329.38 / plan1.48 completed independent prerequisite:** backend fallback now returns JSON404 for unsupported APIs and405/actual Allow for wrong methods, including nested/prefixed lazy included routers. Static serving resolves and contains files in declared public roots, denies Windows traversal/device/ADS/hidden/junction escapes, preserves public downloads/SPA/HEAD, and cannot shadow api/v1. Legacy substring dispatch is restricted to canonical path/methods; no unknown-body inference.22 final synthetic FastAPI/Windows methods,17 source-audit checks and37 actual core/gateway/auth/error/index/review/model/process observations pass. First live404 exposed missing included-router coverage; retained/red/green corrected. A later observer expected JSON on Go's non-proxied plain404; only that response-shape fixture was corrected, API acceptance unchanged. Two main-only restarts loaded the actual code changes; final169608/8080, other service identities and six disabled activation flags preserved. All888 selected documents/copies and two authority DB integrity/counts remain intact. Source38 metadata/checkpoint saved; compiled Go stays its verified37 and Firebase/native distribution is unchanged. Next independent task: legacy memory ownership/directive-authority review before multi-user recall. Browser memory acceptance still requires saved localhost permission resolution; no workaround. VM remains deferred and full isolation/larger-project/platform/retrieval/training gates remain incomplete.

**v5.329.39 / plan1.49 completed personal-memory authority:** verified administrator principal now binds request context and survives existing async/thread/stream/background calls. Personal reads/search/activity/delete require both canonical client and user; supplied labels cannot override the verified scope. Local-admin key retains the legacy brett namespace; Firebase UID namespaces are separate with no inferred ownership migration. Personal router independently requires authorization. References are unverified, source/hash-bearing and bounded6000characters; pinning is ranking, automatic directive-like extraction is unpinned and same-second claims have distinct event-based keys. Known credential patterns/environment secret values are excluded from derived references/extraction, without a universal detection claim.23 initial methods failed;25 final methods and47 private/fallback regressions pass,19 source checks and30 actual core/gateway/auth/read/model/process checks pass. Existing model greeting12.625seconds and its correct asynchronous personal log verified. Existing44facts/all original records in4personal source tables unchanged;389events became390 from the single synthetic greeting, personal schema unchanged and private snapshot retained. All888selected documents/copies and vault/master integrity/counts preserved. Only main service restarted; other service identities and6disabled flags preserved. No model weights, browser, VM, Firebase/native publication or full phase completion. Next: global manual archive/unified recall ownership and provenance, including legacy vault_items and non-personal unified context; broader multi-user privacy is still unproved. Browser memory acceptance remains permission-gated, VM deferred.

Completed the bounded evidence-display improvement at sourcev5.329.22: review cards distinguish no checks, recorded success, failed/interrupted checks and incomplete evidence; display the recorded/requested execution mode; and expose timeout/cancellation/output-limit/process errors alongside separated stdout/stderr. At sourcev5.329.23, server/task changes remount the review session, clear stale proposals/errors/tokens, abort obsolete reads and isolate late apply replies. Loading is explicit; missing tokens, mismatched responses and invalid task IDs cannot offer Apply. Thirteen actual-browser React cases with simulated backend replies and15 prior rendering/integration/parity checks pass. Backend apply authority is unchanged. No live API run, wider-project test or deployment is implied. VM work stays deferred.

At sourcev5.329.24, the saved-task list has its own backend session; late replies cannot mix history across servers or start follow-up reads after that session ends. Recovery/cancellation refresh the affected review and manual Refresh reloads the selected review. Malformed lists show an error and clear stale actions; empty lists are explicit. Thirteen browser cases using actual React DOM with simulated replies pass. Originals, four mirrors and16 metadata originals verified. No real task/API/VM execution or release occurred. Phase count remains3 of6 for the limited local workflow.

At sourcev5.329.25, existing manifest validation/staging accepts schema2 selected Python/JS/JSX inputs with immutable test/config/dependency paths and explicit selected verification profiles. Version1 Python-check compatibility remains. No new execution route, model integration or tool installation. Eighteen new tests plus33 direct input/staging/artifact regressions pass (51 unique methods). Broader attempts ran75/76 methods with one existing journal-write failure each; those runs are NOT passing release evidence. Both failure records and partial files remain saved. See docs/phase5/spec.md and the handoff for exact limits and remaining authorization/transport/runtime prerequisites.

At sourcev5.329.26, task/request/cancellation metadata uses a shared writer with exclusive staging, flush/fsync, Windows-only bounded promotion retries and retained failure evidence. No tasks or commands are retried. Twelve focused writer tests pass; the subsequent88-method regression run and16 additional affected-flow tests pass, followed by14 actual interrupted-worker recovery checks. Historical failed reports remain preserved. Source save point only; no service restart or platform release.

**v5.329.40 / plan1.50 archive prerequisite completed:** owner-aware full JSON/transcript receipts with unchanged source retention, non-destructive hide, independent admin/owner checks for shared vault and explicit recall, bounded source/hash/offset-bearing lexical results and owned-only automatic context. Legacy unassigned data is local-operator display only, excluded from automatic context; old history is not silently assigned to Firebase users. Swarm telemetry metadata only/no invented quality, clear requires matching owner receipt.27 focused methods+82 prior methods+12 new and33 prior Node checks,39 source checks and48 actual live checks pass. Full352716-row private-copy migration preserves every original column; production vault unchanged/no positive schema save yet. Existing model greeting11.11sec, selected888documents/copies and original personal records retained. One main-only restart, six flagsfalse, other services unchanged, Go compiled37. This is local source40, no Firebase/native publication or additional phase completion. Historical cases across all topics remain eligible after ownership/secret/evidence admission; lesson quality, semantic retrieval and weights are separate unverified work.

**v5.329.41 / plan1.51 selected-source preparation:** actual current selected Git repository bytes, including dirty/untracked edits, are read under held Windows handles with scope/path/count/byte/reparse/hardlink/recognized-secret checks. Exact UTF8/CRLF and source hashes bind to actual stable HEAD. Snapshot explicitly grants no authority/execution; no API/runner is wired yet.23 new methods and54 existing input/artifact/staging/VM-guard/schema methods pass;10 source and13 preservation/service checks pass. All888selecteddocuments/copies and existing runtime/model hashes preserved; no restart/model call/publication. Source41 helper is local preparation, running unchanged service code remains the verified40 checkpoint; Go compiled37. Phase count stays3of6 limited-local. Next authenticated prepare-only admission; actual VM/larger execution/platform gates remain open.

**v5.329.42 / plan1.52 preparation API:** server-owned repository/verified-owner/fixed-profile plan, current-source review binding, immutable intent/copies/receipt, independent readback, scoped retry/recovery without replay.29 final methods+88 existing regressions+16 workflows,17 source checks and52 live observations pass, including an actual gateway preparation and separate10.11sec model greeting. No selected project checks ran; receipts explicitly report Not run/execution unauthorized/pending accepted worker. Windows immutable-journal exclusive mode resolves a reproduced folder-lock/rename conflict; mutable default preserved.888selecteddocuments/copies and original personal records retained, one main-only restart, other services/six disabled flags preserved. Local source42, no new phase completion, Firebase/native distribution or browser acceptance. Next BS-Chat receipt wiring; VM remains deferred.

## Added requirements — conversation memory, task alignment and engineering ledger

The user requests durable chat memory, context-sensitive tone/style, broad natural-language ideas with focused clarification when needed, and direct answers to straightforward questions. Reuse accessible historical chats, Gemini folders, build ledgers and transcripts as attributed references while preserving originals. Inventory existing memory components first; do not create parallel stores or claim retrieval/model training works from a folder alone. Separate private transcript archives, curated memory and future training datasets; secret-review before copying/ingestion. Details and acceptance sequence: [Stehouwer_Conversation_and_Task_Alignment_Backlog.md](Stehouwer_Conversation_and_Task_Alignment_Backlog.md).

Maintain a cloud/local engineering ledger of requests, decisions with brief reasons, attempts, actual errors, tests and outcomes. This is a concise engineering summary, not private internal reasoning. The user-authorized private Drive folder is AI-BS Codex Engineering Ledger, with a Conversation Archives subfolder; current daily source ledger is docs/engineering_ledger/2026-10-24_Codex_Engineering_Ledger.md. Preserve prior daily ledgers in the same index. Verify cloud writes and track pending sync. Full archive import and BS-Chat cloud retrieval remain unimplemented/unverified. Standing preference recorded in the user's Codex AGENTS.md and an explicit memory-update note; this does not create an unattended sync service.

Inventory revision 1 distinguishes existing transcript stores, partial summary hooks, vector helpers, two Gemini brain roots, Takeout/carrytodex candidates and capped scans. No runtime/database/doc/model changes or imports occurred. Do not run the old overwrite-style ingestors. Use source-proven gaps and explicit acceptance tests to prioritize protection and saving before recall/learning.

**Clearing and learning requirement, October 24:** retain unfinished chats, successes, failures, corrections and ordinary conversations across topics as eligible attributed learning sources. Reuse the original parsing/RAG approach while evaluating complementary summaries, structured memory and evidence-labeled lessons. Failed or untested logic must stay labeled; archived instructions confer no execution authority. Source retention, retrieval and model-weight updates are separate deliverables, with owner/privacy/secret boundaries and measured acceptance. No automatic trainer or unrestricted self-editing is enabled. Source findings, implemented protections and the next acceptance steps: [memory/Conversation_Learning_and_RAG.md](memory/Conversation_Learning_and_RAG.md).

**Plan 1.47 clarification:** the user reiterates eligibility across all topics, including failed and incomplete discussions. Derived learning must retain source ownership/revision/hash, outcome/evidence, separate privacy/secret admission, linked corrections and measured usefulness. Begin with retrieval, summaries and structured preferences/cases; evaluate optional training separately with the original model preserved. Current save API explicitly reports not_indexed. This is a document-only checkpoint, not a new implementation or phase completion; source remains37. At plan1.47 the unsupported-API fallback correction was next; it is completed at v38 above. Actual browser memory acceptance still awaits the saved localhost permission.

The user's five-stage universal reasoning proposal is reviewed in docs/reasoning/Universal_Reasoning_Design_Review.md. Adopt observable intent, confirmed constraints, plan/alternatives, checks and answer/artifact evidence; use archetypes as optional routing labels rather than proof of internal cognition. Keep direct questions lightweight and ask only material clarifications. Correct unproven diagnostic conclusions, schema/name assumptions and unvalidated security/protocol examples before using them as fixtures or training targets. No new model/runtime/training implementation is claimed.

## Deferred future track — interface organization and potential redesign

The user reports that AI-BS feels crowded/clustered and requests possible complete modernization of the site's CSS, navigation and overall layout, with corresponding native-app organization. Keep this AFTER completion of the current six-phase functional work and its required checks. It is a future optional design track, not permission to begin changing the interface now or a new completion gate for the existing goal.

Preliminary direction: one compact global header, grouped workspace sidebar, contextual workspace toolbar, favorites and searchable All Tools; consistent tokens/components, clearer primary actions, calmer visual density, accessible responsive/mobile/native layouts, and preserved AI-BS identity. Preserve all capabilities/routes, backend permissions, saved preferences, manuscripts and export formatting. Assess active versus obsolete code/mirrors before any consolidation; UI organization does not authorize file/data deletion. Findings, limits and staged delivery recommendations are saved in [UI_Modernization_Backlog.md](UI_Modernization_Backlog.md). No CSS or live layout was changed for this request.

## Revision record

- Revision 1.0: the six-phase sequence approved in this conversation.
- Revision 1.1: added local/offline proof, case-library and bounded-maintenance goals, perimeter acceptance tests, confidential reporting requirements, and evidence-based differentiation rules. No new daemon or maintenance schedule was activated by this document change.


## Phase 4 preparation checkpoint — revision 1.7

Completed two preparation tasks: `phase4/WINDOWS_VM_SETUP_PROPOSAL.md` and `phase4/ISOLATED_WORKER_CONTRACT.md`. They define the reviewed installation proposal and fixed worker/acceptance specification. These are documentation deliverables, not implemented VM protection. No install, purchase, reboot, restart or release occurred. Application remains v5.329.17. Next: review installation/licensing/media, then provision and implement the controller and run all pending VM acceptance cases.


Installation review: `phase4/WINDOWS_VM_INSTALL_REVIEW.md` pins Oracle base-package 7.2.22 and its official hash. Download/signature/install and guest licensing remain pending. User review is required for drivers; no automatic reboot, host network changes or purchase is authorized.


## v5.329.18 — VM-required requests fail closed

Implemented an explicit execution_backend selection in run_coding_task and tool-registry schema/forwarding. windows_vm returns a retained FAILED result with ISOLATION_UNAVAILABLE before worktree creation or any check; unknown backends fail rather than defaulting to the host. trusted_host remains the explicit legacy default. This is an unavailable-worker guard, not a VM adapter. 25 focused/regression tests and version consistency pass. No backend restart/live verification or publishing. The user confirmed they do not own a second Windows license; do not buy or assume guest entitlement. Installation approval and a valid guest licensing route remain unresolved.


## Live v5.329.18 guard verification

Completed 15 live API checks and 16 controlled FastAPI restart/access/document/service checks. VM-required requests return retained ISOLATION_UNAVAILABLE and no working copy or check; anonymous requests on both gateway/backend are denied; unknown modes cannot silently use the host. Review remains inspection-only and recovery does not replay the failed task. This proves the unavailable-worker guard is loaded in the running backend, not working VM isolation. No Firebase/native release or VM setup occurred. Licensing and installation review remain unresolved.


## v5.329.19 — isolated input validation component

Implemented pure `coding_vm_inputs.validate_vm_inputs` against an exact trusted-host admission: fixed IDs/base image/commit/authorization reference, paths/roles/checks/limits, input byte lengths and SHA-256 hashes. Unknown fields, credential paths, case collisions and scope changes are rejected. 37 focused/regression tests pass; no transport/controller integration or VM acceptance is claimed. VM-required calls remain unavailable. Driver installation question remains pending and the user has no second Windows license. No restart/publication.


## Evaluation option review

The user requested and confirmed review of the official 90-day Windows Enterprise evaluation option. See `phase4/WINDOWS_EVALUATION_REVIEW.md`. Temporary professional evaluation may avoid an immediate purchase, subject to actual terms and eligibility. Registration/activation, credential-free guest provisioning, expiry enforcement and separately reviewed host-driver installation remain pending. Do not equate review confirmation with acceptance of unseen terms or permission for host changes. Application remains v5.329.19.


## v5.329.20 — returned artifact validation

Implemented pure `coding_vm_artifacts.validate_vm_artifacts`: bind task/attempt/base image/input manifest, restrict output set and paths, verify bytes/lengths/hashes/size limits, and reject modified verification/dependency files. 45 focused/regression tests pass. This does not prove execution, issue a seal, perform filesystem collection or enable VM use. The next required real-guest integration/acceptance step remains blocked on reviewed host installation and a valid guest/evaluation setup. This condition has persisted through the v5.329.18, v5.329.19 and evaluation-review checkpoints; preparation does not resolve it. Full plan remains incomplete and no Phase5 execution/release is enabled.


## Evaluation media ready

User authorized taking over the browser download. Selected English (United States), ISO Enterprise, 64-bit on the existing official download page. The 8,225,329,152-byte ISO completed in Downloads and SHA256 exactly matches Microsoft publication. Media has not been mounted or executed. This resolves the media-download prerequisite, not license/terms acceptance, activation, driver-install approval or VM acceptance. See the handoff for exact file/report paths. Application remains v5.329.20.


## VirtualBox installed; worker identity next

User approved the reviewed VirtualBox installation with Yes and requested proceeding to next steps. Pinned 7.2.22r175245 is installed, with valid Oracle signatures and the core VBoxSup driver running. Optional USB/network/Python features are absent. Thirteen final checks passed; no reboot, host network change, service restart or document change. Guest setup remains pending because a verified ordinary worker context is not available: UAC is off and tested restricted child launches failed. See `phase4/STANDARD_WORKER_ACCOUNT_REVIEW.md` for the proposed standard local account and user-entered credentials. No account or VM created; no Windows EULA accepted. Application remains v5.329.20.


## Standard worker account setup approved, then unconfirmed locally

User approved the standard aibs_vm_worker account. Prepared and opened a syntax-checked local PowerShell helper requiring matching secure password input and human-entered CREATE. It reported CANCELLED because CREATE was not confirmed, and its process ended. Independent local account lookup found no account. No password recorded and no account/group change made. Do not automatically reopen a cancelled credential prompt; clarify whether the user wants to retry. Application remains v5.329.20.


## Standard worker account verified; ordinary process pending

Independent SAM checks confirm enabled aibs_vm_worker in Users only. Created a new ACL-restricted VM workspace and a protected identity probe; no source/document permissions changed. User must launch the probe as the worker and host must verify its actual token before any VM runs. VirtualBox installation and media are ready; guest configuration, licensing/activation, transport/controller, and live acceptance remain incomplete. No release or application source change; source v5.329.20.


## Ordinary identity verified; powered-off VM preparation pending

Seven independent host token/process checks passed for the actual human-launched standard worker. Prepared a fixed, syntax-checked offline base-VM setup helper; user must launch it as the worker. It never boots a guest. Only the verified ISO received a file-specific Read grant; its original ACL was retained. VM provisioning is not yet executed or verified. Guest terms/activation/controller and all live isolation cases remain pending; app source v5.329.20.


## VM preparation process-wrapper correction

First user-launched preparation stopped at version inspection: the short-lived native process returned the expected version but its exit code was unavailable through Start-Process. No VM/disk was created; empty first-attempt directories and all logs retained. Replaced the helper's wrapper with direct process ownership and recorded actual exit codes; four Windows PowerShell5.1 checks passed (three exit0/version reads, one actual exit2/error rejection). The separate base_preparation_v2 retry is prepared but not run. Guest configuration/terms/activation/controller and live acceptance remain pending. Source app v5.329.20 unchanged.


## Powered-off VM ready for first setup review

The standard worker created the fixed base VM; all12 real native commands succeeded. Sixteen host configuration/process/evidence checks passed. Network/sharing disabled, 4CPUs/8GiB, EFI/TPM2/SecureBoot and only the virtual disk plus verified ISO. These are preparation/configuration checks, not Windows installation or live isolation acceptance. A one-shot existing-token read-only launch was denied with WinError5; no privilege/desktop changes or retry workaround. Prepared a standard-worker-only first-boot helper that rechecks actual settings and media before opening the installer for human terms review. No terms accepted or guest boot yet; no release/app-source change. Source v5.329.20 remains; complete guest provisioning/controller and live acceptance before Phase5.


## First boot: installer not yet reached

Fresh worker checks confirmed the 64GiB dynamic disk and approved settings; the GUI VM started successfully under independently verified non-elevated worker tokens. DVD boot prompt appears to have timed out. After a manual warm reset, firmware logging stalled before Windows Setup. Exact cause unresolved. Preserved all logs/settings and added one explicit cold-start retry with distinct retained records and unchanged isolation checks. Human must power off only the stuck VM, then launch ColdBootAfterFirmwareStall and attend the DVD prompt. Retry not yet run. No security/driver changes, VM deletion, terms acceptance, activation, app-source change or release; source v5.329.20.


## Storage recovery checkpoint; reduce setup retries

Latest runas succeeded; strict preboot guard detected Guest Additions DVD and a newly active snapshot child. Preserved all snapshot/base/child/saved-state data and logs. Added explicit one-shot RestoreInstallerAfterSnapshot: pin the exact observed snapshot, verify real parent-chain and isolation, reconnect only the verified Windows ISO, then recheck before GUI start. Twelve Windows PowerShell5.1 parser/path/current-XML checks pass; native recovery has not run. Acknowledge repeated helper/setup retries and diagnose exact new evidence before more commands. Windows installation/terms/activation/controller and live acceptance remain pending. No release/app-source change; v5.329.20.


## v5.329.21 — real host-side admitted input staging

Implemented Windows handle-protected staging of exact approved byte sets into fresh retained task/attempt folders. Rejects altered inputs, collisions, junctions and duplicate attempts; failed partial attempts keep intent/evidence and receive no staged completion marker. Actual filesystem tests exposed and fixed an attribute-only handle rename gap. Thirteen new tests plus existing related regressions:58 unique tests passed; source AST/version consistency pass. Caller authorization/private ACLs, secret-content policy, bounded wire transport and guest execution are still required. Component is not yet connected to the fail-closed VM execution route. Media recovery has not run; Windows installation/terms/activation, controller and14 live isolation cases remain pending. Phase5/6 not enabled or released. Source metadata originals and all fixtures preserved.


## Windows installer now running

Removed a brittle historical error-string requirement while retaining actual VM/snapshot/disk/media/isolation guards. Seventeen focused helper checks pass. The user completed worker login; all six native storage recovery/start commands succeeded. Snapshot preserved; correct Windows ISO reattached. Native controls caught DVD boot prompt and Windows Setup loaded. User advanced installer, observed Installing Windows11 at11percent; child VDI reached4.41GB with active writes. Installation, terms/eligibility/activation, credential-free base preparation, controller and live isolation acceptance are still pending. Let guest reboot from its virtual disk; do not press a key to restart DVD setup. No app release/service restart. Source v5.329.21 unchanged.

## Current VM job: protected recovery, installation continuing

Installer reached77percent, then remained black without observed progress. Saved a full-state online snapshot AIBS_Installer_77pct_BlackScreen_20261023 (73cdeb79-50d5-418b-810c-e38840094ea4), preserving Snapshot1/base/prior child. Current child59e3fed5-5878-4524-8a70-9b0dc7a5067b. One controlled in-place GUI reset at23:23Z restored the Windows installation progress screen; no DVD boot key, host security/driver/network change or snapshot deletion. Root cause remains unproven. Finish and verify this installation/provisioning before the next test, per user instruction. Human credentials/license/privacy decisions remain handoffs. Task execution still fails closed; sourcev5.329.21, plan1.25, no release.

## Installation recovery: confirmed VirtualBox crash, worker login pending

Recovered installation advanced0 to42percent and performed its own reboot. VBox.log then recorded host process191976 exception0xc0000005 in VCRUNTIME140.dll with VBoxDD.DLL stack entries immediately after bootmgfw.efi loading; the Windows Application Error dialog independently matches the fault address/null read. This establishes an actual VirtualBox process exception, not a verified GPU fault or completed installation. All disks/snapshots/logs retained. No second assistant reset or unsafe configuration workaround. Official release notes list installed7.2.22 as current; related issue170 has different Qt/display stacks and does not establish this cause/fix. Prepared reusable standard-worker-only Open-WorkerVMManager.ps1, syntax checked and confirmed to reject the main account before launch. It opens the existing registry's manager only; no guest start/change. Actual worker launch remains untested until the user enters their password locally. Finish this job before the next test; do not enable expanded execution or release. Sourcev5.329.21, plan1.26.


**v5.329.43 checkpoint:** preparation UI/history source wiring and controlled live backend acceptance completed as above; full six-phase count remains3of6. Existing clear-before-archive protection and owner-scoped source retention are preserved. Successful/failed/incomplete/all-topic discussions remain eligible for source-linked summaries, retrieval and positive/negative cases after privacy/secret admission; model training is a separate evaluated step, not automatic on clear. Evidence, failed fixture approaches and exact runtime/preservation are in the latest handoff. No dependency/product React configuration change, VM restart, browser workaround or platform publication.


**v5.329.44 checkpoint:** backend grounded-planning prerequisite only; live main remains the source43 startup and UI integration is pending. No restart/publish44. See phase5/PREPARATION_PLANNING.md and latest handoff for exact25/26red-green evidence, real-model first-failure/second-success scope and preservation. Full phase count remains3of6, VM deferred.


**v5.329.45 checkpoint:** scoped planning UI and production API acceptance completed, source45/plan1.55. One main-only restart68264; other services/6disabled flags/documents/memory/model retained. Browser permission attempts remain tool-denied, no workaround. No generated project checks or Firebase/native publication, no additional whole phase complete. See latest handoff and phase5/PLANNING_CONTROLS.md.


**Plan1.56 browser-access diagnostic review, source unchanged45:** user proposed public tunnels/hosts alias after saved-origin denial and asked which browsers are supported. Read-only inspection confirms frontend/vite.config.js already binds127.0.0.1/strict5173 and the actual listener remains354960/127.0.0.1; backend health200. The PowerShell export error comes from JavaScript configuration pasted into the shell, not a proven Vite failure. Supplied Cloudflare logs establish a tunnel connection, not frontend reachability or browser authority. No tunnel/alias or alternate browser was used to route around the denied action, no configuration/policy edits/restarts/publication. Official browser docs list Chrome/Edge/Brave/Opera/Vivaldi plus built-in browser; extension browsers share site permissions. Do not claim a proven hardcoded localhost/SSRF block or that switching browsers clears it. Actual browser acceptance remains pending; next coding task remains retained multi-file proposal/diff, not yet implemented46.


**Plan1.57 operational checkpoint, source remains45:** The previous main/gateway/model/Vite processes are absent and all five service ports were stopped. Only Vite was restored, verified PID111384/127.0.0.1:5173 with unchanged config. Backend8080/gateway8000/Ollama11434-11435 remain stopped; browser-control connection unavailable in this session. No actual rendered/chat acceptance or public release is claimed. Restore required services under existing recorded safety controls before live chat checks. Keep VM deferred and retained multi-file proposal/diff as the next implementation task. Evidence: backups/localhost_restore_20261024T1406033034435Z.


**v5.329.46 / plan1.58 retained multi-file proposals:** Reviewed parent plans now produce complete-input exact-hunk candidate source and diffs, retained and independently authenticated, with stale-hash/role/edit boundaries, same-ID inspection, cancellation and recovery. Tests remain NOT RUN and execution/apply stay unauthorized. Retained28focused,69regression and13source observations plus55actual model/core/gateway observations pass; the real two-file Python/JavaScript fixture generated exact changes in57.797seconds and a separate running proposal was cancelled. Current services are loopback8080/332884,8000/116980,11434/165656 and5173/111384; gateway binary remains37, source metadata46. The initial stopped-daemon PID0 expectation was an observer error; this binary reports-1. Existing failure preserved; same processes re-observed without restart. All888selected documents/copies and personal rows unchanged; vault/master integrity/counts retained. No project code/check execution, browser acceptance, VM retry or publication. Next is frontend retained-proposal/diff review and recovery controls, followed by still-open isolated execution and release gates. Full goal remains incomplete; no additional whole-phase completion. Details: docs/phase5/RETAINED_PROPOSALS.md and backups/retained_proposal_5_329_46_20261024T141425139154Z.
