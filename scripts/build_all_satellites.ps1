<#
.SYNOPSIS
AI-BS Master Orchestrator: Multi-Satellite Standalone Build Pipeline
Packages all 5 standalone satellite applications and the Master Hub.
#>

$ErrorActionPreference = "Continue"
$BASE_DIR = "C:\AI-BS"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "       AI-BS MULTI-SATELLITE STANDALONE BUILD ORCHESTRATOR       " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Build Standalone Broadcast Studio App
Write-Host "[1/5] Building Satellite 1: BroadcastStudioApp (Electron + Vite)..." -ForegroundColor Yellow
if (Test-Path "$BASE_DIR\BroadcastStudioApp") {
    Set-Location "$BASE_DIR\BroadcastStudioApp"
    npm run build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> BroadcastStudioApp built successfully." -ForegroundColor Green
    } else {
        Write-Host "  -> BroadcastStudioApp build warning/error code: $LASTEXITCODE" -ForegroundColor DarkYellow
    }
}

# 2. Build Standalone Prestige Mobile Wash App
Write-Host "`n[2/5] Building Satellite 2: PrestigeMobileWash (Capacitor Web)..." -ForegroundColor Yellow
if (Test-Path "$BASE_DIR\PrestigeMobileWash") {
    Set-Location "$BASE_DIR\PrestigeMobileWash"
    npm run build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> PrestigeMobileWash built successfully." -ForegroundColor Green
    } else {
        Write-Host "  -> PrestigeMobileWash build warning/error code: $LASTEXITCODE" -ForegroundColor DarkYellow
    }
}

# 3. Build Standalone Digital Storefront Mobile App
Write-Host "`n[3/5] Building Satellite 3: Digital Storefront Mobile..." -ForegroundColor Yellow
if (Test-Path "$BASE_DIR\apps\digital_storefront_mobile") {
    Set-Location "$BASE_DIR\apps\digital_storefront_mobile"
    npm run build
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> Digital Storefront Mobile built successfully." -ForegroundColor Green
    } else {
        Write-Host "  -> Digital Storefront Mobile build warning/error code: $LASTEXITCODE" -ForegroundColor DarkYellow
    }
}

# 4. Verify Crypto-Swarm Desktop Workspace
Write-Host "`n[4/5] Verifying Satellite 4: Crypto-Swarm (Go Wails + Trade Queue)..." -ForegroundColor Yellow
if (Test-Path "$BASE_DIR\Crypto-Swarm\cryptoswarm-desktop") {
    Set-Location "$BASE_DIR\Crypto-Swarm\cryptoswarm-desktop"
    if (Test-Path "go.mod") {
        Write-Host "  -> Crypto-Swarm Go Wails package verified." -ForegroundColor Green
    }
}

# 5. Verify Virtual Production Cinematics
Write-Host "`n[5/5] Verifying Satellite 5: Virtual Production Scripts (JuliesPlace & NoCo)..." -ForegroundColor Yellow
& "$BASE_DIR\pyppeteer_env\Scripts\python.exe" -c "
import py_compile, os
scripts = [
    r'C:\AI-BS\JuliesPlace\julies_place_master_director.py',
    r'C:\AI-BS\JuliesPlace\build_julies_place_world.py',
    r'C:\AI-BS\NoCo Vision\theatrical_gateway.py'
]
for s in scripts:
    if os.path.exists(s):
        py_compile.compile(s, doraise=True)
        print(f'  -> Verified syntax: {os.path.basename(s)}')
"

Set-Location $BASE_DIR
Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "  MULTI-SATELLITE BUILD & VERIFICATION SEQUENCE COMPLETED        " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green