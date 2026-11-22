#!/bin/bash
set -e
cat << 'EOF' > /opt/peakminer/apply_host_clocks.sh
#!/bin/bash
/mnt/c/Windows/system32/cmd.exe /c "nvidia-smi -lmc 5001 & nvidia-smi -pl 310" > /dev/null 2>&1
EOF
chmod +x /opt/peakminer/apply_host_clocks.sh
systemctl daemon-reload
systemctl restart aibs-gpu-persistent.service
systemctl status aibs-gpu-persistent.service
