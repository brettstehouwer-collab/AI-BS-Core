# Actual standard-account access-open checks. No file contents or ACLs are changed.
$ErrorActionPreference='Stop'
$root='C:\ProgramData\AI-BS-WorkerControl\disposable_probe_v1'
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if($identity.User.Value -cne 'S-1-5-21-2133766663-4066672948-2456486318-1006' -or
   @($identity.Groups|ForEach-Object Value) -contains 'S-1-5-32-544'){throw 'EXACT_STANDARD_HOST_REQUIRED'}
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ProbeAccess127 {
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern IntPtr CreateFileW(string p,uint a,uint s,IntPtr q,uint d,uint f,IntPtr t);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
 public static int Open(string p,uint a){
   IntPtr h=CreateFileW(p,a,7,IntPtr.Zero,3,0x02000000,IntPtr.Zero);
   if(h==new IntPtr(-1))return Marshal.GetLastWin32Error();
   CloseHandle(h);return 0;
 }
}
'@
$results=[Collections.Generic.List[object]]::new()
function Check([string]$Path,[uint32]$Access,[bool]$Allowed,[string]$Label){
 $errorCode=[ProbeAccess127]::Open($Path,$Access)
 $passed=if($Allowed){$errorCode -eq 0}else{$errorCode -eq 5}
 $results.Add([ordered]@{path=$Path;access=('0x{0:X}' -f $Access);expected_allowed=$Allowed;win32=$errorCode;passed=$passed;label=$Label})
}
foreach($relative in @('deployment\pwsh\pwsh.exe','deployment\DiagnosticProbe.exe','policy\provisioning.json','identity\runtime_manifest.json','credentials\guest.txt')){
 $path=Join-Path $root $relative
 Check $path 2147483648 $true 'readable_fixed_input'
 foreach($right in @(2,0x10000,0x40000,0x80000)){Check $path $right $false 'protected_input_write_delete_owner_dacl'}
}
foreach($path in @($root,(Join-Path $root 'deployment'),(Join-Path $root 'deployment\pwsh'),(Join-Path $root 'policy'),(Join-Path $root 'requests'),(Join-Path $root 'identity'),(Join-Path $root 'credentials'))){
 foreach($right in @(2,0x40,0x10000,0x40000,0x80000)){Check $path $right $false 'protected_directory'}
}
foreach($path in @('C:\','C:\ProgramData','C:\ProgramData\AI-BS-WorkerControl','E:\','E:\AI-BS-DisposableProbe-v1','C:\Program Files','C:\Program Files\Oracle','C:\Program Files\Oracle\VirtualBox')){
 # Filesystem volume roots cannot be renamed/unlinked as ordinary directories.
 # DELETE_CHILD remains relevant because it can replace the protected child root.
 $rights=if($path -cin @('C:\','E:\')){@(0x40,0x40000,0x80000)}else{@(0x40,0x10000,0x40000,0x80000)}
 foreach($right in $rights){Check $path $right $false 'ancestor_replacement_protection'}
}
Check 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' 2147483648 $true 'hypervisor_read'
foreach($right in @(2,0x10000,0x40000,0x80000)){Check 'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe' $right $false 'hypervisor_protection'}
foreach($relative in @('private\receipt.key','private\host_credential.dpapi')){Check (Join-Path $root $relative) 2147483648 $false 'controller_secret_inaccessible'}
$report=[ordered]@{schema_version=1;utc=[DateTime]::UtcNow.ToString('o');sid=$identity.User.Value;administrator_group_present=$false;checks=$results.ToArray();passed=@($results|Where-Object passed).Count;failed=@($results|Where-Object {-not $_.passed}).Count;candidate_execution=$false}
$json=$report|ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $root 'worker_outputs\launcher_access_checks.json'),$json,[Text.UTF8Encoding]::new($false))
$json
if($report.failed){exit 2}
