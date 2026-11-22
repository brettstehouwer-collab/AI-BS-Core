#!/bin/bash
# ==============================================================================
#  AI-BS 24/7 Sovereign Cloud Node Installer (Oracle Cloud Always-Free Tier)
#  Host: Ampere A1 (4 OCPU / 24 GB RAM / 200 GB NVMe)
# ==============================================================================
set -e

echo "=== [1/6] Updating Ubuntu OS & Base Toolchains ==="
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv git curl wget ufw sqlite3 jq htop tmux

echo "=== [2/6] Configuring High-Security Firewall (UFW) ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # Secure SSH
sudo ufw allow 80/tcp      # HTTP Web Gateway
sudo ufw allow 443/tcp     # HTTPS SSL Gateway
sudo ufw allow 8000/tcp    # AI-BS Companion API
sudo ufw allow 8007/tcp    # Live Crypto Telemetry
sudo ufw --force enable

echo "=== [3/6] Setting Up AI-BS Cloud Node Directory Matrix ==="
mkdir -p ~/aibs-node/saved_data
mkdir -p ~/aibs-node/logs
mkdir -p ~/aibs-node/certs
mkdir -p ~/aibs-node/scripts

cd ~/aibs-node
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn requests pycryptodome httpx pydantic

echo "=== [4/6] Installing Ollama CPU Companion (Free 24/7 Lightweight LLM) ==="
curl -fsSL https://ollama.com/install.sh | sh
# Pull ultra-fast 3B agent model that runs flawlessly on 4 ARM cores + 24GB RAM
ollama pull llama3.2:3b || true

echo "=== [5/6] Creating Systemd Background Daemons ==="

# 1. AI-BS Crypto Scalper Service (24/7 Execution)
sudo bash -c 'cat << EOF > /etc/systemd/system/aibs-trader.service
[Unit]
Description=AI-BS 24/7 CRO Scalp Engine
After=network.target

[Service]
Type=simple
User='$USER'
WorkingDirectory='$HOME'/aibs-node
ExecStart='$HOME'/aibs-node/venv/bin/python3 live_cro_usdt_trader_cloud.py --daemon
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

# 2. AI-BS Companion API Gateway (Webhooks & Business Services)
sudo bash -c 'cat << EOF > /etc/systemd/system/aibs-gateway.service
[Unit]
Description=AI-BS 24/7 Webhook & Vector Gateway
After=network.target

[Service]
Type=simple
User='$USER'
WorkingDirectory='$HOME'/aibs-node
ExecStart='$HOME'/aibs-node/venv/bin/python3 -m uvicorn cloud_gateway:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
echo "=== [6/6] Node Initialized & Configured for Maximum Free Compute! ==="

