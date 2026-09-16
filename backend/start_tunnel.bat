@echo off
echo ==============================================
echo Bullshit AI - Secure Remote Ngrok Tunnel
echo ==============================================
echo Launching local backend server on port 8000...
start cmd /k "cd /d .. && start.bat"

echo Waiting for backend to spin up...
timeout /t 5 /nobreak > nul


echo Launching Ngrok Secure Tunnel on port 8000 using static domain...
echo.
echo Binding to: https://turbine-jitters-chill.ngrok-free.dev
echo.
ngrok http --domain=turbine-jitters-chill.ngrok-free.dev 8000
pause

