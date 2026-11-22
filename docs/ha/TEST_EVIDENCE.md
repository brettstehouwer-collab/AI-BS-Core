# AI-BS Oracle Hot Standby — Test Evidence (`TEST_EVIDENCE.md`)

**Document ID**: `AI-BS-HA-OCI-001-TEST-EVIDENCE`  
**Captured At (UTC)**: `2026-11-19T18:05:00Z`  
**Host**: `AI-BS` (Windows 11 Home Build 26300, `C:\AI-BS`)  
**Git Branch / Base Revision**: `codex/audit-v532976-20261031` @ `64fad2871e0a716d9964f506bdef1050612b173d`  
**Python Runtime**: `C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe` (Python `3.12.14`)  

> **Truthfulness & Evidence Boundary**: All fault-matrix scenarios (`HA-01`..`HA-08`, `OCI-01`..`OCI-08`, `OPS-01`..`OPS-03`, RSA signer) passed **offline** using isolated temporary SQLite WAL stores, deterministic mocks (`FakeExchange`, `FakeOciTransport`, `FakeClock`), and disposable ephemeral RSA-2048 keys (`OFFLINE_PASS`). Live production cutover and remote ARM64 VM verification remain **`NOT_VERIFIED`**.

---

## 1. Post-Edit Verified File Inventory & SHA-256 Hashes

| File | Size (bytes) | Post-Edit SHA-256 |
| --- | ---: | --- |
| `C:\AI-BS\scratch\ha_execution_gateway.py` | 80,675 | `924a9e0c6881c45dbdbe316897deb4732ccafd8d55a787bf173e5b66cff2bf2e` |
| `C:\AI-BS\scratch\store_readonly_dpapi.py` | 3,062 | `075183d69893f29cd6beb0f52c08a82832678bb159c0ab884e5daf61121aef5d` |
| `C:\AI-BS\scratch\structural_dip_engine.py` | 72,864 | `abfe1c32e6d38d5a85388cd376d312d02868346ae0040d5fb540e201c124cde3` |
| `C:\AI-BS\scratch\agent4_risk_watchdog.py` | 17,150 | `81d7e7d66cb05d4f6a074dc1214163196abda42bed71e9351ee64e69b9743ba` |
| `C:\AI-BS\scratch\aibs_24x7_supervisor.py` | 15,764 | `b5ff503b049ec6165daeb0a01f744532887d443cd24d4f11f78121253e0f5990` |
| `C:\AI-BS\scratch\pure_rsa_sha256.py` | 6,342 | `69578b66ce283204d7b0547b29ab17503afe443a1469cd8ed8700eb3824bf832` |
| `C:\AI-BS\scratch\oci_stack_claimer.py` | 51,649 | `992b1cde961b809ca3b39e427fcb88e9fc589dbef94e3a551f04076d078b042b` |
| `C:\AI-BS\deploy\oci_standby\backup_and_restore.py` | 3,735 | `33fc201647a0372873283fa045f75fc781cba3e04fe62eb523b75b4082ac67a1` |
| `C:\AI-BS\deploy\oci_standby\oci_plan_policy.json` | 554 | `e5d3ca1b56ebf33e9fe43f5058dffcd49d5f5e789fef77f928c38c6cafcfad49` |
| `C:\AI-BS\deploy\oci_standby\install_standby.sh` | 2,676 | `bf33d1cd134d3558291c6d139e7df04d4f086e8dc99fb932390a091f2849d0ea` |
| `C:\AI-BS\tests\ha\test_ha_fault_matrix.py` | 52,216 | `885945be299a70b2215a81f6008dff51eb9e75a0ef8591aac506462b94c5ca27` |

---

## 2. Executed Commands & Observed Summary Results

| Suite / Check | Exact Command | Outcome | Observed Result |
| --- | --- | --- | --- |
| **HA / OCI / OPS Fault Matrix** | `& "C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe" -m unittest discover -s C:\AI-BS\tests\ha -p "test_*.py" -v` | `OFFLINE_PASS` | **20/20 OK** (`11.193s` after final edit) |
| **M2 Trading Engine Regression** | `& "C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe" C:\AI-BS\scratch\test_m2_trading_engine.py` | `OFFLINE_PASS` | **11/11 OK** (`1.030s` after all engine/watchdog edits) |
| **Ollama HTTP Regression** | `& "C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe" C:\AI-BS\scripts\tests\test_local_ollama_http.py` | `OFFLINE_PASS` | **10/10 OK** (`0.518s`) |
| **Isolated Read-Only OCI Inspection** | `oci_stack_claimer.py --check-only --profile DEFAULT --state-file <temp> --status-file <temp> --lock-file <temp>` | `LIVE_VERIFIED` *(read-only)* | **Exit 0** (`31,240.2 ms`): `inspection_ok=true`, HTTP `200`/`200`/`200`, `active_instances=[]`, `unmanaged_instances=[]`, `nonterminal_jobs=[]`, zero mutations |
| **Local DPAPI CLI Smoke** | `store_readonly_dpapi.py --help` & `backup_and_restore.py --help` | `OFFLINE_PASS` | Clean CLI usage & exit `0` |

---

## 3. Section 8 Fault-Test Matrix Detailed Mapping (`test_ha_fault_matrix.py`)

| Scenario ID | Test Function | Key Assertions Verified | Observed Status |
| --- | --- | --- | --- |
| `HA-01` | `test_HA_01_primary_returns_with_old_epoch` | Epoch-1 create/cancel rejected with `StaleEpochError` after promotion to epoch 2+; recovering primary forced to `PASSIVE` and denied with `PassiveAuthorityError` | `OFFLINE_PASS` |
| `HA-02` | `test_HA_02_old_command_queued_during_promotion` | In-memory & SQLite-persisted epoch-1 queued commands aborted before dispatch (`StaleEpochError`, `0` exchange mutations) across promotion and store restart | `OFFLINE_PASS` |
| `HA-03` | `test_HA_03_exchange_accepts_but_response_lost` | Timeout marks intent `UNKNOWN`, blocks follow-up orders (`UnresolvedIntentError`), blocks manual promotion (`GateBlockedError`), clears cleanly after exchange reconciliation | `OFFLINE_PASS` |
| `HA-04` | `test_HA_04_partial_fill_during_handoff` | Partial fill `300/714` reconciled (`remaining=414`, PnL `0.108000`, 50% reserve `0.054000`), duplicate fill key ignored, final `414` fill completes exact totals (`0.257040` / `0.128520`) | `OFFLINE_PASS` |
| `HA-05` | `test_HA_05_gateway_restart_mid_request` | `SUBMITTING` intent persisted prior to simulated crash survives DB reopen, blocks new orders until `reconcile_unresolved_intents` resolves against exchange | `OFFLINE_PASS` |
| `HA-06` | `test_HA_06_lease_unavailable_or_clock_jump` | Lease unavailability and `+120s` wall-clock jump trigger `GateBlockedError` + `CLOCK_JUMP` alert; zero self-promotion | `OFFLINE_PASS` |
| `HA-07` | `test_HA_07_journal_unwritable_or_replica_stale` | Stale replica, read-only SQLite URI, and directory DB path raise `JournalDurabilityError` with `0` mutations and `journal_durable=false` / `application_ready=false` | `OFFLINE_PASS` |
| `HA-08` | `test_HA_08_passive_host_and_engine_deny_all_mutations` | `PassiveStandbyClient` denies create/amend/cancel/bulk/rearm/emergency (`6` denials, `0` mutations); `structural_dip_engine.run_cycle(..., role="passive")` stays read-only; active gateway path logs `ACKED` intents | `OFFLINE_PASS` |
| `RSA-SIGN` | `test_pure_rsa_sha256_disposable_keys_pkcs1_pkcs8_and_validation` | Ephemeral RSA-2048 PKCS#1 + PKCS#8 signatures cross-verified against independent `cryptography` library; encrypted PEM and `<2048`-bit keys raise `ValueError` | `OFFLINE_PASS` |
| `OCI-01` | `test_OCI_01_paginated_empty_then_nonempty_page` | Paginates `[] -> [] -> [target_vm]` via `opc-next-page`, enters `MONITOR`, emits `0` `POST` calls | `OFFLINE_PASS` |
| `OCI-02` | `test_OCI_02_listing_errors_and_malformed_json` | HTTP `401`, `403`, `429`, `503` and malformed JSON set `inspection_ok=false` (`0` "no instances" false positives); `--check-only` exits non-zero on error | `OFFLINE_PASS` |
| `OCI-03` | `test_OCI_03_create_job_response_lost_reconciled` | Lost `POST /20180917/jobs` persists `SUBMISSION_UNKNOWN`; next cycle matches job by persisted `operation_id` without issuing duplicate `POST` (`post_count == 1`) | `OFFLINE_PASS` |
| `OCI-04` | `test_OCI_04_partial_success_or_unmanaged_or_lost_vm` | Active job (`IN_PROGRESS`), unmanaged VM (`MANUAL_REVIEW_UNMANAGED_VM`), and missing prior instance (`OUTAGE_RECOVERY_REQUIRED`) all block new `APPLY` | `OFFLINE_PASS` |
| `OCI-05` | `test_OCI_05_two_controller_processes_single_owner` | Second `ControllerLock` returns `LOCK_HELD_BY_ANOTHER_CONTROLLER` cleanly with `0` mutations | `OFFLINE_PASS` |
| `OCI-06` | `test_OCI_06_restart_preserves_20min_retry_schedule` | Capacity failure sets `1200s` cooldown; reloaded state at `+300s` enforces `900s` remaining; backward `-600s` clock jump returns `CLOCK_JUMP_DELAY` (`1200s`) before allowing retry after window elapses | `OFFLINE_PASS` |
| `OCI-07` | `test_OCI_07_unknown_job_state_or_failed_get_job` | HTTP `500` or missing `lifecycleState` on `GetJob` stays `JOB_STATE_UNKNOWN` and blocks duplicate `APPLY` | `OFFLINE_PASS` |
| `OCI-08` | `test_OCI_08_wrong_profile_region_or_plan_cost_blocked` | Missing profile, `us-ashburn-1` profile vs `us-chicago-1` stack, and `VM.Standard.E4.Flex` `8` OCPU variable halted (`0` `POST` calls) | `OFFLINE_PASS` |
| `OPS-01` | `test_OPS_01_primary_reboot_safe_passive_recovery` | Supervisor launches trader `--role passive` under `safe_recovery_mode=True` and never relaunches `oci_stack_claimer` in `MONITOR`/`HALT`/`MANUAL_REVIEW`/`OUTAGE_RECOVERY_REQUIRED` | `OFFLINE_PASS` |
| `OPS-02` | `test_OPS_02_status_or_alert_write_failure_visible` | Unwritable directory targets across supervisor, dip engine (`save_state` & `send_alert`), watchdog, and OCI claimer visibly report `status_write_ok=false` / `CRITICAL` / `AuditWriteError` | `OFFLINE_PASS` |
| `OPS-03` | `test_OPS_03_backup_restore_disposable_env_stays_passive` | `backup_and_restore.py` (`sqlite3.Connection.backup()`) restores into disposable dir with SHA-256 + `PRAGMA integrity_check == ok`, exact fill/intent counts, and `role=PASSIVE` (`auto_live_disabled=true`) | `OFFLINE_PASS` |

---

## 4. Measured Offline Timings vs. Live RPO / RTO Status

- **Offline Authority Promotion Latency** (`AuthorityStore.acquire_or_promote`, local SSD): **`1.26 ms`**
- **Offline SQLite Consistent `.backup()` + SHA-256 + Passive Restore Verification** (`OPS-03`): **`26.55 ms`** (`PRAGMA integrity_check = ok`)
- **Live End-to-End Failover RTO (Windows Primary -> OCI Standby)**: **`NOT_MEASURED`** *(awaiting OCI VM provisioning, WireGuard tunnel, and live Stage 1 drill)*
- **Live Replication Lag / RPO**: **`NOT_MEASURED`** *(async SQLite `.backup()` interval configured at 5m timer in systemd package; RPO > 0 expected until measured live)*
