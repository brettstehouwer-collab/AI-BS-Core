<#
.SYNOPSIS
Sets the system power plan to High Performance and prevents the computer from sleeping or turning off the screen.
#>

Write-Host "===================================================" -ForegroundColor Green
Write-Host "       AI-BS MAX PERFORMANCE MODE ACTIVATED        " -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host ""

# 1. Switch to High Performance Power Plan
$highPerfGuid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
Write-Host "[1/2] Switching to High Performance Power Plan..." -ForegroundColor Cyan
powercfg -setactive $highPerfGuid
if ($?) {
    Write-Host "  -> Power plan activated." -ForegroundColor Green
} else {
    Write-Host "  -> Failed to change power plan or it is already active." -ForegroundColor Yellow
}

# 2. Prevent Sleep and Screen Off using Windows API
Write-Host "[2/2] Injecting Anti-Sleep API hooks..." -ForegroundColor Cyan

$signature = @"
using System;
using System.Runtime.InteropServices;
public class Awake {
    [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@

try {
    Add-Type -TypeDefinition $signature -ErrorAction SilentlyContinue
} catch {
    # Type might already be added if run multiple times in same session
}

# ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001) | ES_DISPLAY_REQUIRED (0x00000002)
$ES_CONTINUOUS       = 0x80000000
$ES_SYSTEM_REQUIRED  = 0x00000001
$ES_DISPLAY_REQUIRED = 0x00000002
$flags = $ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_DISPLAY_REQUIRED

$result = [Awake]::SetThreadExecutionState($flags)

if ($result -ne 0) {
    Write-Host "  -> System sleep and display timeout are now DISABLED." -ForegroundColor Green
} else {
    Write-Host "  -> Failed to inject anti-sleep hooks." -ForegroundColor Red
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host "  Your PC is now locked in MAXIMUM PERFORMANCE." -ForegroundColor Yellow
Write-Host "  Leave this window open while you are away." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C or close this window to revert to normal." -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Yellow

# Infinite loop to keep the script running and the thread execution state active
try {
    while ($true) {
        Start-Sleep -Seconds 3600
    }
} finally {
    # On exit (Ctrl+C), reset the execution state
    Write-Host "Reverting sleep settings..." -ForegroundColor Cyan
    [Awake]::SetThreadExecutionState($ES_CONTINUOUS)
}
