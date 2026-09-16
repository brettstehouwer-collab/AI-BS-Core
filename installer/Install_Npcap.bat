@echo off
title AI-BS Npcap NDIS 6 Kernel Driver Installer
color 0B

echo =======================================================
echo     AI-BS NPCAP NDIS 6 KERNEL DRIVER INSTALLATION
echo =======================================================
echo.
echo Launching elevated installer for Npcap v1.88...
echo.
echo IMPORTANT SETUP INSTRUCTIONS IN THE WIZARD:
echo   1. Check: [x] Install Npcap in WinPcap API-compatible Mode
echo   2. (Optional) Check: [x] Support raw 802.11 traffic for wireless adapters
echo   3. Complete the installation.
echo.

powershell -ExecutionPolicy Bypass -Command Start-Process -FilePath '%~dp0npcap-1.88.exe' -Verb RunAs

echo Installer launched. Once finished, restart the AI-BS backend or refresh to engage L2/L3 capture.
pause
