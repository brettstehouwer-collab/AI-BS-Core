@echo off
title AI-BS Mobile ADB Push & In-Place Installer
cd /d C:\AI-BS
powershell -ExecutionPolicy Bypass -File push_mobile_update.ps1
pause
