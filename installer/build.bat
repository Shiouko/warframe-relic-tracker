@echo off
REM Warframe Relic Tracker - Windows Build Script

echo =========================================
echo   Warframe Relic Tracker - Build Script
echo =========================================
echo.

REM Navigate to project root
cd /d "%~dp0\.."

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required but not found in PATH.
    echo Download from https://www.python.org/downloads/
    exit /b 1
)

REM Install dependencies
echo Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt 2>nul
python -m pip install pyinstaller

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build
echo.
echo Building standalone executable...
python -m PyInstaller ^
    installer\warframe-relic-tracker.spec ^
    --onefile ^
    --name RelicTracker ^
    --clean

if errorlevel 1 (
    echo.
    echo Build failed!
    exit /b 1
)

echo.
echo =========================================
echo   Build complete!
echo   Output: dist\RelicTracker.exe
echo =========================================
echo.
echo Run with: dist\RelicTracker.exe
echo The app will be available at http://127.0.0.1:8420
