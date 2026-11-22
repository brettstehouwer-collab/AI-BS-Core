$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'IntegrationProfile.ps1')
$prior='C:\AI-BS\isolated_workers\windows\runtime\desktop_inspection_v1\inspection_20261026T0135210380212Z_4e248c90f4dc4748af3d1598ef26ed8e'
$result=Join-Path $prior 'query-1-result.json'
if((Get-FileHash $result -Algorithm SHA256).Hash-cne 'A5A929941FC9725401C21F66BC93C262DADA8078C4679E17368D4436D549633C'){throw 'RETAINED_QUERY_CHANGED'}
$q=([IO.File]::ReadAllText($result)|ConvertFrom-Json).Result
$intent=[IO.File]::ReadAllText((Join-Path $prior 'intent.json'))|ConvertFrom-Json
$binding=@{UUID=[string]$intent.OpticalBinding.UUID;Path=[string]$intent.OpticalBinding.Path;Length=[long]$intent.OpticalBinding.Length;SHA256=[string]$intent.OpticalBinding.SHA256}
# Synthetic updated metadata from retained query, NOT a fresh worker query.
$values=ConvertFrom-DesktopInspectionVMInfo $q.Stdout
$values.memory='16384';$values.nic1='nat';$values.usb='on'
$config=$values.CfgFile;$bytes=[IO.File]::ReadAllBytes($config);$liveText=[IO.File]::ReadAllText($config)
# Pivot to a synthetic reviewed fixture: audio disabled and optical hotplug off.
# Never write these fixture values to the VM or label them current admission.
$fixture=Read-DesktopInspectionXmlSafe $liveText
$machine=Get-DesktopInspectionXmlOne $fixture.DocumentElement 'Machine';$hardware=Get-DesktopInspectionXmlOne $machine 'Hardware'
$audio=Get-DesktopInspectionXmlOne $hardware 'AudioAdapter'
foreach($field in @('enabled','enabledIn','enabledOut')){$audio.SetAttribute($field,'false')}
$storage=Get-DesktopInspectionXmlOne $hardware 'StorageControllers';$sata=Get-DesktopInspectionXmlOne $storage 'StorageController'
foreach($device in $sata.ChildNodes){if($device.NodeType-eq [Xml.XmlNodeType]::Element-and $device.GetAttribute('type')-ceq 'DVD'){$device.SetAttribute('hotpluggable','false')}}
$text=$fixture.OuterXml
$observed=Assert-IntegrationObservationXml (Read-DesktopInspectionXmlSafe $text) $values $binding
if($observed.TaskAuthority-or $observed.ProviderAccepted-or $observed.TransportAccepted-or $observed.ContainmentAccepted-or -not $observed.UnrestrictedLoopbackExposure){throw 'FALSE_ACCEPTANCE'}
$count=1
function Denied([ScriptBlock]$Action){$denied=$false;try{$null=& $Action}catch{$denied=$true};if(-not $denied){throw 'UNEXPECTED_ADMISSION'};$script:count++}
Denied {Assert-IntegrationObservationXml (Read-DesktopInspectionXmlSafe $liveText) $values $binding}
foreach($pair in @(@('memory','8192'),@('nic1','bridged'),@('nic2','nat'),@('clipboard','bidirectional'),@('UUID','00000000-0000-0000-0000-000000000001'))){
 $v=$values.Clone();$v[$pair[0]]=$pair[1];Denied {Assert-IntegrationObservationXml (Read-DesktopInspectionXmlSafe $text) $v $binding}
}
foreach($mutation in @('RAM','BRIDGE','FORWARD','NIC2','USB','SHARE','DISK','CLIPBOARD')){
 $x=Read-DesktopInspectionXmlSafe $text;$m=Get-DesktopInspectionXmlOne $x.DocumentElement 'Machine';$h=Get-DesktopInspectionXmlOne $m 'Hardware';$net=Get-DesktopInspectionXmlOne $h 'Network';$a=Get-DesktopInspectionXmlOne $net 'Adapter'
 switch($mutation){
  RAM{(Get-DesktopInspectionXmlOne $h 'Memory').SetAttribute('RAMSize','8192')}
  BRIDGE{$null=$a.AppendChild($x.CreateElement('BridgedInterface','http://www.virtualbox.org/'))}
  FORWARD{$nat=Get-DesktopInspectionXmlOne $a 'NAT';$null=$nat.AppendChild($x.CreateElement('Forwarding','http://www.virtualbox.org/'))}
  NIC2{$null=$net.AppendChild($a.CloneNode($true))}
  USB{$usb=Get-DesktopInspectionXmlOne $h 'USB';$null=$usb.AppendChild($x.CreateElement('Controllers','http://www.virtualbox.org/'))}
  SHARE{$null=$h.AppendChild($x.CreateElement('SharedFolders','http://www.virtualbox.org/'))}
  DISK{$controllers=Get-DesktopInspectionXmlOne $h 'StorageControllers';$null=$controllers.AppendChild((Get-DesktopInspectionXmlOne $controllers 'StorageController').CloneNode($true))}
  CLIPBOARD{(Get-DesktopInspectionXmlOne $h 'Clipboard').SetAttribute('mode','Bidirectional')}
 }
 Denied {Assert-IntegrationObservationXml $x $values $binding}
}
Denied {Read-DesktopInspectionXmlSafe '<!DOCTYPE x [<!ENTITY e SYSTEM "file:///C:/private">]><x>&e;</x>'}
$pin=Get-IntegrationObservationSpec
$sample=[Text.Encoding]::UTF8.GetBytes('synthetic configuration bytes')
$alg=[Security.Cryptography.SHA256]::Create();try{$sampleHash=[BitConverter]::ToString($alg.ComputeHash($sample)).Replace('-','')}finally{$alg.Dispose()}
$null=Assert-IntegrationObservationFingerprint $sample $sampleHash;$count++
$changed=[byte[]]$sample.Clone();$changed[0]=$changed[0]-bxor 1
Denied {Assert-IntegrationObservationFingerprint $changed $sampleHash}
# The VM manager rewrote the config after Record109. Preserve the prior pin:
# drift is a rejection test, never an automatic repin or task admission.
Denied {Assert-IntegrationObservationFingerprint $bytes $pin.ConfigurationSHA256}
Denied {Assert-IntegrationObservationFingerprint $bytes 'bad'}
if([Convert]::ToBase64String($bytes)-cne [Convert]::ToBase64String([IO.File]::ReadAllBytes($config))){throw 'CONFIGURATION_MUTATED'}
Write-Output ('RESULT passed='+$count+'; synthetic audio-disabled/optical-hotplug-disabled XML and updated metadata; actual XML refused; no native/guest/task authority.')
