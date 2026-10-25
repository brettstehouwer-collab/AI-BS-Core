# AI-BS Autonomy and Differentiation Plan

Plan revision: 1.29 | Updated: October 23, 2026 | Local application source: v5.329.23

## Purpose and current checkpoint

Develop BS-Chat into a reliable central workspace for code changes, creative production, business operations, and local automation. Prove useful workflows between these systems while preserving original work and proprietary methods.

**Latest operator decision: defer Windows VM setup.** Stop VM installation/recovery retries, login requests and monitoring until the user explicitly returns to that task. Preserve the existing VM, ISO, snapshots and evidence. This supersedes the earlier requirement to finish VM provisioning before doing any other work. Phase4 containment acceptance remains incomplete: VM-dependent execution, expanded host execution, unattended maintenance and releases claiming isolation remain disabled. Continue one bounded task at a time on work independent of the VM; do not substitute host execution for the missing worker.

Completed foundation: the existing Stehouwer model has generated a small Python change in a separate Git working copy, run a real test, and retained the result and diff without altering the original files. Administrator access and review-mode behavior have been checked. Phase 1 review/apply has since completed a real fixture application with a retained original backup and authenticated HTTP checks.

Current gate: Phase 4 Windows VM isolation feasibility. Phase 2 includes one actual Stehouwer repair of a seeded failing proposal using a real unittest error; both attempts remain retained. Phase 3 includes real fixture-worker termination during generation, unittest execution, and file application. v5.329.15 fixed concurrent repository application, verified retained originals/test evidence, and stopped stale inputs after inference. v5.329.16 adds an admitted inference worker with retained inputs/output, bounded lifetime and output, a 300-second admitted-request budget, and authenticated cancellation during initial generation, repair, and linked checks. A live HTTP chat request was cancelled while its real inference client was connected to Ollama, with no subsequent code execution. These trusted-host process controls do not isolate host files or networking, and server compute-release timing after client disconnection was not measured. The PC reports Windows 11 Home; VirtualBox and verified evaluation media are installed/downloaded, and a standard-worker VM exists. Windows installation, terms/activation and controller integration remain incomplete. Browser interaction and full VM/network/document isolation gates remain open. Attachment upload remains a separate issue.

Completed at v5.329.17: admitted tasks now retain raw input, hashes and a terminal failure record before source/path validation. Rejected proposals and actual errors are inspectable with Apply disabled. Cancellation during validation stops before worktree creation. The 42 focused tests, 12 live rejection/review checks, and 16 controlled service/document checks pass. Browser interaction and Windows VM isolation acceptance remain open. The user has now requested resuming one task at a time. The first resumed task restored the handoff opening from its hash-verified snapshot, retaining the overwritten copy; application files remain v5.329.17. Next is a concrete Windows VM setup proposal for review, without installation or broader execution.

Local application source is v5.329.23. The previously published Firebase UI was v5.329.9 at last verification; the native Windows release remains deferred. This plan revision does not publish either artifact. Detailed source, tests, live evidence, limitations, and save points are in `docs/CODEX_HANDOFF.md`.

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

VM-independent BS-Chat reliability continues one task at a time. The review card now has accurate verification evidence (v5.329.22) and separate server/task review sessions (v5.329.23). Next inspect the saved-task history list for the same server-switch identity issue and refresh behavior after recovery; prove a specific defect before changing it. No generated-code execution, VM start, model inference, document mutation or publishing is required. Larger-project preparation may follow in separate tasks, while actual expanded execution and its release remain gated by Phase4. Attachment-upload repair remains separate.

Completed the bounded evidence-display improvement at sourcev5.329.22: review cards distinguish no checks, recorded success, failed/interrupted checks and incomplete evidence; display the recorded/requested execution mode; and expose timeout/cancellation/output-limit/process errors alongside separated stdout/stderr. At sourcev5.329.23, server/task changes remount the review session, clear stale proposals/errors/tokens, abort obsolete reads and isolate late apply replies. Loading is explicit; missing tokens, mismatched responses and invalid task IDs cannot offer Apply. Thirteen actual-browser React cases with simulated backend replies and15 prior rendering/integration/parity checks pass. Backend apply authority is unchanged. No live API run, wider-project test or deployment is implied. VM work stays deferred.

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
