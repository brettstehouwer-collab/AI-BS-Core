@echo off
title October 7 Vocal Tracking Studio DAW
cd /d "%~dp0"
echo ============================================================
echo   OCTOBER 7 VOCAL TRACKING STUDIO (WINDOWS CORE PRO)
echo   Realtime MMCSS Pro Audio ^& WASAPI Exclusive Mode
echo ============================================================
echo.

if exist "%~dp0dist\October7_VocalStudio_DAW\October7_VocalStudio_DAW.exe" (
    echo [*] Launching compiled Windows application...
    start "" "%~dp0dist\October7_VocalStudio_DAW\October7_VocalStudio_DAW.exe"
) else (
    echo [*] Launching Python Pro Audio Core Engine...
    python "%~dp0october7_core.py"
)
