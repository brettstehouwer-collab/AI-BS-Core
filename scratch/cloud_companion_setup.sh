#!/bin/bash
# AI-BS 24/7 Cloud Companion Deployer (Oracle Cloud / Ubuntu / Debian)
set -e

echo "=========================================="
echo "  AI-BS 24/7 Companion Node Setup"
echo "=========================================="

sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl ufw

mkdir -p ~/aibs-companion/saved_data
cd ~/aibs-companion

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip requests

cat << 'EOF' > run_daemon.sh
#!/bin/bash
cd ~/aibs-companion
source venv/bin/activate
python3 live_cro_usdt_trader_cloud.py --daemon
EOF

chmod +x run_daemon.sh

echo "Environment initialized! Ready for keys & trading script."

