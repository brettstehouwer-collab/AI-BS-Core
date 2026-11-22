# Controller-only fixed grant and limited-account launch. Describe-only by default.
[CmdletBinding()]param(
 [switch]$Execute,
 [string]$ExpectedModuleSHA256,
 [string]$ExpectedEntrySHA256,
 [string]$ExpectedReadbackSHA256,
 [string]$ExpectedVBoxSHA256,
 [string]$ExpectedPowerShellSHA256
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
if(-not $Execute){[ordered]@{state='DESCRIBE_ONLY';purpose='bootstrap_readback_snapshot_v1';vm_uuid='e5a2fe34-7b90-460c-83af-903d51b4bb16';creates_one_use_grant=$true;launches_only_standard_dispatcher=$true;candidate_execution=$false;profile_published=$false}|ConvertTo-Json -Compress;return}
if($PSVersionTable.PSVersion.Major -lt 7 -or $PSScriptRoot -cne (Join-Path $root 'deployment\host')){throw 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'}
foreach($pin in @($ExpectedModuleSHA256,$ExpectedEntrySHA256,$ExpectedReadbackSHA256,$ExpectedVBoxSHA256,$ExpectedPowerShellSHA256)){if($pin -cnotmatch '^[0-9a-f]{64}$'){throw 'EXACT_SOURCE_AND_RUNTIME_PINS_REQUIRED'}}
$modulePath=Join-Path $PSScriptRoot 'DisposableProbe.psm1'
$moduleStream=[IO.File]::Open($modulePath,'Open','Read','Read')
try{
 if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($moduleStream)).ToLowerInvariant() -cne $ExpectedModuleSHA256){throw 'PINNED_HOST_MODULE_CHANGED'}
 Import-Module $modulePath -Force
 & (Get-Module DisposableProbe) {
  param($ModulePin,$EntryPin,$ReadbackPin,$VBoxPin,$PowerShellPin,$BrokerEntry)
  $credential=$null;$lease=$null
  try{
   Assert-Principal $script:ControllerSID
   foreach($relative in @('state','policy','deployment\host','private')){$null=Assert-Path (Fixed-Path $relative)}
   $null=Assert-Path $BrokerEntry;$null=Read-Bytes $BrokerEntry 32768
   $entry=Fixed-Path 'deployment\host\Readback-And-SnapshotWorker.ps1';$module=Fixed-Path 'deployment\host\DisposableProbe.psm1';$readback=Fixed-Path 'deployment\host\Guest-BootstrapReadback.ps1';$pwsh=Fixed-Path 'deployment\pwsh\pwsh.exe';$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
   foreach($pin in @(@($entry,$EntryPin,65536),@($module,$ModulePin,131072),@($readback,$ReadbackPin,10240),@($pwsh,$PowerShellPin,16777216))){$null=Assert-Path $pin[0];$null=Read-Bytes $pin[0] $pin[2] $pin[1]}
   $null=Assert-Path $vbox $script:TrustedWriters -External;$null=Read-Bytes $vbox 67108864 $VBoxPin
   $secret=Fixed-Path 'private\host_credential.dpapi';$null=Assert-Path $secret;Assert-PrivateReaders $secret
   $credential=ConvertTo-SecureString -String ([Text.UTF8Encoding]::new($false,$true).GetString((Read-Bytes $secret 16384)).Trim())
   Require ($credential.Length -ge 24) 'DISPATCHER_CREDENTIAL_REQUIRED'
   $lease=[IO.File]::Open((Fixed-Path 'state\dispatch.lease'),'OpenOrCreate','ReadWrite','None')
   $grantPath=Fixed-Path 'policy\bootstrap-grant.json';Require (-not [IO.File]::Exists($grantPath)) 'EXISTING_BOOTSTRAP_GRANT_REQUIRES_REVIEW'
   $attempt=[Guid]::NewGuid().ToString('D');$now=Now-UTC
   $grant=[ordered]@{schema_version=1;state='AUTHORIZED_FIXED_BOOTSTRAP_ONLY';purpose='bootstrap_readback_snapshot_v1';attempt_id=$attempt;challenge=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant();issued_at=$now.ToString('o');expires_at=$now.AddMinutes(10).ToString('o');vm_uuid=$script:WorkerUUID;dispatcher_sid=$script:DispatcherSID;vbox_sha256=$VBoxPin;host_entry_sha256=$EntryPin;host_module_sha256=$ModulePin;guest_readback_sha256=$ReadbackPin;guest_probe_sha256='82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531';accepted_snapshot_name='AIBS_ACCEPTED_DIAGNOSTIC_V1'}
   New-JSON (Fixed-Path ('state\bootstrap-'+$attempt+'.bootstrap_reserved.json')) @{purpose=$grant.purpose;attempt_id=$attempt;grant=$grant;status='RESERVED_NO_AUTOMATIC_REPLAY'}
   New-JSON $grantPath $grant
   $grantPin=Hash-Text (JSON $grant)
   New-JSON (Fixed-Path ('state\bootstrap-'+$attempt+'.dispatch_intent.json')) @{purpose=$grant.purpose;attempt_id=$attempt;grant_sha256=$grantPin;dispatcher_sid=$script:DispatcherSID;entry_sha256=$EntryPin;pwsh_sha256=$PowerShellPin;utc=$now.ToString('o')}
   $arguments=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$entry,'-Execute','-ExpectedModuleSHA256',$ModulePin,'-ExpectedGrantSHA256',$grantPin)
   $launch=Invoke-BoundedProcess $pwsh $arguments (Fixed-Path 'vbox_home') (Fixed-Path 'deployment') 1200 131072 0 $credential $script:DispatcherSID
   New-JSON (Fixed-Path ('state\bootstrap-'+$attempt+'.dispatch_result.json')) $launch
   [ordered]@{purpose=$grant.purpose;attempt_id=$attempt;grant_sha256=$grantPin;dispatch=$launch;result_path=(Fixed-Path ('worker_outputs\bootstrap-'+$attempt+'\result.json'));result_provenance='limited_host_dispatcher_observation';profile_published=$false;candidate_execution_authorized=$false;apply_authorized=$false}
  }finally{if($credential){$credential.Dispose()};if($lease){$lease.Dispose()};Close-Held}
 } $ExpectedModuleSHA256 $ExpectedEntrySHA256 $ExpectedReadbackSHA256 $ExpectedVBoxSHA256 $ExpectedPowerShellSHA256 $PSCommandPath | ConvertTo-Json -Depth 24 -Compress
}finally{$moduleStream.Dispose()}
