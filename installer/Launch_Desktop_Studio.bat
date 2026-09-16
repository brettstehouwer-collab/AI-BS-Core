@echo off
title AI-BS Sovereign Intelligence Studio
color 0B

echo =========================================================
echo       AI-BS SOVEREIGN INTELLIGENCE STUDIO (DESKTOP)
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

:: 2. Ensure Go Engine Core is Running on Port 8000
netstat -an | find ":8000 " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    echo [AI-BS] Go Engine Core already active on port 8000.
) else (
    echo [AI-BS] Starting Go Engine Core on port 8000...
    if exist "%APP_DIR%go-core\aibs_engine.exe" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%APP_DIR%go-core\aibs_engine.exe' -WorkingDirectory '%APP_DIR%go-core' -WindowStyle Hidden"
    ) else if exist "%APP_DIR%..\go-core\aibs_engine.exe" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%APP_DIR%..\go-core\aibs_engine.exe' -WorkingDirectory '%APP_DIR%..\go-core' -WindowStyle Hidden"
    )
)

:: 3. Ensure FastAPI Backend Core is Running on Port 8080
netstat -an | find ":8080 " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    echo [AI-BS] FastAPI Backend already active on port 8080.
) else (
    echo [AI-BS] Starting FastAPI Backend on port 8080...
    if exist "%APP_DIR%backend\AI_BS_Backend.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'AI_BS_Backend.py' -WorkingDirectory '%APP_DIR%backend' -WindowStyle Hidden"
    ) else if exist "%APP_DIR%..\backend\AI_BS_Backend.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'AI_BS_Backend.py' -WorkingDirectory '%APP_DIR%..\backend' -WindowStyle Hidden"
    )
)

:: 4. Ensure VST Bridge Daemon is Running on Port 8013
netstat -an | find ":8013 " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    echo [AI-BS] VST Bridge Daemon already active on port 8013.
) else (
    echo [AI-BS] Starting VST Bridge Daemon on port 8013...
    if exist "%APP_DIR%backend\aibs_vst_daemon.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_vst_daemon.py' -WorkingDirectory '%APP_DIR%backend' -WindowStyle Hidden"
    ) else if exist "%APP_DIR%..\backend\aibs_vst_daemon.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_vst_daemon.py' -WorkingDirectory '%APP_DIR%..\backend' -WindowStyle Hidden"
    )
)

:: 5. Ensure Social Feed Daemon is Running on Port 8006
netstat -an | find ":8006 " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    echo [AI-BS] Social Feed Daemon already active on port 8006.
) else (
    echo [AI-BS] Starting Social Feed Daemon on port 8006...
    if exist "%APP_DIR%backend\aibs_social_daemon.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_social_daemon.py' -WorkingDirectory '%APP_DIR%backend' -WindowStyle Hidden"
    ) else if exist "%APP_DIR%..\backend\aibs_social_daemon.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_social_daemon.py' -WorkingDirectory '%APP_DIR%..\backend' -WindowStyle Hidden"
    )
)

:: 6. Ensure Broadcast Engine Daemon is Running on Port 8005
netstat -an | find ":8005 " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    echo [AI-BS] Broadcast Engine Daemon already active on port 8005.
) else (
    echo [AI-BS] Starting Broadcast Engine Daemon on port 8005...
    if exist "%APP_DIR%backend\aibs_broadcast_daemon.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_broadcast_daemon.py' -WorkingDirectory '%APP_DIR%backend' -WindowStyle Hidden"
    ) else if exist "%APP_DIR%..\backend\aibs_broadcast_daemon.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'aibs_broadcast_daemon.py' -WorkingDirectory '%APP_DIR%..\backend' -WindowStyle Hidden"
    )
)

:: 7. Ensure Local Frontend Web Server is Running on Port 5173
netstat -an | find ":5173 " | find "LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    echo [AI-BS] Local Desktop Web Server already active on port 5173.
) else (
    echo [AI-BS] Starting Local Desktop Web Server...
    if exist "%APP_DIR%serve_desktop.py" (
        powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList 'serve_desktop.py 5173' -WorkingDirectory '%APP_DIR%' -WindowStyle Hidden"
    )
    ping 127.0.0.1 -n 3 >nul
)

:: 8. Launch Desktop Studio in Dedicated Application Window Mode
set "TARGET_URL=http://127.0.0.1:5173"
set "USER_DATA=%LOCALAPPDATA%\AI_BS_Studio\DesktopProfile"
set "MEDIA_FLAGS=--unsafely-treat-insecure-origin-as-secure=http://127.0.0.1:5173,http://localhost:5173"

if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
    echo [AI-BS] Launching Desktop Studio in Edge App Window...
    start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app=%TARGET_URL% --window-size=1600,1000 --user-data-dir="%USER_DATA%" %MEDIA_FLAGS%
) else if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" (
    echo [AI-BS] Launching Desktop Studio in Edge App Window...
    start "" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" --app=%TARGET_URL% --window-size=1600,1000 --user-data-dir="%USER_DATA%" %MEDIA_FLAGS%
) else if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
    echo [AI-BS] Launching Desktop Studio in Chrome App Window...
    start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app=%TARGET_URL% --window-size=1600,1000 --user-data-dir="%USER_DATA%" %MEDIA_FLAGS%
) else (
    echo [AI-BS] Launching Desktop Studio in Default Browser...
    start "" "%TARGET_URL%"
)

echo [AI-BS] Desktop Studio initialized successfully.
ping 127.0.0.1 -n 2 >nul
exit /b 0
