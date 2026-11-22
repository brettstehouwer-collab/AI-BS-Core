# Query Device Tree / Parent-Child hierarchy for USB devices
$devices = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "USB*" }

function Get-DeviceHierarchy($instanceId, $indent=0) {
    $dev = Get-PnpDevice -InstanceId $instanceId -ErrorAction SilentlyContinue
    $pad = "  " * $indent
    Write-Host ("$pad+-- " + $dev.FriendlyName + " [" + $dev.Class + "] (" + $dev.InstanceId + ")")
    
    # Get children
    $children = Get-PnpDeviceProperty -InstanceId $instanceId -KeyName 'DEVPKEY_Device_Children' -ErrorAction SilentlyContinue
    if ($children.Value) {
        foreach ($child in $children.Value) {
            Get-DeviceHierarchy $child ($indent + 1)
        }
    }
}

Write-Host "=== USB ROOT HUBS & ATTACHED HIERARCHY ===" -ForegroundColor Cyan
$rootHubs = Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "*ROOT_HUB*" -or $_.InstanceId -like "*USB4*ROOT*" }
foreach ($rh in $rootHubs) {
    Get-DeviceHierarchy $rh.InstanceId 0
    Write-Host ""
}
