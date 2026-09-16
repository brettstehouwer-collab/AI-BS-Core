#!/bin/bash
# start_fastapi.sh
# Invoked by Windows Launch_AI_BS.bat to start the Ubuntu-Bio Bridge.

# Navigate to the bridge directory
cd /mnt/c/AI-BS/backend/ubuntu_bio_bridge

# Ensure the virtual environment exists and is activated
if [ ! -d "/opt/bio_bridge_env" ]; then
    echo "Error: /opt/bio_bridge_env not found. Did you run setup_ubuntu_bio.sh?"
    exit 1
fi

source /opt/bio_bridge_env/bin/activate

# Start the systemd service or fallback to exec uvicorn
systemctl start ubuntu-bio-bridge.service || exec uvicorn main:app --host 0.0.0.0 --port 8085 >> /mnt/c/AI-BS/backend/ubuntu_bio_bridge/bridge.log 2>&1
