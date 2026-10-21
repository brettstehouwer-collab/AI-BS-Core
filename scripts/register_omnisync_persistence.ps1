# C:\AI-BS\scripts\register_omnisync_persistence.ps1
$taskName = "AI-BS-Omni-Sync-Sentinel"
$pythonPath = "C:\Users\footb\AppData\Local\Programs\Python\Python312\pythonw.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = (Get-Command python.exe).Source
}
$scriptPath = "C:\AI-BS\scripts\omni_sync_daemon.py"

$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`"" -WorkingDirectory "C:\AI-BS"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
Write-Host "Persistence Scheduled Task Registered: $taskName" -ForegroundColor Green
