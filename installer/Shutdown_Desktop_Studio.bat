@echo off
title AI-BS Studio Graceful Shutdown
color 0E

echo =========================================================
echo       AI-BS STUDIO GRACEFUL SHUTDOWN SEQUENCE
echo =========================================================
echo.

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo [1/3] Terminating local web servers on ports 5173 and 5174...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5173 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5174 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo [2/3] Terminating background Python daemons...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8088 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8005 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8013 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8006 " ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo [3/3] System state saved. All AI-BS studio processes stopped.
timeout /t 2 /nobreak >nul
exit /b 0
