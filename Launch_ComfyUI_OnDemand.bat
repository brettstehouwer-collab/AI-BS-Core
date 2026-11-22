@echo off
title AI-BS ComfyUI On-Demand Launcher
color 0D

echo ===================================================
echo        AI-BS COMFYUI ON-DEMAND LAUNCHER
echo ===================================================
echo.
echo Launching ComfyUI Renderer on Port 8189...

cd /d C:\AI-BS\ComfyUI
call run_nvidia_gpu.bat

exit /b
