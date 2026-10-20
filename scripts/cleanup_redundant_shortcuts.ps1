# AI-BS Desktop Shortcut Pruner & Consolidator
# Cleans up legacy/duplicate installer shortcuts and leaves canonical links.

$backupDir = "C:\AI-BS\saved_data\shortcuts_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Write-Host "Created backup folder at: $backupDir" -ForegroundColor Cyan

$redundantShortcuts = @(
    "C:\Users\Public\Desktop\AI-BS Broadcast Studio.lnk",
    "C:\Users\Public\Desktop\AI-BS Check Updates.lnk",
    "C:\Users\Public\Desktop\AI-BS Matrix Boot.lnk",
    "C:\Users\Public\Desktop\AI-BS Shutdown.lnk",
    "C:\Users\Public\Desktop\AI-BS Sovereign Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\Stehouwer AI • Sovereign Intelligence Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\Stehouwer AI   Sovereign Intelligence Studio.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Main Workstation (Full Suite & DAW).lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Live Streaming & Video Stage.lnk"
)

$prunedCount = 0
foreach ($path in $redundantShortcuts) {
    if (Test-Path -LiteralPath $path) {
        $fileName = [System.IO.Path]::GetFileName($path)
        Copy-Item -LiteralPath $path -Destination (Join-Path $backupDir $fileName) -Force
        Remove-Item -LiteralPath $path -Force
        Write-Host "  [PRUNED & BACKED UP] $path" -ForegroundColor Green
        $prunedCount++
    }
}

# Ensure canonical shortcuts exist and point cleanly
& "C:\AI-BS\scripts\refresh_desktop_shortcuts.ps1"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Desktop clean-up complete: $prunedCount redundant shortcut(s) removed." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
