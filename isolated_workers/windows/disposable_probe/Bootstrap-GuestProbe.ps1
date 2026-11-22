# Fixed first-boot bootstrap for the NEW offline VirtualBox worker only.
# This script is data on the host. Never invoke its entry on the host.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$probeHash='82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531'
$stage='C:\AIBSBootstrap'
$destination='C:\AIBSProbe'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]$identity
$validatedGuest=$false
function Require([bool]$Condition,[string]$Code){if(-not $Condition){throw [InvalidOperationException]::new($Code)}}
function Hash([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Admin-Only([string]$Path){
 $item=Get-Item -LiteralPath $Path -Force
 Require (-not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'BOOTSTRAP_REPARSE_REFUSED'
 $acl=Get-Acl -LiteralPath $Path;$acl.SetAccessRuleProtection($true,$false)
 foreach($rule in @($acl.Access)){$null=$acl.RemoveAccessRuleSpecific($rule)}
 foreach($sid in @('S-1-5-18','S-1-5-32-544')){
  if($item.PSIsContainer){$rule=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow')}
  else{$rule=[Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','Allow')}
  $acl.AddAccessRule($rule)
 }
 Set-Acl -LiteralPath $Path -AclObject $acl
 $actual=Get-Acl -LiteralPath $Path
 Require ($actual.AreAccessRulesProtected) 'BOOTSTRAP_RECORD_PROTECTION_FAILED'
 foreach($rule in $actual.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])){Require ($rule.IdentityReference.Value -in @('S-1-5-18','S-1-5-32-544')) 'BOOTSTRAP_RECORD_READER_REFUSED'}
}
function Protected-Directory([string]$Path,[string]$ReaderSID){
 Require (-not(Test-Path -LiteralPath $Path)) 'FRESH_GUEST_DIRECTORY_REQUIRED'
 $acl=[Security.AccessControl.DirectorySecurity]::new()
 $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
 $acl.SetAccessRuleProtection($true,$false)
 foreach($sid in @('S-1-5-18','S-1-5-32-544')){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($sid),'FullControl','ContainerInherit,ObjectInherit','None','Allow'))}
 if($ReaderSID){$acl.AddAccessRule([Security.AccessControl.FileSystemAccessRule]::new([Security.Principal.SecurityIdentifier]::new($ReaderSID),'ReadAndExecute','ContainerInherit,ObjectInherit','None','Allow'))}
 [IO.Directory]::CreateDirectory($Path,$acl)|Out-Null
 $actual=Get-Acl -LiteralPath $Path
 Require ($actual.AreAccessRulesProtected -and $actual.GetOwner([Security.Principal.SecurityIdentifier]).Value -ceq 'S-1-5-32-544') 'GUEST_PROTECTION_READBACK_FAILED'
}
try{
 Require ([Environment]::Is64BitProcess -and [Environment]::OSVersion.Platform -eq 'Win32NT') 'WINDOWS64_REQUIRED'
 Require ($env:COMPUTERNAME -ceq 'AIBSPROBE01') 'FIXED_NEW_GUEST_NAME_REQUIRED'
 Require ($identity.Name -ieq ($env:COMPUTERNAME+'\aibs_bootstrap') -and $principal.IsInRole('Administrators')) 'NEW_GUEST_BOOTSTRAP_ADMIN_REQUIRED'
 Require ((Get-ItemPropertyValue -LiteralPath 'HKLM:\HARDWARE\DESCRIPTION\System\BIOS' -Name SystemProductName) -ceq 'VirtualBox') 'VIRTUALBOX_REQUIRED'
 $validatedGuest=$true
 Require ([bool](Confirm-SecureBootUEFI)) 'SECURE_BOOT_REQUIRED'
 $tpm=Get-Tpm;Require ($tpm.TpmPresent -and $tpm.TpmEnabled -and $tpm.TpmActivated) 'TPM_REQUIRED'
 Require (@(Get-CimInstance Win32_NetworkAdapter|Where-Object{$_.PhysicalAdapter -and $_.NetEnabled}).Count -eq 0) 'NO_ENABLED_PHYSICAL_GUEST_NIC_REQUIRED'
 Require (-not(Test-Path -LiteralPath $destination)) 'EXISTING_GUEST_DEPLOYMENT_REFUSED'
 Require (-not(Get-LocalUser -Name aibs_vm_worker -ErrorAction SilentlyContinue)) 'EXISTING_GUEST_WORKER_REFUSED'
 Require ((Hash (Join-Path $stage 'DiagnosticProbe.exe')) -ceq $probeHash) 'GUEST_PROBE_BYTES_CHANGED'
 $passwordBytes=[Convert]::FromBase64String([IO.File]::ReadAllText((Join-Path $stage 'worker.b64')))
 $password=[Text.UTF8Encoding]::new($false,$true).GetString($passwordBytes)
 Require ($password.Length -ge 32 -and $password.Length -le 128 -and $password -notmatch '[\r\n\x00]') 'WORKER_PASSWORD_PROFILE'
 $secure=ConvertTo-SecureString -String $password -AsPlainText -Force
 $worker=New-LocalUser -Name aibs_vm_worker -Password $secure -AccountNeverExpires -PasswordNeverExpires -Description 'AI-BS fixed offline diagnostic worker'
 Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $worker -ErrorAction Stop
 Require ($worker.SID.Value -notlike 'S-1-5-21-2133766663-4066672948-2456486318-*') 'HOST_SID_REFUSED'
 Require (@(Get-LocalGroupMember -SID 'S-1-5-32-544'|Where-Object{$_.SID.Value -ceq $worker.SID.Value}).Count -eq 0) 'STANDARD_GUEST_WORKER_REQUIRED'
 Protected-Directory $destination $worker.SID.Value
 Copy-Item -LiteralPath (Join-Path $stage 'DiagnosticProbe.exe') -Destination (Join-Path $destination 'DiagnosticProbe.exe')
 Require ((Hash (Join-Path $destination 'DiagnosticProbe.exe')) -ceq $probeHash) 'DEPLOYMENT_READBACK_FAILED'

 # Search only optical-drive roots supplied by the pinned unattended media.
 $installers=@()
 foreach($drive in @(Get-CimInstance Win32_CDROMDrive)){
  if($drive.Drive -cmatch '^[D-Z]:$'){
   foreach($relative in @('vboxadditions\VBoxWindowsAdditions.exe','VBoxWindowsAdditions.exe')){
    $candidate=Join-Path ($drive.Drive+'\') $relative
    if(Test-Path -LiteralPath $candidate -PathType Leaf){$installers+=,$candidate}
   }
  }
 }
 Require ($installers.Count -eq 1) 'ONE_PINNED_ADDITIONS_MEDIA_REQUIRED'
 $installer=$installers[0]
 Require ((Hash $installer) -ceq '19811a6077fa55f04c24d954c030f71c1b9a18d0bf4812aa4db30fe729f2d2a1') 'ADDITIONS_INSTALLER_BYTES_CHANGED'
 # Fresh offline Windows must not depend on downloading a signing chain.
 # Trust only the two exact current certificates from the pinned Oracle ISO.
 $certDirectory=Join-Path ([IO.Path]::GetDirectoryName($installer)) 'cert'
 foreach($certificate in @(@('vboxsha256.cer','3d4625739e642d50dc8c58157d127509816746e7c6649f529acbc73f5be1d95f','Cert:\LocalMachine\TrustedPublisher'),@('vboxsha256root.cer','552f7bdcf1a7af9e6ce672017f4f12abf77240c78e761ac203d1d9d20ac89988','Cert:\LocalMachine\Root'))){
  $path=Join-Path $certDirectory $certificate[0]
  Require ((Hash $path) -ceq $certificate[1]) 'ADDITIONS_CERTIFICATE_BYTES_CHANGED'
  Import-Certificate -FilePath $path -CertStoreLocation $certificate[2]|Out-Null
 }
 $signature=Get-AuthenticodeSignature -LiteralPath $installer
 Require ($signature.Status -eq 'Valid' -and ($signature.SignerCertificate.Thumbprint -in @('2B1BD188256EB612578949A943DE0DDC52D1DF79', '7E92B66BE51B79D8CE3FF25C15C2DF6AB8C7F2F2'))) 'EXACT_ORACLE_ADDITIONS_SIGNATURE_REQUIRED'
 $process=Start-Process -FilePath $installer -ArgumentList '/S' -PassThru -WindowStyle Hidden
 Require ($process.WaitForExit(600000)) 'ADDITIONS_INSTALL_TIMEOUT'
 Require ($process.ExitCode -in @(0,3010)) 'ADDITIONS_INSTALL_FAILED'
 $service=Get-Service -Name VBoxService -ErrorAction Stop
 if($service.Status -ne 'Running'){Start-Service -Name VBoxService}
 Require ((Get-Service -Name VBoxService).Status -eq 'Running') 'GUEST_CONTROL_SERVICE_NOT_RUNNING'

 # Remove the first-boot elevation path before the worker can run a probe.
 $winlogon='HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
 Set-ItemProperty -LiteralPath $winlogon -Name AutoAdminLogon -Value '0'
 foreach($name in @('DefaultPassword','DefaultUserName','DefaultDomainName','AutoLogonCount','ForceAutoLogon')){
  if((Get-Item -LiteralPath $winlogon).GetValueNames() -contains $name){Remove-ItemProperty -LiteralPath $winlogon -Name $name}
 }
 Disable-LocalUser -Name aibs_bootstrap
 foreach($builtIn in @(Get-LocalUser|Where-Object{$_.SID.Value -match '-500$'})){if($builtIn.Enabled){Disable-LocalUser -SID $builtIn.SID}}
 # Retain setup evidence but remove standard-user visibility of answer files and
 # setup records, which may contain disposable bootstrap account information.
 foreach($directory in @('C:\Windows\Panther','C:\Windows\System32\Sysprep\Panther')){
  if(Test-Path -LiteralPath $directory -PathType Container){
   Admin-Only $directory
   foreach($item in @(Get-ChildItem -LiteralPath $directory -Force -Recurse)){Admin-Only $item.FullName}
  }
 }
 foreach($file in @('C:\Windows\System32\Sysprep\unattend.xml','C:\Windows\System32\Sysprep\autounattend.xml')){if(Test-Path -LiteralPath $file -PathType Leaf){Admin-Only $file}}
 $password=$null;$secure=$null;[Array]::Clear($passwordBytes,0,$passwordBytes.Length)
 $report=[ordered]@{schema_version=1;state='BOOTSTRAPPED_AWAITING_HOST_VERIFICATION';vm_id='e5a2fe34-7b90-460c-83af-903d51b4bb16';guest_machine=$env:COMPUTERNAME;guest_username='aibs_vm_worker';guest_sid=$worker.SID.Value;executable_sha256=$probeHash;bootstrap_disabled=(-not(Get-LocalUser -Name aibs_bootstrap).Enabled);autologon_disabled=((Get-ItemPropertyValue -LiteralPath $winlogon -Name AutoAdminLogon) -ceq '0');setup_records_admin_only=$true;additions_installer_exit_code=$process.ExitCode;additions_signer_thumbprint=$signature.SignerCertificate.Thumbprint;secure_boot=$true;tpm_present=$true;network='none';worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;verification_status='not_run';utc=[DateTime]::UtcNow.ToString('o')}
 [IO.File]::WriteAllText((Join-Path $destination 'bootstrap.json'),($report|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
 Write-Output 'BOOTSTRAPPED_AWAITING_HOST_VERIFICATION'
 & "$env:SystemRoot\System32\shutdown.exe" /s /t 0 /f
 exit 0
}catch{
 # Retain the protected staging files and partial guest deployment for diagnosis.
 $failureType=$_.Exception.GetType().Name
 if($failureType -cnotmatch '^[A-Za-z][A-Za-z0-9]{0,95}$'){$failureType='WITHHELD'}
 $failureCode=if($_.Exception.Message -cmatch '^[A-Z][A-Z0-9_]{0,127}$'){$_.Exception.Message}else{'DETAILS_WITHHELD'}
 $failure=[ordered]@{schema_version=1;state='BOOTSTRAP_FAILED_RETAINED';vm_id='e5a2fe34-7b90-460c-83af-903d51b4bb16';error_code=$failureCode;error_type=$failureType;utc=[DateTime]::UtcNow.ToString('o');execution_authorized=$false;apply_authorized=$false}
 if($validatedGuest){
  foreach($directory in @($stage,$destination)){
   if(Test-Path -LiteralPath $directory -PathType Container){
    try{[IO.File]::WriteAllText((Join-Path $directory 'bootstrap.failure.json'),($failure|ConvertTo-Json -Depth 3),[Text.UTF8Encoding]::new($false))}catch{}
   }
  }
 }
 Write-Output ('BOOTSTRAP_FAILED_'+$failureCode+'_'+$failureType)
 exit 1
}
