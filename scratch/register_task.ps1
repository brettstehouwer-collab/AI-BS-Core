$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument '/c "C:\AI-BS\miners\apply_gpu_persistence.bat"'
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
$TriggerLogon = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "AI-BS-GPU-Hardware-Persistence" -Action $Action -Trigger @($TriggerStartup, $TriggerLogon) -Principal $Principal -Force
Get-ScheduledTask -TaskName "AI-BS-GPU-Hardware-Persistence" | Format-List TaskName, State, Author
