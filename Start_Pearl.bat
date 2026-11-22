@echo off
title Start Pearl Ecosystem (Background Resumption)
cd /d "%~dp0"
echo ========================================================
echo Starting Pearl Wallet and Resuming 24/7 Supervision...
echo ========================================================
"%~dp0pyppeteer_env\Scripts\python.exe" "%~dp0backend\core\unified_crypto_pearl_watchdog.py" start-pearl
echo.
echo [STATUS] Pearl has been started in the background.
echo The autonomous watchdog is keeping Pearl alive continuously.
pause
