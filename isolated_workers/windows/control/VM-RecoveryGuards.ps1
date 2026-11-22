# Pure validation; dot-sourcing never starts a process.
function ConvertFrom-RecoveryVMInfo([string]$Text) {
    $values=@{}
    foreach ($line in ($Text -split "`r?`n")) {
        if ($line -match '^("[^"]+"|[^=]+)=(.*)$') {
            $key=$matches[1].Trim('"')
            if ($values.ContainsKey($key)) { throw "Duplicate VM field: $key" }
            $values[$key]=$matches[2].Trim('"')
        }
    }
    return $values
}
function Assert-RecoveryPath([string]$Actual,[string]$Expected) {
    if ([string]::IsNullOrWhiteSpace($Actual) -or [IO.Path]::GetFullPath($Actual.Replace('\\','\').Replace('/','\')) -ine [IO.Path]::GetFullPath($Expected)) { throw 'Unexpected recovery path.' }
}
function Assert-RecoveryRegularPath([string]$Path) {
    $node=Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $node) {
        if ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked recovery path rejected.' }
        if ($node -is [IO.FileInfo]) { $node=$node.Directory } else { $node=$node.Parent }
    }
}
function Assert-RecoveryVMInfo([hashtable]$Values,[string]$State,[string]$Disk,[string]$Snapshot) {
    $base='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023'
    $expected=@{
        UUID='6c5a53da-ab80-4ecb-8be6-4059266f736e'; VMState=$State
        memory='8192'; cpus='4'; firmware='EFI'; SecureBoot='on'; clipboard='disabled'
        clipboard_file_transfers='off'; draganddrop='disabled'; usb='off'; ehci='off'; xhci='off'
        audio='none'; audio_in='off'; audio_out='off'; vrde='off'; accelerate3d='off'
        boot1='dvd'; boot2='disk'; boot3='none'; boot4='none'; 'nested-hw-virt'='off'
        teleporterenabled='off'; 'tracing-enabled'='off'; 'autostart-enabled'='off'; recording_enabled='off'
        uart1='off'; uart2='off'; uart3='off'; uart4='off'; lpt1='off'; lpt2='off'
        storagecontrollername0='SATA'; storagecontrollertype0='IntelAhci'; storagecontrollerportcount0='2'
        CurrentSnapshotUUID=$Snapshot; 'SATA-ImageUUID-0-0'=$Disk
        'SATA-ImageUUID-1-0'='9f172218-11ff-45fa-b2ff-9faed642a36c'
        'SATA-hot-pluggable-0-0'='off'; 'SATA-hot-pluggable-1-0'='off'
    }
    foreach ($n in 1..8) { $expected["nic$n"]='none' }
    foreach ($key in $expected.Keys) { if ($Values[$key] -cne $expected[$key]) { throw "VM guard rejected: $key" } }
    if (@($Values.Keys | Where-Object { $_ -match '^storagecontrollername\d+$' }).Count -ne 1 -or
        @($Values.Keys | Where-Object { $_ -match '^SATA-\d+-\d+$' }).Count -ne 2 -or
        @($Values.Keys | Where-Object { $_ -match 'SharedFolder' }).Count) { throw 'Unexpected storage or sharing.' }
    Assert-RecoveryPath $Values.CfgFile (Join-Path $base 'AI-BS-Eval-Base-20261023.vbox')
    Assert-RecoveryPath $Values['SATA-0-0'] (Join-Path $base "Snapshots\{$Disk}.vdi")
    Assert-RecoveryPath $Values['SATA-1-0'] 'C:\Users\footb\Downloads\26300.9457.260913-1737.26h2_ge_release_svc_refresh_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso'
}
