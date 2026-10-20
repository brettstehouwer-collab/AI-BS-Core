import subprocess
import json
import psutil

# Method: PowerShell with -NoProfile and clean output
cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", 
       "Get-Process | Where-Object { $_.MainWindowTitle -ne '' -and $_.MainWindowTitle -ne $null } | Select-Object Id, ProcessName, MainWindowTitle | ConvertTo-Json -Compress"]
res = subprocess.run(cmd, capture_output=True, text=True)
stdout = res.stdout.strip()
print("Raw stdout from PS:\n", stdout)

# Find JSON start '[' or '{'
json_start = -1
for i, ch in enumerate(stdout):
    if ch in ('[', '{'):
        json_start = i
        break

if json_start != -1:
    data = json.loads(stdout[json_start:])
    if isinstance(data, dict):
        data = [data]
    print("\n--- Discovered Windows via PowerShell ---")
    for d in data:
        print(f"  🎮 PID: {d.get('Id')} | Process: {d.get('ProcessName')} | Title: \"{d.get('MainWindowTitle')}\"")
