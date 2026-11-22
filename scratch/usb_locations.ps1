Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "USB\*" } | ForEach-Object {
    $parent = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_Parent' -ErrorAction SilentlyContinue).Value
    $loc = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName 'DEVPKEY_Device_LocationInfo' -ErrorAction SilentlyContinue).Value
    [PSCustomObject]@{
        FriendlyName = $_.FriendlyName
        Class        = $_.Class
        Location     = $loc
        Parent       = $parent
        InstanceId   = $_.InstanceId
    }
} | Format-Table FriendlyName, Class, Location, Parent -AutoSize
