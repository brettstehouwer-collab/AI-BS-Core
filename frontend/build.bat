@echo off
REM AI-BS Frontend Build & Optimization Script for Windows
REM Usage: build.bat [package|analyze]

setlocal enabledelayedexpansion

set TARGET=%1
if "!TARGET!"=="" set TARGET=dry

echo.
echo ===================================================================
echo AI-BS Frontend Build Optimizer v1.0
echo ===================================================================
echo.

if "!TARGET!"=="package" (
    echo [1/3] Building React app...
    call npm run build
    if !errorlevel! neq 0 (
        echo ERROR: npm run build failed
        exit /b 1
    )
    
    echo.
    echo [2/3] Packaging Electron app...
    call npx electron-builder --win --config electron-builder.json
    if !errorlevel! neq 0 (
        echo ERROR: electron-builder failed
        exit /b 1
    )
    
    echo.
    echo [3/3] Optimizing build - removing locales and bloat...
    python scripts\optimize_build.py
    if !errorlevel! neq 0 (
        echo ERROR: optimize_build.py failed
        exit /b 1
    )
    
    echo.
    echo [SUCCESS] Optimized build ready in build-output/
    echo.
    
) else if "!TARGET!"=="dry" (
    echo [1/2] Building React app...
    call npm run build
    if !errorlevel! neq 0 (
        echo ERROR: npm run build failed
        exit /b 1
    )
    
    echo.
    echo [2/2] Packaging Electron app - no installer...
    call npx electron-builder --win --config electron-builder.json --dir
    if !errorlevel! neq 0 (
        echo ERROR: electron-builder failed
        exit /b 1
    )
    
    echo.
    echo [3/2] Optimizing build...
    python scripts\optimize_build.py
    
    echo.
    echo [SUCCESS] Test build ready in build-output/win-unpacked/
    echo Run: start build-output\win-unpacked\AI-BS Matrix.exe
    echo.
    
) else if "!TARGET!"=="analyze" (
    echo [1/1] Analyzing build size...
    call npm run analyze
    echo.
    echo Open dist-analyze/index.html in browser for detailed breakdown
    echo.
    
) else (
    echo Invalid target. Usage:
    echo   build.bat package    - Full build, optimize, create installer
    echo   build.bat dry        - Quick build test with optimization
    echo   build.bat analyze    - Detailed size analysis
    exit /b 1
)

echo Done!
