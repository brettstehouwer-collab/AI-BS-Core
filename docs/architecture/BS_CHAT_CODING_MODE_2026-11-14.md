# BS Chat Coding mode — source checkpoint

## Final integrated checkpoint — November 14, 2026

Single synthetic gate: **156/156 passed**, all subprocesses exit0 and frozen code SHA-256 hashes unchanged. Includes14 distinct trusted-local/partial/restart cases; no tests repeated by the integrated gate runner. Runtime activation remains separate.

## Current trusted-local follow-up — November 14, 2026

The user explicitly selected **Trusted local checks** instead of requiring a VM for every task. This is a scoped architecture extension: isolated mode remains the default and never falls back. A trusted-host execution requires both `execution_backend: trusted_host` and `trusted_local_ack: true` on that particular request. It is same-account execution, not a filesystem/network sandbox. No machine policy or global legacy execution flag was enabled.

The retained candidate bridge now executes selected Python unittest, pinned Node tests and pinned npm CLI scripts as low-priority owned Windows jobs (20% CPU cap, 512MiB aggregate job memory, per-check/overall deadlines, bounded logs and descendant cleanup). Npm uses the selected existing script with pre/post lifecycle hooks disabled, offline mode and separate empty user/global configuration; the selected script itself may invoke a shell and trusted task code retains account privileges. Dependencies are not automatically installed or linked to live project directories. Missing selected files/dependencies/runtimes fail explicitly.

The check authorization binds the owner, source/proposal bytes, selected checks and mode in the retained input. Selected source, tests and dependencies are checked before and after execution. Complete bounded outputs are hash-bound in local check logs; small previews are labeled when truncated. `GET /mode/executions/{id}/checks/{check_id}` reads those outputs only for the authenticated owner. Syntax parsing is distinct from test execution; the installed Babel parser now checks JavaScript/JSX as data without evaluating candidate source ([official parser reference](https://babeljs.io/docs/babel-parser)).

Explicit review rechecks current original bytes, selected verification/dependency bytes, candidate bytes and Git commit. Runtime-authenticated results and short-lived review tokens prevent resealed public JSON from authorizing application. Apply uses the shared legacy repository lock, journals append-only signed progress, retains Windows native backups, then uses ReplaceFileW. Synthetic tests verified original byte backup, DACL/alternate-stream preservation, stale-source rejection and partial multi-file application without automatic undo. This is not global multi-file atomicity against arbitrary external writers. A backend restart invalidates runtime apply authority; preserved records can be inspected without automatic re-execution, and unconfirmed application records require attention.

Native and browser interfaces now display backend capabilities, offer explicit per-task local acknowledgement, discover saved preparations/plans/proposals/check records, poll running tasks without replay, and require an explicit reviewed Apply action. Disabled/unknown capabilities deny state-changing actions; native closed-dialog and browser account/backend changes retire stale callbacks. Existing defaults remain off: `AI_BS_CODING_MODE=1` for a later source backend/native launch and `VITE_AI_BS_CODING_MODE=1` for the candidate browser build.

Current validation: 28 proposal and 26 planning regressions passed after test-only short-path/bounded-handshake fixes. The stalled suite is resolved. Backend retained-candidate/syntax checks17 passed; native trusted-local23 passed; browser16 passed plus V03 candidate build (5,697 modules,22.05s). Actual trusted-local Windows tests passed12 cases plus one focused partial-application case; a final restart-after-application case is recorded separately in the V02 checkpoint. All use synthetic repositories and mocked inference, not execution or application against live AI-BS source. Failed MAX_PATH, rename-sharing and npm-config evidence remains retained.

Production services were not restarted or promoted. A closing read-only check returned200 from backend8080, gateway8000, frontend5173 and Ollama11434; it sent no inference request and does not establish per-message chat success. The pasted challenge transcript has no event timestamps: its 404/context/transport failures cannot all be declared superseded by the separate successful transport receipt. Its scheduling optimum is14minutes, not12.

Current checkpoint: `backups/bs_chat_coding_mode_20261114_v02/checkpoint.json`. Live native/browser owner acceptance, real coding-model quality, installed packaging and opt-in activation remain separate. Isolated execution still requires an accepted worker. FE portal/GPS/personal finance are ACTIVE_IMPLEMENTATION_AUTHORIZED per the later master directive; historical paused notes below describe earlier scope only. No FE account/provider activation or implementation occurred in this coding task.

## Historical V01 source-only checkpoint

Status: source implemented and focused candidate checks passed; execution/application and live acceptance remain incomplete.

The approved addition keeps BS Chat as the interface and adds opt-in Coding workspaces in browser and native Studio. Both reuse the existing owner-scoped preparation, planning and exact-hunk proposal journals. Python and JavaScript/React files use the existing structured Python unittest, Node test and npm script profiles. Placeholder npm scripts now reject at admission. Required current dirty source is captured rather than replaced with HEAD. Existing provider/model selection is unchanged.

## Interfaces and behavior

- Backend `/api/chat/coding-tasks/mode/capabilities` reports current availability. Other `/mode/executions` operations require `AI_BS_CODING_MODE=1` and independently authenticated preparation ownership.
- POST `/mode/executions` accepts `execution_id`, `request_id`, `plan_id`, `proposal_id`. It reconstructs a retained candidate from confirmed proposal bytes and immutable selected inputs. GET `/{execution_id}` and POST `/{execution_id}/review`, `/recover`, `/cancel` inspect retained evidence without inference replay. Recovery seals incomplete staging as INTERRUPTED. POST `/apply` rejects while no qualified execution exists.
- Python AST results are syntax evidence only. JavaScript/JSX parsing and all project checks remain not_run. Candidates remain BLOCKED; no review token or application permission is manufactured.
- Browser opt-in is `VITE_AI_BS_CODING_MODE=1` at build time. Native opt-in is `AI_BS_CODING_MODE=1` at process launch. Defaults remain off. These instructions describe later candidate setup, not activation performed in this session.
- Native uses the existing EngineBus; no parallel scheduler was added. Browser preserves backend/account context for asynchronous responses. Task IDs and recovery controls retain existing evidence rather than replaying interrupted generation.

## Validation

- Backend: 13 focused checks passed (10 retained-candidate/API/tamper/recovery/ownership checks and 3 npm admission checks).
- Native: 12 synthetic checks passed in Qt with recovery dependencies available, including real EngineBus delivery/drain; final diff rendering checked. The standalone Qt environment lacks httpx; disabled ordinary chat no longer imports the coding service, and transport import is deferred until an explicit request. No dependency installation occurred.
- Browser: 4 utility/SSR checks passed, including Plan hiding code-proposal generation. Direct opt-in Vite candidate build passed, 5,696 modules, 21.83 seconds. Existing mixed Firestore import/large-chunk warnings remain. Production dist was not rebuilt.
- Existing preparation regression: 29 passed. Broader proposal suite did not complete: initial fixture environment/path errors were retained; corrected broad run stalled over five minutes and only its exact owned Python processes were stopped. No broad proposal-regression pass is claimed.
- Synthetic native raster inspected. All existing 16 creative executable/dependency pins match current bytes; neither manifest nor pinned engine files changed.

Evidence: `backups/bs_chat_coding_mode_20261114_v01`, `backups/coding_mode_native_20261114_v01`, and separate browser candidate build directory. Earlier test fixtures/failures remain. Scoped local source preservation is distinct from Drive upload or verified restore; no new Drive checkpoint is claimed.

## Remaining work and next step

The existing phase4 VM boundary review records no accepted disposable standard-worker execution environment. This change does not activate or reconfigure that environment. Full plan completion requires a separately reviewed and qualified runner/receipt bridge for Python and web checks, then sealed explicit application with fresh source/test hashes and retained backups. Until then the interface supports preparation, plans, proposals and honest blocked verification, not end-to-end tested application.

Next: qualify the source candidates in a separately scheduled authenticated native/browser session without replacing running services; resolve the retained broader regression stall. Review a concrete isolated-worker profile under the existing VM hold before any expanded execution. Then connect verified results to the existing review/apply protections and qualify stale-original rejection end to end. Other repositories remain a later configured-policy extension; current project registry is AI-BS only. Ordinary chat, real model answers, installed releases, hosted deployment and full-release qualification remain separate gates.

Architecture decision: extend the existing coding journals and EngineBus rather than embedding OpenCode or adding a scheduler. Standalone OpenCode configuration and the optional hosted worker are unchanged. No services were restarted, credentials/private databases read, model requests sent, VM settings changed or original project changes applied by Coding mode.
