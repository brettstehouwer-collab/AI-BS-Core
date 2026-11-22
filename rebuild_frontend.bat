@echo off
ECHO =================================================
ECHO " CLEANING & REBUILDING AI-BS FRONTEND"
ECHO =================================================

REM Set the frontend directory. Assumes this script is run from the project root.
set "FRONTEND_DIR=%~dp0frontend"

ECHO Navigating to frontend directory: %FRONTEND_DIR%
cd /D "%FRONTEND_DIR%"

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Could not navigate to the frontend directory.
    pause
    exit /b
)

ECHO [1/3] Cleaning old build artifacts...

IF EXIST "build-output" (
    ECHO      - Removing 'build-output' directory...
    rmdir /s /q "build-output"
)
IF EXIST "release" (
    ECHO      - Removing 'release' directory...
    rmdir /s /q "release"
)
ECHO [SUCCESS] Old artifacts cleaned.

ECHO.
ECHO [2/3] Installing npm dependencies to ensure freshness...
call npm install

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] 'npm install' failed. Please check the logs above for errors.
    pause
    exit /b
)

ECHO.
ECHO [3/4] Building React frontend (Vite)...
call npm run build

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] 'npm run build' failed.
    pause
    exit /b
)

ECHO.
ECHO [4/4] Packaging new Electron application...
ECHO Running build without code signing to prevent resource lock...
ECHO Disabling compression to prevent CPU hang on large package...
call npx electron-builder --win --publish never --config.win.compression=store --config electron-builder.json

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] 'electron-builder' failed. The build process was unsuccessful.
    pause
    exit /b
)

ECHO.
ECHO =================================================
ECHO  FRONTEND REBUILD COMPLETE!
ECHO =================================================
pause