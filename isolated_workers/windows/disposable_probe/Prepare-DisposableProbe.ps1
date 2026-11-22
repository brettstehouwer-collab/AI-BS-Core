# Trusted host provisioning for ONE new offline diagnostic VM. Never targets the integration guest.
[CmdletBinding()]
param([switch]$Provision,[switch]$ResumePreAccountFailure)
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$store='E:\AI-BS-DisposableProbe-v1'
$evidence='C:\AI-BS\backups\disposable_probe_20261026_record127'
$media='C:\Users\footb\Downloads\26300.9457.260913-1737.26h2_ge_release_svc_refresh_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso'
$isoHash='bc3f24086ebadc94489066b5ad78089e2cf5c3491e90e790bb81a2b199c10e38'
if(-not $Provision){[pscustomobject]@{state='DESCRIBE_ONLY';root=$root;store=$store;disk_gib=64;reserve_gib=40;cpu=4;memory_mib=8192;network='none';integration_guest_modified=$false}|ConvertTo-Json;return}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if($identity.User.Value -cne 'S-1-5-21-2133766663-4066672948-2456486318-1001' -or -not ([Security.Principal.WindowsPrincipal]$identity).IsInRole('Administrators')){throw 'TRUSTED_PROVISIONER_REQUIRED'}
if((Test-Path -LiteralPath $store) -or (Get-LocalUser -Name aibs_probe_host -ErrorAction SilentlyContinue)){throw 'EXISTING_PROVISIONING_PRESERVED_NO_ADOPTION'}
if(Test-Path -LiteralPath $root){
 if(-not $ResumePreAccountFailure -or -not (Test-Path -LiteralPath (Join-Path $evidence 'Prepare-DisposableProbe.failed1.ps1'))){throw 'EXISTING_PROVISIONING_PRESERVED_NO_ADOPTION'}
 if(@(Get-ChildItem -LiteralPath $root -Force).Count -ne 1 -or -not (Test-Path -LiteralPath (Join-Path $root 'private')) -or @(Get-ChildItem -LiteralPath (Join-Path $root 'private') -Force).Count -ne 0){throw 'UNEXPECTED_PARTIAL_PROVISIONING'}
 foreach($p in @($root,(Join-Path $root 'private'))){$a=Get-Acl -LiteralPath $p;if(-not $a.AreAccessRulesProtected -or $a.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne 'S-1-5-32-544' -or (Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'UNTRUSTED_PARTIAL_ROOT'};foreach($r in $a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){if($r.IdentityReference.Value -cnotin @('S-1-5-18','S-1-5-32-544','S-1-3-4')){throw 'UNTRUSTED_PARTIAL_WRITER'}}}
}elseif($ResumePreAccountFailure){throw 'MISSING_PARTIAL_PROVISIONING'}
if((Get-PSDrive E).Free -lt (104GB+64MB)){throw 'NEW_DIAGNOSTIC_STORAGE_PROFILE_UNAVAILABLE'}
if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1KB -lt 12GB){throw 'INSUFFICIENT_CURRENT_RAM'}
if((Get-FileHash -LiteralPath $media).Hash.ToLowerInvariant() -cne $isoHash){throw 'INSTALL_MEDIA_CHANGED'}
if((Get-FileHash -LiteralPath 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe').Hash -cne '178E016ED38CB6E369A5C17C6C960C176674B9C864030D8CE0AD2867613BECFF'){throw 'HYPERVISOR_CHANGED'}
function New-Json([string]$Path,$Object){$b=[Text.Encoding]::UTF8.GetBytes(($Object|ConvertTo-Json -Depth 12));$f=[IO.File]::Open($Path,'CreateNew','Write','None');try{$f.Write($b,0,$b.Length);$f.Flush($true)}finally{$f.Dispose()}}
# Atomic creation with the final protected descriptor; pre-existing objects are never adopted.
$native=Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\control\protection_review\AtomicDirectory.cs') -Raw
if((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot '..\control\protection_review\AtomicDirectory.cs')).Hash -cne 'ABA03C7EB66471D241232FE5DEB4E158F2D2CE7F54ED32CCFA1DE1BD4AF24F89'){throw 'ATOMIC_HELPER_CHANGED'}
$native=$native.Replace('namespace AIBS.HostProtection118','namespace AIBS.Disposable127').Replace('const string Target = @"C:\ProgramData\AI-BS-WorkerControl";', 'const string Target = @"E:\AI-BS-DisposableProbe-v1";').Replace('path.StartsWith(Fixture+"\\",StringComparison.Ordinal)', 'path.StartsWith(@"C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1",StringComparison.Ordinal)')
Add-Type -TypeDefinition $native
function New-ProtectedDirectory([string]$Path,[string]$WorkerSid,[string]$Role='read'){
 $a=[Security.AccessControl.DirectorySecurity]::new();$a.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'));$a.SetAccessRuleProtection($true,$false)
 foreach($sid in @('S-1-5-18','S-1-5-32-544')){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 $a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new('S-1-3-4'),'ReadPermissions','ContainerInherit,ObjectInherit','None','Allow'))
 if($WorkerSid){
  if($Role -eq 'write'){
   $a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($WorkerSid),'ReadAndExecute,Write','None','None','Allow'))
   $a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($WorkerSid),'Modify','ContainerInherit,ObjectInherit','InheritOnly','Allow'))
  }elseif($Role -eq 'claims'){
   $a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($WorkerSid),'ReadAndExecute,Write','ContainerInherit,ObjectInherit','None','Allow'))
  }elseif($Role -eq 'traverse'){
   $a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($WorkerSid),'ReadAndExecute','None','None','Allow'))
  }elseif($Role -eq 'read'){$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($WorkerSid),'ReadAndExecute','ContainerInherit,ObjectInherit','None','Allow'))}
 }
 [AIBS.Disposable127.AtomicDirectory]::CreateNew($Path,$a.GetSecurityDescriptorBinaryForm())
 $actual=Get-Acl -LiteralPath $Path
 if(-not $actual.AreAccessRulesProtected -or $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -cne 'S-1-5-32-544'){throw 'DESCRIPTOR_READBACK_FAILED'}
}
if(-not $ResumePreAccountFailure){New-ProtectedDirectory $root ''}
$private=Join-Path $root 'private';if(-not $ResumePreAccountFailure){New-ProtectedDirectory $private ''}
$password=[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(36))+'aA1!'
$secure=ConvertTo-SecureString -String $password -AsPlainText -Force
$user=New-LocalUser -Name aibs_probe_host -Password $secure -AccountNeverExpires -PasswordNeverExpires -Description 'AI-BS offline diagnostic launcher'
$workerSid=$user.SID.Value
# Retain the only credential in DPAPI and the Task Scheduler vault; never print it.
$secure|ConvertFrom-SecureString|Set-Content -LiteralPath (Join-Path $private 'host_credential.dpapi')
Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $user -ErrorAction Stop
$a=Get-Acl -LiteralPath $root;$a.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new($user.SID,'ReadAndExecute','None','None','Allow'));Set-Acl -LiteralPath $root -AclObject $a
foreach($name in @('deployment','policy','requests','credentials','identity')){New-ProtectedDirectory (Join-Path $root $name) $workerSid}
foreach($name in @('state','receipts')){New-ProtectedDirectory (Join-Path $root $name) ''}
foreach($name in @('worker_state','worker_outputs','vbox_home')){New-ProtectedDirectory (Join-Path $root $name) $workerSid 'write'}
New-ProtectedDirectory (Join-Path $root 'worker_claims') $workerSid 'claims'
New-ProtectedDirectory $store $workerSid 'write'
# Pinned protected copy of the bundled PowerShell distribution. No ambient profile or module loading.
$runtime=Join-Path $root 'deployment\pwsh';New-ProtectedDirectory $runtime $workerSid
Copy-Item -Path (Join-Path $PSHOME '*') -Destination $runtime -Recurse -Force
$runtimeManifest=@(Get-ChildItem -LiteralPath $runtime -File -Recurse|ForEach-Object{[ordered]@{path=$_.FullName.Substring($runtime.Length+1);bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName).Hash.ToLowerInvariant()}})
New-Json (Join-Path $root 'identity\runtime_manifest.json') $runtimeManifest
# The standard launcher must not traverse the signed-in user's Downloads folder.
# Copy only the pinned public installation medium into its protected read-only root.
$protectedMedia=Join-Path $root 'identity\windows.iso'
Copy-Item -LiteralPath $media -Destination $protectedMedia -ErrorAction Stop
if((Get-FileHash -LiteralPath $protectedMedia).Hash.ToLowerInvariant() -cne $isoHash){throw 'COPIED_INSTALL_MEDIA_CHANGED'}
$guestPassword=[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(30))+'aA1!'
$adminPassword=[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(30))+'aA1!'
[IO.File]::WriteAllText((Join-Path $root 'credentials\guest.txt'),$guestPassword,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $root 'credentials\bootstrap.txt'),$adminPassword,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllBytes((Join-Path $private 'receipt.key'),[Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$vmId=[guid]::NewGuid().ToString();$imageId='aibs-fixed-probe-win11-eval-'+$vmId
$plan=[ordered]@{schema_version=1;state='PREPARED';root=$root;store=$store;vm_uuid=$vmId;forbidden_vm_uuid='6c5a53da-ab80-4ecb-8be6-4059266f736e';vm_name='AI-BS-DisposableProbe-20261026';image_id=$imageId;image_sha256=$isoHash;vbox_path='C:\Program Files\Oracle\VirtualBox\VBoxManage.exe';vbox_sha256='178e016ed38cb6e369a5c17c6c960c176674b9c864030d8ce0ad2867613becff';vbox_user_home=(Join-Path $root 'vbox_home');dispatcher_sid=$workerSid;controller_sid=$identity.User.Value;iso_path=$protectedMedia;disk_mib=65536;disk_variant='Fixed';reserve_bytes=40GB;vm_memory_mib=8192;vm_cpus=4;guest_username='aibs_vm_worker';network='none';general_worker_admission=$false;apply_authorized=$false;created_utc=[DateTime]::UtcNow.ToString('o')}
New-Json (Join-Path $root 'policy\provisioning.json') $plan
Copy-Item -LiteralPath (Join-Path $root 'policy\provisioning.json') -Destination (Join-Path $evidence 'provisioning.json')
$source=Join-Path $PSScriptRoot 'Provision-WorkerVM.ps1';$target=Join-Path $root 'deployment\Provision-WorkerVM.ps1';Copy-Item -LiteralPath $source -Destination $target
$action=New-ScheduledTaskAction -Execute (Join-Path $runtime 'pwsh.exe') -Argument ('-NoProfile -NonInteractive -File "'+$target+'"') -WorkingDirectory (Join-Path $root 'deployment')
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::FromMinutes(45)) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$task=Register-ScheduledTask -TaskName 'AIBS_DisposableProbe_Provision_v1' -Action $action -Settings $settings -User ($env:COMPUTERNAME+'\'+$user.Name) -Password $password -RunLevel Limited -Description 'New offline fixed diagnostic VM provisioning only; no triggers' -ErrorAction Stop
$service=New-Object -ComObject 'Schedule.Service';$service.Connect();$registered=$service.GetFolder('\').GetTask($task.TaskName);$registered.SetSecurityDescriptor('D:P(A;;GA;;;SY)(A;;GA;;;BA)',0)
$password=$null;$guestPassword=$null;$adminPassword=$null;$secure=$null
New-Json (Join-Path $evidence 'protected_setup_result.json') ([ordered]@{state='NEW_STANDARD_LAUNCHER_AND_PROTECTED_ROOT_CREATED';vm_uuid=$vmId;dispatcher_sid=$workerSid;task_name=$task.TaskName;root=$root;store=$store;integration_modified=$false;runtime_files=$runtimeManifest.Count;candidate_execution=$false})
[pscustomobject]@{state='PREPARED';vm_uuid=$vmId;dispatcher_sid=$workerSid;task=$task.TaskName;next='Start fixed provisioning task'}|ConvertTo-Json
