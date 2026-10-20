@echo off
title AI-BS Streaming Firewall Port Opener
color 0B

echo ================================================================
echo   AI-BS SOVEREIGN STUDIO - STREAMING FIREWALL PORTS OPENER
echo ================================================================
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0open_streaming_firewall_ports.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to configure Windows Defender Firewall rules.
    echo Please ensure this command is run with Administrator privileges.
) else (
    echo [SUCCESS] Windows Defender Firewall rules successfully configured.
)

echo.
