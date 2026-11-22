# Trusted OFFLINE SYNTHETIC metadata/XML infrastructure; no VM or native commands.
$ErrorActionPreference='Stop'
$candidate=Join-Path $PSScriptRoot 'DesktopProfile.ps1'
if(-not(Test-Path -LiteralPath $candidate)){throw 'RED: DesktopProfile.ps1 is absent; no profile implementation exists.'}
. $candidate
$script:profileCases=New-Object 'System.Collections.Generic.List[object]'
function Test-ProfileAccept([string]$Name,[scriptblock]$Action){
    $null=& $Action
    $script:profileCases.Add([pscustomobject]@{Case=$Name;Passed=$true})
}
function Test-ProfileReject([string]$Name,[scriptblock]$Action){
    $rejected=$false;try{$null=& $Action}catch{$rejected=$true}
    if(-not $rejected){throw "Unexpected acceptance: $Name"}
    $script:profileCases.Add([pscustomobject]@{Case=$Name;Passed=$true})
}
$profiles=@(Get-DesktopInspectionMediaProfiles)
if($profiles.Count-ne 2){throw 'Expected exactly two pinned media profiles.'}
$binding=@{UUID='9f720a31-42c5-462a-ab21-cd34b1140864';Path=$profiles[0].Path;Length=$profiles[0].Length;SHA256=$profiles[0].SHA256}
$base='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023'
# SYNTHETIC CLI fixture: expected current fields, NOT a live hypervisor observation.
$valid=@{
    name='AI-BS-Eval-Base-20261023';UUID='6c5a53da-ab80-4ecb-8be6-4059266f736e';VMState='running'
    memory='8192';cpus='4';firmware='EFI';SecureBoot='on';clipboard='disabled'
    clipboard_file_transfers='off';draganddrop='disabled';usb='off';ehci='off';xhci='off'
    audio='none';audio_in='off';audio_out='off';vrde='off';accelerate3d='off'
    boot1='dvd';boot2='disk';boot3='none';boot4='none';'nested-hw-virt'='off'
    teleporterenabled='off';'tracing-enabled'='off';'autostart-enabled'='off';recording_enabled='off'
    uart1='off';uart2='off';uart3='off';uart4='off';lpt1='off';lpt2='off'
    storagecontrollername0='SATA';storagecontrollertype0='IntelAhci';storagecontrollerportcount0='2'
    CurrentSnapshotName='AIBS_PostDrivers_20261024';CurrentSnapshotUUID='5f014291-52f1-4b18-83c9-37110083b3a0'
    'SATA-ImageUUID-0-0'='9e1efe57-9da5-49f8-acea-763429616968';'SATA-ImageUUID-1-0'=$binding.UUID
    'SATA-hot-pluggable-0-0'='off';'SATA-hot-pluggable-1-0'='off'
    hidpointing='ps2mouse';hidkeyboard='ps2kbd';graphicscontroller='vboxsvga';vram='128';monitorcount='1'
    CfgFile=(Join-Path $base 'AI-BS-Eval-Base-20261023.vbox')
    'SATA-0-0'=(Join-Path $base 'Snapshots\{9e1efe57-9da5-49f8-acea-763429616968}.vdi');'SATA-1-0'=$binding.Path
}
foreach($n in 1..8){$valid["nic$n"]='none'}
$cli=($valid.Keys|Sort-Object|ForEach-Object{'"'+$_+'"="'+([string]$valid[$_]).Replace('\','\\').Replace('"','\"')+'"'})-join "`n"
Test-ProfileAccept 'strict CLI parser roundtrip and literal recording section marker' {
    $parsed=ConvertFrom-DesktopInspectionVMInfo ($cli+"`n rec_screen0`n")
    if($parsed.Count-ne $valid.Count-or $parsed.CfgFile-cne $valid.CfgFile){throw 'Parser changed fields.'}
}
foreach($bad in @('',"name=`"x`"`nNAME=`"y`"",'warning: not a VM observation','name="unterminated','name="bad\q"','name="ok" trailing',('x'*262145),"name=`"a`0b`"",' rec_screen999')){
    Test-ProfileReject 'malformed, duplicate, control or oversized CLI input' {ConvertFrom-DesktopInspectionVMInfo $bad}
}
Test-ProfileAccept 'integer and unquoted facility value are data only' {
    $v=ConvertFrom-DesktopInspectionVMInfo "memory=8192`nGuestAdditionsFacility_VBoxService=50,1792868433`n"
    if($v.memory-cne '8192'-or $v.GuestAdditionsFacility_VBoxService-cne '50,1792868433'){throw 'Wrong parse.'}
}
foreach($state in @('running','saved','poweroff')){
    $copy=$valid.Clone();$copy.VMState=$state
    Test-ProfileAccept "explicit state $state with no task authority" {
        $r=Assert-DesktopInspectionVMInfo $copy $state $binding
        if(-not $r.ProfileMatched-or $r.TaskAuthority-or $r.ProviderAccepted-or $r.RuntimeVerified-or $r.LicensingVerified){throw 'Metadata granted authority.'}
    }
}
foreach($state in @('aborted','paused','','RUNNING')){Test-ProfileReject 'unsupported expected operation state' {Assert-DesktopInspectionVMInfo $valid $state $binding}}
$changed=@{name='other';UUID='00000000-0000-0000-0000-000000000000';VMState='saved';memory='4096';cpus='8';firmware='BIOS';SecureBoot='off';clipboard='bidirectional';clipboard_file_transfers='on';draganddrop='bidirectional';usb='on';ehci='on';xhci='on';audio='was';audio_in='on';audio_out='on';vrde='on';accelerate3d='on';boot1='disk';boot2='dvd';boot3='net';boot4='net';'nested-hw-virt'='on';teleporterenabled='on';'tracing-enabled'='on';'autostart-enabled'='on';recording_enabled='on';uart1='server';uart2='server';uart3='server';uart4='server';lpt1='on';lpt2='on';storagecontrollername0='IDE';storagecontrollertype0='PIIX4';storagecontrollerportcount0='3';storagecontrollername1='IDE';CurrentSnapshotName='AIBS_Desktop_PreProvision_20261024';CurrentSnapshotUUID='dca55e17-086c-46f4-8cd9-aaf98154e2a5';'SATA-ImageUUID-0-0'='7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84';'SATA-ImageUUID-1-0'='0b72ff83-f6d1-4b14-81d7-c637268365b1';'SATA-hot-pluggable-0-0'='on';'SATA-hot-pluggable-1-0'='on';'SATA-2-0'='extra';SharedFolderNameMachineMapping1='host';CfgFile='C:\other.vbox';'SATA-0-0'='C:\other.vdi';'SATA-1-0'='C:\other.iso';hidpointing='usbtablet';hidkeyboard='usbkbd';graphicscontroller='vmsvga';vram='256';monitorcount='2'}
foreach($n in 1..8){$changed["nic$n"]='nat'}
foreach($key in $changed.Keys){$copy=$valid.Clone();$copy[$key]=$changed[$key];Test-ProfileReject "changed VM field $key" {Assert-DesktopInspectionVMInfo $copy 'running' $binding}}
foreach($key in @('UUID','VMState','SecureBoot','nic8','CurrentSnapshotUUID','SATA-0-0','SATA-ImageUUID-1-0','hidpointing','CfgFile')){$copy=$valid.Clone();$copy.Remove($key);Test-ProfileReject "missing required VM field $key" {Assert-DesktopInspectionVMInfo $copy 'running' $binding}}
foreach($key in @('UUID','Path','Length','SHA256')){
    $copy=$binding.Clone();$copy.Remove($key);Test-ProfileReject "missing optical binding $key" {Assert-DesktopInspectionVMInfo $valid 'running' $copy}
}
foreach($entry in @(@('UUID','00000000-0000-0000-0000-000000000000'),@('UUID','not-a-guid'),@('Path','C:\unreviewed.iso'),@('Length',1),@('SHA256',('0'*64)))){
    $copy=$binding.Clone();$copy[$entry[0]]=$entry[1];Test-ProfileReject "unreviewed optical binding $($entry[0])" {Assert-DesktopInspectionVMInfo $valid 'running' $copy}
}
Test-ProfileReject 'binding extra field' {$copy=$binding.Clone();$copy['Trusted']=$true;Assert-DesktopInspectionVMInfo $valid 'running' $copy}
Test-ProfileReject 'path traversal even if it resolves to the same path' {$copy=$valid.Clone();$copy.CfgFile=$base+'\temp\..\AI-BS-Eval-Base-20261023.vbox';Assert-DesktopInspectionVMInfo $copy 'running' $binding}
Test-ProfileAccept 'returned media profiles cannot mutate future pins' {$profiles[0].SHA256='changed';$fresh=@(Get-DesktopInspectionMediaProfiles);if($fresh[0].SHA256-cne $binding.SHA256){throw 'Mutable pins.'}}
# SYNTHETIC XML fixture preserves the observed disk/snapshot graph, with intentionally unsafe
# historical snapshot hardware. Only current Machine/Hardware is an isolation observation.
$snapshotIds=@('5dd088ca-9939-4c13-b285-8eb7b54d8f1c','73cdeb79-50d5-418b-810c-e38840094ea4','afda1952-6c48-4086-9590-897c21323990','dca55e17-086c-46f4-8cd9-aaf98154e2a5','a41350e4-1cd1-438d-bf7a-5110ec4fed47','5f014291-52f1-4b18-83c9-37110083b3a0')
$snapshotNames=@('Snapshot 1','AIBS_Installer_77pct_BlackScreen_20261023','AIBS_PreHeadlessRecovery_1','AIBS_Desktop_PreProvision_20261024','AIBS_PreMouseDriver_20261024','AIBS_PostDrivers_20261024')
$snapshotStates=@('Snapshots/2026-10-23T22-00-19-669064000Z.sav','Snapshots/2026-10-23T23-11-39-231407000Z.sav','','Snapshots/2026-10-24T17-28-04-378390900Z.sav','Snapshots/2026-10-24T18-27-58-241185400Z.sav','Snapshots/2026-10-24T19-02-47-620416800Z.sav')
$snapshots='';for($i=5;$i-ge 0;$i--){$state=if($snapshotStates[$i]){' stateFile="'+$snapshotStates[$i]+'"'}else{''};$snapshots='<Snapshot uuid="{'+$snapshotIds[$i]+'}" name="'+$snapshotNames[$i]+'"'+$state+'><Hardware><Network><Adapter enabled="true"/></Network><Clipboard mode="Bidirectional"/></Hardware>'+$(if($snapshots){'<Snapshots>'+$snapshots+'</Snapshots>'})+'</Snapshot>'}
$diskIds=@('3f632eb6-4348-4aaa-a21d-12b9fdb0f99a','a33ecdc9-9aa5-46d4-b99e-5cd44ef2f721','59e3fed5-5878-4524-8a70-9b0dc7a5067b','cddcb90b-9ea3-42d2-90a5-49de79b7dc0e','7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84','4241e8d4-9315-48e9-aa89-10f7d8ba6ff5','9e1efe57-9da5-49f8-acea-763429616968')
$disks='';for($i=6;$i-ge 0;$i--){$location=if($i-eq 0){'system.vdi'}else{'Snapshots/{'+$diskIds[$i]+'}.vdi'};$disks='<HardDisk uuid="{'+$diskIds[$i]+'}" location="'+$location+'" format="VDI">'+$disks+'</HardDisk>'}
$xmlText='<VirtualBox xmlns="http://www.virtualbox.org/" version="1.19-windows"><Machine uuid="{6c5a53da-ab80-4ecb-8be6-4059266f736e}" name="AI-BS-Eval-Base-20261023" OSType="Windows11_64" currentSnapshot="{5f014291-52f1-4b18-83c9-37110083b3a0}" snapshotFolder="Snapshots"><MediaRegistry><HardDisks>'+$disks+'</HardDisks><DVDImages><Image uuid="{'+$binding.UUID+'}" location="'+$binding.Path.Replace('\','/')+'"/></DVDImages></MediaRegistry>'+$snapshots+'<Hardware><Memory RAMSize="8192"/><Boot><Order position="1" device="DVD"/><Order position="2" device="HardDisk"/><Order position="3" device="None"/><Order position="4" device="None"/></Boot><Display controller="VBoxSVGA" VRAMSize="128"/><Firmware type="EFI"/><BIOS><IOAPIC enabled="true"/></BIOS><TrustedPlatformModule type="v2_0" location=""/><Network><Adapter slot="0" type="82540EM"><NAT localhost-reachable="true"/></Adapter></Network><AudioAdapter useDefault="true" driver="WAS"/><Clipboard/><GuestProperties/><StorageControllers><StorageController name="SATA" type="AHCI" PortCount="2" useHostIOCache="false" Bootable="true"><AttachedDevice type="HardDisk" hotpluggable="false" port="0" device="0"><Image uuid="{9e1efe57-9da5-49f8-acea-763429616968}"/></AttachedDevice><AttachedDevice type="DVD" hotpluggable="false" passthrough="false" port="1" device="0"><Image uuid="{'+$binding.UUID+'}"/></AttachedDevice></StorageController></StorageControllers><CPU count="4"><HardwareVirtExLargePages enabled="true"/><PAE enabled="false"/><LongMode enabled="true"/></CPU></Hardware></Machine></VirtualBox>'
Test-ProfileAccept 'current XML matches despite explicitly unsafe historical hardware' {$x=Read-DesktopInspectionXmlSafe $xmlText;$r=Assert-DesktopInspectionXml $x $valid $binding;if($r.TaskAuthority-or -not$r.ProfileMatched){throw 'XML granted authority.'}}
foreach($replacement in @(
    @('currentSnapshot="{5f014291-52f1-4b18-83c9-37110083b3a0}"','currentSnapshot="{a41350e4-1cd1-438d-bf7a-5110ec4fed47}"'),
    @('<Memory RAMSize="8192"/>','<Memory RAMSize="4096"/>'),
    @('<Firmware type="EFI"/>','<Firmware type="BIOS"/>'),
    @('<TrustedPlatformModule type="v2_0" location=""/>','<TrustedPlatformModule type="v1_2"/>'),
    @('<Adapter slot="0" type="82540EM">','<Adapter slot="0" type="82540EM" enabled="true">'),
    @('<AudioAdapter useDefault="true" driver="WAS"/>','<AudioAdapter enabled="true"/>'),
    @('<Clipboard/>','<Clipboard mode="Bidirectional"/>'),
    @('<GuestProperties/>','<USB><Controllers><Controller name="xHCI" type="XHCI"/></Controllers></USB>'),
    @('<GuestProperties/>','<SharedFolders><SharedFolder name="host" hostPath="C:/AI-BS"/></SharedFolders>'),
    @('<GuestProperties/>','<DragAndDrop mode="Bidirectional"/>'),
    @('<GuestProperties/>','<RemoteDisplay enabled="true"/>'),
    @('<GuestProperties/>','<Tracing enabled="true"/>'),
    @('<GuestProperties/>','<GuestProperties/><Memory RAMSize="8192"/>'),
    @('PortCount="2"','PortCount="3"'),
    @('hotpluggable="false" port="0"','hotpluggable="true" port="0"'),
    @('passthrough="false"','passthrough="true"'),
    @('<CPU count="4">','<CPU count="8">'),
    @('Snapshots/2026-10-24T19-02-47-620416800Z.sav','Snapshots/other.sav'),
    @('location="Snapshots/{4241e8d4-9315-48e9-aa89-10f7d8ba6ff5}.vdi"','location="../outside.vdi"'),
    @('location="Snapshots/{9e1efe57-9da5-49f8-acea-763429616968}.vdi"','location="Snapshots/{other}.vdi"'),
    @('http://www.virtualbox.org/','http://invalid.example/')
)){
    $badXml=$xmlText.Replace($replacement[0],$replacement[1]);Test-ProfileReject 'changed XML current hardware, media, graph or namespace' {$x=Read-DesktopInspectionXmlSafe $badXml;Assert-DesktopInspectionXml $x $valid $binding}
}
Test-ProfileReject 'XML exact optical registration path' {$x=Read-DesktopInspectionXmlSafe ($xmlText.Replace($binding.Path.Replace('\','/'),'C:/unreviewed.iso'));Assert-DesktopInspectionXml $x $valid $binding}
Test-ProfileReject 'XML optical registration UUID mismatch' {$x=Read-DesktopInspectionXmlSafe ($xmlText.Replace('uuid="{'+$binding.UUID+'}" location=','uuid="{11111111-1111-4111-8111-111111111111}" location='));Assert-DesktopInspectionXml $x $valid $binding}
Test-ProfileReject 'XML duplicate current Hardware' {$x=Read-DesktopInspectionXmlSafe ($xmlText.Replace('</Machine>','<Hardware/></Machine>'));Assert-DesktopInspectionXml $x $valid $binding}
Test-ProfileReject 'XML inserted disk changes direct ancestry' {$x=Read-DesktopInspectionXmlSafe ($xmlText.Replace('<HardDisk uuid="{9e1efe57-9da5-49f8-acea-763429616968}"','<HardDisk uuid="{11111111-1111-4111-8111-111111111111}"'));Assert-DesktopInspectionXml $x $valid $binding}
Test-ProfileReject 'DTD and external entity denied before expansion' {Read-DesktopInspectionXmlSafe '<!DOCTYPE VirtualBox [<!ENTITY x SYSTEM "file:///C:/private">]><VirtualBox>&x;</VirtualBox>'}
Test-ProfileReject 'oversized XML rejected before parse' {Read-DesktopInspectionXmlSafe ('x'*1048577)}
Test-ProfileAccept 'second fixed reviewed media with independently bound UUID' {
    $second=@{UUID='22222222-2222-4222-8222-222222222222';Path=$profiles[1].Path;Length=$profiles[1].Length;SHA256=$profiles[1].SHA256};$v=$valid.Clone();$v['SATA-ImageUUID-1-0']=$second.UUID;$v['SATA-1-0']=$second.Path
    $x=Read-DesktopInspectionXmlSafe ($xmlText.Replace($binding.UUID,$second.UUID).Replace($binding.Path.Replace('\','/'),$second.Path.Replace('\','/')))
    $null=Assert-DesktopInspectionVMInfo $v 'running' $second;$null=Assert-DesktopInspectionXml $x $v $second
}
[pscustomobject]@{Mode='OFFLINE_SYNTHETIC_VMINFO_AND_XML';PassedCases=$script:profileCases.Count;TaskAuthority=$false;ProviderAccepted=$false;ActualContainmentCasesRun=0;Cases=$script:profileCases}|ConvertTo-Json -Depth 6
