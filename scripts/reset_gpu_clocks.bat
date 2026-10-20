@echo off
title AI-BS Reset GPU Clocks to Default Auto
echo Resetting RTX 4090 clocks to dynamic default management...
nvidia-smi -i 0 --reset-gpu-clocks
nvidia-smi -i 0 --reset-memory-clocks
echo Done.
