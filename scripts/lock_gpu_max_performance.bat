@echo off
title AI-BS RTX 4090 Max Performance Clocks Lock
echo ==============================================================
echo   Enforcing Max Clocks & Disabling Power Saving Downclocking
echo ==============================================================
nvidia-smi -i 0 --lock-gpu-clocks=2550,2700
nvidia-smi -i 0 --lock-memory-clocks=10501,10501
echo.
echo Current Clocks and Telemetry:
nvidia-smi --query-gpu=clocks.gr,clocks.mem,power.draw,temperature.gpu --format=csv
echo ==============================================================
