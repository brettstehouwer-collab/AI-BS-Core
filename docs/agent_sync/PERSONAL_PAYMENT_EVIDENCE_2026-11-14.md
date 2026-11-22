# Manual weekly payment evidence — source checkpoint

T10 adds append-only `POST /api/personal-finance/payments` and owner-scoped
`GET /api/personal-finance/payments?week_start=YYYY-MM-DD`. Both register only
with exact `AI_BS_ENABLE_PERSONAL_PAYMENTS=1`; no live flag or service changed.
Existing financial admission and accounting writer/storage are reused unchanged.

Records preserve exact positive USD strings, payment date, separately assigned
seven-day work period, payer/source descriptions, notes and bounded load/evidence
references. Payment date need not fall in the assigned work week. A required
Idempotency-Key makes identical retries return the original ID; changed retries
conflict. Client owner, update ID and tax-classification fields are rejected.
References are unverified metadata, not downloaded files or proof of original
document preservation. No transfer is posted automatically as accounting income;
there are no assumed salary, employment, tax or provider-confirmation conclusions.

Twelve focused checks passed with real API admission, synthetic SDK claims and
an owned temporary SQLite database: default-off behavior, unauthorized/PIN denial,
append/text/private headers, retry/conflict behavior, exact money, strict schema,
cross-owner separation, weekly allocation/totals, date/reference limits, preserved
legacy rows/no income inference and corrupt-evidence rejection. Attempt1 retained
Windows fixture cleanup failures; explicitly closing fixture-only SQLite handles
fixed these. Attempt2 passed12/12. Existing accounting/auth code and suites stayed
unchanged; no private database, account or original document was accessed.

Evidence: `backups/personal_payments_20261114_v01/`. Source remains an unreleased
5.329.146 derivative; hosted/native/APK baselines are unchanged. The full program
remains ACTIVE/incomplete. Next implement owner-scoped immutable document intake
and retrieval, then the separate personal-finance phone UI and export composition.
Live activation, account integration and tax/pay-rule qualification remain open.

Scoped Drive backup verified: `1AJpe8YTCr9O-IcTSSl5UvoU8qHV4hjJL`, 8,625 bytes,
seven members; exact download and every member hash/CRC passed. Parent and
existing permissions preserved. Private records and whole-project coverage are
excluded. Receipt: `backups/personal_payments_20261114_v01/drive-verified.json`.
This closing note is newer than the archived checkpoint.
