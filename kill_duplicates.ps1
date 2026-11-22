$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.ExecutablePath -match 'Python312' -and $_.CommandLine -match 'AI-BS' }
foreach ($p in $procs) {
    Write-Host "Killing PID: $($p.ProcessId) - $($p.CommandLine)"
    Stop-Process -Id $p.ProcessId -Force
}
Write-Host "Done killing duplicates."
