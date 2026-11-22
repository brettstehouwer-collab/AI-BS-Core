# Personal-finance phone interface — source and controlled composition

T10 now has a dedicated `/personal/` entry and `build:personal` profile. This
profile compiles only personal-finance assets, without copying the unrelated
public asset tree or modifying Studio/chat/driver profiles. The existing Firebase
account, verified administrator allowlist and backend financial-owner authority
remain in use. A personal-only Google sign-in screen replaces the shared login
component's company-specific phone affordance; no provider configuration changed.

The phone interface records payments with their explicit work week, payer/source,
transfer references, notes and load references. It lists manual transfer totals,
preserves selected original files locally before upload, lists/downloads linked
server originals and exports existing accounting rows by year. Transfer records
are explicitly separate from accounting income/expense exports and confirmed pay.
There is no account import, employer connection or tax/employment inference.

Personal drafts/files use a separate UID-specific IndexedDB, not FE work storage.
One Web Lock admits one writer tab per UID. JSON payloads and upload Blob/filename
remain saved with stable operation IDs before requests; a lost acknowledgement
can be retried after reload without duplicate rows. Only an acknowledged schema
rejection unlocks payment editing; network/uncertain failures retain the pending
operation. Acknowledged files leave the local upload queue while original server
bytes remain immutable. Requests bind the current Firebase user object, acquire
fresh SDK tokens, reject redirects/untrusted origins, omit cookies and stop on
account changes/401/403. Tokens and private response bodies are not cached.
Sign-out retains UID-specific drafts/files on the device; this is not encryption
at rest. Current opening requires successful online server admission. Full offline
personal-page reopening, standalone tax documents and broader financial filing
remain unfinished; FE's separately qualified offline work capture is unchanged.

Raw Unicode document names use an explicit URI-encoding header, decoded with
strict UTF-8 before existing safe-leaf validation. CORS source now includes
Idempotency-Key, X-Document-Name and X-Document-Name-Encoding in Go and FastAPI.
Origin lists/authentication are unchanged; running processes have not adopted
these source changes. Go's existing sensitive-fragment list does not contain this
route: financial admission is enforced in FastAPI. The original new Go test
incorrectly assumed gateway admission and failed; evidence is retained, and its
scope was corrected to actual CORS/credential forwarding rather than changing
the authority model. Backend financial admission remains independently required.

Controlled evidence:

- Actual phone React UI/FastAPI/SQLite/IndexedDB composition:12/12 passed in
  `backups/personal_phone_20261114_v04/receipt.json`. Only SDK verification and
  client sign-in are synthetic. Checks include reload survival, lost-ACK payment
  and document retries, Unicode originals, byte-equal downloads, actual separate
  accounting CSV, account separation, editable validation rejection, production
  FastAPI CORS, second-tab exclusion and untrusted-origin rejection.
- New Go CORS/credential-forwarding check:1/1 passed, receipt/logs in
  `backups/personal_phone_20261114_v03/go-cors-attempt2.*`. Existing passing suites
  were not re-audited. Initial gateway-assumption failure is preserved.
- Actual production Vite profile build:exit0, six emitted files. Compiled entry
  rendered at390×844 with the real SDK imports and existing CSP; Google sign-in
  button fits and meets48px height, no horizontal overflow. One compiled layout
  check passed; screenshot inspected. No real account sign-in or provider call.
- Owned browser/API/static fixtures closed normally; standing services unchanged.
  v01 accessibility-locator failure and prior v02/v03 passes remain preserved.

Source remains an unreleased5.329.146 derivative. Live personal flags remain off;
no Firebase deployment, service restart, native/APK replacement, private database
access or manual phone test occurred. Original14 scoped checks plus production
build do not prove full portal, deployment, offline finance or release acceptance.
Program ACTIVE/incomplete. Next: standalone financial/tax document intake and
source-linked yearly export composition, then reviewed combined rollout gates.

Scoped Drive backup verified: `1pBUGUyQ-ZRCGMCOqmnZ2B0zG82LJlQ2W`,229,579bytes,
33members including14 complete selected source/doc files, compiled personal
assets and reviewed synthetic evidence. Exact download and all member hashes/CRC
passed; existing parent/sharing preserved. Private records/databases and complete
project coverage excluded. Receipt:
`backups/personal_phone_20261114_v04/drive-verified.json`. This closing note is
newer than the archived checkpoint.
