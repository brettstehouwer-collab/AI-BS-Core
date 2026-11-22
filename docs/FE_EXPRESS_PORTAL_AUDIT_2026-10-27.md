# FE Express portal audit — 2026-10-27

Scope: source review of Dispatcher, DriverReports, workspace persistence, FE Express routes, access checks and the associated controller functions. Focused workspace/report/PIN regression: 54 passed, one Starlette/httpx deprecation warning. Live Firebase tab was at the PIN/session-ended screen; no new authenticated walkthrough or external-provider acceptance is claimed. No production records, application source, services or deployments changed by this audit.

## Findings in priority order

1. **Legacy BOL completion can mislead users and lose work.** Dispatcher around lines 3650–3725 reads the selected filename, shows capture success, then updates browser dispatch state with `local_bol_photo.jpg` and reports BOL saved. That path does not upload the selected bytes or persist the dispatch update through an API. The newer DriverReports shipment/document path has stored uploads. Route all paperwork through that canonical path; do not remove historical records or silently migrate them.
2. **Several completion messages exceed the reviewed implementation.** Dispatcher lines 2430/2473 claim funding approval/deposit and SMS transmission. The reviewed `generate_instant_factoring_submission` function (owner_operator_engine.py:575) calculates and writes a local submission, with a placeholder rate-confirmation path and possible PENDING_BOL_UPLOAD. Reviewed dream_cockpit bid/broadcast/lumper functions create local records or text while returning DISPATCHED, BROADCAST_LIVE_ON_5_BOARDS or sent-style fields. These functions do not establish provider delivery, booking, funding or SMS acceptance. Use Prepared locally / Not connected until an actual provider receipt supports a stronger state. Audit all similar actions before operational use.
3. **Trip information spans overlapping screens and records.** Active hauls, trip ledger/BOL, daily reports, shipment files and financial tools create multiple routes through one job. Use one trip detail with a stable trip reference connecting driver, rate confirmation, daily entries, expenses, signed delivery and settlement. Keep manual reviewed copying until a tested migration/linking path exists.
4. **Shared draft storage mixes collaboration and personal navigation.** The singleton workspace saves preferences and business drafts together. Concurrent staff can conflict over filters while another edits a driver or report. Retain revision protection; separate per-user preferences from shared records, provide conflict comparison/recovery and distinguish Save draft from final record submission. Selected upload bytes are not saved by Save portal.
5. **Load search scope is smaller than the apparent board.** The loads API defaults to the newest 50 stored records; client ranking searches that window. Add server-side search/pagination and visible counts. Distinguish provider Posted time from Received time. Only connected imports should show Pull; other providers should show Open board / Awaiting connection. Poll saved results only when useful and back off on failures.
6. **Growth needs attribution and contextual permissions.** Shared quick access does not identify which staff member changed each record. Before wider staff use, add individual attribution and appropriate access to financial/driver documents while preserving the operator's chosen entry experience. This audit makes no login changes.

## Recommended navigation

| Section | Purpose |
| --- | --- |
| Overview | Today's pickups, active trips, missing documents, incomplete logs, drafts and connection alerts |
| Load boards | Unified source-filtered results, optional criteria, explicit Newest / Closest match, collapsed calculator |
| Trips & paperwork | Assignment, progress, rate confirmation, BOL/POD, expenses and printable trip packet |
| Drivers | Profile, assigned trips, daily employee logs and driver-specific weekly history |
| Reports & settlements | Weekly spreadsheet, Excel/PDF exports, payments, expenses and reconciled settlements |
| Tools & connections | Provider setup/status, advanced calculators and optional features |

Daily workflow: Find load → review → assign trip → attach rate confirmation → record daily activity/expenses → attach signed delivery → review weekly file → record payment/settlement. Assignment inside FE Express must remain distinct from confirmed broker booking.

Keep source grouping, optional search inputs, closest alternatives, driver/week navigation, spreadsheet entry, original uploaded documents, printable packets and revision-conflict protection. Put actions next to their relevant trip or driver; move advanced tools out of the daily workflow. Show missing values as Unknown rather than treating incomplete expenses as final profit.

## Suggested bounded sequence

1. Correct unsupported success states and route legacy BOL entry into stored shipment documents.
2. Introduce the navigation above using existing screens and records; preserve current capabilities.
3. Link trip/driver/document records and provide recovery for shared draft conflicts.
4. Expand saved-load search, pagination and provider status clarity.
5. Add staff attribution and deeper operational reporting as needed.

This is an audit recommendation, not an implementation or release approval. Existing unrelated TypeScript issues and VM work remain deferred. No new full security audit, provider integration, funding, SMS delivery, physical printing or disposable-VM execution acceptance is claimed.
