# AI-BS PC Router & Hub Configuration Engine
# Role: Ethernet 2 = WAN IN (Metronet 2.5G Fiber), Ethernet = LAN OUT (Switch/Eero Hub)

Write-Host "=== Step 1: Configuring Interface Metrics and Routing Priority ==="
Set-NetIPInterface -InterfaceAlias "Ethernet 2" -AutomaticMetric Disabled -InterfaceMetric 10
Set-NetIPInterface -InterfaceAlias "Ethernet" -AutomaticMetric Disabled -InterfaceMetric 50
Get-NetIPInterface -InterfaceAlias "Wi-Fi" -ErrorAction SilentlyContinue | ForEach-Object {
    Set-NetIPInterface -InterfaceAlias "Wi-Fi" -AutomaticMetric Disabled -InterfaceMetric 40
}

Write-Host "=== Step 2: Enabling Kernel IP Routing and Packet Forwarding ==="
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "IPEnableRouter" -Value 1 -Type DWord
Set-NetIPInterface -InterfaceAlias "Ethernet 2" -Forwarding Enabled
Set-NetIPInterface -InterfaceAlias "Ethernet" -Forwarding Enabled
Get-NetIPInterface -InterfaceAlias "Wi-Fi" -ErrorAction SilentlyContinue | ForEach-Object {
    Set-NetIPInterface -InterfaceAlias "Wi-Fi" -Forwarding Enabled
}

Write-Host "=== Step 3: Configuring SharedAccess (ICS) Service ==="
Set-Service -Name SharedAccess -StartupType Automatic
Restart-Service -Name SharedAccess -Force

Write-Host "=== Step 4: Configuring Internet Connection Sharing (ICS) via COM ==="
$netShare = New-Object -ComObject HNetCfg.HNetShare
$publicConn = $null
$privateConn = $null

foreach ($conn in $netShare.EnumEveryConnection) {
    $props = $netShare.NetConnectionProps($conn)
    if ($props.Name -eq "Ethernet 2") {
        $publicConn = $conn
    }
    if ($props.Name -eq "Ethernet") {
        $privateConn = $conn
    }
}

if ($publicConn -and $privateConn) {
    $publicConfig = $netShare.INetSharingConfigurationForINetConnection($publicConn)
    $privateConfig = $netShare.INetSharingConfigurationForINetConnection($privateConn)

    Write-Host "Disabling any stale sharing configuration..."
    try { if ($publicConfig.SharingEnabled) { $publicConfig.DisableSharing() } } catch { Write-Host "Notice: $($_.Exception.Message)" }
    try { if ($privateConfig.SharingEnabled) { $privateConfig.DisableSharing() } } catch { Write-Host "Notice: $($_.Exception.Message)" }
    Start-Sleep -Seconds 1

    Write-Host "Enabling Public (WAN IN) on Ethernet 2..."
    $publicConfig.EnableSharing(0)

    Write-Host "Enabling Private (LAN OUT) on Ethernet..."
    $privateConfig.EnableSharing(1)

    Write-Host "Verification: Public Sharing: $($publicConfig.SharingEnabled) | Private Sharing: $($privateConfig.SharingEnabled)"
} else {
    Write-Warning "Failed to locate one or both Ethernet connections."
}

Write-Host "=== Step 5: Post-Configuration Diagnostic State ==="
Get-NetIPInterface -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -match "Ethernet|Wi-Fi" } | 
    Select-Object InterfaceAlias, InterfaceMetric, AutomaticMetric, Forwarding | Format-Table -AutoSize

Get-NetIPAddress -InterfaceAlias "Ethernet", "Ethernet 2" -AddressFamily IPv4 | 
    Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table -AutoSize
