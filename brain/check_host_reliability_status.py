import subprocess
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("📊 CHECKING HOST RELIABILITY & HEARTBEAT STATUS (VAST & CLORE)")
print("=" * 70)

# 1. Vast.ai Kaalia Host Status
print("\n[1] Vast.ai (Ubuntu-24.04):")
try:
    m_id = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu-24.04", "-u", "root", "--", "cat", "/var/lib/vastai_kaalia/machine_id"],
        stderr=subprocess.STDOUT, text=True, errors="replace"
    ).strip()
    print(f"Machine ID: {m_id}")
    
    recent_log = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu-24.04", "-u", "root", "--", "tail", "-n", "30", "/var/lib/vastai_kaalia/kaalia.log"],
        stderr=subprocess.STDOUT, text=True, errors="replace"
    ).strip()
    print("Recent Kaalia Log Lines:")
    for line in recent_log.splitlines()[-10:]:
        print(f"  {line}")
except Exception as e:
    print(f"Vast check error: {e}")

# 2. Clore.ai Hosting Status
print("\n[2] Clore.ai (Ubuntu):")
try:
    status_out = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "bash", "-c", "python3 /opt/clore-hosting/hosting.py --status 2>/dev/null || cat /opt/clore-hosting/settings.json 2>/dev/null || echo 'No status cmd'"],
        stderr=subprocess.STDOUT, text=True, errors="replace"
    ).strip()
    print("Clore Settings / Status:")
    print(status_out)
    
    clore_log = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "bash", "-c", "journalctl -u clore-hosting -n 15 --no-pager"],
        stderr=subprocess.STDOUT, text=True, errors="replace"
    ).strip()
    print("\nClore Service Journal (Last 5 lines):")
    for line in clore_log.splitlines()[-5:]:
        print(f"  {line}")
except Exception as e:
    print(f"Clore check error: {e}")

print("=" * 70)
