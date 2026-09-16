@echo off
title AI-BS Broadcast ^& DAW Workstation
color 0C

echo =========================================================
echo       AI-BS BROADCAST ^& NEURAL DAW WORKSTATION
echo =========================================================
echo.

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

:: 1. Locate Python Interpreter
set "PYTHON_EXE="
if exist "%APP_DIR%pyppeteer_env\Scripts\python.exe" (
    set "PYTHON_EXE=%APP_DIR%pyppeteer_env\Scripts\python.exe"
) else if exist "%APP_DIR%..\pyppeteer_env\Scripts\python.exe" (
    set "PYTHON_EXE=%APP_DIR%..\pyppeteer_env\Scripts\python.exe"
) else if exist "C:\AI-BS\pyppeteer_env\Scripts\python.exe" (
    set "PYTHON_EXE=C:\AI-BS\pyppeteer_env\Scripts\python.exe"
) else (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%i"
    )
)

if not defined PYTHON_EXE (
    echo [WARNING] Python interpreter not found in local path. Checking fallback python...
    set "PYTHON_EXE=python"
)

:: 2. Start Broadcast Kernel on 8088 if not already running
netstat -an | find ":8088 " | find "LISTENING" >nul
if %ERRORLEVEL% neq 0 (
    echo [AI-BS] Starting Broadcast Kernel on port 8088...
    if exist "%APP_DIR%backend\aibs_broadcast_kernel.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_broadcast_kernel.py' -WorkingDirectory '%APP_DIR%backend' -WindowStyle Hidden"
    ) else if exist "C:\AI-BS\backend\aibs_broadcast_kernel.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_broadcast_kernel.py' -WorkingDirectory 'C:\AI-BS\backend' -WindowStyle Hidden"
    )
)

:: 3. Start Broadcast UI Server on 5174 if not already running
netstat -an | find ":5174 " | find "LISTENING" >nul
if %ERRORLEVEL% neq 0 (
    echo [AI-BS] Starting Broadcast UI Server on port 5174...
    if exist "%APP_DIR%broadcast_dist\index.html" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'serve_desktop.py 5174' -WorkingDirectory '%APP_DIR%' -WindowStyle Hidden"
    ) else if exist "%APP_DIR%serve_desktop.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'serve_desktop.py 5174' -WorkingDirectory '%APP_DIR%' -WindowStyle Hidden"
    )
    ping 127.0.0.1 -n 3 >nul
)

:: 4. Launch Dedicated Broadcast & DAW Window Mode
set "TARGET_URL=http://127.0.0.1:5174"
set "USER_DATA=%LOCALAPPDATA%\AI_BS_Studio\BroadcastProfile"
set "MEDIA_FLAGS=--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5174,http://localhost:5174 --use-fake-ui-for-media-stream"

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    echo [AI-BS] Launching Broadcast Studio in Edge App Window...
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app=%TARGET_URL% --window-size=1600,1000 --user-data-dir="%USER_DATA%" %MEDIA_FLAGS%
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    echo [AI-BS] Launching Broadcast Studio in Edge App Window...
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --app=%TARGET_URL% --window-size=1600,1000 --user-data-dir="%USER_DATA%" %MEDIA_FLAGS%
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    echo [AI-BS] Launching Broadcast Studio in Chrome App Window...
    start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app=%TARGET_URL% --window-size=1600,1000 --user-data-dir="%USER_DATA%" %MEDIA_FLAGS%
) else (
    echo [AI-BS] Launching Broadcast Studio in Default Browser...
    start "" "%TARGET_URL%"
)

echo [AI-BS] Broadcast ^& Neural DAW Workstation initialized successfully.
ping 127.0.0.1 -n 3 >nul
exit /b 0
