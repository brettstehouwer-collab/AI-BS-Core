import subprocess
import json

ps_script = """
Get-CimInstance Win32_PnPEntity | Where-Object { 
    $_.Present -eq $true -and (
        $_.DeviceID -like 'USB*' -or 
        $_.DeviceID -like 'USB4*' -or 
        $_.PNPClass -in 'USB', 'USBDevice', 'WPD', 'DiskDrive', 'Ports'
    )
} | Select-Object Name, Description, PNPClass, DeviceID, Manufacturer, Status | ConvertTo-Json
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
try:
    devices = json.loads(res.stdout)
    if isinstance(devices, dict):
        devices = [devices]
    print(f"Total Active Devices Found: {len(devices)}")
    for d in devices:
        print(f"[{d.get('Status')}] {d.get('PNPClass')} | {d.get('Name')} ({d.get('Manufacturer')})")
        print(f"    DeviceID: {d.get('DeviceID')}")
except Exception as e:
    print("Error parsing JSON:", e)
    print(res.stdout[:500])
