@echo off
cd /d "%~dp0"
set VENV_DIR=..\.venv

echo ==========================================
echo      ServiceLauncher Build Script
echo ==========================================

REM 1. Check/Create Virtual Environment
if not exist %VENV_DIR% (
    echo [INFO] Creating virtual environment...
    python -m venv %VENV_DIR%
) else (
    echo [INFO] Virtual environment found.
)

REM 2. Install Dependencies
echo [INFO] Installing dependencies...
%VENV_DIR%\Scripts\python -m pip install --upgrade pip
%VENV_DIR%\Scripts\pip install -r ..\requirements.txt
%VENV_DIR%\Scripts\pip install pyinstaller

REM 3. Clean previous builds
echo [INFO] Cleaning up previous build artifacts...
if exist build rmdir /s /q build
REM if exist dist rmdir /s /q dist
REM Do not delete spec file as we have customized it
REM if exist *.spec del *.spec

REM 4. Run PyInstaller
echo [INFO] Building executable with PyInstaller...
REM Using existing spec file for advanced configuration (version info, upx disabled)
%VENV_DIR%\Scripts\pyinstaller --clean ServiceLauncher.spec

REM 5. Report Success
if exist dist\ServiceLauncher_v2.exe (
    echo.
    echo [SUCCESS] Build completed successfully!
    echo [OUTPUT] %~dp0dist\ServiceLauncher_v2.exe
) else (
    echo.
    echo [ERROR] Build failed. Check the output above for errors.
)

REM pause
