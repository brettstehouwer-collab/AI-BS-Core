@echo off
title AI-BS Mobile App Expo Tunnel (Port 8081)
color 0b
echo =====================================================================
echo           AI-BS Sovereign Mobile Studio - Expo Tunnel
echo =====================================================================
echo.
echo Starting Expo SDK 57 Metro bundler with @expo/ngrok tunnel...
echo Share the generated QR code or exp:// link with friends on iPhone!
echo.
cd /d "C:\AI-BS\mobile-app"
npm run tunnel
pause
