# Personal payment originals — source checkpoint

T10 now stores original document bytes against an existing owner-scoped manual
payment. `POST /api/personal-finance/payments/{id}/documents` accepts a raw body,
required Idempotency-Key and X-Document-Name. GET on the same path lists metadata;
GET with `/{document_id}` downloads an authenticated attachment. Registration
uses the existing exact `AI_BS_ENABLE_PERSONAL_PAYMENTS=1` gate, still off live.

The existing financial-owner boundary and accounting SQLite authority are reused.
Originals occupy an additive `personal_payment_originals_v1` BLOB table inside
that database. The participating writer uses existing WAL/FULL settings; its
transaction rechecks the payment owner, applies count/byte limits and commits bytes
with filename, declared MIME type, SHA-256 and timestamp. SQL triggers reject
updates/deletes through ordinary SQL, and no mutation endpoint exists. This is
application/database enforcement, not protection from an administrator dropping
triggers or modifying the database externally. New evidence uses a new operation
ID and retains earlier originals. Equal retries return the same metadata; changed
bytes or filename conflict. Reads never create a database or schema.

Bodies are bounded to10MiB each,20documents/50MiB per payment. Names are checked
using existing safe leaf validation and never used as filesystem paths. The
declared MIME type is retained as metadata; downloads always use octet-stream,
attachment disposition, nosniff and private/no-store. Documents are not parsed,
rendered, executed, sent to providers or treated as payroll/tax proof. Downloads
verify byte length and SHA-256. Broader standalone tax-document intake, original
document coverage, classification/search/OCR and the phone UI remain unfinished.

Twelve focused API/SQLite checks passed: byte equality after reopen, auth/PIN and
cross-owner rejection, retry/conflict behavior, retained versions, SQL/API mutation
rejection, actual-body/declared-length/empty limits, aggregate quotas with retries,
filename/key validation, active-content attachment headers, inert reads/missing
payment handling and SQLite online-backup restoration of originals/legacy rows.
Fixtures use synthetic SDK claims, temporary databases and synthetic documents;
no private database, original file, account or running service was accessed.

Evidence: `backups/personal_originals_20261114_v01/`. This remains source-only,
an unreleased5.329.146 derivative. Existing accounting/auth/frozen primitives and
their passing suites were not changed or re-audited. Full program ACTIVE/incomplete.
Next compose the personal-finance phone UI, document workflow and yearly export
with actual synthetic browser/API fixtures before any live rollout.

Scoped Drive backup verified: `1e36ahS8c3uYjyvwDDtuMx246Wl9H9oV_`,12,587bytes,
seven members. Exact downloaded bytes and every member hash/CRC passed; existing
parent/sharing preserved. Private databases/documents excluded. Receipt:
`backups/personal_originals_20261114_v01/drive-verified.json`. This closing note
is newer than the archived source checkpoint.
