#!/bin/bash
# setup_ubuntu_bio.sh
# Provisions the Ubuntu Bioinformatics Bridge inside an existing WSL instance.

echo "==================================================="
echo "  Provisioning AI-BS Bioinformatics Bridge"
echo "==================================================="

# Ensure we run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (or with sudo)"
  exit 1
fi

set -e

echo "[1/4] Updating packages and installing core dependencies..."
apt-get update
apt-get install -y wget curl git build-essential python3 python3-pip python3-venv unzip tar pymol

echo "[2/4] Setting up /opt/bio_tools..."
mkdir -p /opt/bio_tools/bin
cd /opt/bio_tools

# Foldseek
if [ ! -d "/opt/bio_tools/foldseek" ]; then
    echo "Downloading Foldseek..."
    wget -q https://mmseqs.com/foldseek/foldseek-linux-avx2.tar.gz
    tar xzf foldseek-linux-avx2.tar.gz
    rm foldseek-linux-avx2.tar.gz
fi

# MMseqs2
if [ ! -d "/opt/bio_tools/mmseqs" ]; then
    echo "Downloading MMseqs2..."
    wget -q https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz
    tar xzf mmseqs-linux-avx2.tar.gz
    rm mmseqs-linux-avx2.tar.gz
fi

# Clustal Omega
if ! command -v clustalo &> /dev/null; then
    echo "Installing Clustal Omega via apt..."
    apt-get install -y clustalo
fi

# Ensure commands are symlinked properly for the main.py tool routing
ln -sf /opt/bio_tools/foldseek/bin/foldseek /opt/bio_tools/bin/foldseek
ln -sf /opt/bio_tools/mmseqs/bin/mmseqs /opt/bio_tools/bin/mmseqs
ln -sf $(which clustalo) /opt/bio_tools/bin/clustalo
# Add to PATH (temporarily for this script context)
export PATH=/opt/bio_tools/bin:$PATH

echo "[3/4] Provisioning Python Virtual Environment at /opt/bio_bridge_env..."
if [ ! -d "/opt/bio_bridge_env" ]; then
    python3 -m venv /opt/bio_bridge_env
fi
source /opt/bio_bridge_env/bin/activate

echo "[4/4] Installing Python Bridge Dependencies..."
pip install --upgrade pip
pip install fastapi uvicorn pydantic

echo "==================================================="
echo "  Provisioning Complete!"
echo "  The Ubuntu-Bio Bridge environment is fully ready."
echo "==================================================="
exit 0
