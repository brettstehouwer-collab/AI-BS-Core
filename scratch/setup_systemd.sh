#!/bin/bash
set -e

# Create apply_host_clocks.sh
cat << 'EOF' > /opt/peakminer/apply_host_clocks.sh
#!/bin/bash
cmd.exe /c "nvidia-smi -lmc 5001 && nvidia-smi -pl 310" > /dev/null 2>&1
EOF
chmod +x /opt/peakminer/apply_host_clocks.sh

# Create systemd service unit
cat << 'EOF' > /etc/systemd/system/aibs-gpu-persistent.service
[Unit]
Description=AI-BS Persistent RTX 4090 Clock and Power Clamping
After=network.target local-fs.target
ConditionPathExists=/proc/sys/fs/binfmt_misc/WSLInterop

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash /opt/peakminer/apply_host_clocks.sh

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable aibs-gpu-persistent.service
systemctl start aibs-gpu-persistent.service
systemctl status aibs-gpu-persistent.service
