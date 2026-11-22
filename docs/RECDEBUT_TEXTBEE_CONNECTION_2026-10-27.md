# RecDebut TextBee connection verification

Checkpoint: Record157. Verified: 2026-10-27T18:52:21.448532+00:00.

The supplied API key is configured privately and active in the AI-BS backend. The existing registered RecDebut phone and webhook were reused. Sending remains disabled.

| Check | Measured result |
| --- | --- |
| Registered device authenticated GET | HTTP200; selected device matches; enabled and receive SMS enabled |
| Webhook authenticated GET | HTTP200; existing inbound subscription active; signing secret matches backend |
| Local/public workflow | Authenticated HTTP200; sending_enabled=false; Cache-Control no-store |
| Unauthorized local workflow | HTTP403 |
| Unsigned public webhook | HTTP401; no valid event submitted |
| Private backend configuration | Saved/running supplied key matches; protected file ACL verified |
| Preservation | Existing RecDebut/swarm rows unchanged; quick_check ok; source and other services preserved |
| Activation | Review hold true; six flags false; loopback bindings retained;8888absent |
| Communications/provider mutations | Zero messages sent; zero provider-setting mutations |

The provider dashboard screenshots are useful context, but its delivered rows do not prove storage in AI-BS. A real incoming phone reply still needs to be observed through TextBee and the RecDebut inbox. Historical messages were not imported; existing synthetic live acceptance remains separately labeled.

## Retained execution and recovery evidence

Commands: `python backups/recdebut_textbee_key_20261027/configure_key.py` and `python backups/recdebut_textbee_key_20261027/verify_current.py`. No secret arguments. See setup_receipt.json, final_verification.json, before_manifest.json and checkpoint_manifest.json for measured identities, statuses and SHA-256 values. The unique protected recovery directory holds an encrypted DPAPI configuration original, original security descriptor and private online database backups. No recovery was invoked.

Two distinct preparation failures were retained before configuration promotion: persisted-work classification assertion and unsupported Windows descriptor method. Source inspection, a descriptor round trip and private ACL probe resolved them. An independent read-only review found two recovery gaps; guarded promotion and immediate owned-child tracking were added before the successful setup. No production source modification or Firebase release was needed for this configuration change.

Sending, polling and automatic acknowledgments remain disabled pending Dennis/operator review. Provider metadata checks do not establish consent or sending eligibility. Shared suppression and exact reviewed dispatch controls remain prerequisites. Cloud ledger synchronization remains pending.
