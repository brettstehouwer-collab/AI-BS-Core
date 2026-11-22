# Standard-account fixed READ-ONLY inspector. Never starts, restores or stops a VM.
[CmdletBinding()]param([switch]$Execute,[string]$SealID,[ValidateSet('preflight','protected','final')][string]$Phase,[string]$ExpectedModuleSHA256,[string]$ExpectedGrantSHA256,[string]$ExpectedSealPolicySHA256)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
if(-not $Execute){[ordered]@{state='DESCRIBE_ONLY';purpose='readonly_image_seal_inspection_v1';vm_uuid='e5a2fe34-7b90-460c-83af-903d51b4bb16';operations=@('showvminfo','showmediuminfo','native_access_open');vm_started=$false;candidate_execution=$false;profile_published=$false}|ConvertTo-Json -Compress;return}
if($PSVersionTable.PSVersion.Major -lt 7 -or $PSScriptRoot -cne (Join-Path $root 'deployment\host')){throw 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'}
foreach($pin in @($ExpectedModuleSHA256,$ExpectedGrantSHA256,$ExpectedSealPolicySHA256)){if($pin -cnotmatch '^[0-9a-f]{64}$'){throw 'EXACT_SEAL_PINS_REQUIRED'}}
$modulePath=Join-Path $PSScriptRoot 'DisposableProbe.psm1';$policyPath=Join-Path $PSScriptRoot 'SealPolicy.ps1'
$moduleStream=[IO.File]::Open($modulePath,'Open','Read','Read');$policyStream=$null
try{
 if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($moduleStream)).ToLowerInvariant() -cne $ExpectedModuleSHA256){throw 'PINNED_HOST_MODULE_CHANGED'}
 $policyStream=[IO.File]::Open($policyPath,'Open','Read','Read');if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($policyStream)).ToLowerInvariant() -cne $ExpectedSealPolicySHA256){throw 'PINNED_SEAL_POLICY_CHANGED'}
 Import-Module $modulePath -Force
 & (Get-Module DisposableProbe) {
  param($SealID,$Phase,$ModulePin,$GrantPin,$PolicyPin,$EntryPath,$PolicyPath)
  try{
   Assert-Principal $script:DispatcherSID -Standard
   $null=Assert-Path $PolicyPath;$null=Read-Bytes $PolicyPath 32768 $PolicyPin;. $PolicyPath
   Require (Is-ID $SealID) 'CANONICAL_SEAL_ID_REQUIRED'
   $grantPath=Fixed-Path ('policy\seal-'+$SealID+'-'+$Phase+'.json');$null=Assert-Path $grantPath
   $grant=Read-StrictJSON (Read-Bytes $grantPath 16384 $GrantPin);Assert-SealGrant $grant $SealID $Phase (Now-UTC)
   Require ($grant.module_sha256 -ceq $ModulePin -and $grant.seal_policy_sha256 -ceq $PolicyPin) 'SEAL_SOURCE_SCOPE'
   $null=Assert-Path $EntryPath;$null=Read-Bytes $EntryPath 32768 $grant.inspector_sha256
   $vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe';$null=Assert-Path $vbox $script:TrustedWriters -External;$null=Read-Bytes $vbox 67108864 $grant.vbox_sha256
   Assert-ClaimPolicy @{dispatcher_sid=$script:DispatcherSID}
   New-JSON (Fixed-Path ('worker_claims\seal-'+$SealID+'-'+$Phase+'.claim')) @{purpose=$grant.purpose;seal_id=$SealID;phase=$Phase;grant_sha256=$GrantPin;utc=(Now-UTC).ToString('o')}
   $operations=[Collections.Generic.List[object]]::new()
   function Inspect-Only([string[]]$Arguments){
    Require ((Now-UTC) -lt (UTC $grant.expires_at)) 'SEAL_INSPECTION_EXPIRED'
    $r=Invoke-BoundedProcess $vbox $Arguments (Fixed-Path 'vbox_home') (Fixed-Path 'deployment') 30 131072
    Successful-Operation $r;$operations.Add(@{arguments_sha256=(Hash-Text (JSON $Arguments));result=$r});return $r.stdout
   }
   $profile=New-SealProfile $grant.guest_sid $grant.accepted_snapshot_uuid ('0'*64) $grant.vbox_sha256
   $info=Parse-VMInfo (Inspect-Only @('showvminfo',$script:WorkerUUID,'--machinereadable'));Assert-VMInfo $info $profile 'poweroff'
   $chain=@();$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);$current=$info['SATA-ImageUUID-0-0'];$ended=$false
   foreach($depth in 0..7){
    Require ((Is-ID $current) -and $seen.Add($current)) 'SEAL_DISK_CYCLE'
    $medium=Parse-MediumInfo (Inspect-Only @('showmediuminfo','disk',$current));Assert-Fields $medium @('UUID','ParentUUID','Location','StorageFormat','Capacity') 'SEAL_MEDIUM_SCHEMA';Assert-StorageLocation $medium.Location;$chain+=,$medium
    Require ($medium.UUID -ceq $current -and $medium.StorageFormat -ceq 'VDI' -and $medium.Capacity -ceq '65536') 'SEAL_DISK_IDENTITY'
    if($current -ceq $profile.system_disk_uuid){$ended=$true;break};$current=$medium.ParentUUID
   }
   Require $ended 'SEAL_DISK_CHAIN_TOO_DEEP'
   $checks=@()
   if($Phase -cne 'preflight'){
    if(-not ('AIBSSealAccess' -as [type])){Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;using Microsoft.Win32.SafeHandles;
public static class AIBSSealAccess{
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint d,uint f,IntPtr t);
 public static int OpenError(string p,uint a){using(var h=CreateFile(p,a,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero)){return h.IsInvalid?Marshal.GetLastWin32Error():0;}}
}
'@}
    foreach($right in @(@('write_data',2),@('append_data',4),@('delete',65536),@('write_dac',262144),@('write_owner',524288),@('read',2147483648L))){$checks+=,@{path=$profile.image_base_path;operation=$right[0];win32_error=[AIBSSealAccess]::OpenError($profile.image_base_path,[uint32]$right[1])}}
    foreach($path in @($script:StorageRoot,'E:\')){foreach($right in @(@('delete_child',64),@('write_dac',262144),@('write_owner',524288))){$checks+=,@{path=$path;operation=$right[0];win32_error=[AIBSSealAccess]::OpenError($path,[uint32]$right[1])}}}
    $checks+=,@{path=$script:StorageRoot;operation='delete';win32_error=[AIBSSealAccess]::OpenError($script:StorageRoot,65536)}
   }
   $observation=[ordered]@{schema_version=1;purpose=$grant.purpose;state='OBSERVED_OFF';seal_id=$SealID;phase=$Phase;challenge=$grant.challenge;vm_uuid=$script:WorkerUUID;accepted_snapshot_uuid=$grant.accepted_snapshot_uuid;dispatcher_sid=$script:DispatcherSID;integrity_sid=[AIBSProbeHost.Native]::IntegritySID();vm_info=$info;config_sha256=(Hash-Text (JSON $info));chain=$chain;chain_sha256=(Hash-Text (JSON $chain));operations=@($operations.ToArray());access_checks=$checks;observed_utc=(Now-UTC).ToString('o');candidate_execution=$false;vm_started=$false}
   $observation=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes((JSON $observation))) 131072;Assert-SealObservation $observation $grant
   JSON $observation
  }finally{Close-Held}
 } $SealID $Phase $ExpectedModuleSHA256 $ExpectedGrantSHA256 $ExpectedSealPolicySHA256 $PSCommandPath $policyPath
}finally{if($policyStream){$policyStream.Dispose()};$moduleStream.Dispose()}
