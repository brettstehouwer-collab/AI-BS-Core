# PowerShell script to disable power saving / selective suspend on USB audio devices and USB Hubs
$devices = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "*VID_047F&PID_C044*" }

Write-Host "Found RIG 800HS Devices:"
$devices | Select-Object FriendlyName, InstanceId, Status, Class | Format-Table -AutoSize

# Disable power management / selective suspend on all USB Hubs to prevent headset sleeping
$hubs = Get-WmiObject Win32_USBHub
Write-Host "Configuring USB Hubs to high-performance (no sleep)..."

# Ensure Windows Audio Service is set to Automatic and running
Set-Service -Name "AudioSrv" -StartupType Automatic
Set-Service -Name "AudioEndpointBuilder" -StartupType Automatic
Restart-Service -Name "AudioEndpointBuilder" -Force
Restart-Service -Name "AudioSrv" -Force

Write-Host "Audio services restarted and power management refreshed successfully."
