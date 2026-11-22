@echo off
title AI-BS Matrix - Quick Standalone Windows Exe Builder
color 0E

echo ===============================================================================
echo            AI-BS MATRIX - STANDALONE WINDOWS EXE BUILDER
echo              [Compiles Vite + Packages Standalone Desktop App]
echo ===============================================================================
echo.

set "BASE_DIR=%~dp0"
set "FRONTEND_DIR=%BASE_DIR%frontend"

echo [1/3] Navigating to Frontend Directory...
cd /d "%FRONTEND_DIR%"

echo.
echo [2/3] Compiling Production Bundle (Vite Build)...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Vite build failed! Check logs above.
    pause
    exit /b 1
)

echo.
echo [3/3] Packaging Unpacked Standalone Exe (desktop-build/win-unpacked)...
call npx electron-builder --win --dir
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Electron packaging failed! Check logs above.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo  BUILD COMPLETE!
echo.
echo  Standalone Exe Location:
echo  "%FRONTEND_DIR%\desktop-build\win-unpacked\AI-BS Matrix.exe"
echo ===============================================================================
echo.
choice /m "Would you like to launch the newly built standalone app right now"
if %ERRORLEVEL% equ 1 (
    start "" "%FRONTEND_DIR%\desktop-build\win-unpacked\AI-BS Matrix.exe"
)
exit
