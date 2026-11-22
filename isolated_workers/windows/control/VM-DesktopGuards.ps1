# Candidate desktop provisioning profile. Pure metadata validation, no VM operation.
# Existing recovery controllers do not import or use this candidate.
. "$PSScriptRoot\VM-RecoveryGuards.ps1"

function Assert-DesktopVMInfo([hashtable]$Values,[string]$ExpectedState) {
    if($ExpectedState -cnotin @('running','saved')){throw 'Desktop operation requires an explicit running or saved state.'}
    if($null -eq $Values){throw 'Missing desktop VM observation.'}
    $base='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023'
    $disk='7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84'
    $expected=@{
        name='AI-BS-Eval-Base-20261023';UUID='6c5a53da-ab80-4ecb-8be6-4059266f736e';VMState=$ExpectedState
        memory='8192';cpus='4';firmware='EFI';SecureBoot='on';clipboard='disabled'
        clipboard_file_transfers='off';draganddrop='disabled';usb='off';ehci='off';xhci='off'
        audio='none';audio_in='off';audio_out='off';vrde='off';accelerate3d='off'
        boot1='dvd';boot2='disk';boot3='none';boot4='none';'nested-hw-virt'='off'
        teleporterenabled='off';'tracing-enabled'='off';'autostart-enabled'='off';recording_enabled='off'
        uart1='off';uart2='off';uart3='off';uart4='off';lpt1='off';lpt2='off'
        storagecontrollername0='SATA';storagecontrollertype0='IntelAhci';storagecontrollerportcount0='2'
        CurrentSnapshotName='AIBS_Desktop_PreProvision_20261024'
        CurrentSnapshotUUID='dca55e17-086c-46f4-8cd9-aaf98154e2a5'
        'SATA-ImageUUID-0-0'=$disk;'SATA-ImageUUID-1-0'='0b72ff83-f6d1-4b14-81d7-c637268365b1'
        'SATA-hot-pluggable-0-0'='off';'SATA-hot-pluggable-1-0'='off'
    }
    foreach($n in 1..8){$expected["nic$n"]='none'}
    foreach($key in $expected.Keys){if($Values[$key] -cne $expected[$key]){throw "Desktop VM guard rejected: $key"}}
    if(@($Values.Keys|Where-Object {$_ -match '^storagecontrollername\d+$'}).Count -ne 1 -or
       @($Values.Keys|Where-Object {$_ -match '^SATA-\d+-\d+$'}).Count -ne 2 -or
       @($Values.Keys|Where-Object {$_ -match 'SharedFolder'}).Count){throw 'Unexpected desktop storage or sharing.'}
    Assert-RecoveryPath $Values.CfgFile (Join-Path $base 'AI-BS-Eval-Base-20261023.vbox')
    Assert-RecoveryPath $Values['SATA-0-0'] (Join-Path $base "Snapshots\{$disk}.vdi")
    Assert-RecoveryPath $Values['SATA-1-0'] 'C:\AI-BS\saved_data\phase4_offline_media\AIBS_Windows_Guest_Provisioning_v1.iso'
}
