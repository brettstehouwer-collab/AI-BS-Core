<#
.SYNOPSIS
Builds the AI-BS Matrix standalone installer.

.DESCRIPTION
This script compiles the Python backend using PyInstaller, 
builds the Vite React frontend, and then packages the entire 
ecosystem into an NSIS installer using electron-builder.
#>

$ErrorActionPreference = "Stop"

$BASE_DIR = "C:\AI-BS"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "     AI-BS MATRIX INSTALLER BUILD SEQUENCE" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Compile Python Backend
Write-Host "[1/3] Compiling Python Backend via PyInstaller..." -ForegroundColor Yellow
Set-Location $BASE_DIR
if (-Not (Test-Path "$BASE_DIR\pyppeteer_env\Scripts\pyinstaller.exe")) {
    Write-Host "Installing PyInstaller..."
    & "$BASE_DIR\pyppeteer_env\Scripts\python.exe" -m pip install pyinstaller
}

& "$BASE_DIR\pyppeteer_env\Scripts\python.exe" -m PyInstaller -y --clean --distpath backend/dist brain_backend.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller backend compilation failed!"
    exit 1
}

# 2. Build Vite Frontend
Write-Host "[2/3] Building Vite React Frontend..." -ForegroundColor Yellow
Set-Location "$BASE_DIR\frontend"
npm install
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Error "Vite frontend build failed!"
    exit 1
}

# 3. Package Electron App
Write-Host "[3/3] Packaging Electron App with electron-builder..." -ForegroundColor Yellow
npx electron-builder --win
if ($LASTEXITCODE -ne 0) {
    Write-Error "Electron builder packaging failed!"
    exit 1
}

Write-Host "===================================================" -ForegroundColor Green
Write-Host "  SUCCESS! Installer generated in frontend\desktop-build" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
