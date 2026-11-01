# Deploy Native Desktop Application to Program Files and Update Shortcuts
$ErrorActionPreference = "Stop"

$source = Join-Path (Get-Location).Path "dist\October7_VocalStudio_Native"
$target = "C:\Program Files\October7_VocalStudio_DAW"

Write-Host "[*] Source: $source"
Write-Host "[*] Target: $target"

if (-not (Test-Path $target)) {
    New-Item -Path $target -ItemType Directory -Force | Out-Null
}

Write-Host "[*] Deploying native files to: $target"
Copy-Item -Path "$source\*" -Destination $target -Recurse -Force
Write-Host "[OK] Files copied successfully."

# Update Desktop Shortcut
$desktop = [System.Environment]::GetFolderPath('Desktop')
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut("$desktop\October 7 Vocal Studio DAW.lnk")
$sc.TargetPath = "$target\October7_VocalStudio_Native.exe"
$sc.WorkingDirectory = $target
$sc.Description = "October 7 Vocal Tracking Studio & Performance Engine (Native Desktop DAW Pro)"
$sc.Save()
Write-Host "[OK] Desktop shortcut updated -> $target\October7_VocalStudio_Native.exe"

# Update Start Menu Entry
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\October 7 Vocal Studio"
if (Test-Path $startMenu) {
    $scMenu = $wsh.CreateShortcut("$startMenu\October 7 Vocal Studio DAW.lnk")
    $scMenu.TargetPath = "$target\October7_VocalStudio_Native.exe"
    $scMenu.WorkingDirectory = $target
    $scMenu.Description = "October 7 Vocal Tracking Studio & Performance Engine (Native Desktop DAW Pro)"
    $scMenu.Save()
    Write-Host "[OK] Start Menu shortcut updated -> $target\October7_VocalStudio_Native.exe"
}

# Verify Authenticode on deployed binary
$sig = Get-AuthenticodeSignature "$target\October7_VocalStudio_Native.exe"
Write-Host "[OK] Target Authenticode Status: $($sig.Status) ($($sig.StatusMessage))"
Write-Host "[OK] Deployment to Program Files Complete!"
