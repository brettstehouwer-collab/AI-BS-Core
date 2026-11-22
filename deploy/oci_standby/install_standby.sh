#!/usr/bin/env bash
set -euo pipefail

# AI-BS ARM64 Passive Standby Host Setup (Ubuntu 24.04 / Oracle Linux 9 aarch64)
# Idempotent setup that installs passive standby units WITHOUT enabling live trading.

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

ARCH="$(uname -m)"
if [[ "${ARCH}" != "aarch64" && "${ARCH}" != "arm64" ]]; then
  echo "Warning: expected ARM64 architecture, detected ${ARCH}" >&2
fi

id -u aibs-standby >/dev/null 2>&1 || useradd --system --shell /usr/sbin/nologin --home-dir /nonexistent aibs-standby
id -u aibs-gateway >/dev/null 2>&1 || useradd --system --shell /usr/sbin/nologin --home-dir /nonexistent aibs-gateway

mkdir -p /opt/ai-bs/scratch /opt/ai-bs/deploy/oci_standby
mkdir -p /etc/aibs /var/lib/aibs-standby /var/log/aibs-standby /var/lib/aibs-gateway /var/log/aibs-gateway /var/backups/aibs

chown root:root /etc/aibs
chmod 0755 /etc/aibs
chown -R aibs-standby:aibs-standby /var/lib/aibs-standby /var/log/aibs-standby
chown -R aibs-gateway:aibs-gateway /var/lib/aibs-gateway /var/log/aibs-gateway /var/backups/aibs
chmod 0750 /var/lib/aibs-gateway /var/backups/aibs

if [[ ! -f /etc/aibs/standby-readonly.env ]]; then
  cat <<'EOF' > /etc/aibs/standby-readonly.env
# Populate ONLY with your Read-Only Crypto.com key (trading & withdrawals disabled)
CRYPTO_READONLY_API_KEY=REPLACE_ME
CRYPTO_READONLY_API_SECRET=REPLACE_ME
EOF
  chown root:aibs-standby /etc/aibs/standby-readonly.env
  chmod 0640 /etc/aibs/standby-readonly.env
fi

if [[ ! -f /etc/aibs/gateway-trade.env ]]; then
  cat <<'EOF' > /etc/aibs/gateway-trade.env
# Stage 1 Exclusive Execution Gateway ONLY (withdrawal-disabled trade key)
CRYPTO_GATEWAY_API_KEY=REPLACE_ME
CRYPTO_GATEWAY_API_SECRET=REPLACE_ME
EOF
  chown root:aibs-gateway /etc/aibs/gateway-trade.env
  chmod 0600 /etc/aibs/gateway-trade.env
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_DIR}/systemd/aibs-standby.service" /etc/systemd/system/aibs-standby.service
cp "${SCRIPT_DIR}/systemd/aibs-gateway.service" /etc/systemd/system/aibs-gateway.service
cp "${SCRIPT_DIR}/systemd/aibs-backup.service" /etc/systemd/system/aibs-backup.service
cp "${SCRIPT_DIR}/systemd/aibs-backup.timer" /etc/systemd/system/aibs-backup.timer

cat <<'EOF' > /etc/logrotate.d/aibs
/var/log/aibs-standby/*.log /var/log/aibs-gateway/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
EOF

systemctl daemon-reload
echo "Installed AI-BS ARM64 standby systemd units safely in PASSIVE configuration."
echo "Next steps: configure private WireGuard/SSH tunnel, populate /etc/aibs/standby-readonly.env, and verify readiness before enabling."
