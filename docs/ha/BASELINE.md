# AI-BS Oracle Hot Standby — Baseline (`BASELINE.md`)

**Document ID**: `AI-BS-HA-OCI-001-BASELINE`  
**Captured At (UTC)**: `2026-11-19T17:34:40Z`  
**Execution Brief**: [`docs/AI-BS_Oracle_Hot_Standby_Agent_Execution_Prompt.md`](../AI-BS_Oracle_Hot_Standby_Agent_Execution_Prompt.md) (`AI-BS-HA-OCI-001-AGENTS`, Rev 1.0)  
**Assessment Scope**: Local Windows primary host inspection + read-only local API/file observations + non-secret OCI configuration inspection. Zero unauthorized live exchange mutations, restarts, or OCI mutations performed.

---

## 1. Verified Host, OS, Runtime & Repository State

| Item | Verified Value |
| --- | --- |
| **Host Name** | `AI-BS` |
| **OS Edition / Build** | Microsoft Windows 11 Home (`10.0.26300 N/A Build 26300`, `x64-based PC`) |
| **Project Root** | `C:\AI-BS` |
| **Git Branch** | `codex/audit-v532976-20261031` |
| **Git HEAD** | `64fad2871e0a716d9964f506bdef1050612b173d` (shared dirty working tree; unrelated local changes preserved untouched) |
| **Applicable Instruction Files** | `C:\AI-BS\AGENTS.md`, `C:\AI-BS\.agents\AGENTS.md`, `C:\AI-BS\docs\CODEX_HANDOFF.md` (all preserved intact) |
| **Python Runtime** | `C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe` — Python `3.12.14` (`cryptography 49.0.0` installed; `openssl` binary not on PATH) |
| **HA Target Doc Folder (`docs/ha/`)** | Absent prior to Phase 0 creation |

> **Evidence Scope Rule**: Localhost checks (`127.0.0.1`) were executed directly on host `AI-BS`. They apply strictly to host `AI-BS` and do **not** verify any remote ARM64 Linux VM.

---

## 2. Pre-Edit Source & Launcher SHA-256 Baseline Hashes

Captured prior to any Phase 1–4 code edits:

| File Path | Size (bytes) | Pre-Edit SHA-256 |
| --- | ---: | --- |
| `C:\AI-BS\scratch\structural_dip_engine.py` | 62,209 | `088245a0ff29c0bd2b2654b1e38d764ee3bbe84741bde688077dfccafb765b08` |
| `C:\AI-BS\scratch\live_cro_usdt_trader.py` | 43,258 | `d449c4177a4db5b45908a32ee9c5f14e6a9cab0d770fee1827d4eff6ce3c779e` |
| `C:\AI-BS\scratch\oci_stack_claimer.py` | 19,677 | `acf0636cce570c5dfcfcf9b649843bb4295f526fb1221afc6ce829bcf88c1433` |
| `C:\AI-BS\scratch\pure_rsa_sha256.py` | 2,644 | `0f6f9b62ce521a43a4e0e432522bb8369bfadce8a8e74ba5ce38823a7355b1ee` |
| `C:\AI-BS\scratch\aibs_24x7_supervisor.py` | 13,060 | `8d385bc9e67cd07c68e1c3cb0b27a9bbcb65139a4c3fcd47d9769c557c22a3ba` |
| `C:\AI-BS\scratch\agent4_risk_watchdog.py` | 14,983 | `745a586b98031969b279d3390a4597196fbbfcd88732609b8aefd1e33e05ca4f` |
| `C:\AI-BS\scratch\test_m2_trading_engine.py` | 25,567 | `113badfacae28d8686b3ee41aa066b2e93187be9b691950c7c6c261d61983c3b` |
| `C:\AI-BS\Start_24x7_Master_Supervisor.bat` | 700 | `b0c80cc2cdea2e85a9920bc591f1b9980d74dcd76fe4c45e85f83c0b1c5102c4` |

---

## 3. Running Services & Process Audit (Read-Only Snapshot)

Captured from `C:\AI-BS\saved_data\master_supervisor_status.json` (`2026-11-19T17:30:57.718113+00:00`, Supervisor `PID 23296`, `12/12` reported healthy by pre-edit supervisor):

| Service ID | Role Classification | Observed PIDs / Port | Minimum HA Trading-Recovery Dependency? | Stale / Audit Finding |
| --- | --- | --- | --- | --- |
| `structural_dip_engine` | Primary Strategy Engine (`HYBRID_SPLIT`) | `38700`, `50320` (`:8007`) | **YES** (or standby equivalent) | Currently mutates exchange directly (`CryptoComClient`); lacks durable intent journal & epoch fencing |
| `agent4_risk_watchdog` | Defense / Drift Watchdog | `48604`, `31516` | **YES** (read-only observer) | Currently loads same trade-capable DPAPI creds as Agent 1 |
| `agent2_orderbook_scout` | Orderbook Depth Scout | `24240`, `43332` | Optional advisory input | Safe fallback exists (`SCOUT_MAX_AGE_SEC = 15s`) |
| `agent3_triangular_arb` | Triangular Arb Scout | `34996`, `32232` | No | Informational only |
| `crypto_email_notifier` | Alert & Fill Notifier | `13568`, `39784` | Alerting | Separate process; SMTP/webhook best-effort |
| `oci_stack_claimer` | OCI Provisioning Controller | `42264` | Provisioning only | **STALE PROCESS**: running legacy script executing direct `LaunchInstance` sweep (`oci_claimer.log` at `12:23:34`), does NOT write `oci_controller_state.json` |
| `aibs_24x7_supervisor` | Windows Master Supervisor | `23296` (parent shim `21372`) | Local supervisor | **STALE PROCESS**: running earlier version spawning `cloudflared.exe` without `--config`, causing `heals_total: 361` churn |
| `cloudflared_tunnel` | Cloudflare Sovereign Tunnel | `44908` | **NO** | Respawn churn (`heals_total: 361`) due to stale supervisor `PID 23296`; not needed for exchange execution or HA standby |
| `go_cognitive_gateway` | Go Cognitive Gateway | `21780` (`:8000`) | **NO** | Non-trading dependency |
| `fastapi_backend` | FastAPI AI-BS Backend | `44620`, `41928` (`:8080`) | **NO** | Non-trading dependency |
| `vite_frontend` | Vite Frontend Dashboard | `33700` (`:5173`) | **NO** | Non-trading dependency |
| `chromadb_vector_store` | ChromaDB Vector Store | `39380`, `14768`, `36640` (`:8002`) | **NO** | Non-trading dependency |
| `ollama_gpu_11434` | Local LLM GPU Node | `:11434` | **NO** | Non-trading dependency |

> **Important Note on Windows PIDs**: Python services launched via `runtime\recovery-20261110\Scripts\python.exe` show a parent venv-shim PID plus a child base Python PID.

---

## 4. Live Exchange & Telemetry State (Read-Only Observed)

Captured directly from `http://127.0.0.1:8007/api/live-telemetry` and `C:\AI-BS\saved_data\agent4_watchdog_status.json` (`2026-11-19T17:31:18Z`):

- **Engine Status**: `LIVE_ACTIVE` (poll `2.5s`, instrument `CRO_USDT`)
- **Strategy Preserved Baseline**: `PROFIT_RESERVE_SHARE = 0.50`, `total_realized_pnl_usdt = "0.453420"`, `profit_reserve_usdt = "0.226710"`
- **Active Exchange Resting Orders (`3` total, all `POST_ONLY` `SELL`)**:
  1. `order_id`: `6530219611182687955` | `client_oid`: `tp-1-1795063726-0c677f` | `811 CRO @ $0.04389` | `status: ACTIVE` | `exec_inst: ["POST_ONLY"]`
  2. `order_id`: `6530219611198439095` | `client_oid`: `tp-2-1795098851-513847` | `706 CRO @ $0.04313` | `status: ACTIVE` | `exec_inst: ["POST_ONLY"]`
  3. `order_id`: `6530219611205721887` | `client_oid`: `tp-0-1795107021-3d77bc` | `714 CRO @ $0.04234` | `status: ACTIVE` | `exec_inst: ["POST_ONLY"]`
- **Watchdog Health (`agent4_watchdog_status.json`)**: `watchdog_status: ONLINE`, `watchdog_health: HEALTHY`, `agent1_telemetry_age_sec: 1.52`, `current_mid_price: 0.041415`, `active_order_count: 3`, `equity_snapshot.total_equity_usdt: 93.7411` (`CRO: 2231.03688...`, `USDT: 1.275784`), `equity_drawdown_usdt: 0.9705`, `kill_switch_tripped: false`.
- **OCI Provisioning Status (Read-Only Disk / Log Audit)**:
  - Config file `C:\Users\Administrator\.oci\config`: single profile `[DEFAULT]` with required keys (`user`, `fingerprint`, `tenancy`, `region`, `key_file`); `region = us-chicago-1`; `key_file` present on disk.
  - Stack OCID: `ocid1.ormstack.oc1.us-chicago-1.amaaaaaacuqpksyalu7rlzfn6tci6ml3fxwetdykbjdpifi5sir44tztpyrq`
  - Observed `oci_claimer_status.json` (`17:23:34Z`): `active_instances: []`, recent Resource Manager `APPLY` jobs `FAILED`; `oci_claimer.log` records `Out of host capacity`.
  - **Standby Live Readiness**: `NOT_VERIFIED` / `NOT_STARTED` (no OCI VM currently running).

---

## 5. Credential, Mutation Path & Dual-Key Separation Audit

*(Inspected by capability only — ZERO secrets read into docs or logs.)*

| Capability / Component | Current Baseline | Security / Authority Gap | Target HA Design |
| --- | --- | --- | --- |
| Primary Trade Credential | Windows DPAPI archive referenced by `C:\AI-BS\backups\crypto_connector_candidate_20261115_v01\private-candidate-location.json` | Readable directly by both `structural_dip_engine.py` AND `agent4_risk_watchdog.py`; no gateway epoch check | Held ONLY by Exclusive Execution Gateway (`ExecutionGateway`); removed from strategy hosts at controlled cutover |
| Read-Only Observer Credential | Not yet wired into running processes; operator generated a **second dedicated Read-Only API key** (`2026-11-19`) | Watchdog currently reuses trade-capable key path | Dedicated Read-Only DPAPI archive (`crypto_readonly_dpapi.json` on Windows) & `/etc/aibs/standby-readonly.env` on OCI ARM64 Linux (`PassiveStandbyClient` enforces zero mutations in code too) |
| OCI Signing Key | File path in `[DEFAULT]` `key_file`; signed via pure-Python `pure_rsa_sha256.py` | Uses raw `open()`, `assert`, and lacks explicit encrypted-PEM / key-length validation | Hardened `pure_rsa_sha256.py` + disposable RSA-2048 unit verification |

---

## 6. Windows Boot Persistence & Security Posture Audit

1. **Boot Persistence Gap**:
   - Scheduled Tasks query shows `\AI-BS-Publishing-Nginx` and standard Windows tasks, and **NO** Scheduled Task for `aibs_24x7_supervisor.py` or crypto/OCI daemons.
   - Boot persistence currently relies on `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Start_24x7_Master_Supervisor.bat`, which **does NOT run before interactive Windows user sign-in** after an unattended reboot.
   - **DPAPI Binding Constraint**: Because Crypto.com DPAPI secrets are bound to user account `ai-bs\administrator`, moving to Task Scheduler must run under that same authenticated user principal (configured for unattended/non-interactive logon) rather than exporting DPAPI secrets to plaintext.
2. **Security Controls Audit**:
   - Registry `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy\VerifiedAndReputablePolicyState = 0x0` (Smart App Control disabled).
   - Microsoft Defender `ExclusionPath` includes blanket directory `C:\AI-BS` (plus `C:\AI-BS\.temp_executor`, `C:\AI-BS\Stehouwer_Server`, etc.).
   - **Constraint**: Do NOT disable Defender, WDAC, Smart App Control, or TLS verification during testing; document targeted remediation (narrow Defender exclusions + formal SAC/WDAC review) in `DEPLOYMENT_AND_ROLLBACK.md`.

---

## 7. Baseline Verification & Rollback Boundary

- **Baseline Tests Prior to Edits**:
  - `test_m2_trading_engine.py`: **11/11 PASS** (`0.974s`)
  - `test_local_ollama_http.py`: **10/10 PASS** (`0.561s`)
- **Explicit Rollback Boundary**:
  - Restoring any earlier script revision or disk snapshot does **not** grant permission to place live trades.
  - Every rollback must start the trading engine in `PASSIVE` mode (`--role passive`), read authoritative exchange orders/balances/fills directly from Crypto.com Exchange, reconcile any `UNKNOWN` / `SUBMITTING` gateway intents, and acquire a fresh monotonically incremented `authority_epoch` before admitting any mutation.
  - Resting `POST_ONLY` `SELL` orders (`811 @ $0.04389`, `706 @ $0.04313`, `714 @ $0.04234`) MUST be preserved across restarts and rollbacks unless risk policy explicitly directs otherwise.
