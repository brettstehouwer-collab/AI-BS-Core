@echo off
title AI-BS Portable OBS Core (64-bit)
color 0B
echo ============================================================
echo          AI-BS PORTABLE OBS CORE LAUNCHER (PORT 4455)
echo ============================================================
echo.
if not exist "C:\AI-BS\obs-core\bin\64bit\obs64.exe" (
    echo [ERROR] OBS Studio 64-bit executable not found in C:\AI-BS\obs-core\bin\64bit\
    echo Run setup_obs_core.ps1 to install portable OBS core.
    pause
    exit /b 1
)
echo Launching Portable OBS Core in isolated mode...
start "" /d "C:\AI-BS\obs-core\bin\64bit" "C:\AI-BS\obs-core\bin\64bit\obs64.exe" --portable