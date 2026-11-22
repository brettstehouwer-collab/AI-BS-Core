# Pure trusted-controller validation and ACL construction. No top-level operations.
function Assert-SealTransport($Transport,$ModuleHash,$WorkerHash,$PowerShellHash) {
 Assert-Fields $Transport @('schema_version','module_sha256','entry_sha256','pwsh_sha256') 'SEAL_TRANSPORT_SCHEMA'
 Require ($Transport.schema_version -is [long] -and $Transport.schema_version -eq 1 -and $Transport.module_sha256 -ceq $ModuleHash -and $Transport.entry_sha256 -ceq $WorkerHash -and $Transport.pwsh_sha256 -ceq $PowerShellHash) 'SEAL_TRANSPORT_PIN_MISMATCH'
}
function Assert-SealGuestProof($Guest,$Grant) {
 Require ($Guest.schema_version -is [long] -and $Guest.schema_version -eq 1 -and $Guest.purpose -ceq $Grant.purpose -and $Guest.challenge -ceq $Grant.challenge -and $Guest.vm_id -ceq $script:WorkerUUID -and $Guest.state -ceq 'OBSERVED_PROTECTED' -and $Guest.executable_sha256 -ceq $Grant.guest_probe_sha256 -and $Guest.guest_machine -ceq 'AIBSPROBE01' -and $Guest.guest_username -ceq 'aibs_vm_worker' -and $Guest.integrity_sid -ceq 'S-1-16-8192' -and $Guest.guest_sid -is [string] -and $Guest.guest_sid -cmatch '^S-1-5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+$' -and -not $Guest.guest_sid.StartsWith($script:HostSIDPrefix,[StringComparison]::Ordinal) -and $Guest.failed_access_checks -is [long] -and $Guest.failed_access_checks -eq 0 -and $Guest.access_checks -is [array] -and $Guest.access_checks.Count -ge 60) 'BOOTSTRAP_GUEST_PROOF_REQUIRED'
 Require ($Guest.administrator_group_present -is [bool] -and -not $Guest.administrator_group_present -and $Guest.guest_groups -is [array] -and 'S-1-5-32-544' -cnotin $Guest.guest_groups -and 'S-1-5-114' -cnotin $Guest.guest_groups) 'BOOTSTRAP_STANDARD_GUEST_REQUIRED'
 foreach($check in $Guest.access_checks){Require ($check.denied -is [bool] -and $check.denied -and $check.win32_error -is [long] -and $check.win32_error -eq 5) 'BOOTSTRAP_GUEST_ACCESS_DENIAL_REQUIRED'}
 foreach($field in @('probe_executed','worker_admitted','execution_authorized','apply_authorized')){Require ($Guest[$field] -is [bool] -and -not $Guest[$field]) 'BOOTSTRAP_GUEST_FALSE_AUTHORITY_REQUIRED'}
 foreach($field in @('bootstrap_disabled','autologon_disabled','setup_records_admin_only','secure_boot','tpm_present')){Require ($Guest.bootstrap[$field] -is [bool] -and $Guest.bootstrap[$field]) 'BOOTSTRAP_LOCKDOWN_REPORT_REQUIRED'}
 Require ($Guest.bootstrap.state -ceq 'BOOTSTRAPPED_AWAITING_HOST_VERIFICATION' -and $Guest.bootstrap.guest_sid -ceq $Guest.guest_sid -and $Guest.bootstrap.executable_sha256 -ceq $Grant.guest_probe_sha256 -and ($Guest.bootstrap.additions_signer_thumbprint -in @('2B1BD188256EB612578949A943DE0DDC52D1DF79', '7E92B66BE51B79D8CE3FF25C15C2DF6AB8C7F2F2'))) 'BOOTSTRAP_LOCKDOWN_BINDING_REQUIRED'
}
function Assert-SealGrant($Grant,[string]$SealID,[string]$Phase,[DateTime]$Now) {
 Assert-Fields $Grant @('schema_version','purpose','seal_id','phase','challenge','issued_at','expires_at','vm_uuid','accepted_snapshot_uuid','guest_sid','dispatcher_sid','module_sha256','inspector_sha256','seal_policy_sha256','vbox_sha256') 'SEAL_GRANT_SCHEMA'
 Require ($Grant.schema_version -is [long] -and $Grant.schema_version -eq 1 -and $Grant.purpose -ceq 'readonly_image_seal_inspection_v1' -and (Is-ID $SealID) -and $Grant.seal_id -ceq $SealID -and $Grant.phase -ceq $Phase -and $Phase -cin @('preflight','protected','final')) 'SEAL_GRANT_SCOPE'
 Require ($Grant.vm_uuid -ceq $script:WorkerUUID -and $Grant.vm_uuid -cne $script:IntegrationUUID -and (Is-ID $Grant.accepted_snapshot_uuid) -and $Grant.dispatcher_sid -ceq $script:DispatcherSID) 'SEAL_GRANT_IDENTITY'
 Require ($Grant.guest_sid -cmatch '^S-1-5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+$' -and -not $Grant.guest_sid.StartsWith($script:HostSIDPrefix,[StringComparison]::Ordinal)) 'SEAL_GUEST_IDENTITY'
 foreach($name in @('challenge','module_sha256','inspector_sha256','seal_policy_sha256','vbox_sha256')){Require (Is-Digest $Grant[$name]) 'SEAL_GRANT_PIN'}
 $issued=UTC $Grant.issued_at;$expiry=UTC $Grant.expires_at
 Require ($issued -le $Now -and $Now -lt $expiry -and $expiry -gt $issued -and $expiry-$issued -le [TimeSpan]::FromMinutes(5)) 'SEAL_GRANT_EXPIRED_OR_FUTURE'
}
function New-SealProfile($GuestSID,$SnapshotUUID,$BaseHash,$VBoxHash) {
 $p=[ordered]@{schema_version=1;state='PROVISIONED';vm_uuid=$script:WorkerUUID;image_id=('aibs-fixed-probe-win11-eval-'+$script:WorkerUUID);image_base_path=($script:StorageRoot+'\system.vdi');image_base_sha256=$BaseHash;system_disk_uuid='5b4f5331-0da2-491d-a257-6b4ecf435a5a';accepted_snapshot_uuid=$SnapshotUUID;vbox_path='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe';vbox_sha256=$VBoxHash;vbox_user_home=(Fixed-Path 'vbox_home');guest_executable='C:\AIBSProbe\DiagnosticProbe.exe';guest_executable_sha256='82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531';guest_username='aibs_vm_worker';guest_sid=$GuestSID;dispatcher_sid=$script:DispatcherSID;controller_sid=$script:ControllerSID;vm_memory_mib=4096;vm_cpus=4}
 $parsed=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes((JSON $p)));Assert-ProfileData $parsed;return ,$parsed
}
function Assert-SealObservation($Observation,$Grant) {
 Assert-Fields $Observation @('schema_version','purpose','state','seal_id','phase','challenge','vm_uuid','accepted_snapshot_uuid','dispatcher_sid','integrity_sid','vm_info','config_sha256','chain','chain_sha256','operations','access_checks','observed_utc','candidate_execution','vm_started') 'SEAL_OBSERVATION_SCHEMA'
 Require ($Observation.schema_version -is [long] -and $Observation.schema_version -eq 1 -and $Observation.purpose -ceq $Grant.purpose -and $Observation.state -ceq 'OBSERVED_OFF' -and $Observation.seal_id -ceq $Grant.seal_id -and $Observation.phase -ceq $Grant.phase -and $Observation.challenge -ceq $Grant.challenge -and $Observation.vm_uuid -ceq $script:WorkerUUID -and $Observation.accepted_snapshot_uuid -ceq $Grant.accepted_snapshot_uuid -and $Observation.dispatcher_sid -ceq $script:DispatcherSID -and $Observation.integrity_sid -ceq 'S-1-16-8192') 'SEAL_OBSERVATION_SCOPE'
 Require ($Observation.candidate_execution -is [bool] -and -not $Observation.candidate_execution -and $Observation.vm_started -is [bool] -and -not $Observation.vm_started) 'SEAL_OBSERVATION_AUTHORITY'
 $observed=UTC $Observation.observed_utc
 Require ($observed -ge (UTC $Grant.issued_at) -and $observed -lt (UTC $Grant.expires_at) -and $observed -le (Now-UTC)) 'SEAL_OBSERVATION_STALE'
 $profile=New-SealProfile $Grant.guest_sid $Grant.accepted_snapshot_uuid ('0'*64) $Grant.vbox_sha256
 Assert-VMInfo $Observation.vm_info $profile 'poweroff'
 Require ($Observation.config_sha256 -ceq (Hash-Text (JSON $Observation.vm_info)) -and $Observation.chain_sha256 -ceq (Hash-Text (JSON $Observation.chain))) 'SEAL_OBSERVATION_DIGEST'
 Require ($Observation.chain -is [array] -and $Observation.chain.Count -ge 2 -and $Observation.chain.Count -le 8) 'SEAL_CHAIN_BOUND'
 $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal);$current=$Observation.vm_info['SATA-ImageUUID-0-0']
 for($index=0;$index -lt $Observation.chain.Count;$index++){
  $medium=$Observation.chain[$index]
  Assert-Fields $medium @('UUID','ParentUUID','Location','StorageFormat','Capacity') 'SEAL_MEDIUM_SCHEMA'
  Require ((Is-ID $current) -and $seen.Add($current) -and $medium.UUID -ceq $current -and $medium.StorageFormat -ceq 'VDI' -and $medium.Capacity -ceq '65536') 'SEAL_CHAIN_IDENTITY'
  Assert-StorageLocation $medium.Location
  if($index -eq 0){Require ($medium.Location -ceq $Observation.vm_info['SATA-0-0']) 'SEAL_CURRENT_DISK_PATH'}
  if($index -eq $Observation.chain.Count-1){Require ($current -ceq $profile.system_disk_uuid -and $medium.Location -ceq $profile.image_base_path -and $medium.ParentUUID -cin @('base','00000000-0000-0000-0000-000000000000')) 'SEAL_CHAIN_BASE'}
  else{Require ($current -cne $profile.system_disk_uuid -and (Is-ID $medium.ParentUUID)) 'SEAL_CHAIN_EARLY_BASE'}
  $current=$medium.ParentUUID
 }
 Require ($Observation.operations.Count -eq $Observation.chain.Count+1) 'SEAL_OPERATION_COUNT'
 for($index=0;$index -lt $Observation.operations.Count;$index++){
  $operation=$Observation.operations[$index];Successful-Operation $operation.result
  $arguments=if($index -eq 0){@('showvminfo',$script:WorkerUUID,'--machinereadable')}else{@('showmediuminfo','disk',$Observation.chain[$index-1].UUID)}
  Require ($operation.arguments_sha256 -ceq (Hash-Text (JSON $arguments))) 'SEAL_OPERATION_ARGUMENTS'
  if($index -eq 0){Require ((Hash-Text (JSON (Parse-VMInfo $operation.result.stdout))) -ceq $Observation.config_sha256) 'SEAL_RAW_VM_BINDING'}
  else{Require ((Hash-Text (JSON (Parse-MediumInfo $operation.result.stdout))) -ceq (Hash-Text (JSON $Observation.chain[$index-1]))) 'SEAL_RAW_MEDIUM_BINDING'}
 }
 if($Grant.phase -ceq 'preflight'){Require ($Observation.access_checks.Count -eq 0) 'PREFLIGHT_ACCESS_SCOPE'}
 else{
  $expected=@()
  foreach($operation in @('write_data','append_data','delete','write_dac','write_owner')){$expected+=,@{path=$profile.image_base_path;operation=$operation;win32_error=5}}
  $expected+=,@{path=$profile.image_base_path;operation='read';win32_error=0}
  foreach($path in @($script:StorageRoot,'E:\')){foreach($operation in @('delete_child','write_dac','write_owner')){$expected+=,@{path=$path;operation=$operation;win32_error=5}}}
  $expected+=,@{path=$script:StorageRoot;operation='delete';win32_error=5}
  Require ($Observation.access_checks.Count -eq $expected.Count) 'SEAL_ACCESS_CHECK_COUNT'
  foreach($item in $expected){$found=@($Observation.access_checks|Where-Object{$_.path -ceq $item.path -and $_.operation -ceq $item.operation});Require ($found.Count -eq 1 -and $found[0].win32_error -is [long] -and $found[0].win32_error -eq $item.win32_error) 'SEAL_EFFECTIVE_ACCESS_FAILED'}
 }
}
function New-SealedBaseACL {
 $acl=[Security.AccessControl.FileSecurity]::new();$acl.SetAccessRuleProtection($true,$false);$acl.SetOwner([Security.Principal.SecurityIdentifier]::new($script:ControllerSID))
 foreach($sid in $script:TrustedWriters){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','Allow'))}
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($script:DispatcherSID),'ReadAndExecute','Allow'));return $acl
}
function New-SealedStoreACL {
 $acl=[Security.AccessControl.DirectorySecurity]::new();$acl.SetAccessRuleProtection($true,$false);$acl.SetOwner([Security.Principal.SecurityIdentifier]::new($script:ControllerSID))
 foreach($sid in $script:TrustedWriters){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 $sid=[Security.Principal.SecurityIdentifier]::new($script:DispatcherSID)
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,([Security.AccessControl.FileSystemRights]::Modify -band (-bnot [Security.AccessControl.FileSystemRights]::Delete)),'None','None','Allow'))
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'Modify','ContainerInherit,ObjectInherit','InheritOnly','Allow'))
 $acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($sid,'Delete,DeleteSubdirectoriesAndFiles,ChangePermissions,TakeOwnership','None','None','Deny'));return $acl
}
