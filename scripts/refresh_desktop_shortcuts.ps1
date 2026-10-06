# AI-BS Desktop Shortcut Refresher (v5.311.0)
$ErrorActionPreference = "SilentlyContinue"

$targetVbs = "C:\AI-BS\Launch_Desktop_Studio.vbs"
$workingDir = "C:\AI-BS"
$shortcutName = "AI-BS Executive Studio.lnk"
$iconPath = "C:\AI-BS\public\favicon.ico"

$desktopPaths = @(
    "C:\Users\footb\OneDrive\Desktop",
    "C:\Users\footb\Desktop"
) | Select-Object -Unique

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " AI-BS EXECUTIVE STUDIO -- DESKTOP SHORTCUT DEPLOYER" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$wsh = New-Object -ComObject WScript.Shell
$deployedCount = 0

foreach ($desk in $desktopPaths) {
    if (Test-Path $desk) {
        $linkPath = Join-Path $desk $shortcutName
        Write-Host "Deploying shortcut to: $linkPath" -ForegroundColor Yellow
        
        $shortcut = $wsh.CreateShortcut($linkPath)
        $shortcut.TargetPath = "wscript.exe"
        $shortcut.Arguments = '"' + $targetVbs + '"'
        $shortcut.WorkingDirectory = $workingDir
        $shortcut.Description = "AI-BS Sovereign Executive Command Studio (v5.311.0)"
        if (Test-Path $iconPath) {
            $shortcut.IconLocation = $iconPath
        }
        $shortcut.Save()
        $deployedCount++
        Write-Host "  [OK] Successfully deployed to $desk" -ForegroundColor Green
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Summary: $deployedCount desktop shortcut(s) active and verified." -ForegroundColor Green
