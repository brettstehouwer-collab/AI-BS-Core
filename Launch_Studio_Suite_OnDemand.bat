@echo off
title AI-BS Studio & Broadcast Suite On-Demand
color 0E

echo ===================================================
echo   AI-BS BROADCAST & STUDIO ON-DEMAND LAUNCHER
echo ===================================================
echo.
set "BASE_DIR=C:\AI-BS\"

powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d %BASE_DIR%BroadcastStudioApp && npm run dev' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_broadcast_kernel.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_broadcast_kernel.log' -RedirectStandardError '%BASE_DIR%logs\aibs_broadcast_kernel.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_broadcast_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_broadcast_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_broadcast_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_social_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_social_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_social_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_overlay_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_overlay_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_overlay_daemon.err' -WindowStyle Hidden"
powershell -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%BASE_DIR%pyppeteer_env\Scripts\pythonw.exe' -ArgumentList 'aibs_vst_daemon.py' -WorkingDirectory '%BASE_DIR%backend' -RedirectStandardOutput '%BASE_DIR%logs\aibs_vst_daemon.log' -RedirectStandardError '%BASE_DIR%logs\aibs_vst_daemon.err' -WindowStyle Hidden"

echo Broadcast and Studio daemons engaged.
ping 127.0.0.1 -n 2 > nul
exit /b
