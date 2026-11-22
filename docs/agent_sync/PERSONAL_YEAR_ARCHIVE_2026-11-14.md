# Personal yearly records and originals archive

T10 adds `GET /api/personal-finance/exports/{year}.zip` under the existing exact
`AI_BS_ENABLE_PERSONAL_LEDGER_EXPORT=1` registration gate. The phone's yearly
section now offers both the accounting CSV and a separate records/originals ZIP.
Live flags remain off; no running service, hosting target or APK changed.

The ZIP uses a single read-only SQLite transaction for owner-scoped accounting
entries, manual payment records and their linked original documents. Selection
uses the recorded accounting date or payment date, not the assigned work week
and not an inferred taxable period. JSON preserves each original stored payload
string as well as its parsed fields and record timestamps. Existing CSV formatting
and formula-cell handling are reused unchanged; transfers remain separate from
accounting income. Originals are checked against saved lengths/SHA-256 and stored
unchanged under generated numeric archive paths. Original filenames, declared
MIME types and payment/document references remain in the manifest.

The manifest records coverage, unattached payments, explicit exclusions and hashes
for all data members. Fixed ZIP metadata makes unchanged snapshots byte-equal.
Corrupt records/originals or limits reject the whole request; no partial archive
is returned. Current review limits:10,000 owner records examined,10,000 originals,
128MiB of source/export data. Larger archives require a later bounded partition
workflow. Unowned legacy rows, other owners, unsent phone drafts/files, standalone
tax documents and unlinked work-area files are excluded. This is a source-linked
records archive, not a tax return, payroll reconciliation or whole-account backup.

Thirteen focused checks passed:

-12API/temporary-SQLite checks cover default-off/auth/owner boundaries, every
 manifest hash, original bytes/paths, payment-date selection, separate CSV,
 coverage gaps, corruption rejection, inert reads/absent DB, resource limits,
 repeatability/private headers and a concurrent write excluded by the snapshot.
-One actual phone React/API/SQLite download check: the clicked ZIP matched the
 direct API response byte for byte, including the linked synthetic original.
 Only Firebase SDK verification/client identity were synthetic; no private
 record or account was used. Owned browser/API fixtures closed normally.

The updated production personal profile compiled successfully to six files in
`backups/personal_year_archive_20261114_v01/dist`; canonical dist is unchanged.
Backend evidence is in that same phase directory; browser evidence is in
`backups/personal_phone_20261114_archive_v01/`. Existing accounting writer, auth,
document store and frozen primitives/tests were not changed or re-audited.

Program remains ACTIVE/incomplete. Source is an unreleased5.329.146 derivative.
Next: standalone owner-scoped financial/tax-document intake and filing, followed
by offline personal-page reopening and reviewed combined deployment/release gates.

Scoped Drive checkpoint verified: `121NkNI5wtTgi_MdIMz-1cP3hTw0J4YNv`,202,402bytes,
20members. Exact downloaded archive and every member hash/CRC passed; expected
BS game parent and existing sharing preserved. Private records/databases excluded;
not a whole-project backup. Receipt:
`backups/personal_year_archive_20261114_v01/drive-verified.json`. This closing note
postdates the archived source snapshot. A reusable local scoped-archive verifier
now lives in `backups/tools/verify_scoped_archive.py`; its actual roundtrip passed.
