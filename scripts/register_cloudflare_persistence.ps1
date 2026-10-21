# C:\AI-BS\scripts\register_cloudflare_persistence.ps1
$taskName = "AI-BS-Publishing-Cloudflare-Tunnel"
$exePath = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$args = "tunnel --config ""C:\Users\footb\.cloudflared\config.yml"" run d1acbd25-06c3-4be0-a7f4-ae3943263aed"

$action = New-ScheduledTaskAction -Execute $exePath -Argument $args
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
Write-Host "Persistence Scheduled Task Registered: $taskName" -ForegroundColor Green
