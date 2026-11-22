@echo off
setlocal DisableDelayedExpansion
if not exist "%~dp0..\Install_October7_DAW.bat" (
    echo [ERROR] The repaired root installer is missing. No installation was attempted.
    exit /b 1
)
call "%~dp0..\Install_October7_DAW.bat"
exit /b %ERRORLEVEL%
