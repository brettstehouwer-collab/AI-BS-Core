# Legacy project-build execution review

## Source153 correction — November14,2026

Legacy build_project now preserves fixed maintenance dispatch and denies other
execution; run_existing_program is unavailable and generated programs require
explicit source-only flags before writes. No caller confirmation bypass exists.
Thirteen scoped checks pass; actual source-only scaffold/ZIP retained. Mounted
denial, UI presentation, live rollout and isolated-worker qualification remain
open. See docs/agent_sync/LEGACY_BUILD_ADMISSION153_2026-11-14.md. The following
review records the pre-correction behavior and remaining broader worker gates.

Status: SOURCE REVIEWED / GAP CONFIRMED / REMEDIATION PENDING. No untrusted repository, build command, model request or service activation was run for this review.

## Findings

- `backend/core/program_builder_engine.py` resolves existing absolute project directories and can execute caller-specified or repository-discovered commands through the host PowerShell path. Script/manifest detection includes repository build/install operations. Source/syntax checks do not isolate execution.
- Natural-language build recognition and explicit build commands survive in `backend/core/hybrid_reasoning_engine.py`; native `native_studio/bs_chat_ide_full.py` has direct legacy build calls.
- Current backend sensitive prefixes have verified administrator admission. This review does not prove anonymous public execution through the Firebase dashboard.
- The canonical fixed `backend/core/project_maintenance.py` lane intercepts supported default project actions. Custom commands and other projects can fall through to legacy behavior; the fixed lane must remain available for established authorized maintenance.
- Historical Host/VM handoff records a staged fixture, not an admitted disposable execution worker. A cwd allowlist, timeout or process job alone is not that isolation boundary.

## Proposed correction boundary

Keep known fixed host-maintenance operations and untrusted arbitrary-project builds as distinct typed capabilities. A request field such as `confirmed:true` is not trusted admission. Before an untrusted build can execute, the host-issued job must identify the admitted worker/image, exact source/test manifest, executable/arguments, resource/output/time limits, expiry, replay scope and returned-evidence contract.

Until an appropriate worker is accepted, return a truthful planning/review-only or unavailable outcome for arbitrary untrusted execution. Do not label host PowerShell a sandbox, silently route through a paid/cloud worker, or remove the existing known maintenance workflow.

## Remaining implementation and acceptance

1. Map every browser, native, natural-language, tool and direct API entrypoint to fixed maintenance versus arbitrary/custom execution; include attachment/model-generated commands.
2. Define the trusted root/source admission and exact operation schema, including symlink/reparse/ancestor and source-change handling. Do not treat all of C:\AI-BS as trusted code merely because it is the canonical checkout.
3. Implement the reviewed admission boundary without public PID/path/executable selection or unknown-command fallback. Preserve denial explanations and drafts/source files.
4. Test denied absolute/traversal/reparse/custom-script/manifest cases with synthetic command spies or inert fixtures; do not execute an untrusted repository to demonstrate refusal.
5. Qualify actual worker lifecycle and resource limits, process-tree cancellation, unknown remote outcomes, artifact quarantine, trusted tests and protected host apply as separate gates.
6. Requalify the existing canonical maintenance path so remediation does not break authorized local builds/restarts.

No new blanket confirmation gate is imposed on the user's already-authorized ordinary local development. Untrusted application-triggered execution retains its task-specific admission boundary.

## Current entrypoint matrix — scoped source review

| Entry | Current chain | Missing qualification |
|---|---|---|
| `/api/tools/execute` | Main administrator middleware -> ToolRegistry -> fixed maintenance first, then legacy build fallback | Custom/noncanonical source and execution admission |
| Chat `/build`, `/program build`, natural-language build | Administrator chat admission -> hybrid reasoning parser -> same tool registry | Exact per-job source/executable/resource authority |
| `/api/executive/run` build commands | Administrator middleware -> maintenance first -> legacy fallback | Same arbitrary/custom gap |
| Native `/build` | Local `bs_chat_ide_full.py` direct legacy builder | Bypasses fixed maintenance interception |
| Native `/program build`, `/app build`, `/builder build` | Local direct builder aliases | Same admission boundary needed |
| Tools `build_program`, `scaffold_program`, `create_program` | Generated files, optional custom command; build/run default enabled | Generated code is not trusted by schema/path validation |
| Tools `run_program`, `execute_program` | Direct saved-program runner | Saved-program location is not trusted code admission |
| Native `/program run` | Direct saved-program runner | Same saved-code boundary |
| Source `/api/artifacts/programs/build` and `/programs/run` | Direct builder/runner; main sensitive prefix exists if mounted | Actual router mounting unverified; no explicit registration found |
| Fixed chat system-tools scaffold | Known template and immediate smoke run | Keep fixed template distinct from arbitrary requested application logic |

Source anchors: `backend/tools/tool_registry.py` around5574–5610; `backend/core/hybrid_reasoning_engine.py` around157–201/1156–1161; `backend/AI_BS_Backend.py` around6182/6474–6499/9290–9292; `native_studio/bs_chat_ide_full.py` around1401–1473; `backend/routers/artifacts_sync_router.py` around119–147; `backend/core/real_system_tools.py` around200/240–246. These are reviewed source references, not proof that every route is mounted or a command was executed.

Sibling methods `build_program` and `run_existing_program` must be included in remediation. Fixing only `build_project` leaves those paths. Do not run `backend/test_project_build_execution.py` as a denial test: it intentionally executes temporary build scripts. Use inert spies for admission checks and keep actual worker/containment qualification separate.
