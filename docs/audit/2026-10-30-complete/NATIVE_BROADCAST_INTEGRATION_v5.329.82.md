# Record207 — Native broadcast integration / v5.329.82



Updated 2026-10-31T19:15:33.197891+00:00. **Full-system audit remains IN_PROGRESS.** Live trading remains disabled. This record covers the shared native broadcast coordinator, game selection, capture ownership, IPC security and release verification. It does not certify every game, tab, button or workflow.



## Current acceptance and release state



The final reviewed suite passes **298 tests across 19 groups**, with zero failures, errors or operational guard denials. The only permitted sockets are the pinned standard-library Windows asyncio self-pipe: 24 socket creations, 12 loopback binds and 12 loopback connects. No operational network socket was admitted. A prior 296-case run failed with seven strict self-pipe guard denials; its diagnostic log remains preserved. That was a harness boundary failure, not a production failure or a silently ignored result. Another 23 build/signing fixtures, TypeScript `--noEmit` and the v82 version checks passed; these counts are not added to overlapping cohorts.



Stage2 Windows compilation exited zero at 19:12:39 UTC after a HUD/preset semantic defect was corrected. Stage1 is retained and was not installed. Stage2 was also retained uninstalled after a preset-label clipping issue was found. Compact labels and a width regression are being included in Stage3. **Final Stage3 PE/PYZ verification, installation and activation are pending the root release receipt.** No new Windows installation or Firebase deployment is claimed by this draft close.



At 19:16:14 UTC the same coordinator46560 / encoder44780 automatically acquired the user-reopened Fortnite window: `source_mode=auto_game`, `capture_state=capturing`, `game_frame_verified=true`, `VERIFIED_GAME`, frame8951 and media298.389 seconds. No source-selection request or runtime restart was sent when the game opened. This verifies one actual automatic game acquisition after safe no-game holding. Independent fresh end-to-end HLS acceptance passed at 19:18:30–34 UTC: local and public playlist sequences advanced211→213 while encoded frames advanced13064→13156. Segment218 matched exactly at1,085,136bytes and SHA256 `f74898594ecfdca0498379b839cc6a08ee4863baa7f4549fde549852d02ac085`. CPU software decoding verified H.2641280×720 plus AAC stereo and a real Fortnite lobby/game frame, without desktop capture. All192,000 decoded audio samples were exactly zero at48kHz stereo. The initial urllib403 probe remains preserved; a requests no-cache fetch succeeded without any source/service/capture change. The observed public playlist was [native HLS](https://stehouwer-publishing.com/hls/native/index.m3u8). This verifies public HLS at that time; RTMP platform dashboard acceptance is not newly certified. Earlier manual exact-window override was verified. Audio is generated silence; microphone capture was not requested.



The retained 19:12:27 UTC observation showed advancing holding frames because the earlier game HWND/PID no longer existed. The repaired catalog already included its Content installation; that was safe holding, not a second catalog failure. Synthetic multi-launcher cases and this single real game do not certify every game.



At 19:12:57 UTC an empty dummy legacy start request was held before dispatch with `COORDINATOR_ACTIVE`; modern encoder44780 remained active and advancing. The inert old control service was deliberately replaced by PID35720 for this guard check. This verifies the coordinator-active dispatch boundary, not general authentication of every older localhost endpoint. Facebook output rejection was observed during Record206 and is not claimed resolved by this coordinator change; fresh platform-dashboard acceptance remains open. Public HLS is independently verified below; RTMP platform dashboard ingest and archive finalization remain separate acceptance requirements.



## Critical / High risks and applied remediation



| Finding | Result | Evidence / remaining boundary |

|---|---|---|

| Shared source-change mailbox allowed writes from other authenticated Windows users. | REPAIRED and verified on controlled Windows ACL fixtures. | New protocol2 IPC uses OS LocalAppData `AI-BS-Private/BroadcastIPC`, protected current-user/SYSTEM owner/DACL checks, strict bounded JSON and session-scoped source/Stop requests. Shared legacy status is read/Stop-only and cannot promote itself to modern source control. |

| A stale selected game or implicit foreground/desktop fallback could expose another application. | REPAIRED, focused offline and manual WGC acceptance. | Exact HWND, PID, process creation time, executable and raw title are pinned. Manual selection has priority; identity loss/change, stale discovery and unsupported screen intent clear and hold. Browser, launcher and known auxiliary executables are excluded from automatic selection. |

| Late WGC startup/cleanup could authorize overlapping providers or falsely acknowledge stop. | REPAIRED with RED/GREEN race fixtures. | One owned asynchronous handover worker supplies holding frames during readiness. The stop path rechecks retired/pending resources after joining that worker; unconfirmed resources retain ownership and dispatch leases. |

| Catalog/filesystem stalls could block video or control requests. | REPAIRED with blocked-worker fixtures. | One owned discovery sampler publishes immutable cached evidence. Reads are nonblocking and expire from sample start time; late or old-intent results cannot refresh stale evidence. A stuck OS operation remains owned rather than creating replacement workers. |

| XboxGames/Content installations were absent from AppModel-only discovery. | REPAIRED, 58 guarded selector/sampler cases. | Generic observed RGBX v1 `.GamingRoot` registration and bounded one-level `Content/MicrosoftGame.config` identity discovery were added. A GDK launch bootstrap is not treated as the exclusive child-game executable. No game-specific title or actual executable whitelist was added. |

| Another encoder could start through legacy control while the shared coordinator owns dispatch. | REPAIRED at the coordinator-active boundary; actual dummy check passed. | Active modern encoder remained advancing; ordinary HTTP JSON cannot provide the internal secondary capture object. |

| Repository and shared-data directories still grant Authenticated Users Modify. | HIGH OPEN. | Private IPC closes its direct cross-user command surface. It does not secure the whole elevated application when other accounts can change repository source or binaries. A separate permissions review remains required. |

| E storage/key custody is unreadable. | HIGH OPEN; C fallback retained. | No E retry, replacement key or substitute recovery format was attempted. Encrypted source/binary cloud recovery remains blocked. |



## Medium / Low risks and controls



Incomplete Win32 writes previously replaced an existing IPC command with truncated data. Two failing controlled fixtures proved the loss; the writer now checks the Win32 error and full byte count before atomic publication, flushes the file, preserves prior bytes on failure and cleans only its owned temporary file. Independent GREEN2 and real Windows ACL roundtrip evidence are retained.



Persisted failed status no longer permanently disables retry: explicit Start can retry only after the fixed owned-controller scan under the startup mutex. A dead private status record cannot hide an independently verified legacy sender. Source changes require fresh owned status and matching request acknowledgements; a shared legacy record cannot self-promote by adding protocol fields.



The native view submits coordinator status/start/stop/source work through its worker bus. Source drafts remain drafts until Apply is accepted. Local preview scene changes no longer synchronously POST legacy services on the GUI thread. Desktop enumeration now closes its owned desktop handle on both success and exception, with pointer-width-correct HANDLE prototypes. Unsupported whole-screen capture and native coordinator video preview are clearly unavailable. Fixed output controls reflect the actual 720p30 H.264 / 4500kb/s profile; the audio mixer cannot claim microphone capture while audio is intentionally silent.



Known helper exclusions and installation provenance are conservative controls, not universal semantic game identification or executable authenticity proof. Additional healthy drives/libraries can be supplied explicitly; the new GamingRoot lookup defaults to the system drive and does not scan E. Every installed game has not been tested.



## Verification incident and recovery history



At 18:54:37 UTC an unguarded composition fixture escaped a `sys.modules`-only mock through the cached native package attribute and wrote the real legacy Stop request. Encoder11256 stopped. The earlier claim that the working stream was untouched applies only to its original timestamp and is not repeated for this record.



The correction patches both the package attribute and module cache and installs an operational-effect guard before Qt/native/test imports. The guard rejects real IPC/profile/database access, nonfixture writes, dispatch, capture, subprocesses and operational network activity, even when production exception handling swallows the guard exception. Controlled C fixtures and the exact public synthetic DPAPI literal remain meaningful tests; no operational credential is admitted.



The first deliberate restoration failed before dispatch with `IPC_OWNER_MISMATCH`. A fresh private namespace was used instead of taking over an existing foreign-owned parent. Actual protocol2 restoration was verified at 18:58:57 UTC with controller47936 / encoder41312, manual window capture, advancing media and silent audio. The subsequent Auto attempt initially held because Xbox registration coverage was missing; that failed evidence remains preserved. After the generic metadata repair, the catalog includes the game; the latest no-game holding observation is described above. No uninterrupted-stream or all-platform-live claim is made.



## Remediation code and records



The applied policy and cache are in [game_capture_selection.py](C:/AI-BS/backend/core/game_capture_selection.py) and [game_selection_sampler.py](C:/AI-BS/backend/core/game_selection_sampler.py). Capture ownership, publication checks and the secondary-only engine adapter are in [game_follow_capture.py](C:/AI-BS/backend/core/game_follow_capture.py), [broadcast_secondary.py](C:/AI-BS/backend/core/broadcast_secondary.py) and [aibs_broadcast_daemon.py](C:/AI-BS/backend/aibs_broadcast_daemon.py). Native IPC/control/UI changes are in [broadcast_ipc.py](C:/AI-BS/native_studio/broadcast_ipc.py), [broadcast_secondary_control.py](C:/AI-BS/native_studio/broadcast_secondary_control.py), [broadcast_control.py](C:/AI-BS/native_studio/broadcast_control.py) and [omni_broadcast_studio.py](C:/AI-BS/native_studio/omni_broadcast_studio.py).



Exact preimages, patches, source snapshots, RED/GREEN logs and independent review receipts remain on C. The final combined receipt is [receipt.json](C:/AI-BS/backups/native_broadcast207_work/guarded_native/run_1793474011251201000/receipt.json). The machine-readable companion is [NATIVE_BROADCAST_INTEGRATION_v5.329.82.json](C:/AI-BS/docs/audit/2026-10-30-complete/NATIVE_BROADCAST_INTEGRATION_v5.329.82.json). Four protected crypto/monetary file hashes match their baseline according to the final root verification. No live trading or microphone capture was enabled.



All Google Drive uploads remain in [the existing audit folder](https://drive.google.com/drive/folders/1yglgqXtK12MWL-6_9FaQ_I9OI44bhB2k). Root owns sanitized public uploads and their receipts. Encryption key identity remains `df96242fbdf6b117`; no key is uploaded or regenerated. Encrypted source/binary cloud backup is still blocked by unreadable E key custody. Private IPC data, credential profiles, `.env` and key-bearing screenshots are excluded from selected public records. Source commit and final installed-build acceptance remain pending root receipts.



## Same-folder public acceptance evidence

Four sanitized Auto-game artifacts are uploaded to the existing audit folder: [proof JSON](https://drive.google.com/file/d/1bJv5ruJ1oocOP_2VZ1eniUU6KBvxFZ6G/view), [verified game frame](https://drive.google.com/file/d/1vogXZvZ1DhCXxQwK6X2Apoiws-EJgHiz/view), [segment218](https://drive.google.com/file/d/1JmWtaI78ZYHxyHN9owT_huFriAX9FIBO/view), and [filtered status](https://drive.google.com/file/d/1146BQOb0de9SUkZOG8p6f2uXWWFIJmKl/view). Every parent folder, metadata size and raw downloaded SHA256 matches the corresponding local artifact. These are sanitized proof/filtered status and already-public game media; no source, executable, private IPC session data, key or E recovery material was uploaded. This public evidence upload does not resolve the blocked encrypted source/binary backup.


## Historical v82 acceptance result — superseded by corrective v83

Stage3 v82 was installed: all2,256 hashes matched and four shortcuts were retargeted. The frozen `--check-local-connection` diagnostic then timed out25s with an unhandled path error caused by MSIX LocalAppData physical-path redirection. Exact installation bytes did not establish functional acceptance. This v82 history is retained; final Record207 continues in [v5.329.83](C:/AI-BS/docs/audit/2026-10-30-complete/NATIVE_BROADCAST_INTEGRATION_v5.329.83.md). No new Record208 is claimed.
