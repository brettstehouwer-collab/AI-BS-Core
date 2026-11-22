@echo off
title AI-BS Mobile ADB Tunnel Initialization
color 0B

echo ========================================================
echo Booting AI-BS Mobile ADB Tunnel...
echo Establishing secure USB connection to Android Device...
echo ========================================================
echo.

set ADB_PATH="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"

echo [INFO] Checking for ADB executable...
if not exist %ADB_PATH% (
    echo [ERROR] ADB not found at %LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe
    echo Please install Android SDK Platform Tools or update your path.
    pause
    exit /b 1
)

echo [INFO] Restarting ADB server (just in case)...
%ADB_PATH% kill-server
%ADB_PATH% start-server

echo.
echo [INFO] Waiting for device...
%ADB_PATH% wait-for-device

echo [INFO] Device connected. Establishing reverse tunnels...

:: Reverse React Frontend
%ADB_PATH% reverse tcp:5173 tcp:5173
echo [SUCCESS] Reversed port 5173 (React Dashboard)

:: Reverse AI-BS API Backend
%ADB_PATH% reverse tcp:8000 tcp:8000
%ADB_PATH% reverse tcp:8080 tcp:8080
echo [SUCCESS] Reversed port 8000/8080 (Backend API)

:: Reverse Crypto Swarm Bot
%ADB_PATH% reverse tcp:8003 tcp:8003
echo [SUCCESS] Reversed port 8003 (Crypto Bot Telemetry)

:: Reverse ComfyUI
%ADB_PATH% reverse tcp:8189 tcp:8189
echo [SUCCESS] Reversed port 8189 (ComfyUI)

echo.
echo ========================================================
echo TUNNEL ESTABLISHED SUCCESSFULLY!
echo ========================================================
echo Open Chrome on your Android device and navigate to:
echo http://localhost:5173
echo.
echo You can now use the Chat interface directly on your phone!
echo Press any key to exit this window...
pause >nul
