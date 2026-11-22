$controllers = Get-CimInstance Win32_USBController
Write-Host "=== USB CONTROLLERS ===" -ForegroundColor Cyan
foreach ($c in $controllers) {
    Write-Host ("Controller: " + $c.Name + " (" + $c.DeviceID + ")") -ForegroundColor Green
}

Write-Host "`n=== CONNECTED USB DEVICES ===" -ForegroundColor Cyan
$usbDevices = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "USB*" -or $_.InstanceId -like "USB4*" }
foreach ($d in $usbDevices) {
    Write-Host ("[" + $d.Status + "] " + $d.Class + " - " + $d.FriendlyName) -ForegroundColor Yellow
    Write-Host ("    ID: " + $d.InstanceId) -ForegroundColor Gray
}

Write-Host "`n=== USB TYPE-C / UCMCX / USB4 CLIENT CONTROLLERS ===" -ForegroundColor Cyan
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'UCMC|USB4|ITE88|RTK54' } | ForEach-Object {
    Write-Host ("[" + $_.Status + "] " + $_.Class + " - " + $_.FriendlyName + " (" + $_.InstanceId + ")")
}
