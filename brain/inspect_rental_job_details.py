import subprocess
import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("🔎 DETAILED INSPECTION: CLORE, VAST.AI, AND PEARL")
print("=" * 70)

# 1. Clore Hosting Details in Ubuntu
print("\n--- [A] CLORE HOSTING (WSL Ubuntu) ---")
try:
    clore_logs = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "tail -n 25 /opt/clore-hosting/logs/*.log 2>/dev/null || journalctl -u clore-hosting -n 20 --no-pager 2>/dev/null || echo 'No log files in /opt/clore-hosting/logs'"],
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10
    )
    print("Clore Logs:")
    print(clore_logs.strip())
except Exception as e:
    print(f"Clore log error: {e}")

try:
    clore_files = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "ls -la /opt/clore-hosting/"],
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10
    )
    print("\nClore Directory:")
    print(clore_files.strip())
except Exception as e:
    print(f"Clore dir error: {e}")

# 2. Vast.ai Details in Ubuntu-24.04
print("\n--- [B] VAST.AI (WSL Ubuntu-24.04) ---")
try:
    vast_log = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-c", "tail -n 25 /var/lib/vastai_kaalia/kaalia.log 2>/dev/null || echo 'No kaalia.log'"],
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10
    )
    print("Vast Kaalia Log:")
    print(vast_log.strip())
except Exception as e:
    print(f"Vast log error: {e}")

try:
    docker_ps = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-c", "sudo docker ps -a"],
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10
    )
    print("\nVast Docker PS (sudo):")
    print(docker_ps.strip())
except Exception as e:
    print(f"Docker ps error: {e}")

# 3. Pearl Details
print("\n--- [C] PEARL DETAILS ---")
pearl_dir = r"C:\AI-BS\pearl"
if os.path.exists(pearl_dir):
    print(f"Files in {pearl_dir}:")
    for root, dirs, files in os.walk(pearl_dir):
        for f in files:
            p = os.path.join(root, f)
            print(f"  {p} ({os.path.getsize(p)} bytes)")
else:
    print("C:\\AI-BS\\pearl not found.")

try:
    wsl_pearl = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "find / -name '*pearl*' -maxdepth 3 2>/dev/null || echo 'None'"],
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10
    )
    print("\nWSL Ubuntu pearl search:")
    print(wsl_pearl.strip())
except Exception as e:
    print(f"WSL pearl search error: {e}")

# 4. Check bzminer / mining launcher in Ubuntu
print("\n--- [D] BZMINER PROCESS IN UBUNTU ---")
try:
    miner_check = subprocess.check_output(
        ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "cat /etc/miner_launcher.sh 2>/dev/null || echo 'None'"],
        stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10
    )
    print("miner_launcher.sh content:")
    print(miner_check.strip())
except Exception as e:
    print(f"miner_check error: {e}")

print("=" * 70)
