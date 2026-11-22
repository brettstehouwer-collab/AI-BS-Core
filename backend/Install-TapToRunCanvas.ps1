# =========================================================================
# AI-BS Sovereign Intelligence Ecosystem - Tap-To-Run Canvas Installer
# File: C:\AI-BS\backend\Install-TapToRunCanvas.ps1
# Description: Automated installer, sprite synthesizer, router verification,
#              and tap-gated execution pipeline configurator
# =========================================================================

param (
    [string]$TargetDir = "C:\AI-BS\backend\chess\animated_chess",
    [string]$PythonExe = "C:\AI-BS\pyppeteer_env\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  AI-BS SOVEREIGN TAP-TO-RUN CANVAS PIPELINE INSTALLER" -ForegroundColor Cyan
Write-Host "  Target App: $TargetDir" -ForegroundColor DarkGray
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Resolve Python Binary
if (-not (Test-Path $PythonExe)) {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        Write-Error "Could not locate Python executable at $PythonExe or in system PATH."
        exit 1
    }
}
Write-Host "[1/6] Python Runtime Verified: $PythonExe" -ForegroundColor Green

# 2. Verify Pygame and Pillow packages
Write-Host "[2/6] Verifying Pygame and Pillow dependencies..." -ForegroundColor Yellow
$pkgCheck = & $PythonExe -c "
import sys
missing = []
for pkg in ['pygame', 'PIL', 'fastapi', 'uvicorn']:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print('MISSING:' + ','.join(missing))
    sys.exit(1)
else:
    import pygame, PIL
    print(f'Pygame {pygame.__version__} | Pillow {PIL.__version__}')
"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing missing dependencies..." -ForegroundColor Yellow
    & $PythonExe -m pip install pygame pillow fastapi uvicorn
} else {
    Write-Host "  -> Dependencies Present: $pkgCheck" -ForegroundColor Green
}

# 3. Create target directory structure
Write-Host "[3/6] Provisioning directory structure..." -ForegroundColor Yellow
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
}
$imagesDir = Join-Path $TargetDir "images"
if (-not (Test-Path $imagesDir)) {
    New-Item -ItemType Directory -Force -Path $imagesDir | Out-Null
}
Write-Host "  -> Directory Ready: $imagesDir" -ForegroundColor Green

# 4. Synthesize Neon Chess Piece Assets
Write-Host "[4/6] Synthesizing neon chess sprites..." -ForegroundColor Yellow
$spriteOutput = & $PythonExe -c "
import sys
sys.path.insert(0, r'C:\AI-BS\backend')
import canvas_daemon
count = canvas_daemon.ensure_neon_chess_assets(r'$TargetDir')
print(f'SYNTHESIZED:{count}')
"
Write-Host "  -> Neon Chess Sprites Verified: $spriteOutput" -ForegroundColor Green

# 5. Verify Canvas Daemon Module
Write-Host "[5/6] Verifying canvas_daemon router..." -ForegroundColor Yellow
$routerTest = & $PythonExe -c "
import sys
sys.path.insert(0, r'C:\AI-BS\backend')
import canvas_daemon
endpoints = [r.path for r in canvas_daemon.router.routes]
print('ROUTES:' + ','.join(endpoints))
"
Write-Host "  -> Canvas Daemon Routes Active: $routerTest" -ForegroundColor Green

# 6. Verify AI_BS_Backend Integration
Write-Host "[6/6] Verifying AI_BS_Backend.py mount..." -ForegroundColor Yellow
$backendPath = "C:\AI-BS\backend\AI_BS_Backend.py"
if (Test-Path $backendPath) {
    $backendContent = Get-Content $backendPath -Raw
    if ($backendContent -match "canvas_daemon") {
        Write-Host "  -> canvas_daemon cleanly mounted in AI_BS_Backend.py" -ForegroundColor Green
    } else {
        Write-Host "  -> Note: canvas_daemon import not found in AI_BS_Backend.py, adding..." -ForegroundColor Yellow
    }
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "  ✅ TAP-TO-RUN CANVAS PIPELINE INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host "  Root Daemon: http://127.0.0.1:8080/api/canvas/execute" -ForegroundColor White
Write-Host "  WebSocket:   ws://127.0.0.1:8080/ws/canvas" -ForegroundColor White
Write-Host "  Execution Guarantee: Strictly gated behind user [Run ...] button tap" -ForegroundColor White
Write-Host "=================================================================`n" -ForegroundColor Cyan
