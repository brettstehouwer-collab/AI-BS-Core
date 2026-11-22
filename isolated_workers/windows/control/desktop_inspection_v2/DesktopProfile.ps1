# Pure, bounded metadata/XML validation for one preserved desktop graph.
# No dot-sourced controller, process launch, filesystem write, guest command or task authority.
function Get-DesktopInspectionMediaProfiles {
    return @(
        [pscustomobject]@{Name='diagnostic_v2';Path='C:\AI-BS\isolated_workers\windows\media\guest_check_v2_20261024T1920072312648Z\AIBS_Guest_Check_v2.iso';Length=[long]75776;SHA256='59ADE00A6E8A7CE1CB77930562CF973475C7BCE18F2A51BB9A701FD938D09546'},
        [pscustomobject]@{Name='offline_wheels_v1';Path='C:\AI-BS\backups\phase4_wheel_setup_media_20261024T2003424861639Z\AI-BS_Wheels_v1.iso';Length=[long]7153664;SHA256='B6B5703DC0A262E0D8E2A85D7221EA3F830EB45DE38166997FEBFC510A37A5B3'}
    )
}
function ConvertFrom-DesktopInspectionVMInfo([string]$Text) {
    if([string]::IsNullOrWhiteSpace($Text)-or $Text.Length-gt 262144-or [Text.Encoding]::UTF8.GetByteCount($Text)-gt 262144-or $Text.IndexOf([char]0)-ge 0){throw 'VMINFO_INPUT_BOUND'}
    $values=@{};$sections=@{};$lines=$Text -split "`r?`n"
    if($lines.Count-gt 4096){throw 'VMINFO_LINE_BOUND'}
    foreach($line in $lines){
        if($line.Length-eq 0){continue}
        if($line.Length-gt 16384-or $line-match '[\x00-\x1f\x7f]'){throw 'VMINFO_LINE_BOUND'}
        # VBoxManage emits these literal recording headings among machine-readable pairs.
        if($line-match '^ rec_screen([0-9]|[1-5][0-9]|6[0-3])$'){
            if($sections.ContainsKey($line)){throw 'VMINFO_DUPLICATE_SECTION'};$sections[$line]=$true;continue
        }
        if($line-cnotmatch '^(?:"([A-Za-z0-9_.:/ ()-]{1,128})"|([A-Za-z0-9_.:/ ()-]{1,128}))=(.*)$'){throw 'VMINFO_FIELD_SYNTAX'}
        $key=if($matches[1]){$matches[1]}else{$matches[2]};$raw=$matches[3]
        if($values.ContainsKey($key)-or $values.Count-ge 2048){throw 'VMINFO_DUPLICATE_OR_FIELD_BOUND'}
        if($raw.StartsWith('"')){
            if($raw-cnotmatch '^"((?:[^"\\]|\\["\\])*)"$'){throw 'VMINFO_VALUE_SYNTAX'}
            $value=[regex]::Replace($matches[1],'\\(["\\])','$1')
        }else{
            if($raw.Length-eq 0-or $raw-match '["\x00-\x1f\x7f]'){throw 'VMINFO_VALUE_SYNTAX'};$value=$raw
        }
        $values[$key]=[string]$value
    }
    if($values.Count-eq 0){throw 'VMINFO_EMPTY'}
    return $values
}
function ConvertTo-DesktopInspectionPath([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path)-or $Path.Length-gt 2048){throw 'PROFILE_PATH_REQUIRED'}
    $p=$Path.Replace('/','\')
    if($p-cnotmatch '^[A-Za-z]:\\'-or $p.Substring(2)-match '[:<>"|?*\x00-\x1f]'-or $p.Substring(3)-match '\\\\|(?:^|\\)\.{1,2}(?:\\|$)|(?:^|\\)[^\\]*[ .](?:\\|$)'){throw 'PROFILE_LOCAL_CANONICAL_PATH_REQUIRED'}
    return [IO.Path]::GetFullPath($p).TrimEnd('\')
}
function Assert-DesktopInspectionPath([string]$Actual,[string]$Expected) {
    if((ConvertTo-DesktopInspectionPath $Actual)-ine (ConvertTo-DesktopInspectionPath $Expected)){throw 'PROFILE_PATH_MISMATCH'}
}
function Assert-DesktopInspectionGuid([string]$Value) {
    $id=[guid]::Empty
    if(-not [guid]::TryParseExact($Value,'D',[ref]$id)-or $id-eq [guid]::Empty){throw 'PROFILE_UUID_REQUIRED'}
}
function Assert-DesktopInspectionOpticalBinding([hashtable]$Binding) {
    if($null-eq $Binding-or $Binding.Count-ne 4){throw 'OPTICAL_BINDING_FIELDS'}
    foreach($key in @('UUID','Path','Length','SHA256')){if(-not $Binding.ContainsKey($key)){throw 'OPTICAL_BINDING_FIELDS'}}
    if($Binding.UUID-isnot [string]-or $Binding.Path-isnot [string]-or $Binding.SHA256-isnot [string]-or ($Binding.Length-isnot [int]-and $Binding.Length-isnot [long])){throw 'OPTICAL_BINDING_TYPES'}
    Assert-DesktopInspectionGuid $Binding.UUID
    if($Binding.SHA256-cnotmatch '^[A-Fa-f0-9]{64}$'){throw 'OPTICAL_BINDING_HASH'}
    $matched=@(Get-DesktopInspectionMediaProfiles|Where-Object {(ConvertTo-DesktopInspectionPath $_.Path)-ieq (ConvertTo-DesktopInspectionPath $Binding.Path)-and $_.Length-eq $Binding.Length-and $_.SHA256-ieq $Binding.SHA256})
    if($matched.Count-ne 1){throw 'OPTICAL_MEDIA_NOT_REVIEWED'}
}
function New-DesktopInspectionProfileResult([string]$State,[hashtable]$OpticalBinding) {
    return [pscustomobject]@{ProfileMatched=$true;TaskAuthority=$false;ProviderAccepted=$false;RuntimeVerified=$false;LicensingVerified=$false;Scope='CURRENT_DESKTOP_METADATA_ONLY';ExpectedState=$State;VMUUID='6c5a53da-ab80-4ecb-8be6-4059266f736e';SnapshotUUID='5f014291-52f1-4b18-83c9-37110083b3a0';DiskUUID='9e1efe57-9da5-49f8-acea-763429616968';OpticalUUID=$OpticalBinding.UUID;OpticalPath=$OpticalBinding.Path;OpticalSHA256=$OpticalBinding.SHA256}
}
function Assert-DesktopInspectionVMInfo([hashtable]$Values,[string]$ExpectedState,[hashtable]$OpticalBinding) {
    if($ExpectedState-cnotin @('running','saved','poweroff')){throw 'EXPLICIT_DESKTOP_STATE_REQUIRED'}
    if($null-eq $Values-or $Values.Count-gt 2048){throw 'VMINFO_FIELDS_REQUIRED'}
    Assert-DesktopInspectionOpticalBinding $OpticalBinding
    $expected=@{
        name='AI-BS-Eval-Base-20261023';UUID='6c5a53da-ab80-4ecb-8be6-4059266f736e';VMState=$ExpectedState
        memory='8192';cpus='4';firmware='EFI';SecureBoot='on';clipboard='disabled'
        clipboard_file_transfers='off';draganddrop='disabled';usb='off';ehci='off';xhci='off'
        audio='none';audio_in='off';audio_out='off';vrde='off';accelerate3d='off'
        boot1='dvd';boot2='disk';boot3='none';boot4='none';'nested-hw-virt'='off'
        teleporterenabled='off';'tracing-enabled'='off';'autostart-enabled'='off';recording_enabled='off'
        uart1='off';uart2='off';uart3='off';uart4='off';lpt1='off';lpt2='off'
        storagecontrollername0='SATA';storagecontrollertype0='IntelAhci';storagecontrollerportcount0='2'
        CurrentSnapshotName='AIBS_PostDrivers_20261024';CurrentSnapshotUUID='5f014291-52f1-4b18-83c9-37110083b3a0'
        'SATA-ImageUUID-0-0'='9e1efe57-9da5-49f8-acea-763429616968';'SATA-ImageUUID-1-0'=$OpticalBinding.UUID
        'SATA-hot-pluggable-0-0'='off';'SATA-hot-pluggable-1-0'='off'
        hidpointing='ps2mouse';hidkeyboard='ps2kbd';graphicscontroller='vboxsvga';vram='128';monitorcount='1'
    }
    foreach($n in 1..8){$expected["nic$n"]='none'}
    foreach($key in $expected.Keys){if($Values[$key]-isnot [string]-or $Values[$key]-cne $expected[$key]){throw ('DESKTOP_FIELD_MISMATCH_'+$key)}}
    # VBoxManage also emits indexed snapshot metadata. These three recognized
    # names are not storage attachment aliases; the exact snapshot graph is
    # independently bound by Assert-DesktopInspectionXml below.
    $unexpected=@($Values.Keys|Where-Object {
        $_-match 'SharedFolder'-or (
            $_-match '^[A-Za-z0-9_. ]+-\d+-\d+$'-and
            $_-cnotin @('SATA-0-0','SATA-1-0')-and
            $_-cnotmatch '^(?:SnapshotName|SnapshotUUID|SnapshotDescription)-[1-9][0-9]*-[1-9][0-9]*$'
        )
    })
    if(@($Values.Keys|Where-Object {$_-match '^storagecontrollername\d+$'}).Count-ne 1-or @($Values.Keys|Where-Object {$_-match '^SATA-\d+-\d+$'}).Count-ne 2-or $unexpected.Count){throw 'UNEXPECTED_STORAGE_OR_SHARING'}
    $base='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023'
    Assert-DesktopInspectionPath $Values.CfgFile (Join-Path $base 'AI-BS-Eval-Base-20261023.vbox')
    Assert-DesktopInspectionPath $Values['SATA-0-0'] (Join-Path $base 'Snapshots\{9e1efe57-9da5-49f8-acea-763429616968}.vdi')
    Assert-DesktopInspectionPath $Values['SATA-1-0'] $OpticalBinding.Path
    return New-DesktopInspectionProfileResult $ExpectedState $OpticalBinding
}
function Read-DesktopInspectionXmlSafe([string]$Text) {
    if([string]::IsNullOrWhiteSpace($Text)-or $Text.Length-gt 1048576-or [Text.Encoding]::UTF8.GetByteCount($Text)-gt 1048576){throw 'XML_INPUT_BOUND'}
    $settings=New-Object Xml.XmlReaderSettings;$settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit;$settings.XmlResolver=$null
    $settings.MaxCharactersInDocument=1048576;$settings.MaxCharactersFromEntities=0
    $inputText=New-Object IO.StringReader($Text);$reader=$null
    try{$reader=[Xml.XmlReader]::Create($inputText,$settings);$doc=New-Object Xml.XmlDocument;$doc.XmlResolver=$null;$doc.Load($reader);return ,$doc}
    finally{if($null-ne $reader){$reader.Dispose()};$inputText.Dispose()}
}
function Get-DesktopInspectionXmlOne([Xml.XmlNode]$Node,[string]$Name) {
    $nodes=@($Node.ChildNodes|Where-Object {$_.NodeType-eq [Xml.XmlNodeType]::Element-and $_.LocalName-ceq $Name-and $_.NamespaceURI-ceq 'http://www.virtualbox.org/'})
    if($nodes.Count-ne 1){throw ('XML_SINGLE_NODE_REQUIRED_'+$Name)};return ,$nodes[0]
}
function Assert-DesktopInspectionXmlNames([Xml.XmlNode]$Node,[string[]]$Names) {
    foreach($child in $Node.ChildNodes){if($child.NodeType-eq [Xml.XmlNodeType]::Element-and ($child.NamespaceURI-cne 'http://www.virtualbox.org/'-or $child.LocalName-cnotin $Names)){throw 'XML_UNEXPECTED_NODE'}}
}
function Assert-DesktopInspectionXmlAttribute([Xml.XmlElement]$Node,[string]$Name,[string]$Expected,[bool]$AllowAbsent=$false) {
    if($AllowAbsent-and -not $Node.HasAttribute($Name)){return};if(-not $Node.HasAttribute($Name)-or $Node.GetAttribute($Name)-cne $Expected){throw ('XML_ATTRIBUTE_MISMATCH_'+$Name)}
}
function Assert-DesktopInspectionXmlUuid([Xml.XmlElement]$Node,[string]$Name,[string]$Expected) {Assert-DesktopInspectionXmlAttribute $Node $Name ('{'+$Expected+'}')}
function Assert-DesktopInspectionXml([Xml.XmlDocument]$Xml,[hashtable]$Values,[hashtable]$OpticalBinding) {
    $null=Assert-DesktopInspectionVMInfo $Values $Values.VMState $OpticalBinding
    if($null-eq $Xml-or $null-ne $Xml.DocumentType-or $Xml.OuterXml.Length-gt 1048576){throw 'XML_DOCUMENT_REFUSED'}
    $Xml.XmlResolver=$null;$root=$Xml.DocumentElement
    if($null-eq $root-or $root.LocalName-cne 'VirtualBox'-or $root.NamespaceURI-cne 'http://www.virtualbox.org/'){throw 'XML_ROOT_MISMATCH'}
    Assert-DesktopInspectionXmlAttribute $root 'version' '1.19-windows'
    Assert-DesktopInspectionXmlNames $root @('Machine');$machine=Get-DesktopInspectionXmlOne $root 'Machine'
    Assert-DesktopInspectionXmlUuid $machine 'uuid' '6c5a53da-ab80-4ecb-8be6-4059266f736e'
    Assert-DesktopInspectionXmlAttribute $machine 'name' 'AI-BS-Eval-Base-20261023';Assert-DesktopInspectionXmlAttribute $machine 'OSType' 'Windows11_64'
    Assert-DesktopInspectionXmlUuid $machine 'currentSnapshot' '5f014291-52f1-4b18-83c9-37110083b3a0';Assert-DesktopInspectionXmlAttribute $machine 'snapshotFolder' 'Snapshots'
    Assert-DesktopInspectionXmlNames $machine @('MediaRegistry','ExtraData','Description','Snapshot','Hardware')
    if($machine.HasAttribute('stateFile')){
        if($Values.VMState-cne 'saved'-or $machine.GetAttribute('stateFile')-cnotmatch '^Snapshots[/\\][0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{9}Z\.sav$'){throw 'XML_CURRENT_STATE_PATH_MISMATCH'}
    }elseif($Values.VMState-ceq 'saved'){throw 'XML_SAVED_STATE_FILE_REQUIRED'}
    $registry=Get-DesktopInspectionXmlOne $machine 'MediaRegistry';Assert-DesktopInspectionXmlNames $registry @('HardDisks','DVDImages')
    $hardDisks=Get-DesktopInspectionXmlOne $registry 'HardDisks';Assert-DesktopInspectionXmlNames $hardDisks @('HardDisk')
    $chain=@('3f632eb6-4348-4aaa-a21d-12b9fdb0f99a','a33ecdc9-9aa5-46d4-b99e-5cd44ef2f721','59e3fed5-5878-4524-8a70-9b0dc7a5067b','cddcb90b-9ea3-42d2-90a5-49de79b7dc0e','7dd3e9fa-d52e-4e63-b9b8-4fa5663ffe84','4241e8d4-9315-48e9-aa89-10f7d8ba6ff5','9e1efe57-9da5-49f8-acea-763429616968')
    $disk=Get-DesktopInspectionXmlOne $hardDisks 'HardDisk';$allUUIDs=@{}
    for($i=0;$i-lt $chain.Count;$i++){
        Assert-DesktopInspectionXmlUuid $disk 'uuid' $chain[$i];Assert-DesktopInspectionXmlAttribute $disk 'format' 'VDI'
        if($disk.HasAttribute('type')-and $disk.type-cne 'Normal'){throw 'XML_DISK_TYPE_MISMATCH'}
        $location=if($i-eq 0){'system.vdi'}else{'Snapshots/{'+$chain[$i]+'}.vdi'}
        if($disk.GetAttribute('location').Replace('\','/')-cne $location){throw 'XML_DISK_LOCATION_MISMATCH'}
        $allUUIDs[$chain[$i]]=$true;Assert-DesktopInspectionXmlNames $disk @('HardDisk')
        if($i-lt ($chain.Count-1)){$disk=Get-DesktopInspectionXmlOne $disk 'HardDisk'}elseif(@($disk.ChildNodes|Where-Object {$_.NodeType-eq [Xml.XmlNodeType]::Element}).Count){throw 'XML_UNEXPECTED_CURRENT_DISK_CHILD'}
    }
    $dvds=Get-DesktopInspectionXmlOne $registry 'DVDImages';Assert-DesktopInspectionXmlNames $dvds @('Image');$opticalMatches=0
    foreach($dvd in @($dvds.ChildNodes|Where-Object {$_.NodeType-eq [Xml.XmlNodeType]::Element})){
        $id=$dvd.GetAttribute('uuid');if($id-cnotmatch '^\{([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\}$'){throw 'XML_MEDIA_UUID_INVALID'};$id=$matches[1]
        Assert-DesktopInspectionGuid $id;if($allUUIDs.ContainsKey($id)){throw 'XML_MEDIA_UUID_DUPLICATE'};$allUUIDs[$id]=$true
        if($id-ceq $OpticalBinding.UUID){Assert-DesktopInspectionPath $dvd.GetAttribute('location') $OpticalBinding.Path;$opticalMatches++}
    }
    if($opticalMatches-ne 1){throw 'XML_OPTICAL_BINDING_NOT_REGISTERED'}
    # Preserve ancestry and state paths without treating historical hardware as current.
    $snapIds=@('5dd088ca-9939-4c13-b285-8eb7b54d8f1c','73cdeb79-50d5-418b-810c-e38840094ea4','afda1952-6c48-4086-9590-897c21323990','dca55e17-086c-46f4-8cd9-aaf98154e2a5','a41350e4-1cd1-438d-bf7a-5110ec4fed47','5f014291-52f1-4b18-83c9-37110083b3a0')
    $snapNames=@('Snapshot 1','AIBS_Installer_77pct_BlackScreen_20261023','AIBS_PreHeadlessRecovery_1','AIBS_Desktop_PreProvision_20261024','AIBS_PreMouseDriver_20261024','AIBS_PostDrivers_20261024')
    $snapStates=@('Snapshots/2026-10-23T22-00-19-669064000Z.sav','Snapshots/2026-10-23T23-11-39-231407000Z.sav','','Snapshots/2026-10-24T17-28-04-378390900Z.sav','Snapshots/2026-10-24T18-27-58-241185400Z.sav','Snapshots/2026-10-24T19-02-47-620416800Z.sav')
    $snapshot=Get-DesktopInspectionXmlOne $machine 'Snapshot'
    for($i=0;$i-lt $snapIds.Count;$i++){
        Assert-DesktopInspectionXmlUuid $snapshot 'uuid' $snapIds[$i];Assert-DesktopInspectionXmlAttribute $snapshot 'name' $snapNames[$i]
        if($snapshot.GetAttribute('stateFile').Replace('\','/')-cne $snapStates[$i]){throw 'XML_PRESERVED_SNAPSHOT_STATE_MISMATCH'}
        Assert-DesktopInspectionXmlNames $snapshot @('Description','Hardware','Snapshots')
        if($i-lt ($snapIds.Count-1)){$children=Get-DesktopInspectionXmlOne $snapshot 'Snapshots';Assert-DesktopInspectionXmlNames $children @('Snapshot');$snapshot=Get-DesktopInspectionXmlOne $children 'Snapshot'}elseif(@($snapshot.ChildNodes|Where-Object {$_.LocalName-ceq 'Snapshots'}).Count){throw 'XML_UNEXPECTED_SNAPSHOT_DESCENDANT'}
    }
    $hardware=Get-DesktopInspectionXmlOne $machine 'Hardware'
    Assert-DesktopInspectionXmlNames $hardware @('Memory','Boot','Display','Firmware','BIOS','TrustedPlatformModule','Network','AudioAdapter','Clipboard','DragAndDrop','GuestProperties','StorageControllers','CPU')
    Assert-DesktopInspectionXmlAttribute (Get-DesktopInspectionXmlOne $hardware 'Memory') 'RAMSize' '8192'
    Assert-DesktopInspectionXmlAttribute (Get-DesktopInspectionXmlOne $hardware 'Firmware') 'type' 'EFI'
    $display=Get-DesktopInspectionXmlOne $hardware 'Display';Assert-DesktopInspectionXmlAttribute $display 'controller' 'VBoxSVGA';Assert-DesktopInspectionXmlAttribute $display 'VRAMSize' '128'
    Assert-DesktopInspectionXmlAttribute $display 'accelerate3D' 'false' $true;Assert-DesktopInspectionXmlAttribute $display 'accelerate2DVideo' 'false' $true;Assert-DesktopInspectionXmlAttribute $display 'monitorCount' '1' $true
    $tpm=Get-DesktopInspectionXmlOne $hardware 'TrustedPlatformModule';Assert-DesktopInspectionXmlAttribute $tpm 'type' 'v2_0';Assert-DesktopInspectionXmlAttribute $tpm 'location' '' $true
    $bios=Get-DesktopInspectionXmlOne $hardware 'BIOS';Assert-DesktopInspectionXmlNames $bios @('IOAPIC','SmbiosUuidLittleEndian','AutoSerialNumGen','NVRAM');Assert-DesktopInspectionXmlAttribute (Get-DesktopInspectionXmlOne $bios 'IOAPIC') 'enabled' 'true'
    $boot=Get-DesktopInspectionXmlOne $hardware 'Boot';Assert-DesktopInspectionXmlNames $boot @('Order');$orders=@($boot.ChildNodes|Where-Object {$_.NodeType-eq [Xml.XmlNodeType]::Element});if($orders.Count-ne 4){throw 'XML_BOOT_ORDER_COUNT'}
    $devices=@('DVD','HardDisk','None','None');for($i=0;$i-lt 4;$i++){Assert-DesktopInspectionXmlAttribute $orders[$i] 'position' ([string]($i+1));Assert-DesktopInspectionXmlAttribute $orders[$i] 'device' $devices[$i]}
    $network=Get-DesktopInspectionXmlOne $hardware 'Network';Assert-DesktopInspectionXmlNames $network @('Adapter');$adapters=@($network.ChildNodes|Where-Object {$_.NodeType-eq [Xml.XmlNodeType]::Element});if($adapters.Count-ne 1){throw 'XML_NETWORK_PROFILE_MISMATCH'}
    $adapter=$adapters[0];Assert-DesktopInspectionXmlAttribute $adapter 'slot' '0';Assert-DesktopInspectionXmlAttribute $adapter 'type' '82540EM';Assert-DesktopInspectionXmlAttribute $adapter 'enabled' 'false' $true
    Assert-DesktopInspectionXmlNames $adapter @('NAT');$nat=Get-DesktopInspectionXmlOne $adapter 'NAT';Assert-DesktopInspectionXmlAttribute $nat 'localhost-reachable' 'true'
    # NAT is a dormant saved attachment under a disabled adapter, not network admission.
    $audio=Get-DesktopInspectionXmlOne $hardware 'AudioAdapter';foreach($attribute in @('enabled','enabledIn','enabledOut')){Assert-DesktopInspectionXmlAttribute $audio $attribute 'false' $true}
    $clipboard=Get-DesktopInspectionXmlOne $hardware 'Clipboard';Assert-DesktopInspectionXmlAttribute $clipboard 'mode' 'Disabled' $true;Assert-DesktopInspectionXmlAttribute $clipboard 'fileTransfersEnabled' 'false' $true
    $drag=@($hardware.ChildNodes|Where-Object {$_.LocalName-ceq 'DragAndDrop'});if($drag.Count-gt 1){throw 'XML_DRAGDROP_DUPLICATE'};if($drag.Count-eq 1){Assert-DesktopInspectionXmlAttribute $drag[0] 'mode' 'Disabled'}
    $cpu=Get-DesktopInspectionXmlOne $hardware 'CPU';Assert-DesktopInspectionXmlAttribute $cpu 'count' '4';Assert-DesktopInspectionXmlAttribute $cpu 'hotplug' 'false' $true;Assert-DesktopInspectionXmlNames $cpu @('HardwareVirtExLargePages','PAE','LongMode')
    Assert-DesktopInspectionXmlAttribute (Get-DesktopInspectionXmlOne $cpu 'HardwareVirtExLargePages') 'enabled' 'true';Assert-DesktopInspectionXmlAttribute (Get-DesktopInspectionXmlOne $cpu 'PAE') 'enabled' 'false';Assert-DesktopInspectionXmlAttribute (Get-DesktopInspectionXmlOne $cpu 'LongMode') 'enabled' 'true'
    $controllers=Get-DesktopInspectionXmlOne $hardware 'StorageControllers';Assert-DesktopInspectionXmlNames $controllers @('StorageController');$controller=Get-DesktopInspectionXmlOne $controllers 'StorageController'
    foreach($pair in @(@('name','SATA'),@('type','AHCI'),@('PortCount','2'),@('useHostIOCache','false'),@('Bootable','true'))){Assert-DesktopInspectionXmlAttribute $controller $pair[0] $pair[1]}
    Assert-DesktopInspectionXmlNames $controller @('AttachedDevice');$attached=@($controller.ChildNodes|Where-Object {$_.NodeType-eq [Xml.XmlNodeType]::Element});if($attached.Count-ne 2){throw 'XML_ATTACHMENT_COUNT'}
    for($i=0;$i-lt 2;$i++){$device=$attached[$i];Assert-DesktopInspectionXmlAttribute $device 'port' ([string]$i);Assert-DesktopInspectionXmlAttribute $device 'device' '0';Assert-DesktopInspectionXmlAttribute $device 'type' (@('HardDisk','DVD')[$i]);Assert-DesktopInspectionXmlAttribute $device 'hotpluggable' 'false';Assert-DesktopInspectionXmlNames $device @('Image');$image=Get-DesktopInspectionXmlOne $device 'Image';$id=if($i-eq 0){$chain[6]}else{$OpticalBinding.UUID};Assert-DesktopInspectionXmlUuid $image 'uuid' $id;if($i-eq 1){Assert-DesktopInspectionXmlAttribute $device 'passthrough' 'false'}}
    return New-DesktopInspectionProfileResult $Values.VMState $OpticalBinding
}
