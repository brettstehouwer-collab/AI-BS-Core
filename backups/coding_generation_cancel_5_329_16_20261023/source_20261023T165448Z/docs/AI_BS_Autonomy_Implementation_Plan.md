# AI-BS Autonomy and Differentiation Plan

Plan revision: 1.4 | Updated: October 23, 2026 | Local application source: v5.329.16

## Purpose and current checkpoint

Develop BS-Chat into a reliable central workspace for code changes, creative production, business operations, and local automation. Prove useful workflows between these systems while preserving original work and proprietary methods.

Completed foundation: the existing Stehouwer model has generated a small Python change in a separate Git working copy, run a real test, and retained the result and diff without altering the original files. Administrator access and review-mode behavior have been checked. Phase 1 review/apply has since completed a real fixture application with a retained original backup and authenticated HTTP checks.

Current gate: Phase 4 Windows VM isolation feasibility. Phase 2 includes one actual Stehouwer repair of a seeded failing proposal using a real unittest error; both attempts remain retained. Phase 3 includes real fixture-worker termination during generation, unittest execution, and file application. v5.329.15 fixed concurrent repository application, verified retained originals/test evidence, and stopped stale inputs after inference. v5.329.16 adds an admitted inference worker with retained inputs/output, bounded lifetime and output, a 300-second admitted-request budget, and authenticated cancellation during initial generation, repair, and linked checks. A live HTTP chat request was cancelled while its real inference client was connected to Ollama, with no subsequent code execution. These trusted-host process controls do not isolate host files or networking, and server compute-release timing after client disconnection was not measured. The PC reports Windows 11 Home; a compatible Windows VM platform and licensed guest have not been selected or installed. Browser interaction and full VM/network/document isolation gates remain open. Attachment upload remains a separate issue.

Next independent recovery fix: preserve a durable failed-attempt record when source/AST validation stops a task before worktree creation. Current generation output is retained, but the rejected attempt itself can lack `result.json`. Full Phase 3 acceptance remains open until that path is covered.

Local application source is v5.329.16. The previously published Firebase UI was v5.329.9 at last verification; the native Windows release remains deferred. This plan revision does not publish either artifact. Detailed source, tests, live evidence, limitations, and save points are in `docs/CODEX_HANDOFF.md`.

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

Complete Phase 1: authenticated review/apply operations, the BS-Chat review card, preservation and stale-state checks, and a verified application example. Keep attachment-upload repair and unrelated integrations separate from this task.

## Revision record

- Revision 1.0: the six-phase sequence approved in this conversation.
- Revision 1.1: added local/offline proof, case-library and bounded-maintenance goals, perimeter acceptance tests, confidential reporting requirements, and evidence-based differentiation rules. No new daemon or maintenance schedule was activated by this document change.
