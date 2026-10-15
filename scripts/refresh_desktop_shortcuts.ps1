# AI-BS Desktop Shortcut Refresher (v5.317.0)
$ErrorActionPreference = "SilentlyContinue"

$targetExe = "C:\AI-BS\native_studio\dist\AI_BS_Studio\AI_BS_Studio.exe"
$workingDir = "C:\AI-BS\native_studio\dist\AI_BS_Studio"
$shortcutName = "AI-BS Executive Studio.lnk"
$iconPath = "C:\AI-BS\public\favicon.ico"

$desktopPaths = @(
    "C:\Users\footb\OneDrive\Desktop",
    "C:\Users\footb\Desktop"
) | Select-Object -Unique

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " AI-BS EXECUTIVE STUDIO -- DESKTOP SHORTCUT DEPLOYER" -ForegroundColor Cyan
Write-Host " Target: Direct2D Pure Native Standalone Executable" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

$wsh = New-Object -ComObject WScript.Shell
$deployedCount = 0

foreach ($desk in $desktopPaths) {
    if (Test-Path $desk) {
        $linkPath = Join-Path $desk $shortcutName
        Write-Host "Deploying shortcut to: $linkPath" -ForegroundColor Yellow
        
        $shortcut = $wsh.CreateShortcut($linkPath)
        $shortcut.TargetPath = $targetExe
        $shortcut.WorkingDirectory = $workingDir
        $shortcut.Description = "AI-BS Sovereign Executive Command Studio (Direct2D Win32, v5.317.0)"
        if (Test-Path $iconPath) {
            $shortcut.IconLocation = $iconPath
        } elseif (Test-Path $targetExe) {
            $shortcut.IconLocation = $targetExe
        }
        $shortcut.Save()
        $deployedCount++
        Write-Host "  [OK] Successfully deployed to $desk" -ForegroundColor Green
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Summary: $deployedCount desktop shortcut(s) active and verified." -ForegroundColor Green

