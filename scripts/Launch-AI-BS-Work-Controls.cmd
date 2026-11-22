@echo off
setlocal
set "AIBS_WORK_PY=C:\Users\Administrator\AppData\Local\AI-BS\packaging_python_20261111_v03\pythonw.exe"
if not exist "%AIBS_WORK_PY%" (
    echo The verified native Qt interpreter is unavailable. No settings were changed.
    exit /b 1
)
"%AIBS_WORK_PY%" -I -B "%~dp0..\native_studio\work_controls_app.py"
exit /b %ERRORLEVEL%
