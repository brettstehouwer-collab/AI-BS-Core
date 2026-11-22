# AI-BS Oracle Hot Standby — Deployment & Rollback Guide (`DEPLOYMENT_AND_ROLLBACK.md`)

**Document ID**: `AI-BS-HA-OCI-001-DEPLOY`  
**Owner**: Brett Stehouwer  
**Target Environment**: Windows Primary (`C:\AI-BS`) + OCI `us-chicago-1` (`VM.Standard.A1.Flex`, ARM64 Linux)  

> **Authorization Boundary**: Procedures below prepare concrete production transitions. Executing any step that restarts live services, changes Scheduled Tasks/Defender, runs Resource Manager `PLAN`/`APPLY`, provisions infrastructure, or switches gateway credentials requires explicit operator authorization first.

---

## 1. Local Dual-Key Credential Isolation Setup (Windows Primary)

1. **Verify Read-Only Key Permissions on Crypto.com Exchange**:
   - Ensure the Read-Only observer key has **Read-Only ON**, **Can Trade OFF**, **Enable Withdraw OFF**, and allowlists your static Windows / OCI IP(s).
   - *(Note: Because the Read-Only key + secret were pasted in chat earlier, rotate that pair before production cutover and store the fresh key locally only.)*
2. **Store Read-Only Pair in Windows DPAPI** (Run interactively in local PowerShell; secret never enters chat/files):
   ```powershell
   & "C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe" C:\AI-BS\scratch\store_readonly_dpapi.py
   ```
   Verify without printing secrets:
   ```powershell
   & "C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe" C:\AI-BS\scratch\store_readonly_dpapi.py --verify-only
   ```
3. **Result**: `agent4_risk_watchdog.py` and passive standby observers load `C:\AI-BS\backups\crypto_readonly_dpapi.json` inside `PassiveStandbyClient`, isolated from the trade-capable gateway DPAPI key.

---

## 2. Staged Rollout Sequence (Authorized Steps Only)

### Stage A — Restart Stale Windows Supervisor (`PID 23296`) & Legacy OCI Claimer (`PID 42264`)
- **Prerequisite**: Confirm all offline fault tests & regression checks (`test_m2_trading_engine.py`, `test_local_ollama_http.py`, `test_ha_fault_matrix.py`) pass cleanly.
- **Steps**:
  1. Stop stale `oci_stack_claimer.py` (`PID 42264`) and stale `aibs_24x7_supervisor.py` (`PID 21372`/`23296`) ONLY (do not interrupt `:8007` trading engine `PID 50320` unnecessarily; it already holds the 3 `POST_ONLY` `SELL` orders).
  2. Run `oci_stack_claimer.py --check-only --profile DEFAULT` to verify clean inspection and atomic status generation (`oci_claimer_status.json`).
  3. Launch updated `aibs_24x7_supervisor.py` via `C:\AI-BS\Start_24x7_Master_Supervisor.bat`.
- **Expected Outcome**: Stops the 360+ `cloudflared` respawn churn loop (restoring `https://api.brettstehouwer.live` tunnel health) and switches OCI claiming cleanly to Resource Manager-only (`oci_controller_state.json`).

### Stage B — Windows Boot Persistence & Targeted Security Remediation
1. **Replace Startup-Folder Pre-Logon Gap**:
   - Create a Windows Scheduled Task running at startup under the exact DPAPI-owning user principal (`ai-bs\administrator`) with `S4U` / highest-needed logon configuration so recovery works even before interactive desktop sign-in **without exporting DPAPI credentials to plaintext**.
   - Launch supervisor in safe boot passive mode (`AIBS_SAFE_RECOVERY_MODE=passive`) after unplanned reboots (`OPS-01`) unless explicit primary re-authorization is confirmed.
2. **Targeted Windows Defender / Smart App Control Remediation**:
   - Replace blanket `C:\AI-BS` Defender exclusion with targeted exclusions ONLY for validated runtime executables/data directories if needed, after verifying `recovery-20261110\Scripts\python.exe`, `sqlite3`, and `pure_rsa_sha256.py` run cleanly with Defender active. Never disable Windows Defender or TLS verification.

### Stage C — Reviewed OCI Resource Manager `PLAN` -> `APPLY` & Cost Controls
- **Cost & Eligibility Policy** (`C:\AI-BS\deploy\oci_standby\oci_plan_policy.json`):
  - Region: `us-chicago-1`
  - Shape: `VM.Standard.A1.Flex`, max `1 OCPU`, `6 GB RAM`, `50 GB` boot volume, `max_instances = 1`, `paid_spend_authorized = false`.
  - **Caveat**: Confirm live tenancy Always Free eligibility in Oracle Cloud Console and configure an OCI Budget alert (`[S3]`) — budgets alert softly rather than acting as a hard billing cap; enforce hard limits via IAM policies/compartments/quotas + reviewed Terraform plans.
- **Workflow**:
  1. Run `oci_stack_claimer.py --check-only --profile DEFAULT`.
  2. Submit one **Resource Manager `PLAN`** job against the stack, inspect the Terraform plan output to confirm **1 create / 0 deletes / 0 paid substitutes / narrow ingress**, and pin its hash in `oci_plan_policy.json` (`expected_plan_hash`).
  3. Authorize `oci_stack_claimer.py` controller (`20-minute` minimum retry cadence preserved across restarts).

### Stage D — ARM64 Standby Installation & Readiness Qualification
1. Copy `scratch/*.py` and `deploy/oci_standby/` to the provisioned `aarch64` Ubuntu 24.04 / OL9 VM (`/opt/ai-bs/`).
2. Run `sudo bash /opt/ai-bs/deploy/oci_standby/install_standby.sh`.
3. Pin the OCI VM's static egress IP on Crypto.com Exchange's Read-Only key allowlist and populate `/etc/aibs/standby-readonly.env` (`chmod 0640 root:aibs-standby`).
4. Configure private WireGuard or SSH port-forward between Windows primary (`AI-BS`) and OCI VM.
5. Verify **Application Readiness** separately from VM running state:
   - `systemctl start aibs-standby` -> verify `/health` returns `role="PASSIVE"`, `exchange_read_access=true`, and any attempted mutation raises `PassiveAuthorityError`.
   - Start `aibs-backup.timer` and test `backup_and_restore.py --verify-restore ...` into a temp directory (`OPS-03`).

### Stage E — Controlled Stage 1 Exclusive Gateway Cutover
1. Keep **manual promotion only** (`auto_promote_enabled = false`).
2. Populate `/etc/aibs/gateway-trade.env` (`chmod 0600 aibs-gateway:aibs-gateway`), start `aibs-gateway.service` bound exclusively to private WireGuard/loopback interface.
3. Point `structural_dip_engine.py` on Windows at `ExecutionGateway`, verify live `CREATE`/`CANCEL` journal recording in SQLite WAL, and **only after verification** remove bypass trade keys from Windows strategy hosts.

---

## 3. Specific Per-Change Rollback Procedures

> **Universal Rollback Invariant**: Rolling back code, systemd units, or SQLite snapshots **never restores permission to trade**. Every rollback starts `structural_dip_engine.py` in `PASSIVE` mode, reads live open orders/balances/fills directly from Crypto.com Exchange, reconciles any `UNKNOWN` intents, and requires an incremented `authority_epoch` before resuming live mutations.

| Change | Prerequisites for Rollback | Exact Rollback Steps | Consequences & Constraints |
| --- | --- | --- | --- |
| **1. Supervisor & Claimer Restart (Stage A)** | Save pre-restart `master_supervisor_status.json` & `oci_claimer.log` evidence | Stop updated supervisor/claimer; restore prior scripts from git/backup; restart `Start_24x7_Master_Supervisor.bat` | Prior `cloudflared` churn may return unless `--config` flag retained; never leave legacy direct `LaunchInstance` active without operator intent |
| **2. Structural Dip Engine HA Integration (Stage E)** | Pause engine cleanly; leave 3 resting `POST_ONLY` orders untouched on Crypto.com | Launch `structural_dip_engine.py --role passive` first; verify `open_orders` & `tracked_orders` match; fence gateway epoch (`role=FENCED`); restore prior script only if needed and audit `trade_ledger.db` | Do **not** restore bypassed trade keys onto multiple hosts simultaneously; reconcile any `UNKNOWN` gateway intents first |
| **3. Agent 4 Dual-Key Read-Only Cutover** | Retain `crypto_readonly_dpapi.json` separately | Point `AIBS_READONLY_CRED_FILE` back or inspect `agent4_risk_watchdog.log`; keep `PassiveStandbyClient` wrapper | Zero trading disruption (watchdog never mutates orders) |
| **4. OCI Standby Package / VM Deployment (Stage C/D)** | Preserve logs & `/var/lib/aibs-gateway/authority_journal.db` backup | Stop `aibs-standby` and `aibs-gateway` (`systemctl stop`); keep Windows primary authoritative on new epoch; **do NOT destroy cloud resources or roll back Terraform state as a shortcut** | Preserves audit trail and prevents orphaned OCI resources; VM teardown is a separate operator action |
| **5. Authority Store / Backup Restore** | Preserve corrupt DB copy for forensics | Run `backup_and_restore.py --verify-restore <bak> --dest-dir <path> --expected-sha256 <sha>`; verify `role=PASSIVE`; reconcile live exchange orders/fills before promoting new epoch | Async RPO > 0 means fills after last backup must be reconstructed directly from Crypto.com `private/get-open-orders` & `private/get-trades` |
