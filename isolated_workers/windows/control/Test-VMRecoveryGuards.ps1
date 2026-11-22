# Offline data tests only. These are NOT the Phase4 guest acceptance cases.
$ErrorActionPreference='Stop'
. "$PSScriptRoot\VM-RecoveryGuards.ps1"
$fixture=Get-Content "$PSScriptRoot\..\runtime\current_inspection_20261024T1547293906514Z\showvminfo.stdout.txt" -Raw
$valid=ConvertFrom-RecoveryVMInfo $fixture
$disk='59e3fed5-5878-4524-8a70-9b0dc7a5067b'
$snapshot='73cdeb79-50d5-418b-810c-e38840094ea4'
$results=@()
Assert-RecoveryVMInfo $valid 'aborted' $disk $snapshot
$results+=@{Case='retained offline fixture accepted';Passed=$true}
$mutations=@{
    UUID='00000000-0000-0000-0000-000000000000'; VMState='running'; SecureBoot='off'
    clipboard='bidirectional'; clipboard_file_transfers='on'; draganddrop='bidirectional'
    usb='on'; ehci='on'; xhci='on'; vrde='on'; accelerate3d='on'; audio='was'
    CurrentSnapshotUUID='5dd088ca-9939-4c13-b285-8eb7b54d8f1c'; 'SATA-ImageUUID-0-0'='wrong'
    'SATA-0-0'='C:\other.vdi'; 'SATA-1-0'='C:\other.iso'; CfgFile='C:\other.vbox'
    storagecontrollername1='IDE'; 'SATA-2-0'='extra'; SharedFolderNameMachineMapping1='host'
    uart1='server'; lpt1='on'; 'nested-hw-virt'='on'; teleporterenabled='on'; 'tracing-enabled'='on'
}
foreach($n in 1..8){$mutations["nic$n"]='nat'}
foreach($key in $mutations.Keys){
    $copy=$valid.Clone();$copy[$key]=$mutations[$key];$rejected=$false
    try{Assert-RecoveryVMInfo $copy 'aborted' $disk $snapshot}catch{$rejected=$true}
    if(-not $rejected){throw "Unsafe field accepted: $key"}
    $results+=@{Case="reject $key";Passed=$true}
}
foreach($key in @('SecureBoot','nic8','UUID','SATA-0-0')){
    $copy=$valid.Clone();$copy.Remove($key);$rejected=$false
    try{Assert-RecoveryVMInfo $copy 'aborted' $disk $snapshot}catch{$rejected=$true}
    if(-not $rejected){throw "Missing field accepted: $key"}
    $results+=@{Case="reject missing $key";Passed=$true}
}
$rejected=$false
try{$null=ConvertFrom-RecoveryVMInfo ($fixture+"`nUUID=duplicate")}catch{$rejected=$true}
if(-not $rejected){throw 'Duplicate field accepted.'}
$results+=@{Case='reject duplicate field';Passed=$true}
$results | ConvertTo-Json -Depth 4
