# FE Express Driver Portal, Truck GPS and Personal Finance Plan

## Current authorization — November 14, 2026

The user explicitly resumed FE Express and personal finance development as part of the master implementation goal. This supersedes paused/planning-only status statements retained below. Initial work: driver-owned offline load capture and separate personal weekly payment evidence, then supported synchronization and truck GPS. Latest truck clarification: 30-foot cargo box, typical 150–300 mile radius; full vehicle dimensions/weights remain unconfirmed. No live account connection or deployment is claimed.



Updated November 14, 2026. **Status: PLANNING SAVED; DEVELOPMENT AND INTEGRATION SETUP PAUSED.**

This is an addition to AI-BS, preserving the existing program and its other work. It does not resume this workstream, activate business modules, schedule reminders, connect accounts, or deploy a portal. The requested features below are requirements and proposals, not completed functionality. The user's latest clarification confirms **Android — Samsung Galaxy S25 Ultra**.

## Intended outcome

I am a company driver for FE Express. I drive a 28-foot box truck and handle at least five loads per week. I want one practical phone-accessible portal for my work records and a separate personal area for pay, financial documents, accounting ledgers and taxes. My AI-BS home workstation can process documents, summarize trips and compare pay where practical. Offline operation is required for phone trip capture; it is not a new offline-only rule for all AI-BS.

FE Express integration means using the company's supported systems and the user's authorized access. Which company, dispatch, payroll and document systems are involved, and whether an existing company portal is available, remain unverified. Existing AI-BS FE Express modules do not establish a connection to the employer's systems.

## Private intake clarification — November 14, 2026

The user reports **between $700 and $1,000 per week**, still to be determined. This supersedes the earlier tentative $1,000/week figure; it is not a confirmed salary, contractual minimum, rate formula, gross/net amount or guaranteed payment. Record actual agreed terms and their effective dates before calculating expected pay.

The user uses **Venmo for transfers**, receives **no pay statements**, and wants records organized for doing their own year-end taxes for this job. Venmo use does not establish that every transfer is work income or establish a supported automatic connection. Start with manually entered payments and original evidence the user supplies; evaluate screenshots, files or exports actually available. No Venmo account was connected or financial record accessed.

The first useful version must work **without pay statements**: a week-by-week load/expense/payment ledger with payment date, payer/source, amount, reference, linked load/week, outstanding questions and original evidence. Keep any later pay statement as another evidence source. Show provisional expectations separately from actual payments and confirmed amounts owed; do not label a discrepancy as a confirmed underpayment from this range alone.

Employee/contractor and tax classification, withholding, pay basis, deductions, reimbursement terms, pay-period boundaries and gross versus take-home amounts remain unconfirmed. Being a company driver, using Venmo or doing one's own taxes does not resolve those questions. Organize source records and tax-year exports without assuming deductions, filing treatment or automatic tax calculations. These private intake facts stay out of the shared engineering derivative by default.

## Requirements to carry forward

| Area | Required behavior |
|---|---|
| Load record | One record per load, with a load/reference number, pickup and delivery locations, appointment times, actual arrival and departure times, delays, notes, pay issues, expenses, receipt photos and delivery/load paperwork. |
| Everyday capture | Quick **Arrived** and **Departed** actions, voice notes and photos. Preserve original attachments. Timestamp corrections should retain the original event and the correction. |
| Offline phone use | Save entries, recordings and attachments locally on Android before reporting local success. Show separate local-save and server-sync states. Reconnect and synchronize without duplicate records or silently overwriting another edit. Unsynced records remain available while the home workstation is offline. |
| Work area | Loads, stop records, dispatch instructions, delivery paperwork, expenses and reimbursement tracking. Company-driver workflows take priority over existing owner-operator, broker or booking functions. |
| Delivery reminders | Remind about incomplete delivery records. Time, timezone handling and daily versus active-load-day behavior remain undecided. **7 PM was only an example. No reminder is scheduled or enabled.** |
| Pay comparison | Start with actual payment evidence when no pay statements are supplied; add statement matching when available. Compare against trip evidence using confirmed FE Express pay rules. Flag possible missing paid miles, eligible detention/layover, extra-stop pay and reimbursements for review. Keep times, notes, receipts and the applicable rule with the finding. |
| Personal area | Pay statements, receipts, accounting ledgers, tax documents and other financial records, organized by source, document type, date and tax year. Preserve originals and distinguish extracted information from source documents. |
| Financial intake | Manual uploads first in the proposed sequence; automatic email, payroll, accounting or other imports only after identifying the sources actually used and their supported access. |
| Truck GPS | Configurable truck profile; routing using maintained mapped clearance, weight and truck-road restrictions; visual and spoken turn-by-turn guidance; recalculation; load pickup/delivery locations offered as navigation stops. |

Work and personal access must be separate at the service and storage boundaries, including offline caches, attachments and exports. A work-only session must not read personal finance records. Existing phone/PIN access must not automatically grant personal financial access. A personal pay comparison may reference the user's authorized trip evidence without opening the personal area to company-work users.

## Truck routing decisions still open

Confirm actual **height, width, overall vehicle length, loaded gross weight, axle weights and applicable restrictions**, with explicit units and the vehicle/configuration they describe. Confirm whether **28 feet is the box length or the overall vehicle length**. Box length is not a complete routing profile.

Select the mapping and truck-routing engine only after checking the actual operating region, maintained restriction-data coverage, licensing, cost, Android support and offline capabilities. Separate offline map viewing, offline truck routing, guidance, recalculation, traffic and restriction updates in that evaluation; support for one does not prove support for the others. No provider, subscription, API key, route configuration or map download has been selected.

The planned UI must make unavailable or stale truck-routing data visible. Do not silently substitute a passenger-car route or claim a route is guaranteed clear. GPS permissions, route history and location retention need an explicit design. Continuous location tracking is not a requirement in this outline. If HOS or ELD features are later requested, assess applicability from the actual vehicle and operations; no exemption is inferred from box length.

## Proposed first-version sequence — not implementation authorization

1. **Discovery and reuse review.** Identify FE Express's exact systems, existing portal, supported exports/imports and pay rules. Identify personal record sources, Android version/device constraints, operating region, reminder preferences, hosting and connection preferences. Inspect the current AI-BS routes, schemas and access controls before choosing changes.
2. **Manual offline load capture.** Start with a single-driver load list, pickup/delivery stop cards, Arrived/Departed, editable times and notes, voice recordings, photo/file capture, expenses and incomplete-record status. Validate a week of at least five loads plus multiple attachments per load. No dispatch scraping, booking, settlement or payment execution is implied.
3. **Durable sync and private document intake.** Add an acknowledged upload queue, resumable/retry-safe attachments, conflict handling, explicit sync/recovery status and workstation retrieval. Keep the personal area separately authorized; manually upload pay/tax/ledger originals. Decide encryption, key recovery, local storage limits and backup retention before using real private documents. A web app/PWA and a native Android client are candidates, not a chosen architecture.
4. **Workstation document processing and pay review.** Support a manual weekly payment ledger even without statements. Extract fields into derived records with source references and review status. Version the confirmed pay rules, units, eligibility, rounding, deductions and effective dates. Match loads/weeks and expenses to actual payments and any later statement lines; leave ambiguous matches for review. Export organized source-linked records by tax year. Report differences without asserting payroll errors or giving automatic tax conclusions.
5. **Truck-navigation increment.** Complete profile and provider evaluation, then qualify known truck-restriction cases, missed-turn recalculation, voice guidance, load-stop handoff and the actual offline behavior before relying on navigation. This is a separate gate from simple address/map display.
6. **Optional supported imports and reminders.** Add only the chosen source connections and reminder schedule. Keep import provenance and duplicate detection, surface failures and preserve manual capture if a connection is unavailable.

This ordering is a proposal. The user will choose the first features when development resumes. No programming, runtime setup, migrations, provider calls, automatic imports, scheduled tasks or account connections follow from saving this plan.

## Proposed data and synchronization boundaries

These are design targets for later schema/API review, not existing database tables or routes:

- A stable internal load ID independent of the entered company reference; pickup/delivery stops and appointment times with timezone/offset; arrival/departure events; corrections and revision history.
- Expenses and pay issues linked to a load; original photo/audio/document objects with size/hash and source; independent metadata and attachment synchronization states.
- A durable client outbox with operation IDs and revisions; server acknowledgements and duplicate detection; visible conflicts rather than silent last-write-wins. Do not delete a local original merely because an upload started.
- Actual payment entries and payment evidence, optional pay statements and statement lines, confirmed rule versions, suggested matches, unmatched items and review findings with their supporting records.
- Personal document metadata for source/type/date/tax year, original file and separate extracted fields. Company and personal authorization scopes apply to reads, writes, processing and exports.

Choose the phone's storage, background-sync/reminder mechanism, encryption and server persistence after Android constraints and actual existing implementations are inspected. Phone recording/storage and workstation speech transcription are separate capabilities. Do not promise offline transcription before it is tested.

Before claiming durable offline capture, test app/browser restart, device reboot, interrupted attachment uploads, insufficient storage and storage eviction on the chosen Android client. Provide visible unsynced status and recovery/export options; do not promise zero data loss from browser storage alone.

## Existing AI-BS source and qualification limits

The scoped November 14 source inventory found FE Express portal/reporting code that may be extended. Source presence and old test references are not current end-to-end acceptance or proof of employer integration. See [reuse inventory](SOURCE_REUSE_INVENTORY_2026-11-14.md).

In the reviewed code, FE access/workspace is shared rather than individually isolated by driver; financial routes require separate administrator authorization. The service worker has no offline application cache, and the existing navigation hazard helper is a demo heuristic. None establishes the requested offline/private truck-GPS portal.

Preserve the current FE Express stored data and adjacent modules. Do not repurpose owner-operator settlement, broker or booking assumptions into company-driver pay calculations. No production database, employer record, account, security rule, tunnel or deployment was changed for this plan.

## Supporting access and hardware history — unverified now

The supplied historical Tailscale screenshot identified AI-BS as **100.104.31.50**, MagicDNS **ai-bs.tail6dd4a6.ts.net**, and showed **Not connected** at that time. A web terminal reported `Failed to fetch` for `https://api.brettstehouwer.live/api/terminal/run`. These are troubleshooting references, not current health or ownership checks. The portal's final hosting and phone-to-workstation connection remain undecided; no remote service has been started or exposed for this workstream.

Historical hardware notes report Windows 11 Home, Ryzen 9 9950X, RTX 4090 and Wake-on-LAN disabled. Verify the current system before depending on it. A home-PC outage must not prevent offline trip capture on the phone. Do not place credentials, actual financial documents or precise trip history in shared engineering backups by default.

## Resume checklist and first questions

- Which FE Express company portal/dispatch/payroll/document tools are used, if any? No statements are currently received; what payment evidence and agreed pay terms can be supplied? Which pay basis and written rules apply?
- Where are the personal pay statements, receipts, ledgers and tax documents now? Which supported import methods exist?
- **Android / Samsung Galaxy S25 Ultra confirmed.** Android version, storage constraints and preferred app format remain open.
- Which features should come first? What reminder time and daily/active-load-day rule are wanted? What should synchronize automatically or manually?
- Where should the portal run, and how should the phone connect to AI-BS? What happens while the workstation is unavailable?
- What are the actual vehicle specifications, operating region and routing restrictions? Which mapping engine passes coverage/licensing/cost/offline evaluation?

**Exact next step on explicit resume:** resolve the FE Express system/pay-rule and personal-source inventory, then produce a scoped implementation plan against the existing routes and data contracts. Do not request credentials in chat. No decisions above are silently filled in by old notes.

## Next-chat directive

Continue my FE Express Driver Portal and Personal Finance Plan from this file. I use an Android Samsung Galaxy S25 Ultra, am a company driver for FE Express, drive a 28-foot box truck and handle at least five loads per week. Preserve the offline load-capture, separate personal-finance, payment/paycheck-review and integrated truck-GPS requirements. Start with a manual payment-evidence ledger that also works without pay statements; consult the private intake clarification locally for current unconfirmed pay/source details. Development and integration setup are paused until I explicitly resume this workstream. Start with focused questions about company systems, pay rules, record sources and the remaining decisions. Preserve existing AI-BS work and original documents, and distinguish proposals from implemented and verified behavior.
