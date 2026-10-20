$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$args = @(
    '--user-data-dir="C:\Users\footb\.cache\chrome-devtools-mcp\chrome-profile"',
    '--profile-directory="Default"',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-blink-features=AutomationControlled'
)
$p = Start-Process -FilePath $chromePath -ArgumentList $args -PassThru
Start-Sleep -Seconds 3
Write-Host "Process ID: $($p.Id), HasExited: $($p.HasExited)"

$procs = Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" | Where-Object { $_.CommandLine -notmatch '--type=' }
foreach ($pr in $procs) {
    Write-Host "PID: $($pr.ProcessId) -> $($pr.CommandLine)"
}
