# Offline synthetic VM-info tests only. No hypervisor process or guest command.
$ErrorActionPreference='Stop'
$candidate=Join-Path $PSScriptRoot 'VM-DesktopGuards.ps1'
if(-not(Test-Path -LiteralPath $candidate)){throw 'Desktop profile guard is missing.'}
. $candidate
$fixture=Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\runtime\current_inspection_20261024T1547293906514Z\showvminfo.stdout.txt') -Raw
# Deliberately synthetic: only the old inspection is an actual CLI observation.
# New identity values come from the preserved desktop XML/media receipts.
$valid=ConvertFrom-RecoveryVMInfo $fixture
$valid.name='AI-BS-Eval-Base-20261023'
$valid.VMState='running'
$valid.CurrentSnapshotName='AIBS_Desktop_PreProvision_20261024'
$valid.CurrentSnapshotUUID='dca55e17-086c-46f4-8cd9-aaf98154e2a5'
$valid['SATA-ImageUUID-0-0']='7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84'
$valid['SATA-0-0']='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023\Snapshots\{7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84}.vdi'
$valid['SATA-ImageUUID-1-0']='0b72ff83-f6d1-4b14-81d7-c637268365b1'
$valid['SATA-1-0']='C:\AI-BS\saved_data\phase4_offline_media\AIBS_Windows_Guest_Provisioning_v1.iso'
$results=@()
Assert-DesktopVMInfo $valid 'running'
$results+=@{Case='synthetic exact running desktop profile';Passed=$true}
$saved=$valid.Clone();$saved.VMState='saved'
Assert-DesktopVMInfo $saved 'saved'
$results+=@{Case='synthetic exact saved desktop profile';Passed=$true}
$mutations=@{
    name='Another VM'; UUID='00000000-0000-0000-0000-000000000000';VMState='aborted'
    memory='4096';cpus='8';firmware='BIOS';SecureBoot='off'
    clipboard='bidirectional';clipboard_file_transfers='on';draganddrop='bidirectional'
    usb='on';ehci='on';xhci='on';vrde='on';accelerate3d='on'
    audio='was';audio_in='on';audio_out='on';boot1='disk';boot2='dvd';boot3='net';boot4='net'
    'nested-hw-virt'='on';teleporterenabled='on';'tracing-enabled'='on';'autostart-enabled'='on';recording_enabled='on'
    uart1='server';uart2='server';uart3='server';uart4='server';lpt1='on';lpt2='on'
    storagecontrollername0='IDE';storagecontrollertype0='PIIX4';storagecontrollerportcount0='3';storagecontrollername1='IDE'
    CurrentSnapshotName='AIBS_PreHeadlessRecovery_1';CurrentSnapshotUUID='afda1952-6c48-4086-9590-897c21323990'
    'SATA-ImageUUID-0-0'='cddcb90b-9ea3-42d2-90a5-49de79b7dc0e';'SATA-0-0'='C:\other.vdi'
    'SATA-ImageUUID-1-0'='9f172218-11ff-45fa-b2ff-9faed642a36c';'SATA-1-0'='C:\other.iso'
    'SATA-hot-pluggable-0-0'='on';'SATA-hot-pluggable-1-0'='on';'SATA-2-0'='extra'
    SharedFolderNameMachineMapping1='host';CfgFile='C:\other.vbox'
}
foreach($n in 1..8){$mutations["nic$n"]='nat'}
foreach($key in $mutations.Keys){
    $copy=$valid.Clone();$copy[$key]=$mutations[$key];$rejected=$false
    try{Assert-DesktopVMInfo $copy 'running'}catch{$rejected=$true}
    if(-not $rejected){throw "Changed desktop field was accepted: $key"}
    $results+=@{Case="reject changed $key";Passed=$true}
}
foreach($key in @('UUID','VMState','name','SecureBoot','nic8','CurrentSnapshotName','CurrentSnapshotUUID','SATA-0-0','SATA-ImageUUID-1-0','CfgFile')){
    $copy=$valid.Clone();$copy.Remove($key);$rejected=$false
    try{Assert-DesktopVMInfo $copy 'running'}catch{$rejected=$true}
    if(-not $rejected){throw "Missing desktop field was accepted: $key"}
    $results+=@{Case="reject missing $key";Passed=$true}
}
foreach($state in @('aborted','poweroff','', 'RUNNING')){
    $rejected=$false;try{Assert-DesktopVMInfo $valid $state}catch{$rejected=$true}
    if(-not $rejected){throw 'Unexpected state request accepted.'}
    $results+=@{Case="reject expected state [$state]";Passed=$true}
}
$rejected=$false;try{Assert-DesktopVMInfo $saved 'running'}catch{$rejected=$true}
if(-not $rejected){throw 'Saved VM was accepted for an operation requiring running state.'}
$results+=@{Case='reject caller/state mismatch';Passed=$true}
$rejected=$false
try{Assert-RecoveryVMInfo $valid 'running' '7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84' 'dca55e17-086c-46f4-8cd9-aaf98154e2a5'}catch{$rejected=$true}
if(-not $rejected){throw 'Historical guard unexpectedly admitted desktop media.'}
$results+=@{Case='unchanged historical recovery guard still rejects desktop media';Passed=$true}
[pscustomobject]@{Mode='OFFLINE_SYNTHETIC_VMINFO';PassedCases=$results.Count;GuestAcceptance=$false;ControllerEnabled=$false;Cases=$results}|ConvertTo-Json -Depth 6
