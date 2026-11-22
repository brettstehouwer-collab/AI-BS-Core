# Recreational Debut portal audit — 2026-10-27

Scope: source audit of active desktop/standalone/mobile components, snapshot loader, RecDebut controller, access/privacy and outbound policy. App.jsx imports components/clients/RecreationalDebut.jsx and DennisBellPortal.jsx; their reviewed base copies match SHA-256. No messaging, contact mutation, provider login test, tracking-link visit, deployment or service restart was performed. Findings describe source behavior; fresh authenticated browser and deployed route acceptance remain untested.

## Findings

### P1 — Mobile actions do not match controller routes and can show incorrect lifecycle state
DennisBellMobileRemote.jsx:178,533,555,583,592 calls POST /replies/sync and /broadcast/single_test,start,pause,stop. These five routes are absent from the reviewed RecDebut router; a source search across backend Python found no literal matching implementations. Desktop uses /sms/sync-replies, /test-sms or /test-email, /broadcast and /broadcast/cancel. Do not invent a pause semantic by treating cancellation as pause.

Mobile handleStartBatch sets isBroadcasting true even when the HTTP response is unsuccessful. Pause/stop ignore response status and set false, so a failed cancellation can appear successful. Use one shared client contract for desktop/mobile, require server acceptance and show observed job state. Source connection to the active mobile path is confirmed by desktop viewMode switching below640px, native detection and explicit mobile URL options.

### P1 — Public tracking redirect accepts an arbitrary destination
rec_debut_router.py:6947–7065 accepts query url and returns RedirectResponse(dest_url) without a destination allowlist. recdebut_access.py explicitly allows public tracking GETs. This creates an open-redirect path in reviewed source, suitable for abuse of a trusted outreach URL. The same handler records click/lead events using public campaign/athlete identifiers, so generated events are not proof a genuine athlete clicked. Allow approved HTTPS destinations and use signed expiring tracking identifiers; distinguish automated/scanner events from verified replies. No exploit request was made and live deployment exposure was not tested.

### P2 — Success and safety messages exceed what is established
RecreationalDebut.jsx:626–634 reports coach cleaning complete without checking res.ok or data.success, and declares the roster 100% coach-free. The backend cleaner uses known numbers/names/keywords and edits/deletes matching records; that is heuristic filtering, not universal identity verification. Replace with preview, reviewable exclusions, retained originals and an actual completion count.

Test SMS/email alerts assert full delivery, caller ID and inbox delivery; carrier/SMTP/API submission acceptance does not establish those outcomes. API configuration saving calls its shield active without independently verifying domain/provider readiness. Show Draft / Queued / Provider accepted / Delivered / Failed only when corresponding evidence exists. Keep outreach activation separate from connection configuration.

### P2 — Campaign drafts and audience state are transient
Message text, subject, selected recipients and new-referral form live in React state. No durable draft save/restore is present in the reviewed desktop component. A refresh/session loss can discard edits; desktop/mobile maintain separate composition state. Add explicit saved campaign drafts, recovery and recipient-preview versions before sending. Do not persist provider secrets in browser drafts.

### P2 — Data loading has a broad failure boundary
recdebutData.js loads ten resources with Promise.all; one failed email configuration/quota/analytics request rejects the entire snapshot. Preserve strict validation, but allow independent roster, inbox, analytics and connection panels to show their own unavailable states. Keep last successful values visibly dated; do not substitute historical counts. Mobile polling errors are often silent and can leave stale state without a warning.

### Maintenance and organization
The desktop portal exceeds5,000 lines; the primary router exceeds9,000. RecreationalDebut and DennisBellPortal currently contain identical full implementations under separate names. Extract shared screens/client contracts while retaining entry routes and deployment mirrors. App backend startup also contains two rec_debut_router inclusion sites: inspect runtime route duplication before consolidation; duplicate live registration was not tested.

## What to keep

- Existing four master groups are a useful foundation; avoid another full navigation rewrite.
- Keep genuine-zero handling, response validation and explicit unavailable messages.
- Keep administrator-protected administration, separately allowed public registration and signed inbound webhook verification.
- Keep fail-closed outbound and inbound-polling activation policies; this audit does not enable them or establish current process flag values.
- Keep athlete/coach separation, campaign history, replies, program assets and resource links, with accurate verification labels.

## Recommended structure

| Section | Contents |
| --- | --- |
| Overview | Pending follow-ups, unread replies, campaign state, connection/disabled warnings |
| Athletes | One profile per athlete: contact details, sport/year, notes, source, contact preferences, interaction history |
| Communications | Inbox plus shared campaign drafts, audience preview, review/send, failures and cancellation |
| Reports | Campaign outcomes, provider acceptance vs delivery, replies and meaningful conversions |
| Organization & resources | Leadership, awards, sports portals and FAQ |
| Settings | Provider accounts, credentials, quotas and authorized activation status |

This can preserve the current four master groups using subpages: Overview/Reports under Campaigns & Analytics; Inbox/Drafts/Campaigns under Communications; profiles/intake under Roster; resources/settings under Organization with permissions. Prefer one responsive workflow over a separately implemented mobile command surface.

First bounded repair: unify mobile/desktop route contracts and correct lifecycle errors; constrain tracking redirects; then add durable campaign drafts and simplify navigation. Do not enable broadcasts merely to test the interface. Outreach claims, dated templates and educational guidance should have review dates and sources before reuse; their external accuracy was not assessed here.

## Verification and limits

- Four backend files passed AST syntax parsing without importing the application or initializing databases.
- Three relevant base/active-copy pairs have SHA-256 parity.
- Five isolated snapshot checks passed: genuine zeros,403 rejection, malformed roster rejection, negative counts and unsuccessful response rejection.
- Raw results and reproducible checks: backups/recdebut_audit_20261027_record143.
- No full build, full security assessment, live message delivery or browser/mobile acceptance claimed. No application repairs or release performed.
