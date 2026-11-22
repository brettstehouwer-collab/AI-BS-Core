# Personal page offline reopening — controlled checkpoint

T10 now emits a personal-only public shell manifest and service worker from the
dedicated production build. Six public HTML/JS/CSS assets are pinned by length and
SHA-256; manifest and worker make eight emitted files. Installation validates the
whole selected closure before caching. Only exact pinned static paths and the
supported clean `/personal/` or `/personal/index.html` navigation can be served
offline. Credentialed requests, API/auth traffic and query-bearing URLs bypass
the worker. It never stores financial responses, claims open clients, forces a
reload or deletes another build's cache. Updates wait until existing tabs close;
the UI reports installation/update status and asks users to finish saving first.

Successful backend owner admission records only UID/scope in the personal
IndexedDB. A later transport outage may reopen that same UID's local drafts and
queued original files. Server records/totals are unavailable offline; no private
response-body cache was introduced. New owner admission is required when no such
record exists. HTTP401/403 revoke local offline admission while preserving drafts
and original files;500 and malformed replies do not authorize fallback. Explicit
Reconnect personal access verifies with the server before server actions resume.
Metadata posts are disabled offline and queued-file requests fail locally without
dispatch. Draft edits continue to persist locally. Remote parent lists are not
cached, so new attachment selection against server-only records needs reconnect.

Offline admission is prior successful access, not a fresh revocation/expiry check
or encryption at rest. Existing Firebase SDK identity persistence remains its own
boundary; the new client does not add token storage. Real cached Google sign-in
on the user's phone is not yet observed. The controlled test substitutes SDK
identity and an owned transport bridge to the actual FastAPI/SQLite fixture.

Twelve focused checks pass in `backups/personal_offline_20261114_v02/receipt.json`:
production pin equality, actual worker installation/scope, admitted local data,
full offline reload/edit durability, no offline mutation dispatch, UID separation,
actual backend rejection clearing admission, fail-closed500/malformed responses,
public-only CacheStorage/credential bypass and corrupt/waiting update preservation.
Worker, IndexedDB, React UI and backend behavior are real controlled execution;
only identity/transport are fixture boundaries. All owned fixtures closed normally.

Production personal build exits0, canonical dist/live services unchanged. v01
retains an invalid CLI-root option attempt and the restored-textarea locator
failure. Explicit accessible names stabilize the restored notes fields; v02
passes the full focused profile. Earlier passing test files, system primitives,
backend auth, databases and providers were not changed or re-audited.

Source remains an unreleased5.329.146 derivative. No real private records, account
connection, deployment, service restart or APK replacement occurred. Program
ACTIVE/incomplete. Next: bounded larger-year export partitions, then combined
source/runtime/hosted release gates with preserved private backups and a clear
qualified launch path. Native, hosted and source versions remain distinct.

Scoped Drive checkpoint verified: `1NET_Wx8QjfJkgPUagQzvBUn0EIWvlHTy`,213,245bytes,
23members. Exact downloaded archive and all member hashes/CRC passed; expected
parent and existing sharing preserved. Private records/databases excluded; no
whole-project backup claim. Receipt:
`backups/personal_offline_20261114_v02/drive-verified.json`. This closing note
postdates the archived source snapshot.
