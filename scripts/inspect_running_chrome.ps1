$procs = Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -notmatch '--type=' }
Write-Host "Running Root Chrome Processes: $($procs.Count)"
foreach ($p in $procs) {
    Write-Host "PID: $($p.ProcessId)"
    Write-Host "CommandLine: $($p.CommandLine)"
    Write-Host "----------------------------------"
}
