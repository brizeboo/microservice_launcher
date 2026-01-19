@echo off
cd /d "%~dp0\.."
:: Check for Admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~0' -Verb RunAs"
    exit
)

echo Registering Microservice Launcher Service...
python src\main.py install
if %errorlevel% neq 0 (
    echo Failed to register service. Ensure pywin32 is installed (pip install pywin32).
    pause
    exit /b %errorlevel%
)

echo Setting service to auto-start...
sc config MicroserviceLauncher start= auto

echo Starting service...
python src\main.py start
if %errorlevel% neq 0 (
    echo Failed to start service.
    pause
    exit /b %errorlevel%
)

echo Service registered and started successfully!
pause
