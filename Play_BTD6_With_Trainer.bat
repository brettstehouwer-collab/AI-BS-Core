@echo off
title AI-BS Bloons TD 6 + Sovereign Memory Trainer
color 0B

echo ===================================================
echo     LAUNCHING BLOONS TD 6 + AI-BS TRAINER
echo ===================================================
echo.

set "BASE_DIR=%~dp0"
set "BTD6_EXE=E:\SteamLibrary\steamapps\common\BloonsTD6\BloonsTD6.exe"

:: 1. Launch AI-BS Trainer (starts background continuous auto-detection & HUD)
echo [1/2] Starting AI-BS BTD6 Memory Trainer (Auto-Detecting)...
start "" "%BASE_DIR%Launch_BTD6_Trainer.bat"

:: 2. Launch Bloons TD 6 via Steam protocol (preferred for Steam Cloud / saves)
echo [2/2] Launching Bloons TD 6 on Steam...
start steam://rungameid/960090

:: Fallback if Steam URI protocol is unhandled:
timeout /t 2 /nobreak > nul
tasklist /fi "imagename eq BloonsTD6.exe" 2>nul | find /i "BloonsTD6.exe" > nul
if errorlevel 1 (
    if exist "%BTD6_EXE%" (
        echo [Fallback] Direct binary execution...
        start "" "%BTD6_EXE%"
    )
)

echo.
echo ===================================================
echo   GAME AND TRAINER RUNNING IN SYNC.
echo   Press F1 for Cash, F2 for Lives, F6 for HUD.
echo ===================================================
timeout /t 3 > nul
exit
