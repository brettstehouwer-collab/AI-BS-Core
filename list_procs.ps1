Get-CimInstance Win32_Process | Where-Object { $_.Name -match "python|node|aibs|brain_backend|electron" } | Select-Object ProcessId, CommandLine | Format-Table -AutoSize -Wrap
