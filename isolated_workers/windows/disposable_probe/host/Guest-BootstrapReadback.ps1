# Fixed trusted infrastructure observation, passed as data to the NEW guest only.
# Never invoke this entry on the host. It does not launch the diagnostic binary.
[CmdletBinding()]param([Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')][string]$Challenge)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
function Require([bool]$Value,[string]$Code){if(-not $Value){throw [InvalidOperationException]::new($Code)}}
Require ($env:COMPUTERNAME -ceq 'AIBSPROBE01' -and [Environment]::Is64BitProcess) 'NEW_GUEST_REQUIRED'
Require ((Get-ItemPropertyValue -LiteralPath 'HKLM:\HARDWARE\DESCRIPTION\System\BIOS' -Name SystemProductName) -ceq 'VirtualBox') 'VIRTUALBOX_REQUIRED'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$groups=@($identity.Groups|ForEach-Object Value)
Require ($identity.Name -ieq 'AIBSPROBE01\aibs_vm_worker' -and $identity.User.Value -notlike 'S-1-5-21-2133766663-4066672948-2456486318-*') 'SEPARATE_STANDARD_GUEST_REQUIRED'
Require ('S-1-5-32-544' -cnotin $groups -and 'S-1-5-114' -cnotin $groups -and -not([Security.Principal.WindowsPrincipal]::new($identity).IsInRole('Administrators'))) 'ADMINISTRATOR_TOKEN_REFUSED'
Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Principal;
using Microsoft.Win32.SafeHandles;
public static class AIBSBootstrapReadback {
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern SafeFileHandle CreateFile(string p,uint a,uint s,IntPtr sa,uint d,uint f,IntPtr t);
 [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr p,uint a,out SafeAccessTokenHandle t);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool GetTokenInformation(SafeAccessTokenHandle t,int k,IntPtr b,int l,out int n);
 public static int OpenError(string p,uint a){using(var h=CreateFile(p,a,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero)){return h.IsInvalid?Marshal.GetLastWin32Error():0;}}
 public static string Integrity(){SafeAccessTokenHandle t;if(!OpenProcessToken(GetCurrentProcess(),8,out t))throw new Win32Exception();using(t){int n;GetTokenInformation(t,25,IntPtr.Zero,0,out n);IntPtr p=Marshal.AllocHGlobal(n);try{if(!GetTokenInformation(t,25,p,n,out n))throw new Win32Exception();return new SecurityIdentifier(Marshal.ReadIntPtr(p)).Value;}finally{Marshal.FreeHGlobal(p);}}}
}
'@
$integrity=[AIBSBootstrapReadback]::Integrity()
Require ($integrity -ceq 'S-1-16-8192') 'MEDIUM_GUEST_TOKEN_REQUIRED'
$probe='C:\AIBSProbe\DiagnosticProbe.exe'
$probeItem=Get-Item -LiteralPath $probe -Force
Require (-not($probeItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'GUEST_REPARSE_PROBE_REFUSED'
$probeHash=(Get-FileHash -LiteralPath $probe -Algorithm SHA256).Hash.ToLowerInvariant()
Require ($probeHash -ceq '82c6b2510807246aaa99668bb4416ec99c4ce3ecbc7d007cfe4165d14aaf1531') 'EXACT_PROBE_BYTES_REQUIRED'
$bootstrapPath='C:\AIBSProbe\bootstrap.json'
$bootstrapBytes=[IO.File]::ReadAllBytes($bootstrapPath)
Require ($bootstrapBytes.Length -gt 0 -and $bootstrapBytes.Length -le 16384) 'BOOTSTRAP_REPORT_BOUND'
$bootstrapRaw=[Text.UTF8Encoding]::new($false,$true).GetString($bootstrapBytes)
$bootstrap=$bootstrapRaw|ConvertFrom-Json
Require ($bootstrap.state -ceq 'BOOTSTRAPPED_AWAITING_HOST_VERIFICATION' -and $bootstrap.guest_sid -ceq $identity.User.Value -and $bootstrap.executable_sha256 -ceq $probeHash) 'BOOTSTRAP_IDENTITY_MISMATCH'
$checks=[Collections.Generic.List[object]]::new()
$runtimePaths=@('C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','C:\Windows\Microsoft.NET\Framework64\v4.0.30319\clr.dll','C:\Windows\Microsoft.NET\Framework64\v4.0.30319\mscorlib.dll')
$runtimeHashes=@()
foreach($path in $runtimePaths){
 $item=Get-Item -LiteralPath $path -Force
 Require (-not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'GUEST_RUNTIME_REPARSE_REFUSED'
 $runtimeHashes+=,[ordered]@{path=$path;length=$item.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$fileTargets=@($probe,$bootstrapPath)+$runtimePaths
$directoryTargets=@('C:\AIBSProbe','C:\Windows\System32\WindowsPowerShell\v1.0','C:\Windows\System32\WindowsPowerShell','C:\Windows\System32','C:\Windows','C:\Windows\Microsoft.NET\Framework64\v4.0.30319','C:\Windows\Microsoft.NET\Framework64','C:\Windows\Microsoft.NET')
foreach($path in $fileTargets+$directoryTargets){
 $item=Get-Item -LiteralPath $path -Force
 Require (-not($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) 'GUEST_PROTECTED_PATH_REPARSE'
 $rights=if($item.PSIsContainer){@(@('create_file',2),@('create_directory',4),@('delete_child',64),@('delete',65536),@('write_dac',262144),@('write_owner',524288))}else{@(@('write_data',2),@('append_data',4),@('delete',65536),@('write_dac',262144),@('write_owner',524288))}
 foreach($right in $rights){
  $errorCode=[AIBSBootstrapReadback]::OpenError($path,[uint32]$right[1])
  $checks.Add([ordered]@{path=$path;operation=$right[0];win32_error=$errorCode;denied=($errorCode -eq 5)})
 }
}
# A volume cannot be renamed/deleted. Test only relevant child replacement/DACL rights.
foreach($right in @(@('delete_child',64),@('write_dac',262144),@('write_owner',524288))){
 $code=[AIBSBootstrapReadback]::OpenError('C:\',[uint32]$right[1]);$checks.Add([ordered]@{path='C:\';operation=$right[0];win32_error=$code;denied=($code -eq 5)})
}
foreach($path in @('C:\AIBSBootstrap\worker.b64','C:\AIBSBootstrap','C:\Windows\Panther')){
 $code=[AIBSBootstrapReadback]::OpenError($path,1);$checks.Add([ordered]@{path=$path;operation='read_secret_or_list_setup';win32_error=$code;denied=($code -eq 5)})
}
$failed=@($checks|Where-Object{-not $_.denied})
$report=[ordered]@{schema_version=1;purpose='bootstrap_readback_snapshot_v1';state=$(if($failed.Count -eq 0){'OBSERVED_PROTECTED'}else{'PROTECTION_FAILED'});challenge=$Challenge;vm_id='e5a2fe34-7b90-460c-83af-903d51b4bb16';guest_machine=$env:COMPUTERNAME;guest_username='aibs_vm_worker';guest_sid=$identity.User.Value;integrity_sid=$integrity;administrator_group_present=$false;guest_groups=$groups;executable_sha256=$probeHash;executable_length=$probeItem.Length;bootstrap_sha256=(Get-FileHash -LiteralPath $bootstrapPath -Algorithm SHA256).Hash.ToLowerInvariant();bootstrap=$bootstrap;runtime_hashes=$runtimeHashes;access_checks=@($checks);failed_access_checks=$failed.Count;probe_executed=$false;worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;utc=[DateTime]::UtcNow.ToString('o')}
[Console]::Out.Write(($report|ConvertTo-Json -Depth 9 -Compress))
if($failed.Count -gt 0){exit 2}
