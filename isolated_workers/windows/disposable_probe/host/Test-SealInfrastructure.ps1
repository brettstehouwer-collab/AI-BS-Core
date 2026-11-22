# Trusted controller infrastructure only. No ACL mutation, VBox or guest execution.
[CmdletBinding()]param([string]$EvidenceDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
if(-not $EvidenceDirectory){$EvidenceDirectory=Join-Path $PSScriptRoot ('evidence\seal-infra-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'-'+[Guid]::NewGuid().ToString('N'))}
$null=[IO.Directory]::CreateDirectory($EvidenceDirectory)
Import-Module (Join-Path $PSScriptRoot 'DisposableProbe.psm1') -Force
$report=& (Get-Module DisposableProbe) {
 param($SourceRoot)
 . (Join-Path $SourceRoot 'SealPolicy.ps1')
 $checks=[Collections.Generic.List[object]]::new()
 function Check($CheckName,[scriptblock]$Body){try{$null=&$Body;$checks.Add(@{name=$CheckName;passed=$true})}catch{$checks.Add(@{name=$CheckName;passed=$false;error=$_.Exception.Message})}}
 function Parsed($Value){Read-StrictJSON ([Text.Encoding]::UTF8.GetBytes((JSON $Value))) 131072}
 function Refuse([scriptblock]$Body,$Code){$caught=$false;try{&$Body}catch{$caught=$true;Require ($_.Exception.Message.Contains($Code,[StringComparison]::Ordinal)) ('WRONG_FAILURE '+$_.Exception.Message)};Require $caught ('EXPECTED_FAILURE '+$Code)}
 foreach($name in @('SealPolicy.ps1','Inspect-SealedWorker.ps1','Seal-WorkerImage.ps1')){Check ('parse '+$name){$tokens=$null;$errors=$null;$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $SourceRoot $name),[ref]$tokens,[ref]$errors);Require (@($errors).Count -eq 0) 'SEAL_SYNTAX'}}
 foreach($name in @('Inspect-SealedWorker.ps1','Seal-WorkerImage.ps1')){
  Check ($name+' defaults to describe only'){$r=& (Join-Path $SourceRoot $name)|ConvertFrom-Json -AsHashtable;Require ($r.state -ceq 'DESCRIBE_ONLY' -and $r.vm_uuid -ceq $script:WorkerUUID -and -not $r.candidate_execution) 'SEAL_DESCRIBE_GATE'}
  Check ($name+' rejects source execution before mutations'){Refuse {& (Join-Path $SourceRoot $name) -Execute} 'PROTECTED_POWERSHELL7_DEPLOYMENT_REQUIRED'}
 }
 $now=[DateTime]::UtcNow;$id='33333333-3333-4333-8333-333333333333';$snapshot='44444444-4444-4444-8444-444444444444';$child='55555555-5555-4555-8555-555555555555'
 $transport=Parsed @{schema_version=1;module_sha256=('a'*64);entry_sha256=('b'*64);pwsh_sha256=('c'*64)}
 Check 'predeployed exact transport policy is accepted without rewriting'{Assert-SealTransport $transport ('a'*64) ('b'*64) ('c'*64)}
 Check 'predeployed changed transport policy is refused'{$copy=Parsed $transport;$copy.entry_sha256='d'*64;Refuse {Assert-SealTransport $copy ('a'*64) ('b'*64) ('c'*64)} 'SEAL_TRANSPORT_PIN_MISMATCH'}
 Check 'predeployed expanded transport policy is refused'{$copy=Parsed $transport;$copy['arbitrary_entry']='bad';Refuse {Assert-SealTransport $copy ('a'*64) ('b'*64) ('c'*64)} 'SEAL_TRANSPORT_SCHEMA'}
 $bootstrapGrant=Parsed @{purpose='bootstrap_readback_snapshot_v1';challenge=('a'*64);guest_probe_sha256=('e'*64)}
 $guest=Parsed @{schema_version=1;purpose=$bootstrapGrant.purpose;state='OBSERVED_PROTECTED';challenge=$bootstrapGrant.challenge;vm_id=$script:WorkerUUID;guest_machine='AIBSPROBE01';guest_username='aibs_vm_worker';guest_sid='S-1-5-21-1-2-3-1001';integrity_sid='S-1-16-8192';administrator_group_present=$false;guest_groups=@('S-1-5-32-545');executable_sha256=$bootstrapGrant.guest_probe_sha256;failed_access_checks=0;access_checks=@(1..60|ForEach-Object{@{path=('fake'+$_);operation='write';denied=$true;win32_error=5}});probe_executed=$false;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;bootstrap=@{state='BOOTSTRAPPED_AWAITING_HOST_VERIFICATION';guest_sid='S-1-5-21-1-2-3-1001';executable_sha256=$bootstrapGrant.guest_probe_sha256;additions_signer_thumbprint='2B1BD188256EB612578949A943DE0DDC52D1DF79';bootstrap_disabled=$true;autologon_disabled=$true;setup_records_admin_only=$true;secure_boot=$true;tpm_present=$true}}
 Check 'retained bound standard guest proof is revalidated'{Assert-SealGuestProof $guest $bootstrapGrant}
 Check 'guest proof refuses an administrator group'{$copy=Parsed $guest;$copy.guest_groups+=,'S-1-5-32-544';Refuse {Assert-SealGuestProof $copy $bootstrapGrant} 'BOOTSTRAP_STANDARD_GUEST_REQUIRED'}
 Check 'guest proof refuses string false as authority'{$copy=Parsed $guest;$copy.probe_executed='false';Refuse {Assert-SealGuestProof $copy $bootstrapGrant} 'BOOTSTRAP_GUEST_FALSE_AUTHORITY_REQUIRED'}
 Check 'guest proof requires disabled autologon'{$copy=Parsed $guest;$copy.bootstrap.autologon_disabled=$false;Refuse {Assert-SealGuestProof $copy $bootstrapGrant} 'BOOTSTRAP_LOCKDOWN_REPORT_REQUIRED'}
 Check 'guest proof refuses host account identity'{$copy=Parsed $guest;$copy.guest_sid=$script:DispatcherSID;Refuse {Assert-SealGuestProof $copy $bootstrapGrant} 'BOOTSTRAP_GUEST_PROOF_REQUIRED'}
 Check 'guest proof requires exact additions signer'{$copy=Parsed $guest;$copy.bootstrap.additions_signer_thumbprint='bad';Refuse {Assert-SealGuestProof $copy $bootstrapGrant} 'BOOTSTRAP_LOCKDOWN_BINDING_REQUIRED'}
 $grant=Parsed @{schema_version=1;purpose='readonly_image_seal_inspection_v1';seal_id=$id;phase='preflight';challenge=('a'*64);issued_at=$now.ToString('o');expires_at=$now.AddMinutes(5).ToString('o');vm_uuid=$script:WorkerUUID;accepted_snapshot_uuid=$snapshot;guest_sid='S-1-5-21-1-2-3-1001';dispatcher_sid=$script:DispatcherSID;module_sha256=('b'*64);inspector_sha256=('c'*64);seal_policy_sha256=('d'*64);vbox_sha256=('e'*64)}
 Check 'exact seal grant accepted at issue time'{Assert-SealGrant $grant $id preflight $now}
 Check 'seal grant rejected at expiration boundary'{Refuse {Assert-SealGrant $grant $id preflight $now.AddMinutes(5)} 'SEAL_GRANT_EXPIRED_OR_FUTURE'}
 Check 'seal grant rejected one microsecond after expiration'{Refuse {Assert-SealGrant $grant $id preflight $now.AddMinutes(5).AddTicks(10)} 'SEAL_GRANT_EXPIRED_OR_FUTURE'}
 Check 'seal grant rejected before issue time'{Refuse {Assert-SealGrant $grant $id preflight $now.AddTicks(-1)} 'SEAL_GRANT_EXPIRED_OR_FUTURE'}
 foreach($change in @(@('vm_uuid',$script:IntegrationUUID,'SEAL_GRANT_IDENTITY'),@('phase','final','SEAL_GRANT_SCOPE'),@('dispatcher_sid',$script:ControllerSID,'SEAL_GRANT_IDENTITY'),@('guest_sid',($script:HostSIDPrefix+'1006'),'SEAL_GUEST_IDENTITY'),@('module_sha256','bad','SEAL_GRANT_PIN'))){$field=$change[0];$value=$change[1];$code=$change[2];Check ('seal grant rejects '+$field){$copy=Parsed $grant;$copy[$field]=$value;Refuse {Assert-SealGrant $copy $id preflight $now} $code}}
 $profile=New-SealProfile $grant.guest_sid $snapshot ('f'*64) $grant.vbox_sha256
 Check 'publication profile has exactly nineteen fields and fixed base'{Require ($profile.Count -eq 19 -and $profile.image_base_path -ceq 'E:\AI-BS-DisposableProbe-v1\system.vdi' -and $profile.vm_memory_mib -eq 4096 -and $profile.vm_cpus -eq 4) 'SEALED_PROFILE_CHANGED';Assert-ProfileData $profile}
 Check 'base ACL has protected trusted owner and dispatcher read execute only'{
  $acl=New-SealedBaseACL;Require ($acl.AreAccessRulesProtected -and $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ceq $script:ControllerSID) 'BASE_ACL_OWNER'
  $aces=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|Where-Object{$_.IdentityReference.Value -ceq $script:DispatcherSID});Require ($aces.Count -eq 1 -and $aces[0].AccessControlType -eq 'Allow' -and ([long]$aces[0].FileSystemRights -band 0xD0156) -eq 0) 'BASE_ACL_WORKER_WRITER'
 }
 Check 'store ACL protects parent deletion while allowing confined disposable children'{
  $acl=New-SealedStoreACL;Require ($acl.AreAccessRulesProtected -and $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ceq $script:ControllerSID) 'STORE_ACL_OWNER'
  $deny=@($acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|Where-Object{$_.IdentityReference.Value -ceq $script:DispatcherSID -and $_.AccessControlType -eq 'Deny'});Require ($deny.Count -eq 1 -and ([long]$deny[0].FileSystemRights -band 0xD0040) -eq 0xD0040 -and $deny[0].InheritanceFlags -eq 'None') 'STORE_ACL_NO_REPLACEMENT_DENY'
 }
 $vm=@{UUID=$script:WorkerUUID;VMState='poweroff';memory='4096';cpus='4';firmware='EFI';SecureBoot='on';clipboard='disabled';clipboard_file_transfers='off';draganddrop='disabled';vrde='off';usb='off';ehci='off';xhci='off';teleporterenabled='off';storagecontrollername0='SATA';CurrentSnapshotUUID=$snapshot;'SATA-ImageUUID-0-0'=$child;'SATA-0-0'=($script:StorageRoot+'\Snapshots\child.vdi');audio='none';audio_in='off';audio_out='off'}
 foreach($i in 1..8){$vm['nic'+$i]='none'};foreach($i in 1..4){$vm['uart'+$i]='off'}
 $vm=Parse-VMInfo (($vm.GetEnumerator()|ForEach-Object{'"'+$_.Key+'"="'+$_.Value+'"'}) -join "`n")
 $chain=@(@{UUID=$child;ParentUUID=$profile.system_disk_uuid;Location=$vm['SATA-0-0'];StorageFormat='VDI';Capacity='65536'},@{UUID=$profile.system_disk_uuid;ParentUUID='base';Location=$profile.image_base_path;StorageFormat='VDI';Capacity='65536'})
 function Make-Observation($Phase){
  $ops=@(@{arguments_sha256=(Hash-Text (JSON @('showvminfo',$script:WorkerUUID,'--machinereadable')));result=@{state='EXITED';exit_code=0;owned_process_termination_confirmed=$true;stdout=(($vm.GetEnumerator()|ForEach-Object{'"'+$_.Key+'"="'+$_.Value+'"'})-join "`n");stderr=''}})
  foreach($medium in $chain){$ops+=,@{arguments_sha256=(Hash-Text (JSON @('showmediuminfo','disk',$medium.UUID)));result=@{state='EXITED';exit_code=0;owned_process_termination_confirmed=$true;stdout=("UUID: "+$medium.UUID+"`nParent UUID: "+$medium.ParentUUID+"`nLocation: "+$medium.Location+"`nStorage format: VDI`nCapacity: 65536 MBytes`n");stderr=''}}}
  $access=@();if($Phase -cne 'preflight'){
   foreach($op in @('write_data','append_data','delete','write_dac','write_owner')){$access+=,@{path=$profile.image_base_path;operation=$op;win32_error=5}};$access+=,@{path=$profile.image_base_path;operation='read';win32_error=0}
   foreach($path in @($script:StorageRoot,'E:\')){foreach($op in @('delete_child','write_dac','write_owner')){$access+=,@{path=$path;operation=$op;win32_error=5}}};$access+=,@{path=$script:StorageRoot;operation='delete';win32_error=5}
  }
  Parsed @{schema_version=1;purpose=$grant.purpose;state='OBSERVED_OFF';seal_id=$id;phase=$Phase;challenge=$grant.challenge;vm_uuid=$script:WorkerUUID;accepted_snapshot_uuid=$snapshot;dispatcher_sid=$script:DispatcherSID;integrity_sid='S-1-16-8192';vm_info=$vm;config_sha256=(Hash-Text (JSON $vm));chain=$chain;chain_sha256=(Hash-Text (JSON $chain));operations=$ops;access_checks=$access;observed_utc=$now.AddTicks(1).ToString('o');candidate_execution=$false;vm_started=$false}
 }
 $original=(Get-Item Function:Assert-StorageLocation).ScriptBlock
 try{
  # Pure policy test: fake metadata paths are never opened; real ancestry is a live prerequisite.
  Set-Item Function:script:Assert-StorageLocation {param($Path) Require ($Path.StartsWith($script:StorageRoot+'\',[StringComparison]::Ordinal) -and $Path -notmatch '\.\.') 'OUTSIDE_DISPOSABLE_STORAGE'}
  $observation=Make-Observation preflight
  Check 'bound off metadata and acyclic snapshot ancestry accepted'{Assert-SealObservation $observation $grant}
  foreach($change in @(@('challenge',('0'*64),'SEAL_OBSERVATION_SCOPE'),@('vm_started',$true,'SEAL_OBSERVATION_AUTHORITY'),@('config_sha256',('0'*64),'SEAL_OBSERVATION_DIGEST'))){$field=$change[0];$value=$change[1];$code=$change[2];Check ('seal observation rejects '+$field){$copy=Parsed $observation;$copy[$field]=$value;Refuse {Assert-SealObservation $copy $grant} $code}}
  Check 'raw medium output cannot contradict parsed metadata'{$copy=Parsed $observation;$copy.operations[1].result.stdout=$copy.operations[1].result.stdout.Replace('VDI','VMDK');Refuse {Assert-SealObservation $copy $grant} 'SEAL_RAW_MEDIUM_BINDING'}
  Check 'cycle in differencing ancestry rejected'{$copy=Parsed $observation;$copy.chain[0].ParentUUID=$child;$copy.chain_sha256=Hash-Text (JSON $copy.chain);Refuse {Assert-SealObservation $copy $grant} 'SEAL_CHAIN_IDENTITY'}
  Check 'current disk path must bind VM attachment'{$copy=Parsed $observation;$copy.chain[0].Location=$script:StorageRoot+'\other.vdi';$copy.chain_sha256=Hash-Text (JSON $copy.chain);Refuse {Assert-SealObservation $copy $grant} 'SEAL_CURRENT_DISK_PATH'}
  Check 'wrong sealed base path rejected'{$copy=Parsed $observation;$copy.chain[1].Location=$script:StorageRoot+'\other.vdi';$copy.chain_sha256=Hash-Text (JSON $copy.chain);Refuse {Assert-SealObservation $copy $grant} 'SEAL_CHAIN_BASE'}
  $protectedGrant=Parsed $grant;$protectedGrant.phase='protected';$protected=Make-Observation protected
  Check 'exact thirteen effective access observations accepted'{Assert-SealObservation $protected $protectedGrant}
  Check 'sharing violation does not count as access denied'{$copy=Parsed $protected;$copy.access_checks[0].win32_error=32;Refuse {Assert-SealObservation $copy $protectedGrant} 'SEAL_EFFECTIVE_ACCESS_FAILED'}
  Check 'duplicate access report cannot hide missing operation'{$copy=Parsed $protected;$copy.access_checks[1]=$copy.access_checks[0];Refuse {Assert-SealObservation $copy $protectedGrant} 'SEAL_EFFECTIVE_ACCESS_FAILED'}
  Check 'base must remain readable to standard dispatcher'{$copy=Parsed $protected;$copy.access_checks[5].win32_error=5;Refuse {Assert-SealObservation $copy $protectedGrant} 'SEAL_EFFECTIVE_ACCESS_FAILED'}
 }finally{Set-Item Function:script:Assert-StorageLocation $original}
 [ordered]@{schema_version=1;evidence_class='trusted_controller_sealing_infrastructure_only';vm_operations_performed=$false;acl_mutations_performed=$false;actual_effective_access_measured=$false;image_hash_measured=$false;profile_published=$false;checks=@($checks.ToArray());passed=@($checks|Where-Object passed).Count;failed=@($checks|Where-Object{-not $_.passed}).Count;completed_utc=[DateTime]::UtcNow.ToString('o')}
} $PSScriptRoot
$path=Join-Path $EvidenceDirectory 'results.json';[IO.File]::WriteAllText($path,($report|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
$report.checks|Where-Object{-not $_.passed}|ForEach-Object{[PSCustomObject]$_}|Format-Table name,error -Wrap
Write-Output ('Sealing infrastructure: '+$report.passed+' passed; '+$report.failed+' failed. '+$path)
if($report.failed -gt 0){exit 1}
