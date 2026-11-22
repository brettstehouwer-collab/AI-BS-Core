@echo off
title AI-BS Unrestricted Studio
cd /d C:\AI-BS
echo Starting AI-BS Unrestricted Studio (Ollama + Diffusers SDXL)...
streamlit run apps/unrestricted_app.py --server.port 8501 --server.headless false
pause
