@echo off
title AI-BS Sovereign Studio Windows Setup Installer
color 0B

echo ===================================================
echo     AI-BS SOVEREIGN STUDIO WINDOWS SETUP INSTALLER
echo     Authentic Elevated Setup Wizard (v5.311.0)
echo ===================================================
echo.

set "SETUP_EXE=%~dp0native_studio\dist\AI_BS_Studio_Setup.exe"

if exist "%SETUP_EXE%" (
    echo [INFO] Launching elevated installer wizard...
    start "" "%SETUP_EXE%"
) else (
    echo [ERROR] Setup executable not found at: %SETUP_EXE%
    pause
    exit /b 1
)

exit /b 0
