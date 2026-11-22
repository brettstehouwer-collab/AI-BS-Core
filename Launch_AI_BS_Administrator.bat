@echo off
title Launch AI-BS Sovereign Ecosystem (Administrator)
color 0A

:: Self-elevate to Administrator if not already elevated
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ELEVATION REQUIRED] Requesting Windows Administrator privileges...
    powershell -ExecutionPolicy Bypass -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Run the Admin-level startup script
powershell -ExecutionPolicy Bypass -NoExit -File "C:\AI-BS\scripts\Start-AIBSSovereignAdmin.ps1"
