import subprocess
import json

ps_script = """
Get-PnpDevice -PresentOnly | Where-Object { 
    $_.InstanceId -like 'USB*' -or 
    $_.InstanceId -like 'USB4*' -or 
    $_.PNPClass -in 'USB', 'USBDevice', 'WPD', 'DiskDrive', 'Ports', 'HIDClass', 'MEDIA', 'Image', 'Camera', 'Net'
} | ForEach-Object {
    $parent = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Data
    $loc = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_LocationInfo' -ErrorAction SilentlyContinue).Data
    $lastArr = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_LastArrivalDate' -ErrorAction SilentlyContinue).Data
    [PSCustomObject]@{
        Status = $_.Status
        Class = $_.Class
        FriendlyName = $_.FriendlyName
        InstanceId = $_.InstanceId
        Parent = $parent
        Location = $loc
        LastArrival = $lastArr
    }
} | ConvertTo-Json -Depth 3
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
try:
    data = json.loads(res.stdout)
    if isinstance(data, dict):
        data = [data]
    print(f"Total Devices Scanned: {len(data)}")
    for d in data:
        # Filter for relevant USB / External devices
        iid = d.get("InstanceId", "")
        cls = d.get("Class", "")
        if "USB" in iid or "USB4" in iid or cls in ['USB', 'USBDevice', 'WPD', 'DiskDrive', 'Ports', 'MEDIA']:
            print(f"[{d.get('Status')}] {cls} | {d.get('FriendlyName')}")
            print(f"    ID: {iid}")
            print(f"    Parent: {d.get('Parent')}")
            print(f"    Location: {d.get('Location')}")
            print(f"    LastArrival: {d.get('LastArrival')}")
            print("-" * 50)
except Exception as e:
    print("Error:", e)
    print(res.stdout[:500])
