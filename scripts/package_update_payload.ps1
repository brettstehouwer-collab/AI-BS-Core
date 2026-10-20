# ==============================================================================
# AI-BS Sovereign Intelligence Studio - Update Payload Packaging Utility
# Location: C:\AI-BS\scripts\package_update_payload.ps1
# Purpose: Compiles changed application binaries & app.asar into a delta zip
#          and updates frontend/public/updates/version.json with hash and size.
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Version = "5.215.0",
    [string]$ReleaseNotes = "AI-BS Sovereign Intelligence Studio v5.215.0: Native Pearl (PRL) & sCash Direct Mining Extraction & Sovereign Renter Disengagement Protocol."
)

$ErrorActionPreference = "Stop"
$baseDir = "C:\AI-BS"
$outputDir = "$baseDir\frontend\public\updates"
$zipPath = "$outputDir\aibs_update_payload.zip"
$versionJsonPath = "$outputDir\version.json"
$stagingDir = "$env:TEMP\aibs_payload_staging"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   PACKAGING AI-BS APP-LEVEL UPDATE PAYLOAD v$Version           " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Ensure output and staging directories
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
if (Test-Path $stagingDir) {
    Remove-Item -Path $stagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null
New-Item -ItemType Directory -Path "$stagingDir\resources" -Force | Out-Null
New-Item -ItemType Directory -Path "$stagingDir\resources\go-core" -Force | Out-Null
New-Item -ItemType Directory -Path "$stagingDir\go-core" -Force | Out-Null

# 2. Gather changed/target files from current desktop build
$asarSource = "$baseDir\frontend\desktop-build\win-unpacked\resources\app.asar"
$engineSource = "$baseDir\go-core\aibs_engine.exe"
$updaterSource = "$baseDir\go-core\aibs_updater.exe"
$distSource = "$baseDir\frontend\dist"
$updateBatSource = "$baseDir\installer\Update_Desktop_Studio.bat"

# A. Bundle Frontend Dist (for Inno Setup and local static server installations)
if (Test-Path $distSource) {
    Copy-Item $distSource "$stagingDir\frontend_dist" -Recurse -Force
    Get-ChildItem -Path "$stagingDir\frontend_dist" -Filter "*.zip" -Recurse | Remove-Item -Force
    Write-Host "  [+] Bundled frontend_dist (Static SPA, excluded recursive archives)" -ForegroundColor Green
}

# B. Bundle Electron app.asar (for standalone Electron desktop installations)
if (Test-Path $asarSource) {
    Copy-Item $asarSource "$stagingDir\resources\app.asar" -Force
    Write-Host "  [+] Bundled resources\app.asar" -ForegroundColor Green
} else {
    Write-Host "  [!] Warning: app.asar not found at $asarSource. Staging empty placeholder." -ForegroundColor Yellow
    Set-Content -Path "$stagingDir\resources\app.asar" -Value "AI-BS App Bundle v$Version"
}

# C. Bundle Go Gateway Engine
if (Test-Path $engineSource) {
    Copy-Item $engineSource "$stagingDir\resources\go-core\aibs_engine.exe" -Force
    Copy-Item $engineSource "$stagingDir\go-core\aibs_engine.exe" -Force
    Write-Host "  [+] Bundled go-core\aibs_engine.exe" -ForegroundColor Green
}

# D. Bundle Out-of-Process Updater Stub & Helper
if (Test-Path $updaterSource) {
    Copy-Item $updaterSource "$stagingDir\aibs_updater.exe" -Force
    Write-Host "  [+] Bundled aibs_updater.exe" -ForegroundColor Green
}
if (Test-Path $updateBatSource) {
    Copy-Item $updateBatSource "$stagingDir\Update_Desktop_Studio.bat" -Force
    Write-Host "  [+] Bundled Update_Desktop_Studio.bat" -ForegroundColor Green
}

# E. Bundle Core Backend & Routers
$backendStaging = "$stagingDir\backend"
New-Item -ItemType Directory -Path $backendStaging -Force | Out-Null
if (Test-Path "$baseDir\backend\AI_BS_Backend.py") {
    Copy-Item "$baseDir\backend\AI_BS_Backend.py" "$backendStaging\AI_BS_Backend.py" -Force
    Write-Host "  [+] Bundled backend\AI_BS_Backend.py" -ForegroundColor Green
}
if (Test-Path "$baseDir\backend\compute_telemetry.json") {
    Copy-Item "$baseDir\backend\compute_telemetry.json" "$backendStaging\compute_telemetry.json" -Force
}
if (Test-Path "$baseDir\backend\pearl_payout_ledger.json") {
    Copy-Item "$baseDir\backend\pearl_payout_ledger.json" "$backendStaging\pearl_payout_ledger.json" -Force
}
if (Test-Path "$baseDir\backend\commercial_gateway") {
    Copy-Item "$baseDir\backend\commercial_gateway" "$backendStaging\commercial_gateway" -Recurse -Force
    Write-Host "  [+] Bundled backend\commercial_gateway" -ForegroundColor Green
}
if (Test-Path "$baseDir\backend\routers") {
    Copy-Item "$baseDir\backend\routers" "$backendStaging\routers" -Recurse -Force
    Write-Host "  [+] Bundled backend\routers" -ForegroundColor Green
}

# F. Bundle Architectural Ledgers & Documentation
if (Test-Path "$baseDir\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md") {
    Copy-Item "$baseDir\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" "$stagingDir\AI_BS_MASTER_ARCHITECTURAL_LEDGER.md" -Force
}
$docsStaging = "$stagingDir\docs"
New-Item -ItemType Directory -Path $docsStaging -Force | Out-Null
if (Test-Path "$baseDir\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md") {
    Copy-Item "$baseDir\docs\AI_BS_MASTER_ECOSYSTEM_MANUAL.md" "$docsStaging\AI_BS_MASTER_ECOSYSTEM_MANUAL.md" -Force
}

# 3. Create zip archive
if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Write-Host "  [*] Compressing payload archive to $zipPath..." -ForegroundColor Cyan
$pyCompress = @"
import os, zipfile
staging = r'$stagingDir'
zip_path = r'$zipPath'
with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zf:
    for root, dirs, files in os.walk(staging):
        for f in files:
            fp = os.path.join(root, f)
            arcname = os.path.relpath(fp, staging)
            zf.write(fp, arcname)
"@
$tmpPy = "$env:TEMP\aibs_compress.py"
Set-Content -Path $tmpPy -Value $pyCompress
python $tmpPy
if (-not (Test-Path $zipPath) -or (Get-Item $zipPath).Length -eq 0) {
    Write-Host "  [!] Python compressor unavailable, falling back to Compress-Archive..." -ForegroundColor Yellow
    Compress-Archive -Path "$stagingDir\*" -DestinationPath $zipPath -CompressionLevel Optimal
}
Remove-Item -Path $tmpPy -Force -ErrorAction SilentlyContinue
Write-Host "  [+] Archive created successfully." -ForegroundColor Green

# 4. Calculate SHA256 & Size
$hash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash.ToLower()
$fileSize = (Get-Item $zipPath).Length
$dateStr = Get-Date -Format "yyyy-MM-dd"

Write-Host "  [+] Payload Size  : $fileSize bytes ($([Math]::Round($fileSize/1MB, 2)) MB)" -ForegroundColor Green
Write-Host "  [+] SHA256 Checksum: $hash" -ForegroundColor Green

# 5. Update version.json manifest
$manifest = [ordered]@{
    appName             = "AI-BS Sovereign Intelligence Studio"
    version             = $Version
    releaseDate         = $dateStr
    channel             = "stable"
    minInstallerVersion = "1.0.0"
    mandatory           = $false
    releaseNotes        = $ReleaseNotes
    downloadUrl         = "https://api.brettstehouwer.live/api/v1/updater/payload"
    fallbackUrl         = "http://127.0.0.1:8080/api/v1/updater/payload"
    sha256              = $hash
    sizeBytes           = $fileSize
    payloadType         = "zip_delta"
    files               = @(
        "frontend_dist/*",
        "resources/app.asar",
        "resources/go-core/aibs_engine.exe",
        "go-core/aibs_engine.exe",
        "aibs_updater.exe",
        "Update_Desktop_Studio.bat",
        "backend/*",
        "AI_BS_MASTER_ARCHITECTURAL_LEDGER.md",
        "docs/AI_BS_MASTER_ECOSYSTEM_MANUAL.md"
    )
}

$jsonOutput = $manifest | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($versionJsonPath, $jsonOutput, [System.Text.UTF8Encoding]::new($false))
Write-Host "  [+] Manifest updated (BOM-free UTF-8): $versionJsonPath" -ForegroundColor Green

# Clean up staging
Remove-Item -Path $stagingDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   UPDATE PAYLOAD PACKAGED & MANIFEST SYNCHRONIZED              " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
