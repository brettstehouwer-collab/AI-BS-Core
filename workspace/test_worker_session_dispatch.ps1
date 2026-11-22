# One-shot, read-only task using an already authenticated interactive worker session.
# No password, elevated worker, automatic trigger, VM start or account-policy change.
$ErrorActionPreference='Stop'
$workerSID='S-1-5-21-2133766663-4066672948-2456486318-1005'
$scriptPath='C:\AI-BS\isolated_workers\windows\control\Read-CurrentVMState.ps1'
$expected='4E89B6E16F656AC82B975E14C12C5490FC5DED7603EC1D033F4D4CB77935E3C4'
if ((Get-FileHash -LiteralPath $scriptPath -Algorithm SHA256).Hash -ne $expected) { throw 'Worker inspection script changed.' }
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Task registration requires the authorized administrator.' }
$name='AIBS-VM-ReadOnly-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
$folder=Join-Path 'C:\AI-BS\snapshots' $name
$null=New-Item -ItemType Directory -Path $folder
$before=Get-LocalGroupMember -Group 'Administrators' | Select-Object -ExpandProperty SID | ForEach-Object Value
if ($before -contains $workerSID) { throw 'Worker unexpectedly has administrator membership.' }
$action=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $scriptPath" -WorkingDirectory 'C:\AI-BS\isolated_workers\windows\control'
$taskPrincipal=New-ScheduledTaskPrincipal -UserId $workerSID -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -Hidden
$task=New-ScheduledTask -Action $action -Principal $taskPrincipal -Settings $settings -Description 'One-shot read-only AI-BS VM state inspection, existing standard worker interactive token only; no stored credential and no trigger.'
$registered=Register-ScheduledTask -TaskName $name -InputObject $task
$xml=Export-ScheduledTask -TaskName $name
[IO.File]::WriteAllText((Join-Path $folder 'registered_task.xml'),$xml,(New-Object Text.UTF8Encoding($false)))
[ordered]@{TaskName=$name;TaskPath='\';RegisteredUTC=[DateTime]::UtcNow.ToString('o');WorkerSID=$workerSID;LogonType='InteractiveToken';RunLevel='Limited';PasswordStored=$false;Triggers=0;ScriptSHA256=$expected;ScriptPath=$scriptPath;Scope='Two read-only VBoxManage queries; no VM/account/policy mutation.'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $folder 'registration.json') -Encoding UTF8
Start-ScheduledTask -TaskName $name
$observed=Get-ScheduledTask -TaskName $name
$info=Get-ScheduledTaskInfo -TaskName $name
[ordered]@{TaskName=$name;State=[string]$observed.State;LastTaskResult=$info.LastTaskResult;Snapshot=$folder} | ConvertTo-Json
