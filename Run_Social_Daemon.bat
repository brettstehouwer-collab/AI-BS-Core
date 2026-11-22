@echo off
title AI-BS Social Daemon (Port 8006)
color 0D
echo ============================================================
echo       AI-BS SOCIAL HUB & TWITCH IRC DAEMON (PORT 8006)
echo ============================================================
echo.
echo [1/2] Reclaiming Port 8006...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8006 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak > nul

echo [2/2] Starting AI-BS Social Daemon...
cd /d "C:\AI-BS\backend"
"C:\AI-BS\pyppeteer_env\Scripts\python.exe" aibs_social_daemon.py
pause