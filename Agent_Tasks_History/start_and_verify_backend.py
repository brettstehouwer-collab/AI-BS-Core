import subprocess
import sys
import time
import requests

print("Launching AI_BS_Backend.py...")
proc = subprocess.Popen(
    [r"C:\AI-BS\pyppeteer_env\Scripts\python.exe", r"C:\AI-BS\backend\AI_BS_Backend.py"],
    cwd=r"C:\AI-BS\backend",
    creationflags=subprocess.DETACHED_PROCESS
)
print("Spawned PID:", proc.pid)

for i in range(15):
    time.sleep(1)
    try:
        r = requests.get("http://127.0.0.1:8080/api/operations/processes", timeout=1)
        if r.status_code == 200:
            print("Successfully connected! Response:")
            data = r.json()
            print("Status:", r.status_code)
            print("Active processes detected:", data.get("total_active_processes"))
            print("Hardware:", data.get("host_hardware"))
            sys.exit(0)
    except Exception as e:
        print(f"Waiting ({i+1}s)... {e}")
