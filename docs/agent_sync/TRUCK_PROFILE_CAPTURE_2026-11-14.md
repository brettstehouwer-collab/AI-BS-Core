# Truck-profile capture — November 14, 2026

Source 5.329.150 adds an owner-scoped vehicle-fact API under the existing exact `AI_BS_ENABLE_DRIVER_PORTAL=1` registration. No service was restarted, flag enabled, database migrated, account connected or release deployed. Native148/web148/gateway149 candidates and hosted146 remain separate.

`backend/fe_truck_profiles.py` exposes GET/POST `/api/v1/fe-express/driver-records/truck-profile` and GET `/history`. It reuses the existing administrator identity and driver-store dependency; owner comes from authentication, never the payload. New tables retain every accepted revision and operation acknowledgement. CAS rejects stale edits; identical retries return the recorded result. History is paginated, 20 revisions per page. Request bodies are limited to32KiB; notes and axle counts are bounded. Duplicate JSON keys, non-finite/boolean measurements, invalid units/types and incomplete confirmations fail validation.

Vehicle configuration, actual height/width/overall length, cargo-box length, loaded gross and individual axle weights, hazardous-material status and original notes can be recorded as incomplete drafts. Units are explicit in field names (inches, feet, pounds). Measurement bounds are input sanity limits, not legal limits. No owner's profile is prefilled from the user's30-foot cargo-box description. Confirmations are user assertions, not independent vehicle verification. Even a complete profile always returns `routing_ready:false` and `provider_qualified:false`.

All disk transactions run outside the ASGI event loop. The retained WAL/FULL connection primitive is unchanged. This caller serializes initial opens/transactions with a bounded process-local lock; it is not a distributed writer queue. External SQLite busy/locked failures return503 with private/no-store and retry guidance. Other database failures remain errors. No load, attachment, master database or frozen offline capture-store format was changed.

## Actual evidence

`backend/tests/test_fe_truck_profiles.py`:12/12 synthetic HTTP checks passed in0.569seconds. Coverage includes exact flag registration, unauthorized no-storage admission, unknown dimensions, owner separation, private successful responses, client reopen/idempotency, stale/reused-operation conflicts, original-note history pagination, numeric/schema bounds, incomplete confirmations, per-axle validation, bounded/ambiguous JSON, concurrent initial CAS and unchanged existing load/attachment bytes plus SQLite integrity/WAL/FULL.

First run:11pass/1new-test error because current FastAPI defers included routers; corrected the new test to use actual HTTP, without changing existing passing suites. Second run:11pass/1error exposed concurrent first-open WAL initialization (`sqlite3.OperationalError: database is locked`). Added the new caller's process-local serialization and busy response without modifying the frozen connection helper. Third run12pass. Failed evidence remains in `backups/truck_profile_20261114_v01`; no live stores or real authentication tokens used. Existing authentication is patched only in this synthetic test; this profile slice has not been qualified with real Firebase identity or through the production gateway.

## Remaining work

Next implement phone profile entry and separate durable owner-scoped offline draft/operation recovery, then compose against this actual API. Preserve unsynced drafts, display revisions/conflicts and never silently overwrite another device's profile. No profile UI/offline synchronization, truck-route provider, map, load-stop navigation, spoken guidance or recalculation is claimed here. Full actual vehicle facts and maintained provider coverage/license/cost/offline qualification remain required before routing.

Checkpoint: `backups/truck_profile_20261114_v01/checkpoint.json`. Engineering backup excludes all private driver/finance intake, stores, keys and fixture databases. Goal ACTIVE/incomplete.

Scoped Drive source/handoff backup verified: `1FyFQlgSAzPIkA-sYr0neA4f8yczCExqx`,470470bytes/44members, SHA256 `45d4032990837f4591ddbf8603ec475eacab9dbfbf2ed50adcde6dc59aa9dbc7`. Downloaded bytes and every member hash/CRC match; existing parent/sharing preserved. Receipt `backups/truck_profile_20261114_v01/drive-verified.json`. Closing notes/pointers postdate the immutable source archive. The prior vault source-archive download block remains separate and unresolved.
