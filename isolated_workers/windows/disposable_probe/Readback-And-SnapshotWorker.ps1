# Reviewed fixed infrastructure entry for the new offline VM. Describe-only by default.
# Controller publishes a separately pinned one-use bootstrap grant, then launches
# this protected entry as the dedicated standard HOST dispatcher. No candidate code.
[CmdletBinding()]param(
 [switch]$Execute,
 [string]$ExpectedModuleSHA256,
 [string]$ExpectedGrantSHA256
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
if(-not $Execute){[ordered]@{state='DESCRIBE_ONLY';purpose='bootstrap_readback_snapshot_v1';vm_uuid='e5a2fe34-7b90-460c-83af-903d51b4bb16';operations=@('inspect_off','detach_optical','start_new_vm','fixed_standard_readback','graceful_off','accepted_off_snapshot','propose_controller_seal');candidate_execution=$false;general_admission=$false;profile_published=$false}|ConvertTo-Json -Compress;return}
if($PSVersionTable.PSVersion.Major -lt 7 -or $PSScriptRoot -cne (Join-Path $root 'deployment\host')){throw 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'}
if($ExpectedModuleSHA256 -cnotmatch '^[0-9a-f]{64}$' -or $ExpectedGrantSHA256 -cnotmatch '^[0-9a-f]{64}$'){throw 'EXACT_SOURCE_AND_GRANT_PINS_REQUIRED'}
$modulePath=Join-Path $PSScriptRoot 'DisposableProbe.psm1'
$moduleStream=[IO.File]::Open($modulePath,'Open','Read','Read')
try{
 if([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($moduleStream)).ToLowerInvariant() -cne $ExpectedModuleSHA256){throw 'PINNED_HOST_MODULE_CHANGED'}
 Import-Module $modulePath -Force
 & (Get-Module DisposableProbe) {
  param($ExpectedGrantSHA256,$ExpectedModuleSHA256,$EntryPath)
  $lease=$null;$vmLease=$null;$attemptRoot=$null;$started=$false;$report=$null
  $result=[ordered]@{schema_version=1;purpose='bootstrap_readback_snapshot_v1';state='BLOCKED';vm_uuid=$script:WorkerUUID;guest_reported=$null;worker_observed=[ordered]@{};error_code='';profile_published=$false;worker_admitted=$false;candidate_execution_authorized=$false;apply_authorized=$false;full_containment_accepted=$false}
  try{
   Assert-Principal $script:DispatcherSID -Standard
   $grantPath=Fixed-Path 'policy\bootstrap-grant.json';$null=Assert-Path $grantPath
   $grant=Read-StrictJSON (Read-Bytes $grantPath 32768 $ExpectedGrantSHA256)
   Assert-Fields $grant @('schema_version','state','purpose','attempt_id','challenge','issued_at','expires_at','vm_uuid','dispatcher_sid','vbox_sha256','host_entry_sha256','host_module_sha256','guest_readback_sha256','guest_probe_sha256','accepted_snapshot_name') 'BOOTSTRAP_GRANT_SCHEMA'
   Require ($grant.schema_version -is [long] -and $grant.schema_version -eq 1 -and $grant.state -ceq 'AUTHORIZED_FIXED_BOOTSTRAP_ONLY' -and $grant.purpose -ceq 'bootstrap_readback_snapshot_v1') 'BOOTSTRAP_GRANT_PURPOSE'
   Require ((Is-ID $grant.attempt_id) -and (Is-Digest $grant.challenge) -and $grant.vm_uuid -ceq $script:WorkerUUID -and $grant.vm_uuid -cne $script:IntegrationUUID -and $grant.dispatcher_sid -ceq $script:DispatcherSID) 'BOOTSTRAP_GRANT_IDENTITY'
   foreach($field in @('vbox_sha256','host_entry_sha256','host_module_sha256','guest_readback_sha256','guest_probe_sha256')){Require (Is-Digest $grant[$field]) 'BOOTSTRAP_GRANT_PIN_REQUIRED'}
   Require ($grant.host_module_sha256 -ceq $ExpectedModuleSHA256 -and $grant.guest_probe_sha256 -ceq '82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531' -and $grant.accepted_snapshot_name -ceq 'AIBS_ACCEPTED_DIAGNOSTIC_V1') 'FIXED_BOOTSTRAP_GRANT_REQUIRED'
   $issued=UTC $grant.issued_at;$expiry=UTC $grant.expires_at
   Require ($issued -le (Now-UTC) -and (Now-UTC) -lt $expiry -and $expiry -gt $issued -and $expiry-$issued -le [TimeSpan]::FromMinutes(10)) 'EXPIRED_OR_FUTURE_BOOTSTRAP_GRANT'
   $null=Assert-Path $EntryPath;$null=Read-Bytes $EntryPath 65536 $grant.host_entry_sha256
   $null=Assert-Path (Fixed-Path 'deployment\host\DisposableProbe.psm1');$null=Read-Bytes (Fixed-Path 'deployment\host\DisposableProbe.psm1') 131072 $ExpectedModuleSHA256
   $readbackPath=Fixed-Path 'deployment\host\Guest-BootstrapReadback.ps1';$null=Assert-Path $readbackPath
   $readback=[Text.UTF8Encoding]::new($false,$true).GetString((Read-Bytes $readbackPath 10240 $grant.guest_readback_sha256))
   $vbox='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe';$null=Assert-Path $vbox $script:TrustedWriters -External;$null=Read-Bytes $vbox 67108864 $grant.vbox_sha256
   $null=Assert-Path (Fixed-Path 'credentials\guest.txt');$null=Read-Bytes (Fixed-Path 'credentials\guest.txt') 1024
   foreach($relative in @('worker_state','worker_outputs','worker_claims','vbox_home')){$null=Assert-Path (Fixed-Path $relative) (@($script:TrustedWriters)+$script:DispatcherSID)}
   Assert-ClaimPolicy @{dispatcher_sid=$script:DispatcherSID}
   $lease=[IO.File]::Open((Fixed-Path 'worker_state\provision.lease'),'Open','ReadWrite','None')
   $vmLease=[IO.File]::Open((Fixed-Path 'worker_state\vm.lease'),'OpenOrCreate','ReadWrite','None')
   New-JSON (Fixed-Path ('worker_claims\bootstrap-'+$grant.attempt_id+'.claim')) @{attempt_id=$grant.attempt_id;grant_sha256=$ExpectedGrantSHA256;purpose=$grant.purpose;claimed_utc=(Now-UTC).ToString('o')}
   $attemptRoot=Fixed-Path ('worker_outputs\bootstrap-'+$grant.attempt_id)
   Require (-not [IO.Directory]::Exists($attemptRoot)) 'EXISTING_BOOTSTRAP_OUTPUT_REFUSED';$null=[IO.Directory]::CreateDirectory($attemptRoot)
   function Boot-Operation([string]$Operation,[string[]]$Arguments){
    $script:BootstrapSequence++
    New-JSON (Join-Path $attemptRoot ('{0:D3}_{1}_intent.json' -f $script:BootstrapSequence,$Operation)) @{operation=$Operation;vm_uuid=$script:WorkerUUID;attempt_id=$grant.attempt_id;arguments_sha256=(Hash-Text (JSON $Arguments));utc=(Now-UTC).ToString('o')}
    $r=Invoke-BoundedProcess $vbox $Arguments (Fixed-Path 'vbox_home') (Fixed-Path 'deployment') 30 65536
    New-JSON (Join-Path $attemptRoot ('{0:D3}_{1}_result.json' -f $script:BootstrapSequence,$Operation)) $r
    Successful-Operation $r;return ,$r
   }
   function Inspect-BootstrapVM([string]$State){
    $r=Boot-Operation Inspect @('showvminfo',$script:WorkerUUID,'--machinereadable');$info=Parse-VMInfo $r.stdout
    foreach($pair in @(@('UUID',$script:WorkerUUID),@('VMState',$State),@('memory','4096'),@('cpus','4'),@('firmware','EFI'),@('SecureBoot','on'),@('clipboard','disabled'),@('clipboard_file_transfers','off'),@('draganddrop','disabled'),@('vrde','off'),@('usb','off'),@('ehci','off'),@('xhci','off'),@('audio','none'),@('audio_in','off'),@('audio_out','off'),@('teleporterenabled','off'),@('storagecontrollername0','SATA'),@('SATA-ImageUUID-0-0','5b4f5331-0da2-491d-a257-6b4ecf435a5a'))){Require ($info.ContainsKey($pair[0]) -and $info[$pair[0]] -ceq $pair[1]) ('BOOTSTRAP_VM_POLICY_'+$pair[0])}
    foreach($index in 1..8){Require ($info.ContainsKey('nic'+$index) -and $info['nic'+$index] -ceq 'none') 'BOOTSTRAP_NETWORK_NOT_DISABLED'}
    foreach($index in 1..4){Require ($info.ContainsKey('uart'+$index) -and $info['uart'+$index] -ceq 'off') 'BOOTSTRAP_UART_NOT_DISABLED'}
    foreach($key in $info.Keys){Require ($key -cnotmatch '^SharedFolder|^storagecontrollername[1-9][0-9]*$') 'BOOTSTRAP_EXTRA_HOST_CHANNEL'}
    Require ($info['SATA-0-0'] -ceq 'E:\AI-BS-DisposableProbe-v1\system.vdi') 'BOOTSTRAP_BASE_DISK_CHANGED'
    return ,$info
   }
   $script:BootstrapSequence=0
   $initial=Inspect-BootstrapVM 'poweroff'
   Require (-not $initial.ContainsKey('CurrentSnapshotUUID')) 'EXISTING_BASELINE_SNAPSHOT_REFUSED'
   $result.worker_observed['before_config_sha256']=Hash-Text (JSON $initial)
   # Credential-bearing optical media is removed while powered off, before the
   # first standard-user session. Never detach the system disk or an unknown disk.
   $detached=@()
   foreach($key in @($initial.Keys|Sort-Object -CaseSensitive)){
    if($key -cmatch '^SATA-([0-9]+)-([0-9]+)$' -and $key -cne 'SATA-0-0' -and $initial[$key] -cnotin @('none','emptydrive')){
     $port=$Matches[1];$device=$Matches[2];$path=$initial[$key]
     Require ($port -cmatch '^[1-3]$' -and $device -ceq '0' -and ($path -ceq (Fixed-Path 'identity\windows.iso') -or $path -ceq (Fixed-Path 'identity\VBoxGuestAdditions.iso') -or $path -cmatch '^C:\\ProgramData\\AI-BS-WorkerControl\\disposable_probe_v1\\worker_state\\install-[0-9a-f]{32}\\media-[A-Za-z0-9_.-]+\.(iso|viso)$')) 'UNEXPECTED_BOOTSTRAP_OPTICAL_MEDIA'
     $null=Boot-Operation DetachOptical @('storageattach',$script:WorkerUUID,'--storagectl','SATA','--port',$port,'--device',$device,'--type','dvddrive','--medium','none');$detached+=,$key
    }
   }
   $cleanMedia=Inspect-BootstrapVM 'poweroff'
   foreach($key in $cleanMedia.Keys){if($key -cmatch '^SATA-([0-9]+)-([0-9]+)$' -and $key -cne 'SATA-0-0'){Require ($cleanMedia[$key] -cin @('none','emptydrive')) 'BOOTSTRAP_MEDIA_STILL_ATTACHED'}}
   $result.worker_observed['detached_optical_slots']=$detached
   Assert-StorageReserve;Assert-HostMemoryReserve
   Require ((Now-UTC) -lt $expiry) 'BOOTSTRAP_GRANT_EXPIRED_BEFORE_START'
   $started=$true;$null=Boot-Operation Start @('startvm',$script:WorkerUUID,'--type','headless')
   $null=Inspect-BootstrapVM 'running'
   $ready=$false;$deadline=(Now-UTC).AddSeconds(180)
   while((Now-UTC) -lt $deadline){
    Require ((Now-UTC) -lt $expiry) 'BOOTSTRAP_GRANT_EXPIRED'
    $r=Boot-Operation Readiness @('guestproperty','get',$script:WorkerUUID,'/VirtualBox/GuestAdd/Version')
    if($r.stdout -cmatch '7\.2\.22'){
     $null=Boot-Operation SetRL @('guestproperty','set',$script:WorkerUUID,'/VirtualBox/GuestAdd/RunLevel','3')
     Start-Sleep -Seconds 3
     $ready=$true;break
    }
    Start-Sleep -Seconds 3
   }
   Require $ready 'BOOTSTRAP_GUEST_CONTROL_NOT_READY'
   $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes("& {`n"+$readback+"`n} -Challenge '"+$grant.challenge+"'"))
   Require ((Now-UTC) -lt $expiry) 'BOOTSTRAP_GRANT_EXPIRED_BEFORE_READBACK'
   $observed=Boot-Operation FixedReadback @('guestcontrol',$script:WorkerUUID,'run','--exe','C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','--username','aibs_vm_worker','--passwordfile',(Fixed-Path 'credentials\guest.txt'),'--wait-stdout','--wait-stderr','--timeout','25000','--cwd','C:\AIBSProbe','--','-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded)
   $report=Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes($observed.stdout)) 32768
   Require ($report.schema_version -is [long] -and $report.schema_version -eq 1 -and $report.purpose -ceq $grant.purpose -and $report.state -ceq 'OBSERVED_PROTECTED' -and $report.challenge -ceq $grant.challenge -and $report.vm_id -ceq $script:WorkerUUID -and $report.guest_machine -ceq 'AIBSPROBE01' -and $report.guest_username -ceq 'aibs_vm_worker') 'FIXED_READBACK_SCOPE_FAILED'
   Require ($report.guest_sid -is [string] -and $report.guest_sid -cmatch '^S-1-5-21-[0-9]+-[0-9]+-[0-9]+-[0-9]+$' -and -not $report.guest_sid.StartsWith($script:HostSIDPrefix,[StringComparison]::Ordinal) -and $report.integrity_sid -ceq 'S-1-16-8192' -and $report.administrator_group_present -is [bool] -and -not $report.administrator_group_present -and 'S-1-5-32-544' -cnotin $report.guest_groups -and 'S-1-5-114' -cnotin $report.guest_groups) 'STANDARD_GUEST_READBACK_FAILED'
   Require ($report.executable_sha256 -ceq $grant.guest_probe_sha256 -and $report.failed_access_checks -is [long] -and $report.failed_access_checks -eq 0 -and $report.access_checks.Count -ge 60) 'GUEST_ACCESS_PROTECTION_FAILED'
   foreach($check in $report.access_checks){Require ($check.denied -is [bool] -and $check.denied -and $check.win32_error -is [long] -and $check.win32_error -eq 5) 'GUEST_ACCESS_PROTECTION_FAILED'}
   foreach($field in @('probe_executed','worker_admitted','execution_authorized','apply_authorized')){Require ($report[$field] -is [bool] -and -not $report[$field]) 'BOOTSTRAP_AUTHORITY_FALSE_REQUIRED'}
   foreach($field in @('bootstrap_disabled','autologon_disabled','setup_records_admin_only','secure_boot','tpm_present')){Require ($report.bootstrap[$field] -is [bool] -and $report.bootstrap[$field]) 'BOOTSTRAP_LOCKDOWN_REPORT_FAILED'}
   Require ($report.bootstrap.guest_sid -ceq $report.guest_sid -and $report.bootstrap.executable_sha256 -ceq $grant.guest_probe_sha256 -and ($report.bootstrap.additions_signer_thumbprint -in @('2B1BD188256EB612578949A943DE0DDC52D1DF79', '7E92B66BE51B79D8CE3FF25C15C2DF6AB8C7F2F2'))) 'BOOTSTRAP_REPORT_BINDING_FAILED'
   $result.guest_reported=$report
   # Ask the guest OS for a clean shutdown; a forced fallback never creates an
   # accepted baseline. Snapshot creation is permitted only after observed off.
   $null=Boot-Operation GracefulOff @('controlvm',$script:WorkerUUID,'acpipowerbutton')
   $deadline=(Now-UTC).AddSeconds(120);$off=$false
   while((Now-UTC) -lt $deadline){$r=Boot-Operation Inspect @('showvminfo',$script:WorkerUUID,'--machinereadable');$info=Parse-VMInfo $r.stdout;Require ($info.UUID -ceq $script:WorkerUUID) 'BOOTSTRAP_VM_IDENTITY_CHANGED';if($info.VMState -ceq 'poweroff'){$off=$true;break};Start-Sleep -Seconds 3}
   Require $off 'CLEAN_BOOTSTRAP_SHUTDOWN_UNCONFIRMED';$started=$false
   $null=Inspect-BootstrapVM 'poweroff'
   Require ((Now-UTC) -lt $expiry) 'BOOTSTRAP_GRANT_EXPIRED_BEFORE_SNAPSHOT'
   $null=Boot-Operation AcceptedSnapshot @('snapshot',$script:WorkerUUID,'take','AIBS_ACCEPTED_DIAGNOSTIC_V1','--description','Fixed diagnostic only; standard identity and protection readback retained; no candidate admission')
   # Snapshot creates a new current differencing disk. Keep the immutable base
   # UUID pinned independently rather than expecting the current disk UUID equal.
   $r=Boot-Operation FinalInspect @('showvminfo',$script:WorkerUUID,'--machinereadable');$final=Parse-VMInfo $r.stdout
   Require ($final.UUID -ceq $script:WorkerUUID -and $final.VMState -ceq 'poweroff' -and (Is-ID $final.CurrentSnapshotUUID) -and (Is-ID $final['SATA-ImageUUID-0-0']) -and $final['SATA-ImageUUID-0-0'] -cne '5b4f5331-0da2-491d-a257-6b4ecf435a5a') 'ACCEPTED_SNAPSHOT_READBACK_FAILED'
   $result.worker_observed['accepted_snapshot_uuid']=$final.CurrentSnapshotUUID;$result.worker_observed['current_disk_uuid']=$final['SATA-ImageUUID-0-0'];$result.worker_observed['terminal_state']='poweroff';$result.worker_observed['terminal_config_sha256']=Hash-Text (JSON $final)
   $result.worker_observed['grant_sha256']=$ExpectedGrantSHA256;$result.worker_observed['readback_command_sha256']=Hash-Text $encoded;$result.worker_observed['readback_report_sha256']=Hash-Text (JSON $report);$result.worker_observed['dispatcher_sid']=$script:DispatcherSID
   $result['controller_next']='Protect base file and relevant parents against dispatcher replacement; stream and retain base SHA256; independently validate disk ancestry; publish exact pinned PROVISIONED profile only after controller review.'
   $result.state='SNAPSHOT_PROPOSED_AWAITING_CONTROLLER_SEAL'
  }catch{$result.state='BLOCKED_RETAINED';$result.error_code=if($_.Exception -is [InvalidOperationException]){$_.Exception.Message}else{'BOOTSTRAP_TRANSPORT_'+$_.Exception.GetType().Name}}
  finally{
   if($started -and $null -ne $attemptRoot){
    try{$null=Boot-Operation ForcedOff @('controlvm',$script:WorkerUUID,'poweroff');$r=Boot-Operation VerifyOff @('showvminfo',$script:WorkerUUID,'--machinereadable');$info=Parse-VMInfo $r.stdout;Require ($info.UUID -ceq $script:WorkerUUID -and $info.VMState -ceq 'poweroff') 'BOOTSTRAP_TERMINATION_UNCONFIRMED';$result.worker_observed['terminal_state']='poweroff';$result.worker_observed['forced_off_no_baseline']=$true}catch{$result.state='QUARANTINED';$result.error_code='BOOTSTRAP_TERMINATION_UNCONFIRMED'}
   }
   $result['completed_utc']=(Now-UTC).ToString('o')
   if($attemptRoot){try{New-JSON (Join-Path $attemptRoot 'result.json') $result}catch{$result.state='QUARANTINED';$result.error_code='BOOTSTRAP_RESULT_PERSISTENCE_UNCERTAIN'}}
   if($vmLease){$vmLease.Dispose()};if($lease){$lease.Dispose()};Close-Held
  }
  $result|ConvertTo-Json -Depth 24 -Compress
  if($result.state -cne 'SNAPSHOT_PROPOSED_AWAITING_CONTROLLER_SEAL'){exit 2}
 } $ExpectedGrantSHA256 $ExpectedModuleSHA256 $PSCommandPath
}finally{$moduleStream.Dispose()}
