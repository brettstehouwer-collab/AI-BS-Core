#!/bin/bash
# setup_ubuntu_bio.sh
# Automates the setup of the Ubuntu-Bio WSL2 subsystem for offline bioinformatics and cloud emulation.

set -e

echo "==================================================="
echo "       AI-BS UBUNTU-BIO SUBSYSTEM PROVISIONING     "
echo "==================================================="

echo "[1/6] Updating APT and installing build essentials..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y build-essential curl wget git unzip python3 python3-pip python3-venv openjdk-17-jdk

echo "[2/6] Installing Node.js (for Firebase Emulators & Wrangler)..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "[3/6] Installing Cloud CLI Tools..."
sudo npm install -g firebase-tools
sudo npm install -g wrangler

echo "[4/6] Installing Python Environment and uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
sudo mkdir -p /opt/bio_bridge_env
sudo chown $USER:$USER /opt/bio_bridge_env
uv venv /opt/bio_bridge_env
/opt/bio_bridge_env/bin/uv pip install fastapi uvicorn pydantic python-multipart

echo "[5/6] Downloading Bioinformatics Binaries..."
sudo mkdir -p /opt/bio_tools
sudo chown $USER:$USER /opt/bio_tools
cd /opt/bio_tools

# Note: Binaries downloaded here will be cached. For a true air-gapped system, 
# these would be copied from E:\WLS2BKUP directly. We will pull standard releases here.

# Foldseek
wget https://mmseqs.com/foldseek/foldseek-linux-avx2.tar.gz
tar -xvzf foldseek-linux-avx2.tar.gz
rm foldseek-linux-avx2.tar.gz

# MMseqs2
wget https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz
tar -xvzf mmseqs-linux-avx2.tar.gz
rm mmseqs-linux-avx2.tar.gz

echo "[6/6] Ensuring E: Drive Auto-Mount is configured..."
if ! grep -q "\[automount\]" /etc/wsl.conf 2>/dev/null; then
    echo -e "[automount]\nenabled = true\noptions = \"metadata,uid=1000,gid=1000,umask=22\"\n" | sudo tee -a /etc/wsl.conf
    echo "Added automount configuration to /etc/wsl.conf. (Requires WSL restart)"
fi

echo "==================================================="
echo " Provisioning Complete. Restart WSL to apply mounts."
echo "==================================================="
