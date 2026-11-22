# AI-BS OCI ARM64 Passive Standby Deployment Package (`deploy/oci_standby`)

Target compute profile: Oracle Cloud `us-chicago-1`, `VM.Standard.A1.Flex` (`1 OCPU`, `6 GB RAM`, `50 GB` boot volume) running Ubuntu 24.04 LTS ARM64 or Oracle Linux 9 ARM64.

## Design Boundaries
- **Zero Non-Trading Dependencies**: Runs Python >= 3.11 stdlib only (`requirements-arm64.txt`). Does **not** require GPU, Ollama, Windows UI, ChromaDB, or Cloudflare Tunnel.
- **Dual-Key Isolation**:
  - `aibs-standby.service` runs under dedicated UNIX user `aibs-standby`, reading ONLY `/etc/aibs/standby-readonly.env` (`CRYPTO_READONLY_API_KEY` / `CRYPTO_READONLY_API_SECRET`) with `--role passive --standby-readonly`. `PassiveStandbyClient` denies all mutation methods in code, and the key has trading/withdrawals disabled at Crypto.com Exchange.
  - `aibs-gateway.service` (Stage 1 cutover) runs under separate UNIX user `aibs-gateway` owning `/etc/aibs/gateway-trade.env` (`chmod 0600`) and SQLite WAL journal `/var/lib/aibs-gateway/authority_journal.db`, bound exclusively to private loopback/WireGuard interface.
- **Egress IP Allowlisting**:
  - Pin the OCI instance's static public egress IP on the **Read-Only** standby key (and gateway key once cut over), without weakening withdrawal/IP restrictions on any key.
- **Provisioning vs. Standby Readiness**:
  - Provisioning (`MONITOR` / `RUNNING` VM) does **not** equal standby readiness. Before marking standby ready: verify private WireGuard/SSH connectivity, systemd non-root service identity, SHA-256 build match, live read-only exchange inspection (`get_open_orders` / `get_balances`), passive mutation denial (`PassiveAuthorityError`), and isolated `.backup()` restore (`backup_and_restore.py --verify-restore`).
- **Cost Policy**: Configured allowlist in `oci_plan_policy.json` (`paid_spend_authorized: false`, `auto_promote_enabled: false`). OCI Budgets provide soft alerts only [S3].
