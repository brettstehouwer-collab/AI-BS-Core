#!/bin/bash
set -e

echo "Starting Docker installation..."
apt-get update
apt-get install -y ca-certificates curl gnupg python3 wget

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes || true
chmod a+r /etc/apt/keyrings/docker.gpg || true
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || true

echo "Starting NVIDIA Container Toolkit installation..."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg --yes || true
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update
apt-get install -y nvidia-container-toolkit || true
nvidia-ctk runtime configure --runtime=docker || true

echo "Restarting Docker service..."
service docker start || true

echo "Running Vast.ai Host Installer (Patched for WSL2)..."
python3 /mnt/c/AI-BS/vast_install.py da80afadb9223eacadf7be60b9b89de6d07d8f0e7b83d62cdcff35ca57dfb478 --no-driver --no-partitioning

echo "Vast.ai Host Installation Completed Successfully!"
