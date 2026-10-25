# Standard-worker Windows setup channel

October24,2026 / operational plan1.62 / source5.329.48.

The saved recovery VM has reached Windows OOBE. `Start-WorkerSetupChannel.ps1` is a temporary setup UI control channel, separate from the still-unaccepted generated-code task controller and artifact transport in ISOLATED_WORKER_CONTRACT.md.

Launch once in the existing authenticated `aibs_vm_worker` PowerShell session:

```powershell
& 'C:\AI-BS\isolated_workers\windows\control\Start-WorkerSetupChannel.ps1'
```

It checks the worker SID/nonadministrator/medium integrity, Oracle signature and current saved VM/disk/snapshot/isolation. An exclusive file handle prevents overlapping setup channels. It creates a fresh UUID directory with a protected ACL for the worker, local operator, SYSTEM and Administrators. It records PID and creation time, heartbeat, immutable requests/intents and each VBox operation. Only fixed resume/capture/save/stop and seven navigation keys are accepted. No text entry, shell/F10, snapshot restore, reset/poweroff, network/sharing change, file transfer or generated execution is exposed.

The operator-side Send-WorkerSetupRequest.ps1 verifies the live worker PID, creation time, SID and fresh channel status before writing an exclusive atomic request. Requests require exact session, sequential integer1..128 and timestamp within60seconds. Extra/missing/duplicate/escaped fields fail closed. A key binds to a frame under60seconds old and immediately recaptures the guest to require identical image bytes before sending its fixed make/break scancodes. A changed frame prevents input. The source script/helper hashes are checked throughout the loop. Completed intents are never replayed; a new process requires a new session and verified SAVEDguest state.

Maximum lifetime20minutes/128requests; idle90seconds. On stop, idle, lifetime exhaustion or operation error, independently revalidate the exact isolated guest, save if running, and verify SAVEDstate. Failed preservation is recorded as PRESERVATION_UNCONFIRMED and requires fresh inspection. The controller does not power off or blindly operate on a mismatched guest. It cannot recover itself from abrupt process termination; inspect retained intents and current VM state before any restart. Automatic save is not hard containment of an externally killed setup process.

Review screenshots after each action. Do not accept Windows terms, type credentials, bypass setup requirements or enable networking based on a guessed screen. This limited channel deliberately cannot finish account/password entry. Use a separate reviewed provisioning action or direct operator input when such a screen is reached. No actual Phase4acceptance case is passed merely by starting this channel.

Local verification:36schema/key-map cases,6actual-dispatch/finalizer cases with fake VBox operations, Windows PowerShell syntax checks and wrong-account denial. Actual worker ACL/lease/heartbeat/dispatch/saved-state behavior still requires live observations; fake operations are not live VM evidence.
