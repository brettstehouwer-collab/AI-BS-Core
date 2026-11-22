@echo off
title AI-BS Broadcast Daemon (Interactive Session)
color 0B
echo ============================================================
echo      AI-BS HARDWARE NVENC BROADCAST DAEMON (PORT 8005)
echo ============================================================
echo.
echo [1/2] Terminating any stale processes listening on Port 8005...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8005 ^| findstr LISTENING') do (
    echo Terminating PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak > nul

echo.
echo [2/2] Launching Broadcast Daemon (Port 8005)...
cd /d "C:\AI-BS\backend"
"C:\AI-BS\pyppeteer_env\Scripts\python.exe" aibs_broadcast_daemon.py
pause