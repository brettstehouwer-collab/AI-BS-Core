# Desktop Shortcuts & Obsolete Installation Cleanup Script
$ErrorActionPreference = "Continue"

$backupDir = "C:\AI-BS\saved_data\desktop_shortcuts_backup_20260909_115600"
New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
Write-Host "[1/5] Safety Backup Directory created: $backupDir" -ForegroundColor Cyan

# 1. Backup all shortcuts in Public Desktop and OneDrive Desktop
$publicDesktop = "C:\Users\Public\Desktop"
$userDesktop = "C:\Users\footb\OneDrive\Desktop"

Get-ChildItem -Path $publicDesktop -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $backupDir ("Public_" + $_.Name)) -Force
}
Get-ChildItem -Path $userDesktop -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination (Join-Path $backupDir ("User_" + $_.Name)) -Force
}
Write-Host "[2/5] Backed up all desktop shortcuts to safety archive." -ForegroundColor Green

# 2. List of redundant shortcuts to delete
$shortcutsToDelete = @(
    "C:\Users\Public\Desktop\AI-BS Shutdown.lnk",
    "C:\Users\Public\Desktop\AI-BS Broadcast Studio.lnk",
    "C:\Users\Public\Desktop\BS-Studio.lnk",
    "C:\Users\Public\Desktop\AI-BS Sovereign Studio.lnk",
    "C:\Users\Public\Desktop\AI-BS Matrix Boot.lnk",
    "C:\Users\Public\Desktop\AI-BS Matrix.lnk",
    "C:\Users\footb\OneDrive\Desktop\AI-BS Matrix.lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut.lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_AI_BS - Shortcut (2).lnk",
    "C:\Users\footb\OneDrive\Desktop\Launch_Unreal_OnDemand (2).lnk",
    "C:\Users\footb\OneDrive\Desktop\Stehouwer Publishing AI-BS Matrix.lnk",
    "C:\Users\footb\OneDrive\Desktop\Stehouwer Publishing AI-BS Matrix (2).lnk",
    "C:\Users\footb\OneDrive\Desktop\Start Crypto Swarm (2).lnk"
)

Write-Host "[3/5] Removing redundant / collision shortcuts..." -ForegroundColor Cyan
foreach ($path in $shortcutsToDelete) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Force -ErrorAction SilentlyContinue
        Write-Host "  [-] Deleted redundant shortcut: $path" -ForegroundColor Yellow
    }
}

# 3. Standardize and configure remaining clean shortcuts on User Desktop
$wsh = New-Object -ComObject WScript.Shell

# Ensure AI-BS Matrix Boot.lnk points directly to C:\AI-BS\Launch_AI_BS.bat
$bootLnkPath = Join-Path $userDesktop "AI-BS Matrix Boot.lnk"
$bootLnk = $wsh.CreateShortcut($bootLnkPath)
$bootLnk.TargetPath = "C:\AI-BS\Launch_AI_BS.bat"
$bootLnk.WorkingDirectory = "C:\AI-BS"
$bootLnk.Description = "Launch AI-BS Full Matrix Architecture & Engines"
if (Test-Path "C:\AI-BS\installer\app_icon.ico") {
    $bootLnk.IconLocation = "C:\AI-BS\installer\app_icon.ico,0"
}
$bootLnk.Save()
Write-Host "  [+] Standardized: $bootLnkPath -> C:\AI-BS\Launch_AI_BS.bat" -ForegroundColor Green

# Ensure AI-BS Shutdown.lnk points to C:\AI-BS\Shutdown_AI_BS.bat
$shutdownLnkPath = Join-Path $userDesktop "AI-BS Shutdown.lnk"
$shutdownLnk = $wsh.CreateShortcut($shutdownLnkPath)
$shutdownLnk.TargetPath = "C:\AI-BS\Shutdown_AI_BS.bat"
$shutdownLnk.WorkingDirectory = "C:\AI-BS"
$shutdownLnk.Description = "Shutdown All AI-BS Matrix Background Engines"
$shutdownLnk.Save()
Write-Host "  [+] Standardized: $shutdownLnkPath -> C:\AI-BS\Shutdown_AI_BS.bat" -ForegroundColor Green

Write-Host "[4/5] Desktop shortcuts standardized and cleaned." -ForegroundColor Green

# 4. Storage Reclamation: Remove obsolete C:\Program Files\AI-BS Matrix (3.03 GB)
$matrixDir = "C:\Program Files\AI-BS Matrix"
if (Test-Path $matrixDir) {
    Write-Host "[5/5] Reclaiming 3.03 GB from obsolete directory: $matrixDir..." -ForegroundColor Cyan
    Remove-Item -Path $matrixDir -Recurse -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $matrixDir)) {
        Write-Host "  [OK] Successfully removed $matrixDir. Reclaimed ~3.03 GB free space on C: Drive!" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Some files in $matrixDir were in use or could not be removed." -ForegroundColor Yellow
    }
} else {
    Write-Host "[5/5] $matrixDir was already removed." -ForegroundColor Gray
}

Write-Host "`nAll operations complete! Desktop is cleanly organized." -ForegroundColor Green
