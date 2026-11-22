@echo off
title AI-BS Single Master 24/7 Auto-Heal Supervisor
cd /d "%~dp0"
echo ===================================================================
echo   AI-BS Single Master 24/7 Auto-Heal Supervisor (12 Core Pillars)
echo ===================================================================
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'C:\AI-BS\runtime\recovery-20261110\Scripts\python.exe' -ArgumentList '-u -B C:\AI-BS\scratch\aibs_24x7_supervisor.py' -WorkingDirectory 'C:\AI-BS\scratch' -WindowStyle Hidden"
echo [OK] Master 24/7 Auto-Heal Supervisor launched in background.
echo Telemetry: C:\AI-BS\saved_data\master_supervisor_status.json
timeout /t 2 /nobreak >nul

