$procs = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -match 'pyppeteer_env' -or $_.Name -match 'aibs_engine.exe|ollama.exe' -or $_.CommandLine -match 'AI_BS_Backend|daemon' }
foreach ($p in $procs) {
    if ($p.Name -ne 'Antigravity IDE.exe' -and $p.CommandLine -notmatch 'mcp_proxy_bundle') {
        Write-Host "Killing PID: $($p.ProcessId) - $($p.Name)"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Write-Host "Memory flush complete."
