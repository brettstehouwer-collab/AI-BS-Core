# Host administrator: add only SeBatchLogonRight for the existing standard worker.
[CmdletBinding()]
param([switch]$Grant)
$ErrorActionPreference='Stop'
$sid='S-1-5-21-2133766663-4066672948-2456486318-1005'
$user=Get-CimInstance Win32_UserAccount -Filter "Name='aibs_vm_worker' AND LocalAccount=True"
if($null-eq $user-or $user.SID-cne $sid-or $user.Disabled-or $user.Lockout){throw 'EXISTING_ENABLED_WORKER_ACCOUNT_REQUIRED'}
$source=Join-Path $PSScriptRoot 'WorkerBatchRights.cs'
if(-not('AIBS.WorkerBootstrap.BatchRights'-as [type])){Add-Type -Path $source}
$before=@([AIBS.WorkerBootstrap.BatchRights]::ReadWorker())
$result=[ordered]@{WorkerSID=$sid;Before=$before;After=$before;BatchRightPresent=($before-ccontains 'SeBatchLogonRight');Changed=$false;GrantRequested=[bool]$Grant;PasswordOrAccountChanged=$false;GroupOrFilesystemRightsChanged=$false;OtherAccountRightsModified=$false;SeServiceLogonRightGranted=$false;TaskRegistered=$false}
if($Grant-and -not $result.BatchRightPresent){
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=New-Object Security.Principal.WindowsPrincipal($identity)
 if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'HOST_ADMIN_REQUIRED_FOR_SINGLE_BATCH_RIGHT'}
 $result.After=@([AIBS.WorkerBootstrap.BatchRights]::AddWorkerBatchOnly());$result.Changed=$true;$result.BatchRightPresent=($result.After-ccontains 'SeBatchLogonRight')
}
$result|ConvertTo-Json -Depth 4
