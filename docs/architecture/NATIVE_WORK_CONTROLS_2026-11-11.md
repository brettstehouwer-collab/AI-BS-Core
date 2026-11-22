# Native work controls, local proposals and pre-write recovery

November 11, 2026. Separate user-authorized implementation while the original ten-goal program stays paused. This extends current source; installed Studio107, held Studio143 packages, shortcuts and existing provider selection are unchanged.

## Available entry points

- `scripts/Launch-AI-BS-Work-Controls.cmd` opens a standalone native source application using the verified Qt interpreter. It controls its own queues, not a different running Studio instance.
- Current source BS-Chat and System Health have **Background batch controls** buttons sharing one controller per application. BS-Chat's existing **Open Terminal** / `/terminal` action opens the embedded streaming terminal.
- `scripts/Configure-AI-BS-Privileges.ps1` performs a preflight by default. `-Launch` opens the verified source entry; optional `-Elevated` uses normal Windows UAC only when needed. The original pasted `ai_bs_ide.py` path is absent. No recursive ownership/ACL/attribute changes, global execution-policy changes, registry elevation flags or persistent environment changes are applied.

The current account was verified administrative and the project root is owned by Administrators. The supplied blanket-permissions deployment was not executed: it would modify preserved private stores and restricted fixtures, and target nonexistent entry points. PowerShell child commands use the explicitly requested `-ExecutionPolicy Bypass`; this does not grant a Windows token or change machine policy.

## What the controls govern

| Path | Implemented behavior | Boundary |
|---|---|---|
| Registered child-process batches | Worker cap, jobs per batch, minimum start gap, inter-batch cooldown, pause/resume, owned-tree cancellation, per-job deadlines, bounded output | Existing Windows suspended-create JobObject owns children before their first instruction. Not filesystem/network isolation. |
| Shared native EngineBus | All submit/dispatch work can be paced, capped, grouped, paused and have waiting tasks cancelled | Default immediate behavior remains until controls are used. Running callables finish cooperatively. |
| Embedded terminal | PowerShell/WSL runtime selector, working directory, explicit command queue, streaming output, pacing, cancellation and failure halt | One foreground shell at a time. A new command never kills the current one. Arbitrary explicit operator commands have no synthetic confirmation or path blacklist. |
| Existing backend, provider, GPU, server and real-time engines | Existing resource/admission/authorization rules retained | These independent execution paths are not globally throttled merely by changing a native queue setting. |

The process pool accepts trusted explicit executable/argument specifications; its initial registered UI operations are read-only Python source checks and version checks. No generated shell command is executed from a model response. Shared controls do not turn on unrelated work. Worker limits are admission limits, not hard OS CPU/GPU utilization quotas.

Two consecutive equal nonzero process-job exit codes halt further process admission. Terminal failures are tracked by command, runtime, directory and error code; two consecutive identical failures halt its queue. Active jobs are not silently killed by a throttle change. Reset/resume is explicit and no automatic retry, model rotation or paid fallback is introduced.

## Terminal lifecycle and output

QProcess supplies asynchronous transport to a local pure-Python helper. The helper starts the real shell suspended inside an owned Windows JobObject, then streams helper-framed output. This avoids the race of assigning an already-running QProcess shell to a job. Child output cannot forge helper control messages. Separate incremental UTF-8 decoders preserve split characters; display and queues are bounded.

Success requires both a trusted drained-child result and the actual helper's normal zero exit. A command's zero exit cannot hide a crashed helper. Closing Studio waits for the native task pool, process queue and terminal to drain. Unproved cleanup retains an attention state rather than destroying owners.

WSL argument construction is tested, but the host currently reports Class not registered. Windows helper/process drain does not prove termination of arbitrary Linux-side descendants. Actual WSL execution remains unqualified.

## Explicit local single-file refactoring

The local-refactor tab submits one selected Python source to one selected loopback Ollama origin on11434 or11435. It uses the existing local inference/GPU admission contract, temperature0, bounded context and a stateless source-only prompt. The primary BS-Chat provider configuration remains unchanged. There is no cloud fallback or replay through another endpoint.

Exact original bytes are committed to a private additive SQLite journal before inference. The journaled source hash is checked again before dispatch, so a source changed between snapshot and read is rejected without a model request. A proposal requires a verified completion/model/origin receipt, valid encoding and Python syntax. Candidate bytes are committed before optional export to a new file. Existing files cannot be overwritten by the proposal-export action.

Temperature0 does not establish determinism. Syntax validation does not establish public-API or semantic equivalence. The current proposal limit is32KiB of source with a conservative context budget; oversized input fails without truncation. This is not an activated30-day unattended refactoring/automatic-commit service. No real generation was requested during this implementation.

## Editor preservation

BS-Chat's explicit scratchpad and last-code-block save methods now use `editor_file_store.py`. The existing master database must open successfully with checked WAL/FULL settings; a missing master is not silently replaced. The helper commits exact original bytes, draft bytes, hashes and owned staging/backup paths before target changes, then checks the loaded/current state again.

Existing-file promotion uses Windows ReplaceFileW with flags0 and retains an original backup. Isolated NTFS checks cover original bytes, DACL, creation time and named streams. New-file creation is exclusive. Failed stages, partial replacement evidence and journal checkpoints remain available; reading recovery does not replay a save. The UI distinguishes a pre-write failure from bytes promoted with a failed final acknowledgement.

These are concrete recovery boundaries, not a universal zero-loss guarantee. SQLite serializes cooperating saves; it cannot provide an OS-global compare-and-swap against arbitrary external writers. Filesystem/storage failure remains possible. Existing screenplay, manuscript and chat recovery contracts remain authoritative; they were not bulk-migrated or rewritten.

## Evidence and retained failures

Evidence root: `backups/native_batch_controls_20261111_v01`.

Final combined qualification: **113 tests passed in24.251seconds**, recorded in `combined-final-tests.log`. This includes actual Windows processes, native task/close barriers, local synthetic proposals and SQLite/file recovery. It does not include a genuine model answer, private-master migration, WSL execution or frozen-release qualification.

- Real Windows process tests exercised concurrency, live cap reduction, pauses, pacing, cancellation of descendants, output/deadline bounds and repeated-error halt.
- Native admission and existing shutdown regressions exercised actual short callables and pool joins. Window-close methods were tested on inert owned Qt windows with the new process/terminal barriers.
- Local-proposal tests use injected synthetic inference; the actual backend settings adapter was separately checked without HTTP, leases, database access or generation.
- SQLite/editor tests use synthetic databases and files; no private master database was opened during verification.
- A real source controls window ran two registered source children and an explicit harmless PowerShell command. Final receipt `gui-final-v03.json` records command0/helper0/normal-exit/drained, exact expected output and zero queued/running jobs. Local-refactor controls were inspected without submitting a request.
- The production standalone source launcher was observed opening and closing normally; small-screen layout uses the existing screen-fit helper and scrolling controls.

Earlier failures remain: absent PyQt in recoveryPython for GUI hosting, Qt signal name `event` colliding with a virtual method, a source GUI hidden by startup settings, unreadable inherited control colors, a buffered daemon stdin watcher crashing at helper shutdown, and an initial snapshot-before-inference race. The test-only visible Windows Terminal error2147942632 came from a synthetic Start-Process missing Hidden; its corrected test proved child cleanup without new Windows Terminal/OpenConsole identities.

## Remaining qualification and preservation

No installed Studio107 or held143 artifact was replaced. No public deployment, business operation, campaign, model request, original manuscript edit or mass refactoring occurred. The new source changes shared engine dependencies; existing pinned creative-launcher/source manifests require reconciliation and requalification before reuse. Frozen/package/import parity for the new controls and genuine local generation remain open.

The server repair is separate: see `NGINX_CLOUDFLARE_RECOVERY_2026-11-11.md`. Publishing HTTPS was rechecked200 after the native work. WSL/HLS, tunnel reboot persistence, untested public aliases and whole-control-center parity remain open. Scoped source/checkpoint preservation is distinct from full saved-data recovery.


## Release144 launchers and recovery-history save — November 11, 2026

The long-term ten-goal program remains **PAUSED**. Separately authorized release/recovery work: Firebase static5.329.144 is verified live, preserving816existing media hashes. Current native144v02 static429-file package passes; normal direct GameDevelopment startup visibly opens the correct workspace and closes normally. Packaged WorkControls opens and actual version-metadata child passes exit0 with drift[]. New currentAdministrator desktop entries **AI-BS Game Development** and **AI-BS Work Controls** have exact target/argument readback; originalfootb shortcuts/releases/saves remain preserved. RootCMD launchers and user guide are in docs/game_engine/UPDATED_GAME_TOOLS_2026-11-11.md.

Controlled creator/save/freshreopen/viewports/saved-player qualification is v01 unchanged-implementation evidence; only five app startup lines differ for v02. No full new gameplay, model, clean-machine/signing or every-subsystem qualification. Executive service showed unavailable in the normal shell; listener status is not workflow acceptance. Original profile C:/Users/footb remains the user-identified recovery authority.

All supplied recovery folder/Drive references, including sensitive path references, are being saved to docs/architecture/AI_BS_RECOVERY_SOURCE_HISTORY_2026-11-11.md and.json. Registration is distinct from content review or copy. The ongoing BS game folder1siuY6PGT0MFtfzFN6SWsgtgTyhHt9d6m retains its existing shared permissions. Current source/log/history/handoff and clean runtime archives have separate manifests; final upload/readback/hash receipts are linked from docs/agent_sync/current_long_term_goal.json after verification. No whole-profile/saved-data synchronization claim. Private authored material unexpectedly present in DIRECTORY_INDEX.md is not copied into the shared source-history package.

Next on explicit goal resume: reconcile current shared-engine/creative-launcher pins, then authenticated creative edit/save/reopen/export. Preserve ordinary human pacing/captions/likeness, signing/clean-machine/fullparity/Nsight gates and all failed evidence. No manual gameplay requests. Final observations: docs/agent_sync/RELEASE144_FINAL_SAVE_2026-11-11.json. Backup verification follows as a separate receipt; the snapshot does not claim to contain its own later receipt.
