@echo off
title AI-BS Autonomous 24/7 Crypto ^& Pearl Watchdog
cd /d "%~dp0"
echo ========================================================
echo Starting AI-BS Autonomous 24/7 Crypto ^& Pearl Watchdog...
echo - Crypto Trader Bot (Port 8007): Supervised (Zero Missed Triggers)
echo - Pearl Wallet ^& Watcher: Supervised (Unless stopped by user)
echo ========================================================
"%~dp0pyppeteer_env\Scripts\python.exe" "%~dp0backend\core\unified_crypto_pearl_watchdog.py"
pause
