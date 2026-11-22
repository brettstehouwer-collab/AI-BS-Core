# Bounded multipart personal-year exports

T10 adds `GET /api/personal-finance/exports/{year}/parts` and
`GET /api/personal-finance/exports/{year}/parts/{fingerprint}/{index}.zip`.
Registration uses the existing personal-ledger export flag, still off live.
V1/V2 yearly ZIP and CSV endpoints remain intact.

The owner-bound plan inventories selected source records, per-entry accounting
CSVs and stored payment/filing originals. Original planning queries read metadata,
not BLOB content. Part source payload is limited to32MiB; manifests/ZIP framing add
bounded overhead. Each record JSON and each original stays a complete member;
original bytes are not rewritten or split. Planning has explicit10,000record,
20,000file,8MiB metadata and32MiB inline-data review limits. Aggregate original-byte
volume is not subject to the previous single-ZIP128MiB ceiling. This is not an
unlimited export service, and real multi-gigabyte throughput is not yet measured.

A plan fingerprint binds owner, selected year, policy and all member metadata /
hashes. Each part recomputes that inventory inside its own read transaction before
reading just its selected BLOBs. A changed source returns409 before another ZIP
is produced. Parts therefore require an unchanged inventory, not a persistent
frozen snapshot across requests; active edits may require a fresh plan/restart.
Every part includes its index/count/fingerprint, member hashes and full-year
completion requirement. Corrupt originals reject the whole part. Public paths
are generated from record IDs; original filenames stay metadata.

The phone UI offers plan download and one explicit part download at a time.
Source changes mark the prepared plan stale; regeneration is explicit, and files
from different fingerprints must not be mixed. UI progress says downloads offered,
not verified saved, because browser save dialogs can be cancelled. Plans remain
transient unless the user downloads their JSON. No private response caching or
automatic bulk-download loop was added. Financial/source labels remain manual
and unreconciled; there is no inferred pay or tax classification.

Evidence: `backups/personal_export_parts_20261114_v01/` and
`backups/personal_phone_20261114_parts_v01/`.

-12 focused API/temporary-SQLite checks pass, using a scaled1KiB part limit for
 multipart reconstruction: owner/auth/fingerprint binding, no BLOB planning reads,
 exact full member union/hashes/originals, repeatability, other-owner stability,
 stale-plan rejection, concurrent snapshot behavior, corruption, explicit limits,
 inert/empty reads and faithful accounting/source output.
-One actual React/API/SQLite phone check passes: plan JSON and part ZIPs equal
 direct API responses, names carry the fingerprint, stale plans stop and a new
 plan can be prepared. Only SDK identity and transport are fixture boundaries.
-Production personal build exits0; eight final emitted files retained. Source
 helper closes live cursors even on integrity failures; this fixed the initial
 new multipart cleanup failure. Original failing evidence is retained. Existing
 passing suites, accounting/auth, databases and frozen primitives stayed intact.

No private record was read or changed, no worker/service was restarted and no
hosted/native/APK release was promoted. Program ACTIVE/incomplete; source remains
an unreleased5.329.146 derivative. Next reconcile the full master-plan priorities
and prepare the combined source/runtime/hosted release gate, preserving actual
owner/device and original game/creative acceptance gaps.

Scoped Drive checkpoint verified: `1PZnyRDRapkiQwzLNZPhWBQyi_NOxxmVv`,211,208bytes,
23members. Exact downloaded archive and every member hash/CRC passed; existing
parent/sharing preserved. Private records/databases excluded; not a whole-project
backup. Receipt: `backups/personal_export_parts_20261114_v01/drive-verified.json`.
This closing note postdates the archived source snapshot.
