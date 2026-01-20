@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run this script as administrator!
    pause
    exit /b 1
)
set EXE_DIR=%~dp0
if "%EXE_DIR:~-1%"=="\" set "EXE_DIR=%EXE_DIR:~0,-1%"
if not exist "%EXE_DIR%\MicroServiceLauncher.exe" (
    echo No executable found. Place MicroServiceLauncher.exe in script directory.
    pause
    exit /b 1
)
nssm install MicroserviceLauncher "%EXE_DIR%\MicroServiceLauncher.exe" --nssm
if %errorlevel% neq 0 (
    echo Failed to install service.
    pause
    exit /b %errorlevel%
)
nssm set MicroserviceLauncher AppDirectory "%EXE_DIR%"
nssm set MicroserviceLauncher Start SERVICE_AUTO_START
if not exist "%EXE_DIR%\logs" mkdir "%EXE_DIR%\logs" 2>nul
nssm set MicroserviceLauncher AppStdout "%EXE_DIR%\logs\microservice_launcher.out.log"
nssm set MicroserviceLauncher AppStderr "%EXE_DIR%\logs\microservice_launcher.err.log"
nssm start MicroserviceLauncher
if %errorlevel% neq 0 (
    echo Failed to start service.
    pause
    exit /b %errorlevel%
)
echo Service registered and started successfully.
pause
