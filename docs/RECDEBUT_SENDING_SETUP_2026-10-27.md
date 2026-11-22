# RecDebut sending preparation — 2026-10-27

Record153. **Sending remains disabled. No email, SMS, provider test message or campaign was sent.** Connections were checked without reading mail or contacting recipients. The companion [sender review profile](recdebut_sending_review.json) is review data only; it is not loaded by the application and cannot authorize dispatch.

## Verified connections

Measured 17:28–17:34 UTC, 2026-10-27. Connection authentication, sender authority, recipient permission and successful delivery are separate checks.

| Connection | Fresh observation | Readiness decision |
| --- | --- | --- |
| IONOS business SMTP, saved account1 | Authentication and NOOP250 over TLS1.3 succeeded. Configured mailbox domain is `stehouwerproductions.com`. | Preferred candidate for review. Exact From identity, RecDebut branding, DKIM/alignment and reply handling still need acceptance. No provider switch made. |
| Gmail SMTP, saved accounts2 and3 | Both authenticated; NOOP250, TLS1.3. | Account access verified. Retain as separate accounts; no campaign rotation or fallback. |
| Primary Gmail mailbox, IMAP | LOGIN/NOOP over TLS1.3 succeeded. No mailbox selected or messages read. | Mailbox connection verified. Background polling remains off. |
| Primary Gmail mailbox, SMTP | Two bounded attempts disconnected during authentication; the second confirmed EHLO/STARTTLS succeeded. | SMTP remains unverified. Stop retries and retain both results; IMAP success does not resolve SMTP. |
| Resend, currently saved email provider | Domain-list request returned HTTP401, `restricted_api_key`. Configured From domain is `stehouwerproductions.com`. | Domain verification cannot be inspected with this key. This does not prove the send key is invalid. Keep current settings unchanged; obtain account-side verification or narrowly scoped read access later. |
| TextBee | Authenticated device GET200; configured device matched, enabled and receive-SMS enabled. Last heartbeat17:28:33Z was about56 seconds before the check. | Provider/device connection verified; carrier delivery and reply processing are unaccepted. No send or webhook test performed. |
| TextBee inbound subscription | Provider GET showed one active `MESSAGE_RECEIVED` subscription to `recdebut-recruit.org/api/v1/recdebut/webhooks/textbee`. | Subscription metadata only. Public path delivery, durable storage and opt-out handling remain blocked as described below. |

Saved account labels identify existing private configuration. No mailbox addresses, account IDs, API keys or passwords are included here. The separately configured reply-to identity has not been authenticated or approved; its reachability remains unknown.

## Domain findings

All 18 portfolio hostnames, including six aliases and Dennis's partner website, received bounded DNS/TLS/root-HEAD checks. Eleven returned final HTTP200. Thirteen completed a separate CA/hostname-validated TLS handshake; that count also includes HTTP404 and530 responses. Root status and DNS do not establish business functionality or ownership.

| Group | Result |
| --- | --- |
| AI-BS | Both `ai-bs-dashboard.web.app` and `ai-bs-dashboard.firebaseapp.com` returned200. |
| RecDebut | `recdebut.com`, `recdebut-recruit.org`, `r.recdebut-recruit.org` and `www.recdebut-recruit.org` returned200 at their roots. No recipient tracking URL or registration form was exercised. |
| Publishing | `stehouwer-publishing.com` and its `www` alias returned200. The separate `stehouwerpublishing.com` spelling and its `www` alias returned NXDOMAIN. |
| Infrastructure | `brettstehouwer.live` returned200; `api.brettstehouwer.live/` returned404; `ai-bs.brettstehouwer.live/` returned530. A root404 does not establish the status of individual API routes. |
| Business mail domain website | `stehouwerproductions.com` resolved but failed TLS negotiation (`TLSV1_ALERT_INTERNAL_ERROR`). Its authenticated IONOS mail connection remains a separate result. Avoid using this website as an outreach destination until repaired and checked. |
| Chef properties | `thesimplecheff.com` and `thesimplechefs.com` returned200; the latter redirected to its `www` host. `thesimplechef.com` returned no A/AAAA or MX answer despite nameserver records. |
| Contributor property | `global-contribute.live` returned NXDOMAIN. |

Public mail DNS observations: `stehouwerproductions.com` and `recdebut-recruit.org` publish IONOS MX/SPF and DMARC `p=none`; `recdebut.com` publishes Titan MX/SPF and DMARC `p=none`. The hyphenated publishing domain publishes Cloudflare routing MX/SPF and DMARC `p=reject`. Mail routing does not establish an approved outbound provider. DKIM selectors/signing/alignment were not verified. Registrar access, renewals, exact sender authority and ownership remain unverified. These checks do not grant control of Dennis's website.

Full per-host observations are in the updated [domain portfolio](DOMAIN_PORTFOLIO.md) and local evidence directory.

## Required repairs before sending

1. **Preserve signed inbound messages independently of sending.** Existing raw-body HMAC verification is present in `backend/security/recdebut_access.py:37`. The legacy TextBee handler then calls `process_inbound_reply`, whose outbound guard at `backend/routers/rec_debut_router.py:5167` runs before persistence. The handler catches that failure and returns HTTP200 with an error status. An incoming reply can therefore be acknowledged without durable storage. This is a source-level finding; no provider event was generated to exercise it.
2. **Persist opt-outs before roster or campaign filtering.** Automatic STOP handling is absent from the reviewed inbound path. Keep the existing manual common suppression store; add authenticated, deduplicated intake that suppresses the normalized destination even when it is not in an athlete roster. Save replies without forwarding or automatic responses while the hold remains. Acknowledge only after durable commit; retain a recoverable event identity and explicit failure status.
3. **Extend the existing review workflow.** Its current digest binds draft/contact revisions, destinations and personalized body, but not the provider, From/reply-to, email subject, footer, cap or expiry. A later sender must bind all of those plus audience/permission/suppression freshness. A staff review event alone remains insufficient to authorize sending.
4. **Use one explicit provider for each approved attempt.** Disable legacy automatic provider selection and SMTP rotation in the eventual approved path. Handle SMTP recipient-refusal results and provider outcomes explicitly. Reserve each normalized destination durably before dispatch; do not automatically retry unknown outcomes or change providers. Add cancellation and restart reconciliation.
5. **Correct connection status labels before activation.** The existing email settings endpoint reports an active API from key presence. A saved key is configuration, not an authentication or delivery receipt. Reuse the existing review UI rather than adding a parallel dispatcher.

No production source, credentials, provider settings or subscriptions were changed in this preparation. The active TextBee subscription remains as found. Its current reply-handling limitation is a blocker, not an accepted inbound service.

## Prepared review profile

The profile leaves provider, sender, reply-to, message, audience digest, expiration and approvals unset. IONOS account1 is nominated only as a candidate, based on authentication and matching domain configuration. The existing saved provider remains Resend.

The future pilot proposal is **one channel, one provider, at most five unique permission-qualified parent/guardian destinations total per approval**, no automatic fallback, and no automatic retry. A first delivery test would require separate approval for one internal recipient. Proposed approvals expire30 minutes after issue and are single use. **These limits are proposals, not implemented enforcement.** No approval was issued and no timer or queue was started.

Current production workflow tables contain zero parent/guardian records, permission-evidence records, drafts and review events. No approved pilot audience or exact message is prepared. Historical SMS recipients, uploaded recruiting guides and earlier campaign activity were not promoted into consent or re-imported. Their preservation is separate from this empty new workflow.

Before any later activation, Dennis and the operator need to review:

- The exact sender display name, mailbox authority and reply destination, including who monitors replies.
- The exact parent/guardian audience, verified relationship, channel-specific permission evidence, common suppressions and duplicate/shared-number decisions.
- Exact subject/body/personalization, approved website destination, recruiting/endorsement claims, and whether to include the still-unreviewed promotional video.
- For commercial email, the business identification, valid postal address and functional opt-out text/link. SMS identification and opt-out handling must be tested without enrolling historical contacts by assumption.
- The separately implemented cap, expiry, cancellation, durable reservation and receipt behavior, followed by an explicitly approved internal delivery and reply/STOP test.

For this project, preparing or recording a review cannot release the source hold. No bulk campaign, background polling, legacy drip or swarm is admitted by this document.

## Verification and retained evidence

- **52 existing focused synthetic checks passed**, with one existing Starlette deprecation warning. They cover workflow permissions, review freshness, suppression, registration intake and private inbox/timeline. The hold-overrides-enabled-environment test passed. These are controller/application checks, not live sending or delivery acceptance.
- Domain checks used public DNS and unauthenticated root HEAD/TLS only. SMTP used EHLO/STARTTLS/AUTH/NOOP/QUIT; IMAP used LOGIN/NOOP/LOGOUT. Provider API checks used authenticated metadata GET with redirects disabled. No MAIL/RCPT/DATA, provider send endpoint, mailbox message read or webhook replay was used.
- Existing source hold is true; six current backend activation controls are false. Core listeners were observed on `127.0.0.1`; Unreal signaling8888 was absent. No restart, deployment, DNS/tunnel change or VM operation occurred.
- The initial diagnostic refused an unexpected working-directory assumption before network access. Fresh backend identity confirmed its actual `backend` directory and the audit was corrected. The original failure, two primary-SMTP failures and all successful observations are retained.
- Evidence: `backups/recdebut_send_setup_20261027_record152/`, including `connection_results.json`, `smtp_followup.json`, `domain_checks/observations.json`, `source_review/provider_free_review.json`, `source_review/workflow_readiness_aggregates.json` and `focused_tests.txt`. Before/after hashes and preservation checks accompany checkpoint finalization. Cloud engineering-ledger synchronization remains pending.

## Reference guidance

Provider/domain requirements were checked against the [Resend domain-list API](https://resend.com/docs/api-reference/domains/list-domains), [TextBee API](https://textbee.dev/docs/api-reference) and [signed webhook documentation](https://textbee.dev/docs/webhooks). Google's [sender guidelines](https://support.google.com/mail/answer/81126) distinguish general SPF-or-DKIM requirements from stricter bulk requirements; this preparation requires verification of SPF, DKIM and DMARC alignment before choosing a branded sender. The [FTC commercial-email guide](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business) informs identification, postal-address and opt-out review. This is a preparation checklist, not a claim that the current system has met every applicable requirement.

Checkpoint allocation: this review is Record153. The retained evidence directory keeps its initial `record152` task name; the separate E-drive assessment owns Record152.
