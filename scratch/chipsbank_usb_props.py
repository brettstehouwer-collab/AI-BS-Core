import subprocess
import json

ps_script = """
Get-PnpDeviceProperty -InstanceId 'USB\\VID_1E3D&PID_198A\\9&12fc30f1&0&4' | Where-Object { $_.Data -ne $null } | Select-Object KeyName, Type, Data | ConvertTo-Json -Depth 3
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
try:
    props = json.loads(res.stdout)
    for p in props:
        print(f"{p['KeyName']}: {p['Data']}")
except Exception as e:
    print("Error:", e)
    print(res.stdout[:500])
