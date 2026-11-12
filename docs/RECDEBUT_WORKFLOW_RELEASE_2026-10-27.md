# RecDebut workflow foundation and historical context review

2026-10-27 — Record147

## Operating direction

AI-BS supplies the RecDebut backend automation foundation. The private staff workspace now organizes Today & follow-ups, Families & athletes, Messages & review, Registrations & services, Media & delivery, and Results & work log. Official public destinations: https://recdebut.com/ and https://recdebut.com/all-registration/ (read, no submissions).

Family/contact records retain source, relationship and separate channel permission evidence. Follow-ups have owners, due dates and observation labels. Services separate free registration, consultation, proposed offers, staff-confirmed payment and fulfillment. Delivery records store references and status; they do not upload or publish files. Work entries retain staff, minutes, expenses and outcomes. Existing records remain available read-only; no roster was automatically imported.

SQLite revision-checked saves persist across sessions and reject stale updates. An append-only application event history binds record revisions and payload hashes. New suppression records normalize destinations and survive later permission changes. Draft previews bind exact draft, audience, contact revisions and rendered content. Recording review does not authorize sending. Staff-entered identity is attribution, not independently verified Dennis approval.

## Changes and boundaries

RecDebut sending and its old scheduler are held off in source, even if an environment activation setting is enabled. Six runtime activation controls remain false. Removed inline credential fallbacks. TextBee HTTP errors no longer become queued success. Unsigned public tracking is inert and redirects only to the official registration destination. The legacy public registration endpoint returns 503 before any record or automatic endorsement is created. No provider communication occurred.

This is an incremental foundation using the existing admin authorization and private SQLite database. Full multi-client role isolation, PostgreSQL, continuous public intake, verified payment webhooks, persistent execution queues and automatic fulfillment remain outstanding. Hosted data still depends on the existing backend connection. Registration/payment/delivery entries are staff records, not independently reconciled external events.

Before enabling sending, resolve all relevant Record144 blockers: one eligibility/suppression path for every sender, legacy STOP reconciliation, confirmed permissions and parent relationships, exact authorized audience and copy, current offers/claims, durable jobs, cancellation/replay/idempotency and provider outcome reconciliation. This release does not clear those gates.

## Newly supplied activity summary

The additional pasted account supports the family-first recruiting-support workflow, Dennis review and consultation role, Brett operations and Julie follow-up/media role. Treat reported historical whitelists, cleanup, dates, counts and role assignments as historical assertions until matched to retained source evidence. Do not repeat its deletion instructions or change existing exclusions based on this summary.

Its browser/user-agent classification cannot establish a verified human, identity, consent or lead. A number containing 555 is not by itself a valid or invalid destination; the summary's area-code explanation is not accepted as verification. Review the complete number and source without blanket removal. Do not promote historical messages, opens or clicks into registrations, payments or completed service.

The supplied SMS handoff totals (1,665 records, 1,662 sent, 3 inbox, 1,626 unique addresses, 39 repeats and 1,643 registration identifiers) remain user-supplied historical figures, not newly reconciled live metrics. Historical recdebut-recruit.org links are not silently replaced or treated as approved current links. Gold $150/Silver $35/Bronze $25 remain unconfirmed historical offers. 300 Silver is $10,500 and 300 Bronze is $7,500.

## Verification and release

31 isolated backend tests passed with one existing deprecation warning. Four changed backend files compile. Desktop 1440px and phone 390px synthetic browser tests passed persistence, stale-save edit retention, unsaved-edit guards, six sections and no horizontal overflow/page errors. These browser writes used mocked APIs, not production contacts. Whole-project TypeScript remains failing on pre-existing diagnostics; the changed workspace had zero matching diagnostics after its annotations were corrected.

Production build passed; 6,628 bundled source hashes were revalidated, four component mirrors match, and only 37 reviewed public assets were added. Publication artifact: 191 files, 80,110,384 bytes; recognized privileged-secret signatures zero, forbidden files zero. Firebase release web-v5-329-71-d47a0191435f, Hosting version ebe02403917aea01. All 191 live served hashes and version matched; excluded private paths were not published.

Controlled backend reload passed health, authenticated workflow read, unauthenticated denial, held public registration, six false controls and exact counts for all 11 existing RecDebut tables. Only the verified owned backend was reloaded. New workflow has no production business records from tests. Private online backup retained; never restore it over later user writes.

Rollback retains Hosting version 55981680f461ebcd and original router, policy and scheduler source. Review source freshness, restore only affected files, and reload the owned backend with health checks. Keep additive workflow tables and later writes. Failed harness/build/type-check attempts remain in the private checkpoint directory. VM work and general execution remain disabled/unmodified; no disposable acceptance claimed. Cloud ledger synchronization pending.

Evidence: backups/recdebut_workflow_20261027_record147. Private backups and raw output are excluded from publication.
