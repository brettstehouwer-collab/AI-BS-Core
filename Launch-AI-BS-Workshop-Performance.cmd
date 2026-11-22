@echo off
setlocal
set AI_BS_NATIVE_MANAGE_DAEMONS=false
set AI_BS_NATIVE_BACKGROUND_UPDATES=false
set AI_BS_NATIVE_EXIT_PROCESS_CLEANUP=false
if not exist "%~dp0.venv\Scripts\python.exe" exit /b 1
if "%~1"=="" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0engine\tools\play_and_measure_workshop.py" --play
) else (
  "%~dp0.venv\Scripts\python.exe" "%~dp0engine\tools\play_and_measure_workshop.py" --play --project "%~1"
)
set "AIBS_REVIEW_EXIT=%ERRORLEVEL%"
echo Review finished with code %AIBS_REVIEW_EXIT%. Reports and separate review save are retained.
pause
exit /b %AIBS_REVIEW_EXIT%
