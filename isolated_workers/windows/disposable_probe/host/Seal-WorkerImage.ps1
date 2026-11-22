# Controller-only image sealing. Describe-only default; no VM start/stop/restore.
[CmdletBinding()]param(
 [switch]$Execute,[string]$BootstrapAttemptID,[string]$ExpectedBootstrapGrantSHA256,
 [string]$ExpectedModuleSHA256,[string]$ExpectedInspectorSHA256,[string]$ExpectedSealPolicySHA256,
 [string]$ExpectedWorkerEntrySHA256,[string]$ExpectedVBoxSHA256,[string]$ExpectedPowerShellSHA256
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
if(-not $Execute){[ordered]@{state='DESCRIBE_ONLY';purpose='controller_image_seal_v1';vm_uuid='e5a2fe34-7b90-460c-83af-903d51b4bb16';preserves_original_acls=$true;streams_base_sha256=$true;requires_real_standard_access_observation=$true;creates_profile_only_after_acceptance=$true;starts_vm=$false;candidate_execution=$false}|ConvertTo-Json -Compress;return}
if($PSVersionTable.PSVersion.Major -lt 7 -or $PSScriptRoot -cne (Join-Path $root 'deployment\host')){throw 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'}
foreach($pin in @($ExpectedBootstrapGrantSHA256,$ExpectedModuleSHA256,$ExpectedInspectorSHA256,$ExpectedSealPolicySHA256,$ExpectedWorkerEntrySHA256,$ExpectedVBoxSHA256,$ExpectedPowerShellSHA256)){if($pin -cnotmatch '^[0-9a-f]{64}$'){throw 'EXACT_SEAL_PINS_REQUIRED'}}
$modulePath=Join-Path $PSScriptRoot 'DisposableProbe.psm1';$policyPath=Join-Path $PSScriptRoot 'SealPolicy.ps1'
$moduleStream=[IO.File]::Open($modulePath,'Open','Read','Read');$policyStream=$null
try{
 if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($moduleStream)).ToLowerInvariant() -cne $ExpectedModuleSHA256){throw 'PINNED_HOST_MODULE_CHANGED'}
 $policyStream=[IO.File]::Open($policyPath,'Open','Read','Read');if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($policyStream)).ToLowerInvariant() -cne $ExpectedSealPolicySHA256){throw 'PINNED_SEAL_POLICY_CHANGED'}
 Import-Module $modulePath -Force
 & (Get-Module DisposableProbe) {
  param($BootstrapAttempt,$BootstrapGrantPin,$ModulePin,$InspectorPin,$PolicyPin,$WorkerPin,$VBoxPin,$PowerShellPin,$EntryPath,$PolicyPath)
  $leases=[Collections.Generic.List[IDisposable]]::new();$credential=$null;$baseHandle=$null;$key=$null;$evidence=$null;$published=$false
  try{
   Assert-Principal $script:ControllerSID
   Require (Is-ID $BootstrapAttempt) 'CANONICAL_BOOTSTRAP_ATTEMPT_REQUIRED'
   foreach($relative in @('state','policy','private','deployment\host')){$null=Assert-Path (Fixed-Path $relative)}
   $null=Assert-Path $EntryPath;$null=Read-Bytes $EntryPath 65536
   $null=Assert-Path $PolicyPath;$null=Read-Bytes $PolicyPath 32768 $PolicyPin;. $PolicyPath
   $inspector=Fixed-Path 'deployment\host\Inspect-SealedWorker.ps1';$pwsh=Fixed-Path 'deployment\pwsh\pwsh.exe';$vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'
   foreach($pin in @(@($inspector,$InspectorPin,32768),@((Fixed-Path 'deployment\host\Invoke-WorkerTransport.ps1'),$WorkerPin,32768),@($pwsh,$PowerShellPin,16777216))){$null=Assert-Path $pin[0];$null=Read-Bytes $pin[0] $pin[2] $pin[1]}
   $null=Assert-Path $vbox $script:TrustedWriters -External;$null=Read-Bytes $vbox 67108864 $VBoxPin
   foreach($relative in @('state\controller.lease','state\dispatch.lease','worker_state\provision.lease','worker_state\vm.lease')){$leases.Add([IO.File]::Open((Fixed-Path $relative),'OpenOrCreate','ReadWrite','None'))}
   Require (-not [IO.File]::Exists((Fixed-Path 'policy\profile.json'))) 'EXISTING_SEAL_PROFILE_REQUIRES_REVIEW'
   $transportPath=Fixed-Path 'policy\transport.json';$transportAlreadyPresent=[IO.File]::Exists($transportPath)
   if($transportAlreadyPresent){$null=Assert-Path $transportPath;$transportBytes=Read-Bytes $transportPath 8192;$existingTransport=Read-StrictJSON $transportBytes;Assert-SealTransport $existingTransport $ModulePin $WorkerPin $PowerShellPin;$transportPin=Hash-Bytes $transportBytes}
   $seal=[Guid]::NewGuid().ToString('D');$evidence=Fixed-Path ('state\seal-'+$seal);$null=[IO.Directory]::CreateDirectory($evidence);$null=Assert-Path $evidence
   New-JSON (Join-Path $evidence 'intent.json') @{purpose='controller_image_seal_v1';seal_id=$seal;bootstrap_attempt_id=$BootstrapAttempt;utc=(Now-UTC).ToString('o');automatic_replay=$false}
   $bootstrapGrantPath=Fixed-Path 'policy\bootstrap-grant.json';$null=Assert-Path $bootstrapGrantPath
   $grant=Read-StrictJSON (Read-Bytes $bootstrapGrantPath 32768 $BootstrapGrantPin)
   Require ($grant.attempt_id -ceq $BootstrapAttempt -and $grant.vm_uuid -ceq $script:WorkerUUID -and $grant.dispatcher_sid -ceq $script:DispatcherSID -and $grant.host_module_sha256 -ceq $ModulePin -and $grant.vbox_sha256 -ceq $VBoxPin -and $grant.purpose -ceq 'bootstrap_readback_snapshot_v1' -and $grant.accepted_snapshot_name -ceq 'AIBS_ACCEPTED_DIAGNOSTIC_V1') 'BOOTSTRAP_GRANT_SEAL_SCOPE'
   foreach($field in @('challenge','host_entry_sha256','guest_readback_sha256','guest_probe_sha256')){Require (Is-Digest $grant[$field]) 'BOOTSTRAP_SOURCE_PIN_REQUIRED'}
   foreach($pin in @(@((Fixed-Path 'deployment\host\Readback-And-SnapshotWorker.ps1'),$grant.host_entry_sha256,65536),@((Fixed-Path 'deployment\host\Guest-BootstrapReadback.ps1'),$grant.guest_readback_sha256,10240))){$null=Assert-Path $pin[0];$null=Read-Bytes $pin[0] $pin[2] $pin[1]}
   $reservationPath=Fixed-Path ('state\bootstrap-'+$BootstrapAttempt+'.bootstrap_reserved.json');$null=Assert-Path $reservationPath;$reserved=Read-StrictJSON (Read-Bytes $reservationPath 65536)
   Require ($reserved.attempt_id -ceq $BootstrapAttempt -and (Hash-Text (JSON $reserved.grant)) -ceq $BootstrapGrantPin) 'BOOTSTRAP_RESERVATION_BINDING'
   $intentPath=Fixed-Path ('state\bootstrap-'+$BootstrapAttempt+'.dispatch_intent.json');$null=Assert-Path $intentPath;$intent=Read-StrictJSON (Read-Bytes $intentPath 16384)
   Require ($intent.attempt_id -ceq $BootstrapAttempt -and $intent.grant_sha256 -ceq $BootstrapGrantPin -and $intent.dispatcher_sid -ceq $script:DispatcherSID -and $intent.entry_sha256 -ceq $grant.host_entry_sha256 -and $intent.pwsh_sha256 -ceq $PowerShellPin) 'BOOTSTRAP_DISPATCH_INTENT_BINDING'
   $launchPath=Fixed-Path ('state\bootstrap-'+$BootstrapAttempt+'.dispatch_result.json');$null=Assert-Path $launchPath;$launch=Read-StrictJSON (Read-Bytes $launchPath 262144)
   Successful-Operation $launch;Require ($launch.owner_sid -ceq $script:DispatcherSID -and (UTC $launch.started_utc) -ge (UTC $grant.issued_at) -and (UTC $launch.started_utc) -lt (UTC $grant.expires_at)) 'BOOTSTRAP_ACTUAL_LAUNCH_REQUIRED'
   $bootstrap=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes($launch.stdout)) 131072
   Require ($bootstrap.state -ceq 'SNAPSHOT_PROPOSED_AWAITING_CONTROLLER_SEAL' -and $bootstrap.purpose -ceq $grant.purpose -and $bootstrap.vm_uuid -ceq $script:WorkerUUID -and $bootstrap.error_code -ceq '' -and (UTC $bootstrap.completed_utc) -lt (UTC $grant.expires_at)) 'BOOTSTRAP_ACCEPTED_RESULT_REQUIRED'
   $observed=$bootstrap.worker_observed;$guest=$bootstrap.guest_reported
   Require ($observed.grant_sha256 -ceq $BootstrapGrantPin -and $observed.dispatcher_sid -ceq $script:DispatcherSID -and $observed.terminal_state -ceq 'poweroff' -and (Is-ID $observed.accepted_snapshot_uuid) -and (Is-ID $observed.current_disk_uuid) -and -not $observed.ContainsKey('forced_off_no_baseline')) 'BOOTSTRAP_CLEAN_OFF_SNAPSHOT_REQUIRED'
   Assert-SealGuestProof $guest $grant
   foreach($field in @('profile_published','worker_admitted','candidate_execution_authorized','apply_authorized','full_containment_accepted')){Require ($bootstrap[$field] -is [bool] -and -not $bootstrap[$field]) 'BOOTSTRAP_FALSE_AUTHORITY_REQUIRED'}
   Require ($observed.readback_report_sha256 -ceq (Hash-Text (JSON $guest))) 'BOOTSTRAP_GUEST_REPORT_DIGEST'
   New-JSON (Join-Path $evidence 'retained_bootstrap.json') @{grant=$grant;reservation=$reserved;dispatch_intent=$intent;controller_launch=$launch;bootstrap_result=$bootstrap;source_files=@{module=$ModulePin;inspector=$InspectorPin;seal_policy=$PolicyPin;worker_entry=$WorkerPin;pwsh=$PowerShellPin;vbox=$VBoxPin}}
   $secret=Fixed-Path 'private\host_credential.dpapi';$null=Assert-Path $secret;Assert-PrivateReaders $secret;$credential=ConvertTo-SecureString -String ([Text.UTF8Encoding]::new($false,$true).GetString((Read-Bytes $secret 16384)).Trim());Require ($credential.Length -ge 24) 'DISPATCHER_CREDENTIAL_REQUIRED'
   function Seal-Inspect([string]$Phase){
    $now=Now-UTC;$g=[ordered]@{schema_version=1;purpose='readonly_image_seal_inspection_v1';seal_id=$seal;phase=$Phase;challenge=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant();issued_at=$now.ToString('o');expires_at=$now.AddMinutes(5).ToString('o');vm_uuid=$script:WorkerUUID;accepted_snapshot_uuid=$observed.accepted_snapshot_uuid;guest_sid=$guest.guest_sid;dispatcher_sid=$script:DispatcherSID;module_sha256=$ModulePin;inspector_sha256=$InspectorPin;seal_policy_sha256=$PolicyPin;vbox_sha256=$VBoxPin}
    $g=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes((JSON $g)));Assert-SealGrant $g $seal $Phase $now
    $path=Fixed-Path ('policy\seal-'+$seal+'-'+$Phase+'.json');New-JSON $path $g;$gpin=Hash-Text (JSON $g)
    New-JSON (Join-Path $evidence ($Phase+'_intent.json')) @{grant=$g;grant_sha256=$gpin;inspector_sha256=$InspectorPin;utc=$now.ToString('o')}
    $args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',$inspector,'-Execute','-SealID',$seal,'-Phase',$Phase,'-ExpectedModuleSHA256',$ModulePin,'-ExpectedGrantSHA256',$gpin,'-ExpectedSealPolicySHA256',$PolicyPin)
    $dispatch=Invoke-BoundedProcess $pwsh $args (Fixed-Path 'vbox_home') (Fixed-Path 'deployment') 300 131072 0 $credential $script:DispatcherSID
    New-JSON (Join-Path $evidence ($Phase+'_dispatch.json')) $dispatch;Successful-Operation $dispatch;Require ($dispatch.owner_sid -ceq $script:DispatcherSID) 'SEAL_INSPECTOR_OWNER_REQUIRED'
    $r=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes($dispatch.stdout)) 131072;Assert-SealObservation $r $g;New-JSON (Join-Path $evidence ($Phase+'_accepted.json')) $r;return ,$r
   }
   $before=Seal-Inspect preflight
   Require ($before.config_sha256 -ceq $observed.terminal_config_sha256 -and $before.vm_info['SATA-ImageUUID-0-0'] -ceq $observed.current_disk_uuid) 'SNAPSHOT_CHANGED_AFTER_BOOTSTRAP'
   $base=$script:StorageRoot+'\system.vdi';Assert-StorageLocation $base
   foreach($path in @($script:StorageRoot,$base)){
    $item=Get-Item -LiteralPath $path -Force;Require (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) 'SEAL_ACL_REPARSE_REFUSED'
    $acl=Get-Acl -LiteralPath $path;$sddl=$acl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Owner -bor [Security.AccessControl.AccessControlSections]::Group -bor [Security.AccessControl.AccessControlSections]::Access)
    New-JSON (Join-Path $evidence ($(if($path -ceq $base){'base'}else{'store'})+'_original_acl.json')) @{path=$path;sddl=$sddl;sddl_sha256=(Hash-Text $sddl);utc=(Now-UTC).ToString('o')}
   }
   # Protect immutable base first, then its parent replacement rights. No image bytes move.
   Set-Acl -LiteralPath $base -AclObject (New-SealedBaseACL)
   Set-Acl -LiteralPath $script:StorageRoot -AclObject (New-SealedStoreACL)
   $null=Assert-Path $base $script:TrustedWriters -External
   foreach($path in @($script:StorageRoot,$base)){$acl=Get-Acl -LiteralPath $path;$sddl=$acl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::Owner -bor [Security.AccessControl.AccessControlSections]::Group -bor [Security.AccessControl.AccessControlSections]::Access);New-JSON (Join-Path $evidence ($(if($path -ceq $base){'base'}else{'store'})+'_sealed_acl.json')) @{path=$path;sddl=$sddl;sddl_sha256=(Hash-Text $sddl)}}
   $protected=Seal-Inspect protected
   Require ($protected.config_sha256 -ceq $before.config_sha256 -and $protected.chain_sha256 -ceq $before.chain_sha256) 'VM_CHANGED_DURING_ACL_SEAL'
   $baseHandle=[IO.File]::Open($base,'Open','Read','Read');Require ([AIBSProbeHost.Native]::Links($baseHandle.SafeFileHandle) -eq 1 -and $baseHandle.Length -ge 68719476736L -and $baseHandle.Length -le 68723671040L) 'FIXED_BASE_LENGTH_OR_LINKS'
   $baseLength=$baseHandle.Length;$hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($baseHandle)).ToLowerInvariant()
   New-JSON (Join-Path $evidence 'streamed_image.json') @{path=$base;length=$baseLength;sha256=$hash;file_share='Read';hard_links=1;hash_mode='streamed_sha256';utc=(Now-UTC).ToString('o')}
   $final=Seal-Inspect final
   Require ($final.config_sha256 -ceq $before.config_sha256 -and $final.chain_sha256 -ceq $before.chain_sha256 -and $baseHandle.Length -eq $baseLength) 'VM_CHANGED_DURING_IMAGE_HASH'
   $null=Assert-Path $base $script:TrustedWriters -External
   $keyPath=Fixed-Path 'private\receipt.key'
   if(-not [IO.File]::Exists($keyPath)){New-File $keyPath ([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))}
   $key=Read-ReceiptKey
   $profile=New-SealProfile $guest.guest_sid $observed.accepted_snapshot_uuid $hash $VBoxPin
   $transport=[ordered]@{schema_version=1;module_sha256=$ModulePin;entry_sha256=$WorkerPin;pwsh_sha256=$PowerShellPin}
   if(-not $transportAlreadyPresent){$transportPin=Hash-Text (JSON $transport)}
   New-JSON (Join-Path $evidence 'transport_policy.json') @{sha256=$transportPin;preexisting_bytes_preserved=$transportAlreadyPresent;parsed=$transport}
   $evidenceFiles=@(Get-ChildItem -LiteralPath $evidence -File|Sort-Object Name|ForEach-Object{@{name=$_.Name;length=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}})
   $body=[ordered]@{domain='AI-BS/controller-image-seal/v1';seal_id=$seal;vm_uuid=$script:WorkerUUID;bootstrap_attempt_id=$BootstrapAttempt;bootstrap_grant_sha256=$BootstrapGrantPin;profile_sha256=(Hash-Text (JSON $profile));transport_sha256=$transportPin;base_sha256=$hash;base_length=$baseLength;accepted_snapshot_uuid=$observed.accepted_snapshot_uuid;source_pins=@{module=$ModulePin;inspector=$InspectorPin;seal_policy=$PolicyPin;worker_entry=$WorkerPin;pwsh=$PowerShellPin;vbox=$VBoxPin};evidence=$evidenceFiles;guest_identity_provenance='guest_reported_under_bound_standard_dispatch';image_identity_provenance='controller_streamed_base_and_standard_dispatcher_off_metadata';general_worker_admission=$false;candidate_execution_authorized=$false;apply_authorized=$false;full_phase4_accepted=$false;sealed_utc=(Now-UTC).ToString('o')}
   New-JSON (Join-Path $evidence 'controller_seal_receipt.json') @{body=$body;hmac_sha256=(Receipt-Tag $body $key)}
   # transport first leaves isolation unavailable if interruption precedes profile.
   if(-not $transportAlreadyPresent){New-JSON $transportPath $transport}
   New-JSON (Fixed-Path 'policy\profile.json') $profile;$published=$true
   $profilePin=Hash-Text (JSON $profile);$null=Read-Profile (Fixed-Path 'policy\profile.json') $profilePin
   New-JSON (Join-Path $evidence 'publication.json') @{state='PROVISIONED_FIXED_DIAGNOSTICS_ONLY';profile_sha256=$profilePin;transport_sha256=$transportPin;seal_id=$seal;utc=(Now-UTC).ToString('o');diagnostic_executed=$false}
   [ordered]@{state='PROVISIONED_FIXED_DIAGNOSTICS_ONLY';seal_id=$seal;profile_sha256=$profilePin;transport_sha256=$transportPin;image_base_sha256=$hash;accepted_snapshot_uuid=$observed.accepted_snapshot_uuid;evidence_directory=$evidence;diagnostic_executed=$false;candidate_execution_authorized=$false;apply_authorized=$false}
  }catch{
   if($evidence){try{New-JSON (Join-Path $evidence 'failure_retained.json') @{state='BLOCKED_RETAINED';profile_may_have_been_published=$published;error_type=$_.Exception.GetType().Name;error_code=$(if($_.Exception -is [InvalidOperationException]){$_.Exception.Message}else{'SEAL_OPERATION_FAILED'});utc=(Now-UTC).ToString('o');automatic_acl_rollback=$false;automatic_retry=$false}}catch{}}
   throw
  }finally{if($key){[Array]::Clear($key,0,$key.Length)};if($baseHandle){$baseHandle.Dispose()};if($credential){$credential.Dispose()};foreach($lease in $leases){$lease.Dispose()};Close-Held}
 } $BootstrapAttemptID $ExpectedBootstrapGrantSHA256 $ExpectedModuleSHA256 $ExpectedInspectorSHA256 $ExpectedSealPolicySHA256 $ExpectedWorkerEntrySHA256 $ExpectedVBoxSHA256 $ExpectedPowerShellSHA256 $PSCommandPath $policyPath | ConvertTo-Json -Depth 24 -Compress
}finally{if($policyStream){$policyStream.Dispose()};$moduleStream.Dispose()}
