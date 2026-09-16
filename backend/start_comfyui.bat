@echo off
echo Starting ComfyUI...
cd /d "%~dp0..\ComfyUI"
.\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build
pause

