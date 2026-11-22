import subprocess
import json

ps_script = """
Get-PnpDeviceProperty -InstanceId 'USB\\VID_04E8&PID_6860\\R5CY11L1QCN' | Where-Object { $_.Data -ne $null } | Select-Object KeyName, Type, Data | ConvertTo-Json -Depth 3
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
try:
    props = json.loads(res.stdout)
    print("=== SAMSUNG PHONE ON USB4 PORT PROPERTIES ===")
    for p in props:
        if any(k in p['KeyName'].lower() for k in ['speed', 'location', 'parent', 'bus', 'desc', 'power', 'device']):
            print(f"{p['KeyName']}: {p['Data']}")
except Exception as e:
    print("Error:", e)
    print(res.stdout[:500])
