import subprocess
import json

ps_script = """
Get-PnpDeviceProperty -InstanceId 'PCI\\VEN_1B21&DEV_2425&SUBSYS_24211B21&REV_01&USB4_MS_CM\\451ECAFFFF5177A000' | Where-Object { $_.Data -ne $null } | Select-Object KeyName, Type, Data | ConvertTo-Json -Depth 3
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
try:
    props = json.loads(res.stdout)
    print("=== USB4 HOST ROUTER PROPERTIES ===")
    for p in props:
        print(f"{p['KeyName']} ({p['Type']}): {p['Data']}")
except Exception as e:
    print("Error:", e)
    print(res.stdout[:1000])
