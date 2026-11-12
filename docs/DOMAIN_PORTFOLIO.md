# Shared domain portfolio and project assignments

Recorded 2026-10-27, Record151. This is the planning register for AI-BS, Recreational Debut, Stehouwer Publishing, BS PC Service and future projects. Its structured counterpart is [domain_portfolio.json](domain_portfolio.json). Neither file is runtime configuration.

The operator supplied a current/historical control list. That report establishes the inventory's provenance; it does not establish current registration, renewal, DNS, provider access, email delivery or service availability. No domain has been reassigned or activated by this register.

## Portfolio

| Domain or hosted address | Project / brand | Evidence available on 2026-10-27 | Planned use and next decision |
| --- | --- | --- | --- |
| `stehouwerproductions.com` | Stehouwer Productions / business communications | Operator-reported control; local IONOS/mail identity references | Retain the established business identity. Verify mailbox access and sending-domain authentication before outreach. Do not silently rename existing mailboxes. |
| `stehouwer-publishing.com` | Stehouwer Publishing | Operator-reported control; CORS entry and historical ingress documentation | Candidate publishing/business homepage and client entry point. Choose the canonical spelling after confirming both registrations and existing usage. |
| `stehouwerpublishing.com` | Stehouwer Publishing | Operator-reported control; historical ingress and legacy email alias normalization | Alternate publishing spelling. Keep separate until domain and mailbox behavior are verified; no redirect or email alias is presumed. |
| `brettstehouwer.live` | Shared infrastructure / personal identity | Operator-reported control; local references to `api.` and `ai-bs.` subdomains | Retain documented infrastructure roles as historical references. Verify each public route and its authentication before adopting it for a project. |
| `ai-bs-dashboard.web.app` | AI-BS | Firebase project/site configuration; Record149 records a completed deployment | Existing dashboard address and current project entry point of record. Current live health was not retested for this inventory. |
| `ai-bs-dashboard.firebaseapp.com` | AI-BS | Firebase authentication-domain configuration | Firebase platform address associated with the project. Login/redirect configuration and current hosting behavior require their own verification. |
| `recdebut-recruit.org` | Recreational Debut | Operator-reported control; code generates tracking URLs; historical ingress map | Candidate reviewed campaign links and narrowly scoped integration endpoints. Audit destinations, authentication and event attribution before use. A click is not a registration. |
| `thesimplechef.com` | The Simple Chef | Operator-reported control; storefront email/footer template references | Culinary storefront, orders and customer service after current ownership and hosting are checked. |
| `thesimplecheff.com` | The Simple Chef | Operator-reported current/historical variant | Preserve the exact spelling as an unverified alternate. Decide whether to retain or redirect after checking registration and existing use. |
| `thesimplechefs.com` | The Simple Chef | Operator-reported current/historical variant | Preserve the exact spelling as an unverified alternate. Do not infer a working redirect or shared mailbox. |
| `global-contribute.live` | Future contributor / compute project | Operator-reported role; no confirming current reference found in the bounded source review | Reserved planning entry. Compute admission, public exposure and any activation require separate review. |
| `recdebut.com` | Dennis / Recreational Debut partner website | Prior operator report: Dennis's site; operator administrator access unavailable | External client website dependency. Connect only after delegated access, form mapping and receiver testing. This is not listed as an operator-owned domain. |

The supplied list groups **nine independent custom-domain spellings**, **two Firebase hostnames**, and the API subdomain `api.brettstehouwer.live`. Firebase hostnames and subdomains are not additional independently registered domains. `recdebut.com` is a separate partner dependency.

## Project map

| Project | Address allocation | Operating decision |
| --- | --- | --- |
| AI-BS | Existing Firebase project addresses; documented infrastructure subdomains | Reuse working deployment and authentication paths. Any new public API exposes only the reviewed business operations it needs. |
| Recreational Debut | `recdebut-recruit.org`; partner website `recdebut.com` | Keep AI-BS as the dedicated tenant's automation backend. Website access and real registration acceptance remain dependencies. Sending stays disabled pending Dennis/operator review and dispatch safeguards. |
| Stehouwer Publishing / Productions | Both publishing spellings plus `stehouwerproductions.com` | Preserve existing brand and email uses. Select one public publishing homepage later; web redirects and email aliases are separate changes. |
| BS PC Service | **Unassigned** | A dedicated service area or a subdomain of a verified business domain is an option. No new hostname is claimed, registered or configured. |
| The Simple Chef | Three supplied chef spellings | Confirm ownership and choose one canonical storefront before consolidating traffic. |
| FE Express and future clients | **No dedicated domain supplied** | Continue using their existing AI-BS workspaces. Record future client-domain access separately from operator ownership. |
| Contributor compute | `global-contribute.live`, reported only | Planning only; no automatic peer admission, outbound activation or service launch. |

## Evidence and historical aliases

- [CREDENTIALS_AND_CONNECTIONS_MAP.md](CREDENTIALS_AND_CONNECTIONS_MAP.md), starting at line 30, is the existing historical routing/connection reference. Its heading "Active Ingress" is not a fresh health or ownership check. Preserve that history.
- Historical publishing aliases: `www.stehouwer-publishing.com`, `www.stehouwerpublishing.com`.
- Historical infrastructure aliases: `api.brettstehouwer.live`, `ai-bs.brettstehouwer.live`.
- Historical RecDebut aliases: `r.recdebut-recruit.org`, `www.recdebut-recruit.org`.
- Local references inspected: `frontend/.firebaserc`, `frontend/firebase.json`, `frontend/src/firebase.js`, `backend/AI_BS_Backend.py`, `backend/routers/email_client_router.py`, `backend/routers/rec_debut_router.py`, and `backend/routers/chef_orders_router.py`. These establish configuration or source references only. Private email configuration was checked without copying values.
- [RECDEBUT_WEBSITE_CONNECTION.md](RECDEBUT_WEBSITE_CONNECTION.md) retains the partner website setup dependency. [RECDEBUT_INBOX_TIMELINE_2026-10-27.md](RECDEBUT_INBOX_TIMELINE_2026-10-27.md) retains the Record149 release and acceptance boundaries.
- Pasted endpoint totals, active-tab/file counts, Cloudflare account/zone identifiers and service claims were not promoted into current verified facts. Static route counts do not establish reachable or authorized operations.

## Before using or moving a domain

1. Confirm current registrar/account access, expiration date, auto-renewal and responsible business. Keep credentials in the private credential store; save only verification date and a non-secret reference here.
2. Read existing nameservers, DNS, website destinations, mail routing and redirects. Preserve a change/rollback record before any later mutation.
3. Agree the canonical project address and purpose. Check for existing clients, mailboxes, authentication callbacks and tracking links before changing them.
4. Verify the intended service independently: HTTPS, authentication, tenant permissions, form delivery or webhook verification, as applicable. A local reference or resolving DNS alone is insufficient.
5. For outreach, verify sender/domain authentication, channel permission, suppressions and the reviewed send path. Ownership of a domain is not approval to send.
6. Record the measured evidence, responsible person, verification date and remaining prerequisites in this register. Update both files together.

## Guardrails for future work

- Use this register as a discovery and planning index. Never automatically turn its domains or aliases into trusted origins, CORS entries, redirect destinations, email aliases or public tunnel ingress.
- Unknown ownership, renewal and health fields mean **unknown**. Reported past control does not imply current control.
- Shared infrastructure does not merge client permissions, contacts, payments or sending identities. Preserve tenant isolation and private administrative operations.
- Keep local loopback services, the six disabled activation controls and the RecDebut sending hold. DNS, hosting, mail changes and deployment remain separately scoped work.
- Domain configuration must not expose host command execution, personal files, credentials or VM execution authority.
- No external publication, DNS/mail/tunnel change, provider login, message, deployment or tracked-link request occurred while preparing this register. Cloud ledger synchronization remains pending.



## Record153 — measured service observations, 2026-10-27

The Record151 inventory above preserves its original local-only verification scope. This follow-up adds fresh observations at17:28–17:34UTC. Current ownership, registrar access, renewal, canonical choices and application acceptance remain unverified. No DNS, redirect, mail identity or provider settings were changed.

| Hostname | DNS A lookup | TLS | HTTPS HEAD final |
| --- | --- | --- | --- |
| `stehouwerproductions.com` | A/alias returned | error | request_error (SSLError) |
| `stehouwer-publishing.com` | A/alias returned | validated | 200 https://stehouwer-publishing.com/ |
| `www.stehouwer-publishing.com` | A/alias returned | validated | 200 https://www.stehouwer-publishing.com/ |
| `stehouwerpublishing.com` | NXDOMAIN | error | request_error (ConnectionError) |
| `www.stehouwerpublishing.com` | NXDOMAIN | error | request_error (ConnectionError) |
| `brettstehouwer.live` | A/alias returned | validated | 200 https://brettstehouwer.live/ |
| `api.brettstehouwer.live` | A/alias returned | validated | 404 https://api.brettstehouwer.live/ |
| `ai-bs.brettstehouwer.live` | A/alias returned | validated | 530 https://ai-bs.brettstehouwer.live/ |
| `ai-bs-dashboard.web.app` | A/alias returned | validated | 200 https://ai-bs-dashboard.web.app/ |
| `ai-bs-dashboard.firebaseapp.com` | A/alias returned | validated | 200 https://ai-bs-dashboard.firebaseapp.com/ |
| `recdebut-recruit.org` | A/alias returned | validated | 200 https://recdebut-recruit.org/ |
| `r.recdebut-recruit.org` | A/alias returned | validated | 200 https://r.recdebut-recruit.org/ |
| `www.recdebut-recruit.org` | A/alias returned | validated | 200 https://www.recdebut-recruit.org/ |
| `thesimplechef.com` | No A answer | error | request_error (ConnectionError) |
| `thesimplecheff.com` | A/alias returned | validated | 200 https://thesimplecheff.com/ |
| `thesimplechefs.com` | A/alias returned | validated | 200 https://www.thesimplechefs.com/ |
| `global-contribute.live` | NXDOMAIN | error | request_error (ConnectionError) |
| `recdebut.com` | A/alias returned | validated | 200 https://recdebut.com/ |

## Public mail DNS

| Domain | MX returned | SPF TXT | DMARC TXT |
| --- | --- | --- | --- |
| `stehouwerproductions.com` | 10 mx00.ionos.com.; 10 mx01.ionos.com. | v=spf1 include:_spf-us.ionos.com ~all | v=DMARC1; p=none; |
| `stehouwer-publishing.com` | 61 route2.mx.cloudflare.net.; 82 route3.mx.cloudflare.net.; 71 route1.mx.cloudflare.net. | v=spf1 include:_spf.mx.cloudflare.net ~all | v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s; rua=mailto:[redacted-report-address] |
| `stehouwerpublishing.com` | NXDOMAIN / no MX answer | NXDOMAIN | NXDOMAIN |
| `brettstehouwer.live` | 20 eforward5.registrar-servers.com.; 15 eforward4.registrar-servers.com.; 10 eforward3.registrar-servers.com.; 10 eforward2.registrar-servers.com.; 10 eforward1.registrar-servers.com. | v=spf1 include:spf.efwd.registrar-servers.com ~all | NXDOMAIN |
| `recdebut-recruit.org` | 10 mx01.ionos.com.; 10 mx00.ionos.com. | v=spf1 include:_spf-us.ionos.com ~all | v=DMARC1; p=none; |
| `thesimplechef.com` | NOERROR / no MX answer | not returned | NXDOMAIN |
| `thesimplecheff.com` | NOERROR / no MX answer | not returned | not returned |
| `thesimplechefs.com` | 10 thesimplechefs-com.mail.protection.outlook.com. | v=spf1 include:secureserver.net include:spf.protection.outlook.com -all | v=DMARC1; p=quarantine; rua=mailto:[redacted-report-address]; |
| `global-contribute.live` | NXDOMAIN / no MX answer | NXDOMAIN | NXDOMAIN |
| `recdebut.com` | 10 mx2.titan.email.; 5 mx1.titan.email. | v=spf1 include:spf.titan.email ~all | v=DMARC1;p=none;sp=none;adkim=r;aspf=r;pct=100 |


The two public Firebase hosts and RecDebut roots responded; website root responses do not establish registration or webhook acceptance. The productions website TLS failure is separate from its successful IONOS SMTP authentication. Three saved SMTP accounts authenticated; the primary mailbox authenticated IMAP only, while two SMTP attempts disconnected during authentication. Resend domain-read scope is restricted; TextBee authenticated, but durable inbound and automatic STOP suppression remain blockers.

Prepared an inactive [RecDebut sender review profile](recdebut_sending_review.json) and [connection/readiness report](RECDEBUT_SENDING_SETUP_2026-10-27.md). Provider and sender remain unselected. No message was sent; the source hold and six disabled runtime controls remain. Local evidence: `backups/recdebut_send_setup_20261027_record152/`. Cloud ledger synchronization pending.
