# =====================================================================
# AI-BS Sovereign Intelligence Studio - Desktop Installer Build Script
# Compiles AI_BS_Studio_Setup_v<Version>.exe using Inno Setup 6
# =====================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VersionFile = "C:\AI-BS\version.txt"
$AppVersion = "5.296.0"
if (Test-Path $VersionFile) {
    $AppVersion = (Get-Content $VersionFile).Trim().TrimStart('v')
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  AI-BS SOVEREIGN STUDIO - DESKTOP INSTALLER COMPILER" -ForegroundColor Cyan
Write-Host "  Version: $AppVersion" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Inno Setup Compiler (ISCC.exe)
$IsccCandidates = @(
    "C:\Users\footb\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$IsccPath = $null
foreach ($path in $IsccCandidates) {
    if (Test-Path $path) {
        $IsccPath = $path
        break
    }
}

if (-not $IsccPath) {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $IsccPath = $cmd.Source
    }
}

if (-not $IsccPath) {
    Write-Error "[FATAL] Inno Setup Compiler (ISCC.exe) could not be located. Please ensure Inno Setup 6 is installed."
    exit 1
}

Write-Host "[OK] Inno Setup Compiler found: $IsccPath" -ForegroundColor Green

# 2. Ensure Output directories exist
$OutputDir = Join-Path $ScriptDir "Output"
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$GlobalInstallerDir = "C:\AI-BS\InstallerEXE's"
if (-not (Test-Path $GlobalInstallerDir)) {
    New-Item -ItemType Directory -Path $GlobalInstallerDir -Force | Out-Null
}

# 3. Verify Prerequisites
$IssFile = Join-Path $ScriptDir "AI_BS_Studio_Setup.iss"
if (-not (Test-Path $IssFile)) {
    Write-Error "[FATAL] Missing script file: $IssFile"
    exit 1
}

$FrontendDist = "C:\AI-BS\frontend\dist\index.html"
if (-not (Test-Path $FrontendDist)) {
    Write-Error "[FATAL] Frontend distribution not found at $FrontendDist. Run 'npm run build' first."
    exit 1
}

# 4. Compile Installer Executable
Write-Host "[AI-BS] Compiling standalone Windows desktop setup executable..." -ForegroundColor Yellow
$Sw = [System.Diagnostics.Stopwatch]::StartNew()

& "$IsccPath" /Qp "$IssFile"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FATAL] ISCC compilation failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

$Sw.Stop()
$ElapsedTime = [math]::Round($Sw.Elapsed.TotalSeconds, 2)
Write-Host "[OK] Installer compiled successfully in $ElapsedTime seconds!" -ForegroundColor Green

# 5. Verify Output and Mirror to Global InstallerEXEs
$TargetExe = Join-Path $OutputDir "AI_BS_Studio_Setup_v$AppVersion.exe"
if (-not (Test-Path $TargetExe)) {
    Write-Error "[FATAL] Expected output executable not found: $TargetExe"
    exit 1
}

$FileInfo = Get-Item $TargetExe
$SizeMB = [math]::Round($FileInfo.Length / 1MB, 2)
Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  BUILD ARTIFACT CREATED SUCCESSFULLY" -ForegroundColor Green
Write-Host "  File: $($FileInfo.FullName)" -ForegroundColor White
Write-Host "  Size: $SizeMB MB ($($FileInfo.Length) bytes)" -ForegroundColor White
Write-Host "  Date: $($FileInfo.LastWriteTime)" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Green

# Mirror to C:\AI-BS\InstallerEXE's
$MirroredPath = Join-Path $GlobalInstallerDir "AI_BS_Studio_Setup_v$AppVersion.exe"
Copy-Item -Path $TargetExe -Destination $MirroredPath -Force
Write-Host "[OK] Mirrored release installer to: $MirroredPath" -ForegroundColor Green

# Generate SHA256 Hash
$Hash = (Get-FileHash -Path $TargetExe -Algorithm SHA256).Hash
Write-Host "[SHA256] $Hash" -ForegroundColor Cyan
Write-Host ""
