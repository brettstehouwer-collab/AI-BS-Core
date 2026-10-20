# AI-BS Clore.ai Hosting Agent & WSL2 Persistent Keepalive Watchdog
# Ensures WSL2 Ubuntu instance and clore-hosting.service remain active 24/7 without idle power-downs.

$ErrorActionPreference = "SilentlyContinue"

Write-Host "[AI-BS Clore Watchdog] Checking WSL2 keepalive background process..." -ForegroundColor Cyan

# Check if an active wsl.exe process exists in Windows
$wslProcesses = Get-Process -Name "wsl" -ErrorAction SilentlyContinue

$keepaliveRunning = $false
if ($wslProcesses) {
    # Check inside WSL if sleep infinity is running
    $sleepPid = wsl.exe -d Ubuntu -u root pgrep -f "sleep infinity" 2>$null
    if ($sleepPid) {
        $keepaliveRunning = $true
        Write-Host "[AI-BS Clore Watchdog] Active WSL keepalive detected (WSL PIDs: $($sleepPid -join ', '))." -ForegroundColor Green
    }
}

if (-not $keepaliveRunning) {
    Write-Host "[AI-BS Clore Watchdog] No active WSL keepalive session found. Spawning background daemon..." -ForegroundColor Yellow
    Start-Process -FilePath "wsl.exe" -ArgumentList "-d Ubuntu -u root -- sleep infinity" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# Verify clore-hosting.service inside WSL
$status = (wsl.exe -d Ubuntu -u root systemctl is-active clore-hosting.service 2>$null).Trim()
if ($status -eq "active") {
    Write-Host "[AI-BS Clore Watchdog] clore-hosting.service is ACTIVE." -ForegroundColor Green
} else {
    Write-Host "[AI-BS Clore Watchdog] clore-hosting.service is '$status'. Starting service..." -ForegroundColor Yellow
    wsl.exe -d Ubuntu -u root systemctl start clore-hosting.service
    Start-Sleep -Seconds 2
    $newStatus = (wsl.exe -d Ubuntu -u root systemctl is-active clore-hosting.service 2>$null).Trim()
    Write-Host "[AI-BS Clore Watchdog] clore-hosting.service status is now: $newStatus" -ForegroundColor Green
}

# Check docker status
$containers = wsl.exe -d Ubuntu -u root docker ps --format "{{.Names}} ({{.Status}})" 2>$null
if ($containers) {
    Write-Host "[AI-BS Clore Watchdog] Active Containers:" -ForegroundColor Cyan
    $containers | ForEach-Object { Write-Host "  -> $_" -ForegroundColor Gray }
}
