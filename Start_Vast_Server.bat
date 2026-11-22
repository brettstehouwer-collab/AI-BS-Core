@echo off
title AI-BS Vast.ai Hosting Agent Server
color 0D

echo ===================================================
echo       AI-BS VAST.AI HOSTING SERVER BOOT
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"

echo [1/3] Verifying WSL2 Ubuntu-24.04 environment...
wsl.exe -d Ubuntu-24.04 -u root id >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] WSL2 Ubuntu-24.04 instance is not running or accessible.
    echo Please ensure WSL2 is enabled and the Ubuntu-24.04 distribution is installed.
    pause
    exit /b 1
)

echo [2/3] Ensuring Docker is running in WSL2 Ubuntu-24.04...
wsl.exe -d Ubuntu-24.04 -u root service docker start >nul 2>&1

echo [3/3] Starting Vast.ai Daemon in WSL2...
echo.
echo ===================================================
echo  [SUCCESS] Vast.ai Hosting Agent Server is ACTIVE!
echo ===================================================
echo.
echo Executing Vast.ai python host...
wsl.exe -d Ubuntu-24.04 -u root bash -c "python3 /mnt/c/AI-BS/vast.py > /var/log/vast.log 2>&1 & tail -f /var/log/vast.log"

echo.
echo Vast Server execution complete.
pause
