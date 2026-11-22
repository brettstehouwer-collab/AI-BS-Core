@echo off
setlocal
set "AIBS_WORK_TOOLS=%~dp0native_studio\releases\v5.329.144\AI_BS_Studio\AI_BS_Studio.exe"
if not exist "%AIBS_WORK_TOOLS%" (
  echo AI-BS work controls 5.329.144 are missing from:
  echo %AIBS_WORK_TOOLS%
  pause
  exit /b 1
)
start "AI-BS Work Controls" /D "%~dp0" "%AIBS_WORK_TOOLS%" --work-controls
exit /b %errorlevel%
