import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("--- [1] CLORE HOSTING SERVICE LOGS (WSL Ubuntu) ---")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "journalctl -u clore-hosting -n 30 --no-pager 2>/dev/null || cat /opt/clore-hosting/hosting.log 2>/dev/null | tail -n 30 || echo 'No systemd log'"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
except Exception as e:
    print(f"Error: {e}")

print("\n--- [2] CLORE DOCKER CONTAINERS (WSL Ubuntu) ---")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "docker ps -a"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
except Exception as e:
    print(f"Error: {e}")

print("\n--- [3] VAST.AI KAALIA LOGS (WSL Ubuntu-24.04) ---")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-c", "cat /var/lib/vastai_kaalia/kaalia.log | tail -n 35"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
except Exception as e:
    print(f"Error: {e}")

print("\n--- [4] VAST.AI DOCKER CONTAINERS (WSL Ubuntu-24.04) ---")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-c", "docker ps -a"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
except Exception as e:
    print(f"Error: {e}")

print("\n--- [5] BZMINER IN UBUNTU ---")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "ps aux | grep bzminer"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
except Exception as e:
    print(f"Error: {e}")
