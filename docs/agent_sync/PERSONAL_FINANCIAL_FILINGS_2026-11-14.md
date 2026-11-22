# Standalone personal financial filing — controlled source checkpoint

T10 now supports financial documents without a payment record. The personal phone
area captures document date, user-chosen filing year, source, document type and
original notes. Types are pay_statement, receipt, ledger, tax_document and
other_financial. These are user-assigned labels, not verified tax treatment.

`/api/personal-finance/filings` lists/creates append-only owner-scoped metadata
using the existing accounting authority and required idempotency keys. Its
`/{id}/originals` routes reuse the existing immutable-original byte store, quotas,
UTF-8 filename handling, hashes and download controls. Internal parent validation
now explicitly admits only personal_payment or personal_filing, retaining payment
as the existing default. The shared table's legacy payment_id column holds the
globally unique accounting-record ID; filing API metadata exposes filing_id.
Cross-owner and cross-family access remain rejected. No parallel original store
or live database migration was introduced; existing originals remain unchanged.

Personal IndexedDB retains a separate filing draft/pending operation and filing
file queue. A lost acknowledgement keeps the same operation ID and original Blob
for explicit retry after reload. Pending filing uploads are excluded from the
payment-specific queue display. New filing inputs remain disabled until the saved
draft has loaded. Existing payment drafts/operations and UID isolation remain.

The existing V1 yearly ZIP remains unchanged. New
`/api/personal-finance/exports/{year}/complete.zip` produces V2: accounting/payment
records use their recorded dates; standalone documents use the explicitly assigned
filing_year. The same read transaction covers both families and originals. The
manifest records filing metadata, missing originals, byte hashes and exclusions.
Corruption/limits reject the complete request. Neither version is a tax return or
whole-account backup; large-archive partitioning is still pending.

Registration uses the existing exact personal-payments and personal-ledger flags.
Both remain disabled live. Source qualification does not activate accounts,
providers, imports, reminders, hosted routes, private databases or existing daemons.

Evidence in `backups/personal_filings_20261114_v01/` and
`backups/personal_phone_20261114_filings_v01/`:

-12 focused API/temporary-SQLite checks pass: standalone admission, auth/owner/
 family separation, strict metadata, idempotency, immutable byte/version handling,
 upload bounds, assigned-year filtering, V1/V2 scope, all hashes, corruption,
 concurrent snapshot behavior and backup/default-off preservation.
-Two actual React/IndexedDB/FastAPI/SQLite composition checks pass: metadata draft
 and lost-ACK retry; original recovery/retry, exact download, byte-equal V2 ZIP,
 no payment dependency and account separation. Only SDK verification/client
 sign-in are synthetic. Owned browser/API fixtures closed normally.
-Updated production personal Vite build exits0; six final assets retained under
 dist-final. Earlier dist and the original test failure remain preserved. The
 initial new test expected405 for an absent deletion route;404 also correctly
 rejects deletion. The assertion was corrected and now verifies the row remains.

No private records were read or changed. Existing accounting/auth, frozen system
primitives and passing test files were not modified or re-audited. Shared original
helpers were extended for the new parent type with payment defaults preserved.
Source remains an unreleased5.329.146 derivative; full program ACTIVE/incomplete.
Next: qualify offline personal-page reopening and larger-year export partitioning,
then combined source/runtime/hosted release gates with preserved private backups.

Scoped Drive checkpoint verified: `1Shbn-cB9eKJNbWmbErHYkpslDHgMz_FC`,218,415bytes,
26members. Exact downloaded archive and every member hash/CRC passed; existing
parent/sharing preserved. Private records/databases and whole-project coverage
excluded. Receipt: `backups/personal_filings_20261114_v01/drive-verified.json`.
This closing note is newer than the archived source snapshot.
