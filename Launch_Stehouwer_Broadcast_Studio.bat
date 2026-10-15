@echo off
title Stehouwer Publishing Broadcast Studio
color 0B

echo =========================================================================
echo           STEHOUWER PUBLISHING BROADCAST STUDIO
echo        Hardware NVENC 4K/8K Streaming ^& Neural Audio Workstation
echo            [Pure Native Windows Direct2D / MMCSS Pro Audio]
echo =========================================================================
echo.

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

:: 1. Locate Python Interpreter
set "PYTHON_EXE="
if exist "%APP_DIR%pyppeteer_env\Scripts\python.exe" (
    set "PYTHON_EXE=%APP_DIR%pyppeteer_env\Scripts\python.exe"
) else (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo [ERROR] Python interpreter not found!
    pause
    exit /b 1
)

:: 2. Local Microservices & Web Servers
:: Local web servers (FastAPI 8080, Broadcast Daemon 8005, Kernel 8088, Vite 5174)
:: operate freely to power the Native Windows version.

:: 3. Start Hardware Broadcast Kernel (Port 8088 NVENC / OBS IPC) if not already active
netstat -an | find ":8088 " | find "LISTENING" >nul
if %ERRORLEVEL% neq 0 (
    echo [STEHOUWER BROADCAST] Starting Hardware Broadcast Kernel on port 8088...
    if exist "%APP_DIR%backend\aibs_broadcast_kernel.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_broadcast_kernel.py' -WorkingDirectory '%APP_DIR%backend' -WindowStyle Hidden"
    )
    ping 127.0.0.1 -n 2 >nul
)

:: 4. Locate Native Stehouwer Broadcast Studio Script
set "STUDIO_SCRIPT=%APP_DIR%native_studio\stehouwer_broadcast_studio.py"
if not exist "%STUDIO_SCRIPT%" (
    echo [ERROR] Native broadcast studio script not found at %STUDIO_SCRIPT%!
    pause
    exit /b 1
)

:: 5. Launch Pure Native Desktop Application (Direct2D / DirectX 11 / MMCSS Priority 15)
echo [STEHOUWER BROADCAST] Launching Pure Native Desktop Application...
echo                      Zero Browser Engines ^| Zero Local Web Servers
start "" "%PYTHON_EXE%" "%STUDIO_SCRIPT%"

echo [STEHOUWER BROADCAST] Studio launched successfully.
ping 127.0.0.1 -n 2 >nul
exit /b 0
