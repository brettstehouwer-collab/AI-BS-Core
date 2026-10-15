@echo off
title Stehouwer Publishing Broadcast Studio - Standalone Native Builder
color 0B

echo ===============================================================================
echo       STEHOUWER PUBLISHING BROADCAST STUDIO - STANDALONE EXE BUILDER
echo            [Compiles Pure Native Windows PyQt6 / Direct2D Binary]
echo ===============================================================================
echo.

set "PYTHON_EXE=C:\AI-BS\pyppeteer_env\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python environment not found at %PYTHON_EXE%!
    pause
    exit /b 1
)

set "ICON_PATH=C:\AI-BS\installer\app_icon.ico"
if not exist "%ICON_PATH%" (
    set "ICON_PATH=C:\AI-BS\BroadcastStudioApp\build\icon.ico"
)

echo [1/2] Compiling Standalone Native Windows Binary with PyInstaller...
"%PYTHON_EXE%" -m PyInstaller ^
    --name="Stehouwer-Publishing-Broadcast-Studio" ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --icon="%ICON_PATH%" ^
    --paths="C:\AI-BS" ^
    --paths="C:\AI-BS\native_studio" ^
    --paths="C:\AI-BS\backend" ^
    --distpath="C:\AI-BS\dist_native" ^
    --workpath="C:\AI-BS\build_native" ^
    "C:\AI-BS\native_studio\stehouwer_broadcast_studio.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] PyInstaller compilation failed! Check logs above.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo  BUILD COMPLETE! Pure Native Windows Binary Generated:
echo  "C:\AI-BS\dist_native\Stehouwer-Publishing-Broadcast-Studio\Stehouwer-Publishing-Broadcast-Studio.exe"
echo ===============================================================================
echo.
pause
