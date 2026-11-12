# RecDebut website registration connection

Status: AI-BS receiver implemented and tested with synthetic data. Website installation and actual registration acceptance remain pending website administrator access. Sending remains disabled until Dennis and Brett separately review it. This connection does not enable messages, payments or endorsements.

## What the website administrator needs to do

The public basketball registration page uses an Elementor form. Its footer also contains a separate newsletter form. Select the exact registration page/post and form widget identities; do not select by the generic name “New Form.” Inventory and approve each additional sport form individually.

Before testing, review the selected form's existing submit actions, notifications, marketing hooks and payment actions. Disable outbound messages for the test workflow on the website too: AI-BS cannot block WordPress or another provider's independent sending. Preserve the existing form and submissions. Do not change the live form until its configuration and recovery copy have been reviewed.

Configure a server-side connection to the AI-BS route below. Never put the signing secret in a browser form, JavaScript, a URL, a shared document, source control or Firebase static hosting. No WordPress plugin has been installed or verified by this work.

The website must durably retain submissions and a delivery outbox. Generate one UUID per submission, retain the exact event payload, and retry that event after temporary failures. A website success page must not imply AI-BS received a queued event. Retry timeouts/5xx with bounded backoff; retain 4xx failures for staff review. Do not generate a fresh event ID for a retry.

## Receiver contract, version 1

POST `/api/v1/recdebut/webhooks/registration` through the separately verified HTTPS backend origin. Firebase Hosting's static dashboard address is not itself proof of a working backend route. No public origin is certified by this preparation.

Server configuration required before activation:

- `RECDEBUT_REGISTRATION_SECRET`: unique cryptographically random secret of at least 32 characters, provisioned privately on the website server and AI-BS server. No secret was generated or installed by this task.
- `RECDEBUT_REGISTRATION_FORMS`: comma-separated exact approved form references, for example `post:123/widget:abc123`. Confirm actual identities in WordPress first. No forms are currently approved by this task.

JSON payload (UTF-8, maximum 16 KiB):

```json
{
  "schema_version": 1,
  "event_id": "11111111-1111-4111-8111-111111111111",
  "source": "https://recdebut.com",
  "form_reference": "post:123/widget:abc123",
  "athlete_name": "Synthetic Athlete",
  "sport": "Basketball",
  "grad_year": "2027",
  "school": "",
  "athlete_email": "",
  "athlete_phone": "",
  "guardian_name": "Synthetic Parent",
  "guardian_email": "parent@example.test",
  "guardian_phone": ""
}
```

All contact fields are optional except athlete name. Missing optional values are unknown. Unknown fields are rejected. Do not transmit birth dates, addresses, medical data, academic scores, uploads, card information or marketing consent claims through this version.

Headers:

- `Content-Type: application/json`
- `X-RecDebut-Timestamp`: decimal Unix UTC seconds, within 300 seconds of the receiver clock.
- `X-RecDebut-Signature`: lowercase hex HMAC-SHA256 using the dedicated secret over `timestamp + "." + exact raw UTF-8 body bytes`.

Sign a fresh timestamp on retries while preserving the event ID and payload. Accepted retry returns `duplicate:true` without adding another case. Same event ID with different normalized payload returns 409. Different event IDs are separate submissions; staff must reconcile repeat registrations. Shared guardian contact details do not merge families automatically.

Successful response includes `accepted:true`, `duplicate`, `family_id`, and `sending_enabled:false`. It means the private casework transaction committed. It does not establish identity, consent, delivery, payment, enrollment or an endorsement.

Responses: 401 invalid/expired signature; 403 unapproved form; 409 changed event; 413 oversized request; 422 invalid fields; 503 connection or form approval missing. Response messages do not echo submission data.

## Initial mapping to verify with administrator

Observed basketball fields: athlete name `name`; athlete email `email`; athlete phone `field_68dd24e`; guardian name `field_ac88a70`; guardian phone `field_a85dbbb`; guardian email `field_33a4127`; graduation year `field_ee2254c`; school `field_7048021`. These public observations are provisional. Verify actual form IDs and values before installation; other sports may differ. Footer newsletter must be excluded.

AI-BS creates a family, athlete and optional guardian contact, a registration review task, and an audit receipt in one transaction. Channel permissions and guardian relationship remain unknown for staff review. Existing suppression records remain effective.

## Acceptance still required

1. Website administrator reviews configuration, backups, approved forms and all independent notification actions.
2. Establish and verify the actual HTTPS backend route, server-only secret storage and exact form allowlist.
3. Submit one clearly synthetic registration and confirm it appears in AI-BS Families and Today; verify no email, SMS, endorsement or payment action occurs on either system.
4. Verify duplicate retry, changed-event rejection and an offline-then-recovered website outbox delivery.
5. Record evidence without copying private registration data or secrets into engineering logs.

Website installation, public-route availability, outbox recovery and genuine website-to-AI-BS acceptance have not been completed. Local workstation availability remains a business reliability dependency.

## Historical outreach evidence

The operator supplied a past report describing TextBee, several email routes, campaign queues and link tracking. Retain it as historical reported activity. Its active-service, delivered, human-click and consent claims were not verified by this connection work. Queued, provider-accepted, delivered, registered and paid remain separate measures. No credential fragments or recipient details from that report are copied into this handoff.
