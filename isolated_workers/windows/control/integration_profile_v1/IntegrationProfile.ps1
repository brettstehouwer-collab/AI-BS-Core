# Static observation profile only. Never grants execution, transport or task authority.
# The original offline inspector is unchanged and remains a separate admission boundary.
$offline=Join-Path (Split-Path $PSScriptRoot -Parent) 'desktop_inspection_v2\DesktopProfile.ps1'
if((Get-FileHash -LiteralPath $offline -Algorithm SHA256).Hash-cne 'AB194E76ECEEA4B2C914DE1AC704559DEF1C66A82646983902EE56DFC92C6803'){throw 'OFFLINE_PROFILE_SOURCE_CHANGED'}
. $offline
function Get-IntegrationObservationSpec {
 return [pscustomobject]@{
  Role='NETWORKED_INTEGRATION_OBSERVATION_ONLY';ConfigurationSHA256='73815AA20C9FC45F39E794EDE8FAFA229ADE9CD0458C14DB96975A26399497D5'
  ConfigurationPath='C:\AI-BS\isolated_workers\windows\runtime\base_preparation_v2\vms\AI-BS-Eval-Base-20261023\AI-BS-Eval-Base-20261023.vbox'
  MemoryMiB=16384;CPUs=4;NIC='NAT';GatewayPort=8000;ModelPort=11434
  TaskAuthority=$false;ProviderAccepted=$false;TransportAccepted=$false;ContainmentAccepted=$false
  UnrestrictedLoopbackExposure=$true;RequiresRestrictedTransport=$true
  USBController='OHCI';HostUSBPassthroughVerified=$false
  RequiredAudioEnabled=$false;CurrentConfigurationAccepted=$false
 }
}
function Assert-IntegrationObservationFingerprint([byte[]]$Bytes,[string]$ExpectedSHA256){
 if($null-eq $Bytes-or $Bytes.Length-eq 0-or $Bytes.Length-gt 1048576){throw 'CONFIGURATION_BYTE_BOUND'}
 if($ExpectedSHA256-cnotmatch '^[A-F0-9]{64}$'){throw 'EXACT_CONFIG_PIN_REQUIRED'}
 $algorithm=[Security.Cryptography.SHA256]::Create()
 try{$actual=[BitConverter]::ToString($algorithm.ComputeHash($Bytes)).Replace('-','')}finally{$algorithm.Dispose()}
 if($actual-cne $ExpectedSHA256){throw 'INTEGRATION_CONFIGURATION_DRIFT'}
 return $true
}
function Assert-IntegrationObservationXml([Xml.XmlDocument]$Xml,[hashtable]$Values,[hashtable]$OpticalBinding){
 if($null-eq $Xml-or $null-ne $Xml.DocumentType-or $Xml.OuterXml.Length-gt 1048576){throw 'XML_DOCUMENT_REFUSED'}
 if($null-eq $Values-or $Values.memory-cne '16384'-or $Values.nic1-cne 'nat'-or $Values.usb-cne 'on'){throw 'INTEGRATION_MEMORY_NIC_OR_USB_MISMATCH'}
 foreach($n in 2..8){if($Values["nic$n"]-cne 'none'){throw 'INTEGRATION_ADDITIONAL_NIC_REFUSED'}}
 # Validate reviewed differences explicitly, then delegate unchanged ancestry,
 # storage, peripherals and metadata to the pinned offline validator on a clone.
 # Never write normalized XML to disk or use it for the offline execution role.
 $copy=$Xml.CloneNode($true);$m=Get-DesktopInspectionXmlOne $copy.DocumentElement 'Machine';$h=Get-DesktopInspectionXmlOne $m 'Hardware'
 $memory=Get-DesktopInspectionXmlOne $h 'Memory';Assert-DesktopInspectionXmlAttribute $memory 'RAMSize' '16384'
 $network=Get-DesktopInspectionXmlOne $h 'Network';Assert-DesktopInspectionXmlNames $network @('Adapter')
 $adapter=Get-DesktopInspectionXmlOne $network 'Adapter'
 foreach($attribute in $adapter.Attributes){if($attribute.Name-cnotin @('slot','enabled','MACAddress','type')){throw 'INTEGRATION_ADAPTER_ATTRIBUTE_REFUSED'}}
 Assert-DesktopInspectionXmlAttribute $adapter 'enabled' 'true';Assert-DesktopInspectionXmlAttribute $adapter 'slot' '0';Assert-DesktopInspectionXmlAttribute $adapter 'type' '82540EM'
 Assert-DesktopInspectionXmlNames $adapter @('NAT');$nat=Get-DesktopInspectionXmlOne $adapter 'NAT'
 if($nat.Attributes.Count-ne 1){throw 'INTEGRATION_NAT_ATTRIBUTE_REFUSED'}
 Assert-DesktopInspectionXmlAttribute $nat 'localhost-reachable' 'true';Assert-DesktopInspectionXmlNames $nat @()
 # Observe the operator-enabled OHCI controller without admitting host-device
 # passthrough. Runtime USB attachment evidence remains an explicit open gate.
 $usb=Get-DesktopInspectionXmlOne $h 'USB'
 if($usb.Attributes.Count-ne 0){throw 'INTEGRATION_USB_ATTRIBUTE_REFUSED'}
 Assert-DesktopInspectionXmlNames $usb @('Controllers')
 $controllers=Get-DesktopInspectionXmlOne $usb 'Controllers';Assert-DesktopInspectionXmlNames $controllers @('Controller')
 if($controllers.Attributes.Count-ne 0){throw 'INTEGRATION_USB_ATTRIBUTE_REFUSED'}
 $controller=Get-DesktopInspectionXmlOne $controllers 'Controller'
 if($controller.Attributes.Count-ne 2){throw 'INTEGRATION_USB_ATTRIBUTE_REFUSED'}
 Assert-DesktopInspectionXmlAttribute $controller 'name' 'OHCI';Assert-DesktopInspectionXmlAttribute $controller 'type' 'OHCI';Assert-DesktopInspectionXmlNames $controller @()
 $null=$h.RemoveChild($usb)
 $memory.SetAttribute('RAMSize','8192');$adapter.SetAttribute('enabled','false')
 $baseline=$Values.Clone();$baseline.memory='8192';$baseline.nic1='none';$baseline.usb='off'
 $null=Assert-DesktopInspectionXml $copy $baseline $OpticalBinding
 return Get-IntegrationObservationSpec
}
