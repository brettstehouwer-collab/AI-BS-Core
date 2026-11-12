# RecDebut TextBee public webhook acceptance - 2026-10-27

All 25 checks passed for host-signed synthetic events through the production HTTPS webhook. Actual TextBee device/carrier delivery remains unverified. SMS and email sending remain disabled pending Dennis/operator review.

Attempt: `20261027T182754Z_404b2b1b`. Live interval: 2026-10-27T18:27:54.105623+00:00 to 2026-10-27T18:28:01.530324+00:00. Public endpoint: `https://recdebut-recruit.org/api/v1/recdebut/webhooks/textbee`.

## Measured results

| Case | Actual result |
| --- | --- |
| Active provider subscription | Authenticated read found exactly one active expected MESSAGE_RECEIVED subscription; no settings changed |
| Unsigned public event | HTTP 401 |
| Signed ordinary reply | HTTP 200, stored, forwarding false, sending false |
| Identical reply replay | HTTP 200, duplicate true, no additional records |
| Changed content under reused identity | HTTP 409, no additional effects |
| Signed STOP | HTTP 200, retained reply, persistent suppression, family opt-out event |
| STOP replay | HTTP 200, duplicate true, no additional effects |
| START after STOP | HTTP 200, retained as reply; suppression remains and permission stays unknown |
| Invalid signature | HTTP 401, no additional records |
| Public authenticated RecDebut API | Three fixture replies with exact expected bodies; three inbound timeline events |
| Held draft preview | Blocked for unverified relationship, unknown channel permission and suppression; audience digest changed |
| Existing data | Every pre-existing row retained unchanged; additions only |
| Runtime/source preservation | Owned service identities unchanged, six controls false, review hold true, loopback services and no 8888 listener; source/configuration/AGENTS digests unchanged |

The retained synthetic fixture uses unused reserved number `2025550199`; it was collision-checked against athlete, workflow, personal-contact and suppression records. Family `test_textbee_family_20261027T182754Z_404b2b1b`, parent `test_textbee_parent_20261027T182754Z_404b2b1b` and held draft `test_textbee_draft_20261027T182754Z_404b2b1b` remain labeled TEST ONLY / never contact. No real athlete record or permission was invented. Added records: three replies, three receipts, one suppression and six family-history events (three saves plus three inbound events). These are fixture counts, not totals for the database.

## Actual browser verification

The existing Brett administrator session restored on the deployed [RecDebut workspace](https://ai-bs-dashboard.web.app/?tab=rec_debut). No credential entry or authentication change was needed; this does not establish a fresh Google sign-in flow.

- Families & athletes / Timeline shows two `sms_reply_received` events and one `sms_opt_out_received` event for the test family.
- Suppression register shows the reserved test destination and TextBee STOP reason.
- Results & work log / Load existing records / View retained replies shows the ordinary test body, STOP and START (reply IDs 30, 31 and 32).
- Review hold banner remains visible. SMS and email permissions remain unknown.

Evidence: `backups/recdebut_textbee_live_20261027/ui_replies.txt`, `ui_family_timeline.txt`, and `ui_family_timeline.png`. No formal browser-console audit or new frontend deployment is claimed.

## Commands and retained evidence

Executed from `C:\AI-BS`:

```powershell
python backups/recdebut_textbee_live_20261027/preflight.py
python backups/recdebut_textbee_live_20261027/run_live.py
python backups/recdebut_textbee_live_20261027/finalize_checkpoint.py
```

Preflight and live execution passed on the first attempt. The 25 checks include setup and preservation assertions: the live runner made seven webhook POSTs (ordinary/replay/conflict/STOP/STOP replay/START/invalid signature), plus the preflight unsigned probe. The live runner is evidence, not an automatic replay instruction: it has an existing-backup guard and must not be re-run against retained output. Raw request and response SHA-256 values and each assertion are retained in `live_results.json`. Credentials stayed in memory and were not placed in command arguments, logs or reports.

Online SQLite backup: private owner-protected `backups/recdebut_textbee_live_20261027/private/rec_debut_before.sqlite`, SHA-256 `96285c2d79aa8eba7630ef41a14ecef435b935d7360803d255acfe688d341c5b`. This contains private production records and must not be copied into a release or cloud ledger. Historical document prefixes are checked against `before_manifest.json`; full pre-append document copies, before/after hashes and final evidence digests are retained locally.

## Boundaries and remaining prerequisites

No SMS/email, provider-setting mutation, polling activation, automatic acknowledgment, deployment, service restart or VM action was performed. No-send evidence is the inspected request paths, review hold, disabled controls and webhook responses; no independent provider billing/carrier-log audit was performed. Existing Record154 implementation and Record155 Hosting release remain in place; no repair was needed for this acceptance run. The 101 offline checks in Record154 are separate historical infrastructure evidence, not additional tests run here.

This proves the public HTTPS endpoint, signed intake, durable storage, suppression, authenticated read APIs and deployed UI path with synthetic inputs. It does not prove real phone -> TextBee application -> provider delivery, carrier delivery, production sending readiness or all future dispatch paths. A later operator/device test can establish provider-originated delivery while preserving the outbound hold. Legacy dispatch selectors still require shared suppression reconciliation and exact reviewed sender/audience/permission/message/limits/retry controls before any sending activation. Website registration remains unconfigured pending site access. Cloud engineering-ledger synchronization remains pending.
