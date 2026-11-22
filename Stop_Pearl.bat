@echo off
title Stop Pearl Ecosystem (User Intentional Stop)
cd /d "%~dp0"
echo ========================================================
echo Stopping Pearl Wallet and Background Watchers...
echo (Marking Pearl as stopped by user so watchdog will NOT restart)
echo ========================================================
"%~dp0pyppeteer_env\Scripts\python.exe" "%~dp0backend\core\unified_crypto_pearl_watchdog.py" stop-pearl
echo.
echo [STATUS] Pearl has been stopped.
echo The autonomous watchdog will leave Pearl stopped until you run Start_Pearl.bat.
pause
