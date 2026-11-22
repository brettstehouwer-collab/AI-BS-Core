# FE Express driver source integration

T08 now has a standalone phone-oriented `/driver/` source entry, owner-bound
API registration, authenticated offline client and scoped public offline shell.
This is an **unreleased candidate based on source5.329.146**. Hosting146 and the
installed BS-Chat1.0 APK remain separate artifacts; neither contains a promoted
FE driver release.

Backend registration requires exact `AI_BS_ENABLE_DRIVER_PORTAL=1`. The running
backend was not restarted and the flag was not enabled. Shared FE PIN/workspace
routes are unchanged and do not grant driver ownership. Import does not open
storage. The existing verified administrator principal owns each server record.

The client enrolls the current Firebase UID through the authenticated identity
route. Previously enrolled work can reopen offline, including network loss when
the browser still reports online. Authentication denial, identity mismatch and
malformed identity responses never become offline admission. Each sync request
requires fresh identity/token checks, retains failed or conflicting work, and
checks attachment operation ID and original Blob SHA-256 before acknowledging.
Enrollment metadata and IndexedDB are not encryption or server authorization.

The work-only UI edits fourteen load fields, preserves raw dispatch notes,
provides immediate arrival/departure saves, bounded photos/PDF/voice evidence,
coalesced local saves, explicit sync and visible unsynced/conflict status.
Voice capture requires a user action; selection stays locked until its evidence
save finishes. Account changes revoke operations and clear the visible work
without deleting the previous owner's local database.

The `/driver/` service worker caches only build-pinned public shell resources.
It does not cache API/auth responses, tokens, documents or account data. Offline
preparation/storage persistence and update activation are explicit gestures; no
global Studio worker, automatic reload or account/provider setting was changed.

Actual evidence:

- Backend registration:12 synthetic HTTP checks passed using actual admission
  with mocked SDK verification and temporary storage.
- Final authenticated client:12 Chromium/IndexedDB checks passed.
- Composed actual UI:12 checks passed with synthetic auth/API and real IndexedDB;
  zero unexpected console/page errors.
- Scoped shell:12 checks passed, including real Chrome worker/offline behavior.
- Final combined Vite build exited0. Its10 shell pins total2,406,301bytes, with
  compiled shell version `76807d2e0bcd35806d2334bf30e578f2ea8cb7c9d11ecb5a71784c016deab069`.
  An additional11-check actual-build gate verified final byte hashes, real
  signed-out offline reload and exclusion of API responses from shell caches.

These are distinct profiles, not a new full regression run or real-owner
qualification. Earlier fixture/build failures and prior successful snapshots
remain retained. No inference, employer integration, financial connection,
reminder, routing provider, live feature activation or deployment occurred.

Next: compose the UI with the actual owned ASGI API in a controlled candidate;
complete remote record/evidence retrieval and explicit conflict resolution;
then qualify real-owner phone reconnect/process restart/reboot and deployment
separately. Personal payment evidence remains a separate owner-scoped workstream.
Truck dimensions/weights and GPS provider remain unconfirmed.

Later continuation completed remote retrieval, bounded verified evidence caching,
explicit conflict decisions and real UI/ASGI/temp-SQLite composition in a controlled
fixture. The corrected backward-compatible design uses a separate review database
and write-ahead confirmation; earlier reserved-row candidates were rejected.
Read FE_DRIVER_SYNC_2026-11-14.md for current proofs and remaining rollout/owner
gates. The earlier source profiles above retain their own dated scope.

Evidence: `backups/fe_route_integration_20261114_v01/`,
`backups/fe_client_integration_20261114_v01/`,
`backups/fe_ui_integration_20261114_v01/`,
`backups/fe_shell_integration_20261114_v01/`, and
`backups/fe_portal_integration_20261114_v01/`.
