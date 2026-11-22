@echo off
rem Start signaling only for this explicitly requested streaming session.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-UnrealPixelStreaming.ps1"
exit /b %errorlevel%
