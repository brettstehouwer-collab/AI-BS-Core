# Fixed noninteractive standard-worker diagnostic; never starts a VM or project.
$ErrorActionPreference='Stop'
$env:PSModulePath=(Join-Path $PSHOME 'Modules')+';'+(Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\Modules')
$expected='S-1-5-21-2133766663-4066672948-2456486318-1005'
$run='37c20e5e6fea43f5bbbf74ce4c48def5'
$root='C:\ProgramData\AI-BS-WorkerControl'
$reportPath=Join-Path $root ('incoming_outputs\worker_prerequisites_'+$run+'.json')
$result=[ordered]@{schema_version=1;run_id=$run;state='FAILED';started_utc=[DateTime]::UtcNow.ToString('o');worker_sid=$null;medium_integrity=$false;administrator_group_present=$true;administrator_token=$true;x64=[Environment]::Is64BitProcess;dangerous_privileges=@();checks=@();worker_admitted=$false;execution_authorized=$false;apply_authorized=$false;verification_status='not_run';vm_command_issued=$false;project_executed=$false}
try{
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=New-Object Security.Principal.WindowsPrincipal($identity)
 $result.worker_sid=$identity.User.Value;$result.administrator_token=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
 if($result.worker_sid-cne $expected-or $result.administrator_token-or -not $result.x64){throw 'EXACT_NONADMIN_X64_WORKER_REQUIRED'}
 $groupLines=@(& C:\Windows\System32\whoami.exe /groups /fo csv /nh)
 if($LASTEXITCODE-ne 0-or $groupLines.Count-gt 256){throw 'GROUP_METADATA_FAILED'}
 $groups=@($groupLines|ConvertFrom-Csv -Header Name,Type,SID,Attributes)
 $labels=@($groups|Where-Object {$_.SID-cmatch '^S-1-16-[0-9]+$'})
 $result.medium_integrity=($labels.Count-eq 1-and $labels[0].SID-ceq 'S-1-16-8192')
 $result.administrator_group_present=[bool](@($groups|Where-Object {$_.SID-in @('S-1-5-32-544','S-1-5-114')}).Count)
 if(-not $result.medium_integrity-or $result.administrator_group_present){throw 'STANDARD_MEDIUM_WORKER_REQUIRED'}
 $privilegeLines=@(& C:\Windows\System32\whoami.exe /priv /fo csv /nh)
 if($LASTEXITCODE-ne 0-or $privilegeLines.Count-gt 128){throw 'PRIVILEGE_METADATA_FAILED'}
 $privileges=@($privilegeLines|ConvertFrom-Csv -Header Name,Description,State)
 $danger=@('SeTcbPrivilege','SeDebugPrivilege','SeImpersonatePrivilege','SeAssignPrimaryTokenPrivilege','SeTakeOwnershipPrivilege','SeRestorePrivilege','SeBackupPrivilege','SeCreateTokenPrivilege')
 $result.dangerous_privileges=@($privileges|Where-Object {$_.Name-in $danger}|ForEach-Object {$_.Name})
 if($result.dangerous_privileges.Count){throw 'UNEXPECTED_WORKER_PRIVILEGE'}
 Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
namespace AIBS.WorkerPrereq119 {
 public static class AccessProbe {
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
  static extern SafeFileHandle CreateFileW(string p,uint a,uint s,IntPtr d,uint c,uint f,IntPtr t);
  public static int Request(string path,uint access) {
   const string root=@"C:\ProgramData\AI-BS-WorkerControl";
   if(path!=root&&!path.StartsWith(root+"\\",StringComparison.Ordinal))throw new IOException("PROBE_SCOPE_REFUSED");
   if(Path.GetFullPath(path)!=path)throw new IOException("PROBE_CANONICAL_PATH_REQUIRED");
   // OPEN_EXISTING, BACKUP_SEMANTICS|OPEN_REPARSE_POINT; no delete-on-close.
   using(SafeFileHandle h=CreateFileW(path,access,7,IntPtr.Zero,3,0x02200000,IntPtr.Zero)) {
    return h.IsInvalid?Marshal.GetLastWin32Error():0;
   }
  }
 }
}
'@
 $canary=Join-Path $root ('incoming_outputs\worker_canary_'+$run+'.txt')
 $bytes=[Text.Encoding]::UTF8.GetBytes('AI-BS synthetic worker access canary')
 $stream=[IO.File]::Open($canary,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 $owner=(Get-Acl -LiteralPath $canary).GetOwner([Security.Principal.SecurityIdentifier]).Value
 if($owner-cne $expected){throw 'CANARY_OWNER_MISMATCH'}
 $cases=@(
  @('deployment_write_denied',(Join-Path $root 'deployment'),[uint32]1073741824,5),
  @('receipt_write_denied',(Join-Path $root 'receipts'),[uint32]1073741824,5),
  @('output_root_delete_denied',(Join-Path $root 'incoming_outputs'),[uint32]65536,5),
  @('output_root_dacl_change_denied',(Join-Path $root 'incoming_outputs'),[uint32]262144,5),
  @('owned_canary_dacl_change_denied',$canary,[uint32]262144,5),
  @('owned_canary_write_allowed',$canary,[uint32]1073741824,0),
  @('protected_review_read_allowed',(Join-Path $root 'deployment\review_candidate\policy.review.json'),[uint32]2147483648,0)
 )
 foreach($case in $cases){$code=[AIBS.WorkerPrereq119.AccessProbe]::Request($case[1],$case[2]);$result.checks+=,[ordered]@{name=$case[0];win32_result=$code;expected=$case[3];passed=($code-eq $case[3])}}
 if(@($result.checks|Where-Object {-not $_.passed}).Count){throw 'ACCESS_BOUNDARY_CHECK_FAILED'}
 $process=[Diagnostics.Process]::GetCurrentProcess();$result['process_id']=$process.Id;$result['process_started_utc']=$process.StartTime.ToUniversalTime().ToString('o');$result['session_id']=$process.SessionId
 $result.state='STANDARD_WORKER_PREREQUISITES_OBSERVED'
}catch{$result['error_type']=$_.Exception.GetType().FullName;$result['error_code']=if($_.Exception.Message-cmatch '^[A-Z0-9_]+$'){$_.Exception.Message}else{'WORKER_PREREQUISITES_FAILED'}}
$result['completed_utc']=[DateTime]::UtcNow.ToString('o')
$data=[Text.Encoding]::UTF8.GetBytes(($result|ConvertTo-Json -Depth 8))
if($data.Length-gt 65536){throw 'REPORT_BOUND'}
$file=[IO.File]::Open($reportPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$file.Write($data,0,$data.Length);$file.Flush($true)}finally{$file.Dispose()}
# Allow the independent host observer to match the live PID/owner to this run.
Start-Sleep -Seconds 4
if($result.state-cne 'STANDARD_WORKER_PREREQUISITES_OBSERVED'){exit 2}
exit 0
