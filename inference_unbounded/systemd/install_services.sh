#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[AI-BS] Installing Systemd Services into /etc/systemd/system/..."
cp "${SCRIPT_DIR}/aibs-vllm.service" /etc/systemd/system/
cp "${SCRIPT_DIR}/aibs-unbounded-engine.service" /etc/systemd/system/

systemctl daemon-reload
echo "[AI-BS] Enabling automated persistence on boot..."
systemctl enable aibs-vllm.service
systemctl enable aibs-unbounded-engine.service

echo "[AI-BS] Systemd configuration complete."
echo "Use: systemctl start aibs-vllm && systemctl start aibs-unbounded-engine"
