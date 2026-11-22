@echo off
title AI-BS Clore.ai Hosting Agent Server
color 0B

echo ===================================================
echo       AI-BS CLORE.AI HOSTING SERVER BOOT
echo ===================================================
echo.

set "SCRIPT_DIR=%~dp0"

echo [1/4] Verifying WSL2 Ubuntu environment...
wsl.exe -d Ubuntu -u root id >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] WSL2 Ubuntu instance is not running or accessible.
    echo Please ensure WSL2 is enabled and the Ubuntu distribution is installed.
    pause
    exit /b 1
)

echo [2/4] Ensuring persistent WSL2 background keepalive...
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\ensure_clore_keepalive.ps1"

echo.
echo [3/4] Starting clore-hosting.service in WSL2...
wsl.exe -d Ubuntu -u root systemctl start clore-hosting.service

echo.
echo [4/4] Verifying Clore Server Status...
wsl.exe -d Ubuntu -u root systemctl is-active clore-hosting.service >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ===================================================
    echo  [SUCCESS] Clore.ai Hosting Agent Server is ACTIVE!
    echo ===================================================
    echo.
    echo Active Docker Containers:
    wsl.exe -d Ubuntu -u root docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"
    echo.
    echo Service logs (last 5 lines):
    wsl.exe -d Ubuntu -u root journalctl -u clore-hosting.service -n 5 --no-pager
) else (
    echo.
    echo [WARNING] clore-hosting.service is not active via systemd.
    echo Attempting direct execution fallback via /opt/clore-hosting/service.sh...
    wsl.exe -d Ubuntu -u root bash /opt/clore-hosting/service.sh
)

echo.
echo Clore Server execution complete.
pause
