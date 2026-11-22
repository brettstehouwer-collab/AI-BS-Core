$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'WorkerInspectionPolicy.ps1')
$spec=Get-WorkerInspectionSpec;$null=Assert-WorkerInspectionSpec $spec
$passed=1
foreach($case in @(
    @('UserId','S-1-5-18'),@('LogonType',1),@('RunLevel',1),@('ActionCount',2),@('ActionType',5),
    @('Path','C:\unexpected.exe'),@('Arguments','-Command unexpected'),@('WorkingDirectory','C:\'),
    @('TriggerCount',1),@('RestartCount',3),@('MultipleInstances',0),@('ExecutionTimeLimit','PT0S')
)){
    $bad=$spec|Select-Object *;$bad.($case[0])=$case[1];$denied=$false
    try{$null=Assert-WorkerInspectionSpec $bad}catch{$denied=$true}
    if(-not $denied){throw ('UNSAFE_TASK_ACCEPTED_'+$case[0])};$passed++
}
$denied=$false;try{$null=Assert-WorkerInspectionSpec $null}catch{$denied=$true}
if(-not $denied){throw 'MISSING_TASK_ACCEPTED'};$passed++
Write-Output ('RESULT passed='+$passed+'; pure task-policy fixtures only; no task registration or execution.')
