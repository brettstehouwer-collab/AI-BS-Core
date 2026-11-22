$ErrorActionPreference = "Stop"

$obsUrl = "https://github.com/obsproject/obs-studio/releases/download/30.1.2/OBS-Studio-30.1.2.zip"
$obsZip = "C:\AI-BS\obs-core.zip"
$obsDir = "C:\AI-BS\obs-core"

Write-Host "=== AI-BS Portable OBS Core Installer ===" -ForegroundColor Cyan
if (Test-Path "$obsDir\bin\64bit\obs64.exe") {
    Write-Host "[OK] OBS Core already installed at $obsDir." -ForegroundColor Green
    exit 0
}

Write-Host "Downloading OBS Studio 30.1.2 Portable Core..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $obsUrl -OutFile $obsZip

if (Test-Path $obsDir) {
    Remove-Item -Recurse -Force $obsDir
}
New-Item -ItemType Directory -Force -Path $obsDir | Out-Null

Write-Host "Extracting OBS Studio into $obsDir..." -ForegroundColor Yellow
Expand-Archive -Path $obsZip -DestinationPath $obsDir -Force

Write-Host "Cleaning up archive..."
Remove-Item -Force $obsZip

Write-Host "Enabling Portable Mode..."
New-Item -ItemType File -Path "$obsDir\obs_portable_mode.txt" -Force | Out-Null

# Auto-configure WebSocket
& "C:\AI-BS\setup_obs_websocket.ps1"

Write-Host "[SUCCESS] OBS Core Setup Complete." -ForegroundColor Green