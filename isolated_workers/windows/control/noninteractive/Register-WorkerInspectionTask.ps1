# Run once from the existing authenticated standard-worker PowerShell.
# Registers only a fixed, demand-only S4U metadata inspector. No VM start or queue.
[CmdletBinding()]
param([switch]$Register,[switch]$RunOnce,[switch]$Describe)
$ErrorActionPreference='Stop'
$worker='S-1-5-21-2133766663-4066672948-2456486318-1005'
if($Describe){. (Join-Path $PSScriptRoot 'WorkerInspectionPolicy.ps1');Get-WorkerInspectionSpec|ConvertTo-Json -Depth 4;exit 0}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent();$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if($identity.User.Value-cne $worker-or $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)-or -not [Environment]::Is64BitProcess){Write-Host 'REFUSED: existing x64 nonadministrator worker context required; no task change.';exit 2}
if(-not $Register){Write-Host 'Use -Describe to inspect, or -Register [-RunOnce] from the worker context.';exit 0}
$groups=& 'C:\Windows\System32\whoami.exe' /groups /fo csv /nh
if($LASTEXITCODE-ne 0){throw 'WORKER_INTEGRITY_QUERY_FAILED'}
. (Join-Path $PSScriptRoot 'WorkerInspectionPolicy.ps1')
$spec=Get-WorkerInspectionSpec
$null=Assert-WorkerInspectionConfiguration $spec.ConfigurationPath $spec.ConfigurationSHA256
$entry='C:\AI-BS\isolated_workers\windows\control\Inspect-CurrentWorkerDesktopV2.ps1'
if((Get-FileHash -LiteralPath $entry -Algorithm SHA256).Hash-cne $spec.EntrySHA256){throw 'INSPECTION_ENTRY_PIN_CHANGED'}
$tokens=$null;$errors=$null;$tree=[Management.Automation.Language.Parser]::ParseFile($entry,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'INSPECTION_ENTRY_PARSE_FAILED'}
$medium=@($tree.FindAll({param($n)$n-is [Management.Automation.Language.FunctionDefinitionAst]-and $n.Name-ceq 'Assert-InspectionMediumCsv'},$true))
if($medium.Count-ne 1){throw 'ONE_PINNED_MEDIUM_CHECK_REQUIRED'}
. ([ScriptBlock]::Create($medium[0].Extent.Text));$null=Assert-InspectionMediumCsv $groups
function Write-WorkerBootstrapJson([string]$Path,$Value){
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(($Value|ConvertTo-Json -Depth 8))
    if($bytes.Length-gt 65536){throw 'BOOTSTRAP_RECEIPT_BOUND'}
    $f=New-Object IO.FileStream($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}
}
function Read-WorkerTaskSpec($Task){
    $d=$Task.Definition;$action=if($d.Actions.Count-eq 1){$d.Actions.Item(1)}else{$null}
    return [pscustomobject]@{TaskName=$Task.Name;UserId=$d.Principal.UserId;LogonType=[int]$d.Principal.LogonType;RunLevel=[int]$d.Principal.RunLevel;ActionCount=[int]$d.Actions.Count;ActionType=if($null-ne $action){[int]$action.Type}else{-1};Path=if($null-ne $action){$action.Path}else{''};Arguments=if($null-ne $action){$action.Arguments}else{''};WorkingDirectory=if($null-ne $action){$action.WorkingDirectory}else{''};TriggerCount=[int]$d.Triggers.Count;RestartCount=[int]$d.Settings.RestartCount;MultipleInstances=[int]$d.Settings.MultipleInstances;ExecutionTimeLimit=$d.Settings.ExecutionTimeLimit}
}
$runtime='C:\AI-BS\isolated_workers\windows\runtime\noninteractive_inspection_v2'
if(-not(Test-Path -LiteralPath $runtime)){New-Item -ItemType Directory -Path $runtime -ErrorAction Stop|Out-Null}
$node=Get-Item -LiteralPath $runtime
while($null-ne $node){if($node.Attributes-band [IO.FileAttributes]::ReparsePoint){throw 'LINKED_BOOTSTRAP_PATH_REFUSED'};$node=if($node-is [IO.FileInfo]){$node.Directory}else{$node.Parent}}
$allowed=@($worker,'S-1-5-18','S-1-5-32-544')
foreach($rule in (Get-Acl -LiteralPath $runtime).Access){if($rule.AccessControlType-eq 'Allow'-and $allowed-cnotcontains $rule.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value){throw 'PRIVATE_BOOTSTRAP_ACL_REQUIRED'}}
$previous=@(Get-ChildItem -LiteralPath $runtime -Directory -Force)
if($previous.Count-gt 32){throw 'BOOTSTRAP_HISTORY_BOUND'}
foreach($prior in $previous){if(-not(Test-Path -LiteralPath (Join-Path $prior.FullName 'installation.json'))-or (Test-Path -LiteralPath (Join-Path $prior.FullName 'run_request.json'))){throw 'PRIOR_BOOTSTRAP_REQUIRES_RECONCILIATION_NO_REPLAY'}}
$out=Join-Path $runtime ('bootstrap_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'_'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out -ErrorAction Stop|Out-Null
$report=[ordered]@{State='REGISTER_INTENT';WorkerSID=$worker;TaskName=$spec.TaskName;S4U=$true;RunLevel='Limited';Triggers=0;RestartCount=0;EntrySHA256=$spec.EntrySHA256;PasswordProvidedOrStored=$false;TaskAuthority=$false;ProviderAccepted=$false;VMStartRequested=$false;UTC=[DateTime]::UtcNow.ToString('o')}
Write-WorkerBootstrapJson (Join-Path $out 'intent.json') $report
try{
    $service=New-Object -ComObject 'Schedule.Service';$service.Connect();$folder=$service.GetFolder('\');$task=$null
    try{$task=$folder.GetTask($spec.TaskName)}catch{
        $e=$_.Exception;while($null-ne $e.InnerException){$e=$e.InnerException}
        if($e.HResult-notin @(-2147024894,-2147216625)){throw}
    }
    if($null-eq $task){
        $d=$service.NewTask(0);$d.RegistrationInfo.Description='AI-BS v2 fixed read-only VM metadata inspection; not an execution worker.'
        $d.Principal.UserId=$worker;$d.Principal.LogonType=2;$d.Principal.RunLevel=0
        $d.Settings.Enabled=$true;$d.Settings.Hidden=$true;$d.Settings.AllowDemandStart=$true;$d.Settings.StartWhenAvailable=$false
        $d.Settings.DisallowStartIfOnBatteries=$false;$d.Settings.StopIfGoingOnBatteries=$false;$d.Settings.WakeToRun=$false
        $d.Settings.MultipleInstances=2;$d.Settings.RestartCount=0;$d.Settings.ExecutionTimeLimit='PT3M'
        $action=$d.Actions.Create(0);$action.Path=$spec.Path;$action.Arguments=$spec.Arguments;$action.WorkingDirectory=$spec.WorkingDirectory
        # Own-account S4U registration: no password, no elevation, no startup trigger.
        $task=$folder.RegisterTaskDefinition($spec.TaskName,$d,2,$worker,$null,2,$null)
    }
    $snapshot=Read-WorkerTaskSpec $task;$null=Assert-WorkerInspectionSpec $snapshot
    $report.State='REGISTERED_DEMAND_ONLY';$report['Definition']=$snapshot
    Write-WorkerBootstrapJson (Join-Path $out 'installation.json') $report
    Write-Host ('Registered/verified limited S4U task '+$spec.TaskName+'. No startup trigger or automatic retry.')
    if($RunOnce){
        if([int]$task.State-in @(2,4)){throw 'EXISTING_INSPECTION_TASK_ACTIVE_NO_REPLAY'}
        if((Get-FileHash -LiteralPath $entry -Algorithm SHA256).Hash-cne $spec.EntrySHA256){throw 'ENTRY_CHANGED_BEFORE_RUN'}
        $null=Assert-WorkerInspectionConfiguration $spec.ConfigurationPath $spec.ConfigurationSHA256
        Write-WorkerBootstrapJson (Join-Path $out 'run_request.json') @{State='RUN_INTENT_NO_REPLAY';UTC=[DateTime]::UtcNow.ToString('o');TaskName=$spec.TaskName;TaskAuthority=$false}
        $instance=$task.Run($null)
        Write-WorkerBootstrapJson (Join-Path $out 'run_submitted.json') @{State='SUBMITTED_NOT_VERIFIED';InstanceGuid=[string]$instance.InstanceGuid;UTC=[DateTime]::UtcNow.ToString('o');TaskAuthority=$false}
        Write-Host 'Read-only inspection submitted. Completion, licensing and execution authority are not yet verified.'
    }
    Write-Host ('Private receipts: '+$out)
}catch{
    Write-WorkerBootstrapJson (Join-Path $out 'failure.json') @{State='FAILED_REVIEW_REQUIRED';ErrorType=$_.Exception.GetType().FullName;HResult=$_.Exception.HResult;TaskAuthority=$false;UTC=[DateTime]::UtcNow.ToString('o')}
    Write-Host ('Bootstrap stopped; preserve '+$out+' for review. No automatic retry.');exit 3
}
