@echo off
title AI-BS Cymatics Drop Sniper & Watchdog
color 0B

echo ===================================================
echo     AI-BS ENTERPRISE CYMATICS DROP SNIPER
echo ===================================================
echo.
echo [*] Starting Watchdog Supervisor with 5-Channel Ingestion...
echo [*] Fail-Safe Audio Siren + Windows Toast Alerts + Auto-Cart Active.
echo.

:LOOP
"C:\AI-BS\pyppeteer_env\Scripts\python.exe" -u "C:\AI-BS\backend\aibs_drop_watchdog.py"
echo.
echo [!] Watchdog process exited. Restarting in 2 seconds...
timeout /t 2 /nobreak > nul
goto LOOP
