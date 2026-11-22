AI-BS Offline Wheel Setup v1

This read-only CD-ROM is limited to the existing current-user Python:
  %LOCALAPPDATA%\Programs\Python\Python313\python.exe
Required interpreter: Python 3.13.17, 64-bit, matching installation prefix.
Approved packages: psutil 7.2.2 and pywin32 312 only.

The operator must manually launch D:\AI-BS Wheel Setup.exe inside the dedicated
offline VirtualBox guest, then click Install approved wheels once. Do not launch
on the host. Do not copy it to another location. There is no autorun.

The helper refuses every other VM or host, elevated/non-medium accounts,
enabled guest NICs, unexpected files, linked paths, wrong media or wheel hashes,
and alternate Python paths/prefixes/versions. The fixed volume label is
AIBS_WHEELS_V1 and D: must be a CD-ROM.

One flushed attempt intent and an exclusive lease are retained under:
  %LOCALAPPDATA%\AI-BS\OfflineWheelSetup\v1
Any prior intent, including failure, interruption or corruption, blocks replay.
Do not delete intent/history to retry. Ask for a separately reviewed remedy.

If both imports and versions already match, pip is not run. Otherwise pip must
already be present and its effective configuration must be empty. No bootstrap,
ensurepip, Python/Node reinstall, elevation or user-site fallback is included.
The two pinned local wheels are installed without an index, dependencies,
cache or compilation; both imports and package versions are checked afterward.

Closing during work requests bounded shutdown. Timeout, output overflow,
interruption or uncertain results quarantine the attempt and prohibit retry.
Client termination is not proof that any descendants are contained or stopped.
The read-only output is bounded; retain the visible result for operator review.
Each bounded native result is also flushed to an exclusive local step JSON file
with numeric exit, stdout/stderr, deadline and timeout/output-cap facts. Raw
guest output must remain local. Closing before Install, accepted cancellation,
or any
unverified/failed result returns a nonzero process status. Normal GUI execution
returns success only after both package imports and versions are VERIFIED.
Cancellation and the flushed VERIFIED commit share one atomic boundary. An
accepted cancellation before that boundary prevents any VERIFIED commit and
quarantines the attempt. If the durable commit wins first, a later close is a
completed-before-cancel request and cannot be accepted as cancellation.
Reparse checks and held files do not prove adversarial directory-race isolation.

This helper grants no task authority and does not establish Windows licensing,
accepted-base, controller/transport security or Phase 4 acceptance. It changes
no accounts, security settings, networking, clock, licensing or VM settings.
