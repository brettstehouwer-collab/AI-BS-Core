import subprocess
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("🔍 AUDITING ACTIVE JOBS & COMPUTE RENTAL PROCESSES")
print("=" * 70)

# 1. WSL Distribution Status
print("\n[1] WSL2 Distributions State:")
try:
    wsl_out = subprocess.check_output(["wsl.exe", "-l", "-v"], stderr=subprocess.STDOUT, text=True, errors="replace")
    print(wsl_out.strip())
except Exception as e:
    print(f"WSL error: {e}")

# 2. Check WSL Ubuntu (Clore & Pearl)
print("\n[2] Checking WSL 'Ubuntu' (Clore & Pearl):")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "ps aux | grep -iE 'clore|pearl|vast|miner|docker|xmrig' | grep -v grep || echo 'NO_MATCHING_PROCESSES'"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
    # Docker containers
    docker_cmd = ["wsl.exe", "-d", "Ubuntu", "--", "bash", "-c", "docker ps -a 2>/dev/null || echo 'Docker not running or no permission'"]
    d_out = subprocess.check_output(docker_cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print("Docker Containers in Ubuntu:")
    print(d_out.strip())
except Exception as e:
    print(f"Ubuntu check notice: {e}")

# 3. Check WSL Ubuntu-24.04 (Vast.ai)
print("\n[3] Checking WSL 'Ubuntu-24.04' (Vast.ai):")
try:
    cmd = ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-c", "ps aux | grep -iE 'vast|clore|pearl|miner|docker|containerd' | grep -v grep || echo 'NO_MATCHING_PROCESSES'"]
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print(out.strip())
    # Docker containers
    docker_cmd = ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-c", "docker ps -a 2>/dev/null || echo 'Docker not running or no permission'"]
    d_out = subprocess.check_output(docker_cmd, stderr=subprocess.STDOUT, text=True, errors="replace", timeout=10)
    print("Docker Containers in Ubuntu-24.04:")
    print(d_out.strip())
except Exception as e:
    print(f"Ubuntu-24.04 check notice: {e}")

# 4. Windows Host Processes
print("\n[4] Windows Host Processes (checking tasklist for pearl, clore, vast, miner, xmrig, docker):")
try:
    tl_out = subprocess.check_output(["tasklist", "/FO", "CSV"], stderr=subprocess.STDOUT, text=True, errors="replace")
    matches = []
    for line in tl_out.splitlines():
        low = line.lower()
        if any(k in low for k in ["pearl", "clore", "vast", "miner", "xmrig", "docker", "vmmem"]):
            matches.append(line)
    if matches:
        print("\n".join(matches))
    else:
        print("None found on Windows host.")
except Exception as e:
    print(f"Tasklist error: {e}")

# 5. Check AI-BS local miner / swarm folders
print("\n[5] Checking Local AI-BS Miners & Swarm Folders:")
import os
for path in [r"C:\AI-BS\miners", r"C:\AI-BS\Crypto-Swarm", r"C:\AI-BS\pearl"]:
    if os.path.exists(path):
        print(f"Found folder: {path}")
    else:
        print(f"Folder not present: {path}")

print("=" * 70)
